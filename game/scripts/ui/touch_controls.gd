class_name TouchControls
extends Control
## Mobile landscape controls: analog pad (left) + action buttons (right). True multi-touch:
## each finger is owned by one control until released, so moving + attacking + jumping works together.
## Buttons press InputMap actions, so game logic stays device-independent.

var world: Node
var stick_center := Vector2.ZERO
var stick_finger := -1
var stick_vec := Vector2.ZERO
var buttons: Array = []          # {name, action, pos, r, finger}
var active := false
var hidden_for_menu := false
const STICK_R := 40.0
const BTN_R := 26.0

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS

func _ready() -> void:
	_layout()
	get_viewport().size_changed.connect(_layout)
	Settings.changed.connect(_refresh_active)
	InputPrompts.device_changed.connect(func(_k): _refresh_active())
	_refresh_active()

func _refresh_active() -> void:
	match Settings.touch_controls:
		"on": active = true
		"off": active = false
		_: active = InputPrompts.touch_seen or (OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios"))
	visible = active and not hidden_for_menu
	if not visible:
		_release_all()
	queue_redraw()

func visible_for_menus(menu_open: bool) -> void:
	hidden_for_menu = menu_open
	_refresh_active()

func _layout() -> void:
	var vs := get_viewport_rect().size
	stick_center = Vector2(70, vs.y - 74)
	var bx := vs.x - 60
	var by := vs.y - 64
	buttons = [
		{"name": "P", "label": "PUNCH", "action": "punch", "pos": Vector2(bx - 62, by + 4), "finger": -1, "icon": "touch_btn_punch"},
		{"name": "K", "label": "KICK", "action": "kick", "pos": Vector2(bx - 8, by - 40), "finger": -1, "icon": "touch_btn_kick"},
		{"name": "J", "label": "JUMP", "action": "jump", "pos": Vector2(bx, by + 18), "finger": -1, "icon": "touch_btn_jump"},
		{"name": "G", "label": "GRD", "action": "guard", "pos": Vector2(bx - 118, by + 14), "finger": -1, "icon": "touch_btn_guard"},
		{"name": "E", "label": "GRAB", "action": "interact", "pos": Vector2(bx - 66, by - 52), "finger": -1, "icon": "touch_btn_grab"},
		{"name": "R", "label": "RUN", "action": "run", "pos": Vector2(bx - 122, by - 40), "finger": -1, "icon": "touch_btn_run", "toggle": false},
		{"name": "II", "label": "II", "action": "pause", "pos": Vector2(vs.x - 22, 22), "finger": -1, "icon": "touch_btn_pause", "small": true},
		{"name": "BAG", "label": "BAG", "action": "status", "pos": Vector2(vs.x - 58, 22), "finger": -1, "icon": "touch_btn_status", "small": true},
	]
	queue_redraw()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch or event is InputEventScreenDrag:
		if not active and Settings.touch_controls == "auto":
			InputPrompts.touch_seen = true
			_refresh_active()
		if not visible:
			return
		var pos: Vector2 = event.position  # already in viewport (640x360-space) coordinates
		if event is InputEventScreenTouch:
			if event.pressed:
				if _try_press(event.index, pos):
					get_viewport().set_input_as_handled()
			else:
				if _release(event.index):
					get_viewport().set_input_as_handled()
		else:
			if event.index == stick_finger:
				_update_stick(pos)
				get_viewport().set_input_as_handled()

func _try_press(finger: int, pos: Vector2) -> bool:
	for b in buttons:
		var r := BTN_R * (0.7 if b.get("small", false) else 1.0) + 6.0
		if pos.distance_to(b.pos) <= r and b.finger == -1:
			b.finger = finger
			Input.action_press(b.action)
			queue_redraw()
			return true
	if pos.x < get_viewport_rect().size.x * 0.45 and pos.y > get_viewport_rect().size.y * 0.35 and stick_finger == -1:
		stick_finger = finger
		stick_center = pos
		_update_stick(pos)
		return true
	return false

func _release(finger: int) -> bool:
	var handled := false
	if finger == stick_finger:
		stick_finger = -1
		stick_vec = Vector2.ZERO
		_apply_stick()
		_layout_stick_home()
		handled = true
	for b in buttons:
		if b.finger == finger:
			b.finger = -1
			Input.action_release(b.action)
			handled = true
	queue_redraw()
	return handled

func _layout_stick_home() -> void:
	stick_center = Vector2(70, get_viewport_rect().size.y - 74)

func _update_stick(pos: Vector2) -> void:
	var d := pos - stick_center
	if d.length() > STICK_R:
		d = d.normalized() * STICK_R
	stick_vec = d / STICK_R
	_apply_stick()
	queue_redraw()

func _apply_stick() -> void:
	var v := stick_vec
	if v.length() < 0.22:
		v = Vector2.ZERO
	for pair in [["move_left", maxf(-v.x, 0.0)], ["move_right", maxf(v.x, 0.0)], ["move_up", maxf(-v.y, 0.0)], ["move_down", maxf(v.y, 0.0)]]:
		if pair[1] > 0.0:
			Input.action_press(pair[0], clampf(pair[1] * 1.25, 0.0, 1.0))
		else:
			Input.action_release(pair[0])

func _release_all() -> void:
	if stick_finger != -1 or stick_vec != Vector2.ZERO:
		stick_finger = -1
		stick_vec = Vector2.ZERO
		_apply_stick()
	for b in buttons:
		if b.finger != -1:
			b.finger = -1
			Input.action_release(b.action)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_release_all()

func _draw() -> void:
	if not visible:
		return
	var base := SpriteLib.ui("touch_stick_base")
	var knob := SpriteLib.ui("touch_stick_knob")
	if base:
		draw_texture(base, stick_center - base.get_size() / 2.0, Color(1, 1, 1, 0.55))
	else:
		draw_arc(stick_center, STICK_R, 0, TAU, 32, Color(1, 1, 1, 0.35), 2.0)
	var kp := stick_center + stick_vec * STICK_R
	if knob:
		draw_texture(knob, kp - knob.get_size() / 2.0, Color(1, 1, 1, 0.75))
	else:
		draw_circle(kp, 16, Color(1, 1, 1, 0.35))
	var f := UIKit.font_small
	for b in buttons:
		var pressed: bool = b.finger != -1
		var tex := SpriteLib.ui(b.icon)
		var alpha := 0.85 if pressed else 0.5
		if tex:
			var sz := tex.get_size()
			draw_texture(tex, b.pos - sz / 2.0, Color(1, 1, 1, alpha) if not pressed else Color(1.3, 1.2, 0.8, 0.95))
		else:
			var r := BTN_R * (0.7 if b.get("small", false) else 1.0)
			draw_circle(b.pos, r, Color(0.1, 0.07, 0.12, 0.45 if not pressed else 0.75))
			draw_arc(b.pos, r, 0, TAU, 24, Color(0.95, 0.85, 0.7, alpha), 2.0)
			if f:
				draw_string(f, b.pos + Vector2(-16, 3), b.label, HORIZONTAL_ALIGNMENT_CENTER, 32, 8, Color(1, 1, 1, 0.9))
