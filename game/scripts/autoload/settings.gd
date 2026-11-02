extends Node
## Player options and input bindings. Persisted to user://settings.cfg (separate from saves).
## All gameplay commands live in Godot's InputMap; game logic only reads action names.

signal changed

const PATH := "user://settings.cfg"
const GAME_ACTIONS := ["move_left", "move_right", "move_up", "move_down", "punch", "kick", "jump", "guard", "interact", "run", "status", "pause"]
const ACTION_LABELS := {
	"move_left": "Move Left", "move_right": "Move Right", "move_up": "Move Up (depth)", "move_down": "Move Down (depth)",
	"punch": "Punch / Confirm", "kick": "Kick", "jump": "Jump", "guard": "Guard", "interact": "Grab / Talk / Throw",
	"run": "Run (hold)", "status": "Status / Inventory", "pause": "Pause"
}
# Default bindings: keyboard physical keycodes (two slots) + gamepad buttons / axes.
const DEFAULT_KEYS := {
	"move_left": [KEY_A, KEY_LEFT], "move_right": [KEY_D, KEY_RIGHT],
	"move_up": [KEY_W, KEY_UP], "move_down": [KEY_S, KEY_DOWN],
	"punch": [KEY_J, KEY_Z], "kick": [KEY_K, KEY_X], "jump": [KEY_SPACE, KEY_C],
	"guard": [KEY_L, KEY_V], "interact": [KEY_E, KEY_F], "run": [KEY_SHIFT, KEY_B],
	"status": [KEY_TAB, KEY_I], "pause": [KEY_ESCAPE, KEY_P]
}
const DEFAULT_PAD := {
	"move_left": [JOY_BUTTON_DPAD_LEFT], "move_right": [JOY_BUTTON_DPAD_RIGHT],
	"move_up": [JOY_BUTTON_DPAD_UP], "move_down": [JOY_BUTTON_DPAD_DOWN],
	"punch": [JOY_BUTTON_X], "kick": [JOY_BUTTON_Y], "jump": [JOY_BUTTON_A],
	"guard": [JOY_BUTTON_LEFT_SHOULDER], "interact": [JOY_BUTTON_B], "run": [JOY_BUTTON_RIGHT_SHOULDER],
	"status": [JOY_BUTTON_BACK], "pause": [JOY_BUTTON_START]
}
const DEFAULT_AXES := {
	"move_left": [[JOY_AXIS_LEFT_X, -1.0]], "move_right": [[JOY_AXIS_LEFT_X, 1.0]],
	"move_up": [[JOY_AXIS_LEFT_Y, -1.0]], "move_down": [[JOY_AXIS_LEFT_Y, 1.0]],
	"guard": [[JOY_AXIS_TRIGGER_LEFT, 1.0]], "run": [[JOY_AXIS_TRIGGER_RIGHT, 1.0]]
}

var master_volume := 0.8
var music_volume := 0.7
var sfx_volume := 0.85
var screen_shake := 1.0          # 0 off, 0.5 low, 1 full
var flash := 1.0                 # 0 off .. 1 full hit flash / screen flash
var text_speed := 1              # 0 slow, 1 normal, 2 fast, 3 instant
var difficulty := "normal"       # "normal" or "relaxed"
var large_text := false
var deadzone := 0.25
var fullscreen := false
var touch_controls := "auto"     # auto / on / off
var show_hints := true
var effects := "full"            # "full" or "reduced" (fewer particles, no cast shadows/reflections/ambient)
var cinematic_bars := true
var show_fps := false
var bindings: Dictionary = {}    # action -> {"keys": [...], "pad": [...]}

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_reset_bindings_to_default()
	load_settings()
	_ensure_ui_actions()
	apply_input_map()
	apply_display()

func _reset_bindings_to_default() -> void:
	bindings.clear()
	for a in GAME_ACTIONS:
		bindings[a] = {"keys": DEFAULT_KEYS.get(a, []).duplicate(), "pad": DEFAULT_PAD.get(a, []).duplicate()}

func reset_bindings() -> void:
	_reset_bindings_to_default()
	apply_input_map()
	save_settings()

