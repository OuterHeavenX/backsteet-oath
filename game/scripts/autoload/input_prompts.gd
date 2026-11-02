extends Node
## Tracks the most recently used input device so prompts show the right glyphs,
## and handles gamepad connect/disconnect safely.

signal device_changed(kind: String)
signal pad_disconnected

var kind := "keyboard"   # keyboard / gamepad / touch
var touch_seen := false
const PAD_NAMES := {
	JOY_BUTTON_A: "A", JOY_BUTTON_B: "B", JOY_BUTTON_X: "X", JOY_BUTTON_Y: "Y",
	JOY_BUTTON_LEFT_SHOULDER: "LB", JOY_BUTTON_RIGHT_SHOULDER: "RB", JOY_BUTTON_BACK: "View",
	JOY_BUTTON_START: "Menu", JOY_BUTTON_DPAD_UP: "D-Up", JOY_BUTTON_DPAD_DOWN: "D-Down",
	JOY_BUTTON_DPAD_LEFT: "D-Left", JOY_BUTTON_DPAD_RIGHT: "D-Right", JOY_BUTTON_LEFT_STICK: "LS", JOY_BUTTON_RIGHT_STICK: "RS"
}
const PAD_ICONS := {
	JOY_BUTTON_A: "gp_a", JOY_BUTTON_B: "gp_b", JOY_BUTTON_X: "gp_x", JOY_BUTTON_Y: "gp_y",
	JOY_BUTTON_LEFT_SHOULDER: "gp_lb", JOY_BUTTON_RIGHT_SHOULDER: "gp_rb", JOY_BUTTON_BACK: "gp_select", JOY_BUTTON_START: "gp_start"
}
const TOUCH_NAMES := {"punch": "PUNCH", "kick": "KICK", "jump": "JUMP", "guard": "GUARD", "interact": "ACTION", "run": "RUN", "status": "BAG", "pause": "PAUSE"}

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Input.joy_connection_changed.connect(_on_joy)
	if DisplayServer.is_touchscreen_available() and OS.has_feature("mobile"):
		touch_seen = true
		kind = "touch"
	elif OS.has_feature("web"):
		# phones and tablets report a coarse primary pointer; start them in touch mode
		var coarse = JavaScriptBridge.eval("(window.matchMedia && window.matchMedia('(pointer: coarse)').matches) ? 1 : 0", true)
		if coarse != null and int(coarse) == 1:
			touch_seen = true
			kind = "touch"
	elif Input.get_connected_joypads().size() > 0 and OS.has_feature("steamdeck"):
		kind = "gamepad"

func _input(event: InputEvent) -> void:
	var k := kind
	if event is InputEventKey and event.pressed:
		k = "keyboard"
	elif event is InputEventJoypadButton and event.pressed:
		k = "gamepad"
	elif event is InputEventJoypadMotion and absf(event.axis_value) > 0.5:
		k = "gamepad"
	elif event is InputEventScreenTouch and event.pressed:
		k = "touch"
		touch_seen = true
	elif event is InputEventMouseButton and event.pressed and kind == "touch" and not touch_seen:
		k = "keyboard"
	if k != kind:
		kind = k
		device_changed.emit(kind)

func _on_joy(device: int, connected: bool) -> void:
	if not connected:
		pad_disconnected.emit()
		if Input.get_connected_joypads().is_empty() and kind == "gamepad":
			kind = "keyboard"
			device_changed.emit(kind)

## Short text label for an action on the current device, e.g. "J", "X", "P".
func label(action: String) -> String:
	match kind:
		"gamepad":
			var pads: Array = Settings.pad_buttons(action)
			if pads.size() > 0:
				return PAD_NAMES.get(int(pads[0]), "Btn%d" % int(pads[0]))
			return "?"
		"touch":
			return TOUCH_NAMES.get(action, action.to_upper())
		_:
			var keys := Settings.key_names(action)
			return keys[0] if keys.size() > 0 else "?"

## Bracketed form for inline text: "[J]" on keyboard, "(X)" on pad, "<P>" on touch.
func tag(action: String) -> String:
	match kind:
		"gamepad": return "(" + label(action) + ")"
		"touch": return "[" + label(action) + "]"
		_: return "[" + label(action) + "]"

func icon_name(action: String) -> String:
	if kind != "gamepad":
		return ""
	var pads: Array = Settings.pad_buttons(action)
	return PAD_ICONS.get(int(pads[0]), "") if pads.size() > 0 else ""

func move_label() -> String:
	match kind:
		"gamepad": return "Left Stick / D-Pad"
		"touch": return "Left Pad"
		_:
			var k := []
			for a in ["move_up", "move_left", "move_down", "move_right"]:
				var n := Settings.key_names(a)
				k.append(n[0] if n.size() > 0 else "?")
			var s := "".join(k)
			return ("WASD or arrow keys" if s == "WASD" else s)
