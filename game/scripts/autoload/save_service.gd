extends Node
## Versioned save slots with backup + corruption recovery, and JSON export/import.
## Desktop: user:// data dir. Browser: IndexedDB-backed user:// (persists unless private mode/cleared).

signal saved(slot: int)
signal save_failed(message: String)
signal import_finished(ok: bool, message: String)

const SAVE_VERSION := 2
const SLOTS := 3
const MAX_BYTES := 262144
const GAME_VERSION := "1.0.0"

var current_slot := 1
var last_error := ""

func slot_path(slot: int) -> String:
	return "user://save_%d.json" % slot

func backup_path(slot: int) -> String:
	return "user://save_%d.bak" % slot

func has_save(slot: int) -> bool:
	return FileAccess.file_exists(slot_path(slot)) or FileAccess.file_exists(backup_path(slot))

func any_save() -> bool:
	for i in range(1, SLOTS + 1):
		if has_save(i):
			return true
	return false

func most_recent_slot() -> int:
	var best := 0
	var best_t := -1.0
	for i in range(1, SLOTS + 1):
		var info := slot_info(i)
		if not info.is_empty() and float(info.get("timestamp", 0)) > best_t:
			best_t = float(info.get("timestamp", 0))
			best = i
	return best

## Lightweight summary for the slot picker. Empty dict if no readable save.
func slot_info(slot: int) -> Dictionary:
	var d := _read_valid(slot)
	if d.is_empty():
		return {}
	var p: Dictionary = d.get("data", {}).get("player", {})
	var w: Dictionary = d.get("data", {}).get("world", {})
	var s: Dictionary = d.get("data", {}).get("story", {})
	return {
		"timestamp": float(d.get("timestamp", 0)), "level": int(p.get("level", 1)), "cash": int(p.get("cash", 0)),
		"room": str(w.get("room", "")), "stage": str(s.get("stage", "")),
		"playtime": float(d.get("data", {}).get("stats", {}).get("playtime", 0.0)),
		"recovered": bool(d.get("_recovered", false))
	}

func build_payload() -> Dictionary:
	return {
		"game": "backstreet_oath", "version": SAVE_VERSION, "game_version": GAME_VERSION,
		"timestamp": Time.get_unix_time_from_system(), "data": GameState.to_dict()
	}

## Writes the current GameState to a slot. Previous good save becomes the .bak.
func save_game(slot: int = -1) -> bool:
	if slot < 0:
		slot = current_slot
	var payload := build_payload()
	var text := JSON.stringify(payload, "", false)
	if text.length() > MAX_BYTES:
		return _fail("Save data too large.")
	var path := slot_path(slot)
	var tmp := path + ".tmp"
	var f := FileAccess.open(tmp, FileAccess.WRITE)
	if f == null:
		return _fail("Could not write save file (%s)." % error_string(FileAccess.get_open_error()))
	f.store_string(text)
	f.close()
	# verify the temp file before replacing anything
	var check := FileAccess.get_file_as_string(tmp)
	if check != text:
		return _fail("Save verification failed.")
	var dir := DirAccess.open("user://")
	if dir == null:
		return _fail("Could not open save directory.")
	if FileAccess.file_exists(path):
		if FileAccess.file_exists(backup_path(slot)):
			dir.remove(backup_path(slot).get_file())
		dir.rename(path.get_file(), backup_path(slot).get_file())
	var err := dir.rename(tmp.get_file(), path.get_file())
	if err != OK:
		return _fail("Could not finalize save (%s)." % error_string(err))
	current_slot = slot
	saved.emit(slot)
	return true

func _fail(msg: String) -> bool:
	last_error = msg
	push_warning("SaveService: " + msg)
	save_failed.emit(msg)
	return false

func load_game(slot: int) -> bool:
	var d := _read_valid(slot)
	if d.is_empty():
		last_error = "No readable save in slot %d." % slot
		return false
	GameState.from_dict(d.data)
	current_slot = slot
	return true

func delete_slot(slot: int) -> void:
	var dir := DirAccess.open("user://")
	if dir == null:
		return
	for p in [slot_path(slot), backup_path(slot)]:
		if FileAccess.file_exists(p):
			dir.remove(p.get_file())

## Reads the slot, falling back to the backup if the main file is corrupt.
func _read_valid(slot: int) -> Dictionary:
	var d := _parse_file(slot_path(slot))
	if d.is_empty():
		d = _parse_file(backup_path(slot))
		if not d.is_empty():
			d["_recovered"] = true
	return d