func apply_input_map() -> void:
	for a in GAME_ACTIONS:
		if InputMap.has_action(a):
			InputMap.erase_action(a)
		InputMap.add_action(a, deadzone if a.begins_with("move_") else 0.45)
		var b: Dictionary = bindings.get(a, {})
		for kc in b.get("keys", []):
			var ev := InputEventKey.new()
			ev.physical_keycode = int(kc)
			InputMap.action_add_event(a, ev)
		for btn in b.get("pad", []):
			var jb := InputEventJoypadButton.new()
			jb.button_index = int(btn)
			jb.device = -1
			InputMap.action_add_event(a, jb)
		for ax in DEFAULT_AXES.get(a, []):
			var jm := InputEventJoypadMotion.new()
			jm.axis = ax[0]
			jm.axis_value = ax[1]
			jm.device = -1
			InputMap.action_add_event(a, jm)
	for ui in ["ui_left", "ui_right", "ui_up", "ui_down"]:
		InputMap.action_set_deadzone(ui, maxf(deadzone, 0.3))
	changed.emit()

func _ensure_ui_actions() -> void:
	# Menus are fully keyboard/controller navigable: add WASD + J/E confirm, K/Backspace back.
	var extra := {
		"ui_left": [KEY_A], "ui_right": [KEY_D], "ui_up": [KEY_W], "ui_down": [KEY_S],
		"ui_accept": [KEY_J, KEY_E], "ui_cancel": [KEY_K, KEY_BACKSPACE]
	}
	for a in extra:
		for kc in extra[a]:
			var ev := InputEventKey.new()
			ev.physical_keycode = kc
			if not InputMap.action_has_event(a, ev):
				InputMap.action_add_event(a, ev)
	# Controller: A confirm, B back (Godot defaults), plus left stick for navigation.
	var axes := {"ui_left": [JOY_AXIS_LEFT_X, -1.0], "ui_right": [JOY_AXIS_LEFT_X, 1.0], "ui_up": [JOY_AXIS_LEFT_Y, -1.0], "ui_down": [JOY_AXIS_LEFT_Y, 1.0]}
	for a in axes:
		var jm := InputEventJoypadMotion.new()
		jm.axis = axes[a][0]
		jm.axis_value = axes[a][1]
		if not InputMap.action_has_event(a, jm):
			InputMap.action_add_event(a, jm)
	for pair in [["ui_page_up", JOY_BUTTON_LEFT_SHOULDER], ["ui_page_down", JOY_BUTTON_RIGHT_SHOULDER]]:
		var jb := InputEventJoypadButton.new()
		jb.button_index = pair[1]
		if not InputMap.action_has_event(pair[0], jb):
			InputMap.action_add_event(pair[0], jb)
	for pair in [["ui_page_up", KEY_Q], ["ui_page_down", KEY_R]]:
		var ke := InputEventKey.new()
		ke.physical_keycode = pair[1]
		if not InputMap.action_has_event(pair[0], ke):
			InputMap.action_add_event(pair[0], ke)

## Rebind: replace slot of an action with a new event (key or pad button). Resolves conflicts by swapping.
func rebind(action: String, event: InputEvent, slot: int = 0) -> void:
	if not bindings.has(action):
		return
	if event is InputEventKey:
		var kc: int = event.physical_keycode if event.physical_keycode != 0 else event.keycode
		_remove_key_elsewhere(action, kc)
		var keys: Array = bindings[action].keys
		while keys.size() <= slot:
			keys.append(0)
		keys[slot] = kc
		bindings[action].keys = keys.filter(func(k): return int(k) != 0)
	elif event is InputEventJoypadButton:
		_remove_pad_elsewhere(action, event.button_index)
		bindings[action].pad = [event.button_index]
	apply_input_map()
	save_settings()

func _remove_key_elsewhere(action: String, kc: int) -> void:
	for a in bindings:
		if a == action:
			continue
		var keys: Array = bindings[a].keys
		if kc in keys:
			keys.erase(kc)
			# give the other action back its displaced default so nothing ends up unbound
			if keys.is_empty():
				for d in DEFAULT_KEYS.get(a, []):
					if not _key_used(d):
						keys.append(d)
						break

func _remove_pad_elsewhere(action: String, btn: int) -> void:
	for a in bindings:
		if a != action and btn in bindings[a].pad:
			bindings[a].pad = bindings[action].pad.duplicate()

func _key_used(kc: int) -> bool:
	for a in bindings:
		if kc in bindings[a].keys:
			return true
	return false

