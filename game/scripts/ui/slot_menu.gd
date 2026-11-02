class_name SlotMenu
extends Menu
## Save slot picker. Modes: "new" (start game), "load", "save" (in-game, safe rooms), "manage" (export/import/delete).
## Every overwrite or delete asks for confirmation.

var mode := "load"
var info: Label

func build() -> void:
	var titles := {"new": "NEW GAME - CHOOSE A SLOT", "load": "LOAD GAME", "save": "SAVE GAME", "manage": "MANAGE SAVES",
		"ngplus": "NEW GAME+ - CHOOSE A FINISHED SAVE"}
	var c := make_frame(titles.get(mode, "SAVES"), Vector2(440, 0))
	var first: Control = null
	for slot in range(1, SaveService.SLOTS + 1):
		var si := SaveService.slot_info(slot)
		var text := "Slot %d   -   empty" % slot
		if not si.is_empty():
			text = "Slot %d   Lv %d   %s   %s   %s%s" % [slot, int(si.level), Content.room(si.room).get("name", si.room), UIKit.fmt_time(float(si.playtime)), Time.get_datetime_string_from_unix_time(int(si.timestamp)).replace("T", " ").substr(0, 16), "  (recovered backup)" if si.recovered else ""]
		var b := UIKit.button(text, func(): _pick(slot), 420)
		if mode == "load" and si.is_empty():
			b.disabled = true
		if mode == "ngplus":
			b.disabled = si.is_empty() or not bool(si.get("complete", false))
			if not si.is_empty() and int(si.get("ng_cycle", 0)) > 0:
				b.text += "   NG+%d" % int(si.ng_cycle)
		c.add_child(b)
		if first == null and not b.disabled:
			first = b
		if mode == "manage" and not si.is_empty():
			var row := UIKit.hbox(4)
			row.add_child(UIKit.label("     ", UIKit.DIM))
			row.add_child(UIKit.button("Export", func(): _export(slot), 80))
			row.add_child(UIKit.button("Delete", func(): _delete(slot), 80))
			c.add_child(row)
	if mode == "manage":
		var imp := UIKit.hbox(4)
		for slot in range(1, SaveService.SLOTS + 1):
			imp.add_child(UIKit.button("Import to %d" % slot, func(): _import(slot), 100))
		c.add_child(imp)
		var note := "Browser saves live in this browser's storage (cleared by private mode or clearing site data). Export a backup file to be safe." if OS.has_feature("web") else "Saves are stored in: " + ProjectSettings.globalize_path("user://")
		c.add_child(UIKit.wrap_label(note, 420, UIKit.DIM))
	info = UIKit.wrap_label("Saves that reached the ending can start New Game+." if mode == "ngplus" else "", 420, UIKit.MUSTARD)
	c.add_child(info)
	var back := UIKit.button("Back", close, 120)
	c.add_child(back)
	first_focus = first if first else back
	if not SaveService.import_finished.is_connected(_on_import):
		SaveService.import_finished.connect(_on_import)

func _pick(slot: int) -> void:
	var has := SaveService.has_save(slot)
	match mode:
		"new":
			if has:
				var yes: bool = await ConfirmMenu.ask(host, "Slot %d already has a save. Overwrite it with a new game? This cannot be undone." % slot)
				if not yes:
					return
			SaveService.current_slot = slot
			host.start_new_game(slot)
		"load":
			if not has:
				return
			if SaveService.load_game(slot):
				host.start_loaded_game()
			else:
				info.text = SaveService.last_error
		"save":
			if has and slot != SaveService.current_slot:
				var yes2: bool = await ConfirmMenu.ask(host, "Overwrite the save in slot %d?" % slot)
				if not yes2:
					return
			if SaveService.save_game(slot):
				Audio.sfx("save")
				info.text = "Saved to slot %d." % slot
				await get_tree().create_timer(0.3).timeout
				rebuild()
			else:
				info.text = "Save failed: " + SaveService.last_error
		"manage":
			info.text = "Choose Export or Delete below a slot."
		"ngplus":
			if not has:
				return
			var ok: bool = await ConfirmMenu.ask(host, "Start New Game+ in slot %d? You keep your level, stats, techniques, gear, bag and cash. The story restarts with tougher crews, and this slot's finished save is replaced (the previous save stays as the slot's backup)." % slot)
			if not ok:
				return
			if SaveService.load_game(slot):
				host.start_new_game_plus(slot)
			else:
				info.text = SaveService.last_error

func _export(slot: int) -> void:
	var r := SaveService.export_slot(slot)
	info.text = ("Exported: " + r) if r != "" else "Export failed."

func _delete(slot: int) -> void:
	var yes: bool = await ConfirmMenu.ask(host, "Delete slot %d permanently?" % slot)
	if yes:
		SaveService.delete_slot(slot)
		rebuild()

func _import(slot: int) -> void:
	if SaveService.has_save(slot):
		var yes: bool = await ConfirmMenu.ask(host, "Importing replaces slot %d (a backup copy is kept). Continue?" % slot)
		if not yes:
			return
	info.text = SaveService.begin_import(slot)

func _on_import(ok: bool, msg: String) -> void:
	if not is_instance_valid(self) or not is_inside_tree():
		return
	info.text = msg
	if ok:
		await get_tree().create_timer(0.5).timeout
		rebuild()