func _parse_file(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null or f.get_length() > MAX_BYTES:
		return {}
	var text := f.get_as_text()
	f.close()
	return validate_payload_text(text)

## Parses + validates + migrates a save payload. Returns {} if unusable.
func validate_payload_text(text: String) -> Dictionary:
	if text.length() == 0 or text.length() > MAX_BYTES:
		return {}
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {}
	var d: Dictionary = parsed
	if d.get("game", "") != "backstreet_oath":
		return {}
	var v := int(d.get("version", 0))
	if v < 1 or v > SAVE_VERSION:
		return {}
	if typeof(d.get("data")) != TYPE_DICTIONARY:
		return {}
	if v < SAVE_VERSION:
		d = migrate(d)
	var data: Dictionary = d.data
	for key in ["player", "story", "world"]:
		if typeof(data.get(key)) != TYPE_DICTIONARY:
			return {}
	return d

## v1 -> v2: v1 stored "quest_flags" at the story root instead of "quests" and had no mastery/upgrades.
func migrate(d: Dictionary) -> Dictionary:
	var v := int(d.get("version", 1))
	if v == 1:
		var story: Dictionary = d.data.get("story", {})
		if story.has("quest_flags") and not story.has("quests"):
			story["quests"] = story["quest_flags"]
			story.erase("quest_flags")
		var p: Dictionary = d.data.get("player", {})
		if not p.has("mastery"):
			p["mastery"] = {}
		if not p.has("upgrades"):
			p["upgrades"] = {}
		d["version"] = 2
	return d

# ---------------------------------------------------------------- export / import
func export_text(slot: int) -> String:
	var path := slot_path(slot)
	if not FileAccess.file_exists(path):
		return ""
	return FileAccess.get_file_as_string(path)

## Exports a slot. Web: browser download. Desktop: writes to user://exports and returns the absolute path.
func export_slot(slot: int) -> String:
	var text := export_text(slot)
	if text == "":
		return ""
	var fname := "backstreet_oath_slot%d_%s.json" % [slot, Time.get_datetime_string_from_system().replace(":", "-")]
	if OS.has_feature("web"):
		JavaScriptBridge.download_buffer(text.to_utf8_buffer(), fname, "application/json")
		return fname
	DirAccess.make_dir_recursive_absolute("user://exports")
	var p := "user://exports/" + fname
	var f := FileAccess.open(p, FileAccess.WRITE)
	if f == null:
		return ""
	f.store_string(text)
	f.close()
	return ProjectSettings.globalize_path(p)

## Imports save text into a slot. Backs up whatever is in the slot first.
func import_text(text: String, slot: int) -> bool:
	var d := validate_payload_text(text)
	if d.is_empty():
		import_finished.emit(false, "That file is not a valid Backstreet Oath save.")
		return false
	var dir := DirAccess.open("user://")
	if FileAccess.file_exists(slot_path(slot)) and dir:
		var stamp := str(int(Time.get_unix_time_from_system()))
		dir.copy(slot_path(slot), "user://save_%d_before_import_%s.json" % [slot, stamp])
	var f := FileAccess.open(slot_path(slot), FileAccess.WRITE)
	if f == null:
		import_finished.emit(false, "Could not write the save slot.")
		return false
	f.store_string(JSON.stringify(d, "", false))
	f.close()
	import_finished.emit(true, "Save imported into slot %d." % slot)
	return true

var _web_import_slot := 1
var _web_poll := 0.0

## Desktop: looks for user://import/save.json (documented). Web: opens the browser file picker.
func begin_import(slot: int) -> String:
	_web_import_slot = slot
	if OS.has_feature("web"):
		JavaScriptBridge.eval("""
			window.__bo_import = null;
			(function(){
				var i = document.createElement('input');
				i.type = 'file'; i.accept = '.json,application/json';
				i.onchange = function(){
					var f = i.files[0]; if (!f) { window.__bo_import = ''; return; }
					if (f.size > 262144) { window.__bo_import = ''; return; }
					var r = new FileReader();
					r.onload = function(){ window.__bo_import = String(r.result); };
					r.onerror = function(){ window.__bo_import = ''; };
					r.readAsText(f);
				};
				i.click();
			})();
		""", true)
		_web_poll = 60.0
		set_process(true)
		return "Choose a save file in the browser dialog..."
	var p := "user://import/save.json"
	DirAccess.make_dir_recursive_absolute("user://import")
	if not FileAccess.file_exists(p):
		return "Place your exported save at:\n" + ProjectSettings.globalize_path(p) + "\nthen choose Import again."
	var ok := import_text(FileAccess.get_file_as_string(p), slot)
	if ok:
		DirAccess.open("user://import").rename("save.json", "save_imported_%d.json" % int(Time.get_unix_time_from_system()))
	return "Imported into slot %d." % slot if ok else "Import failed: not a valid save."

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_process(false)

func _process(delta: float) -> void:
	_web_poll -= delta
	if _web_poll <= 0.0:
		set_process(false)
		return
	var v = JavaScriptBridge.eval("window.__bo_import", true)
	if v == null:
		return
	set_process(false)
	var text := str(v)
	JavaScriptBridge.eval("window.__bo_import = null;", true)
	if text == "":
		import_finished.emit(false, "Import cancelled.")
		return
	import_text(text, _web_import_slot)