func key_names(action: String) -> PackedStringArray:
	var out: PackedStringArray = []
	for kc in bindings.get(action, {}).get("keys", []):
		out.append(OS.get_keycode_string(int(kc)))
	return out

func pad_buttons(action: String) -> Array:
	return bindings.get(action, {}).get("pad", [])

# ---------------------------------------------------------------- persistence
func load_settings() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	master_volume = clampf(float(cfg.get_value("audio", "master", master_volume)), 0.0, 1.0)
	music_volume = clampf(float(cfg.get_value("audio", "music", music_volume)), 0.0, 1.0)
	sfx_volume = clampf(float(cfg.get_value("audio", "sfx", sfx_volume)), 0.0, 1.0)
	screen_shake = clampf(float(cfg.get_value("access", "shake", screen_shake)), 0.0, 1.0)
	flash = clampf(float(cfg.get_value("access", "flash", flash)), 0.0, 1.0)
	text_speed = clampi(int(cfg.get_value("access", "text_speed", text_speed)), 0, 3)
	var diff: String = str(cfg.get_value("game", "difficulty", difficulty))
	difficulty = diff if diff in ["normal", "relaxed"] else "normal"
	large_text = bool(cfg.get_value("access", "large_text", large_text))
	deadzone = clampf(float(cfg.get_value("input", "deadzone", deadzone)), 0.05, 0.6)
	fullscreen = bool(cfg.get_value("display", "fullscreen", fullscreen))
	var tc: String = str(cfg.get_value("input", "touch", touch_controls))
	touch_controls = tc if tc in ["auto", "on", "off"] else "auto"
	show_hints = bool(cfg.get_value("game", "hints", show_hints))
	var fx_q: String = str(cfg.get_value("display", "effects", effects))
	effects = fx_q if fx_q in ["full", "reduced"] else "full"
	cinematic_bars = bool(cfg.get_value("display", "cinematic_bars", cinematic_bars))
	show_fps = bool(cfg.get_value("display", "show_fps", show_fps))
	var saved_b = cfg.get_value("input", "bindings", {})
	if typeof(saved_b) == TYPE_DICTIONARY:
		for a in saved_b:
			if bindings.has(a) and typeof(saved_b[a]) == TYPE_DICTIONARY:
				var keys = saved_b[a].get("keys", [])
				var pad = saved_b[a].get("pad", [])
				if typeof(keys) == TYPE_ARRAY and not keys.is_empty():
					bindings[a].keys = keys.map(func(k): return int(k))
				if typeof(pad) == TYPE_ARRAY and not pad.is_empty():
					bindings[a].pad = pad.map(func(k): return int(k))

func save_settings() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("audio", "master", master_volume)
	cfg.set_value("audio", "music", music_volume)
	cfg.set_value("audio", "sfx", sfx_volume)
	cfg.set_value("access", "shake", screen_shake)
	cfg.set_value("access", "flash", flash)
	cfg.set_value("access", "text_speed", text_speed)
	cfg.set_value("access", "large_text", large_text)
	cfg.set_value("game", "difficulty", difficulty)
	cfg.set_value("game", "hints", show_hints)
	cfg.set_value("input", "deadzone", deadzone)
	cfg.set_value("input", "touch", touch_controls)
	cfg.set_value("input", "bindings", bindings)
	cfg.set_value("display", "fullscreen", fullscreen)
	cfg.set_value("display", "effects", effects)
	cfg.set_value("display", "cinematic_bars", cinematic_bars)
	cfg.set_value("display", "show_fps", show_fps)
	cfg.save(PATH)
	changed.emit()

func apply_display() -> void:
	if OS.has_feature("web"):
		return
	var mode := DisplayServer.WINDOW_MODE_FULLSCREEN if fullscreen else DisplayServer.WINDOW_MODE_WINDOWED
	if DisplayServer.window_get_mode() != mode:
		DisplayServer.window_set_mode(mode)

func set_fullscreen(on: bool) -> void:
	fullscreen = on
	if OS.has_feature("web"):
		# Browsers only allow fullscreen from a user gesture; this is called from an input handler.
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN if on else DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		apply_display()
	save_settings()

func effects_full() -> bool:
	return effects == "full"

func incoming_damage_mult() -> float:
	return 0.6 if difficulty == "relaxed" else 1.0

func text_cps() -> float:
	return [30.0, 60.0, 120.0, 100000.0][text_speed]
