class_name TouchControls
extends Control
## Touch controls: analog pad (left) + action buttons (right), true multi-touch (each finger is owned
## by one control until it lifts). Buttons dispatch real InputEventActions, so gameplay, menus and
## dialogue all react exactly as they would to a keyboard or controller.
##
## Layouts:
##  - Docked (tablets / taller screens): the playfield sits at the top and the controls live in their own
##    deck underneath, so they never cover the fight or the dialogue.
##  - Overlay (phones in landscape): controls sit over the street's lower corners and fade out whenever
##    a conversation or cutscene is on screen.
## The ACTION button relabels itself with what it will do: TALK, ENTER, PICK UP, LIFT, GRAB, THROW, BUS.

signal layout_changed

const STICK_R := 40.0
const BTN_R := 26.0
const LABEL_COL := Color(0.96, 0.9, 0.78)

var world: Node
var active := false
var hidden_for_menu := false
var docked := false
var deck_rect := Rect2()
var stick_home := Vector2.ZERO
var stick_center := Vector2.ZERO
var stick_finger := -1
var stick_vec := Vector2.ZERO
var buttons: Array = []
var fade := 1.0
var blocked := false
var action_label := "ACTION"
var action_live := false
var pulse := 0.0
var labels_below := false

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS

func _ready() -> void:
	UIKit.apply(self)
	get_viewport().size_changed.connect(_layout)
	Settings.changed.connect(_refresh_active)
	InputPrompts.device_changed.connect(func(_k): _refresh_active())
	_refresh_active()

## Auto mode shows the controls only while touch is the device being used, so hybrid laptops and
## tablets with keyboards switch cleanly. On/Off settings force it.
func _refresh_active() -> void:
	var was := active
	match Settings.touch_controls:
		"on": active = true
		"off": active = false
		_: active = InputPrompts.kind == "touch"
	visible = active and not hidden_for_menu
	if not visible:
		_release_all()
	if was != active:
		_layout()
	queue_redraw()

func visible_for_menus(menu_open: bool) -> void:
	hidden_for_menu = menu_open
	_refresh_active()

func _layout() -> void:
	var vs := get_viewport_rect().size
	var pf_top: float = world.playfield_top() if world and world.has_method("playfield_top") else 0.0
	var deck_h := vs.y - (pf_top + 360.0)
	docked = active and deck_h >= 72.0
	var small := {"small": true}
	if docked:
		deck_rect = Rect2(0, pf_top + 360.0, vs.x, deck_h)
		var cy := deck_rect.position.y + deck_h * 0.5
		var two_rows := deck_h >= 116.0
		labels_below = not two_rows
		if labels_below:
			cy -= 6.0   # leave room for the labels under the buttons
		stick_home = Vector2(maxf(64.0, vs.x * 0.11), deck_rect.position.y + deck_h * 0.5)
		var bx := vs.x - maxf(44.0, vs.x * 0.07)
		var dy := 29.0 if two_rows else 0.0
		var dx := 62.0
		var shift := 0.0 if two_rows else dx * 3.0
		buttons = [
			_btn("jump", "JUMP", Vector2(bx, cy + dy), "touch_btn_jump_bare"),
			_btn("punch", "PUNCH", Vector2(bx - dx, cy + dy), "touch_btn_punch_bare"),
			_btn("guard", "GUARD", Vector2(bx - dx * 2.0, cy + dy), "touch_btn_guard_bare"),
			_btn("kick", "KICK", Vector2(bx - shift, cy - dy), "touch_btn_kick_bare"),
			_btn("interact", "ACTION", Vector2(bx - dx - shift, cy - dy), "touch_btn_grab_bare"),
			_btn("run", "RUN", Vector2(bx - dx * 2.0 - shift, cy - dy), "touch_btn_run_bare"),
		]
		# BAG and PAUSE sit in the gap between the stick and the button cluster
		var left_edge := stick_home.x + STICK_R + 10.0
		var right_edge := bx - dx * 2.0 - shift - BTN_R - 10.0
		var mid := (left_edge + right_edge) * 0.5
		var gap := clampf((right_edge - left_edge) * 0.5, 18.0, 28.0)
		buttons.append(_btn("status", "BAG", Vector2(mid - gap, stick_home.y), "touch_btn_status", small))
		buttons.append(_btn("pause", "PAUSE", Vector2(mid + gap, stick_home.y), "touch_btn_pause", small))
	else:
		deck_rect = Rect2()
		labels_below = false
		var bottom := pf_top + 360.0
		stick_home = Vector2(70, bottom - 74)
		var bx2 := vs.x - 60.0
		var by := bottom - 64.0
		buttons = [
			_btn("punch", "PUNCH", Vector2(bx2 - 62, by + 4), "touch_btn_punch_bare"),
			_btn("kick", "KICK", Vector2(bx2 - 8, by - 40), "touch_btn_kick_bare"),
			_btn("jump", "JUMP", Vector2(bx2, by + 18), "touch_btn_jump_bare"),
			_btn("guard", "GUARD", Vector2(bx2 - 118, by + 14), "touch_btn_guard_bare"),
			_btn("interact", "ACTION", Vector2(bx2 - 66, by - 52), "touch_btn_grab_bare"),
			_btn("run", "RUN", Vector2(bx2 - 122, by - 40), "touch_btn_run_bare"),
			_btn("pause", "PAUSE", Vector2(vs.x - 22, pf_top + 22), "touch_btn_pause", small),
			_btn("status", "BAG", Vector2(vs.x - 58, pf_top + 22), "touch_btn_status", small),
		]
	if stick_finger == -1:
		stick_center = stick_home
	layout_changed.emit()
	queue_redraw()

func _btn(action: String, label: String, pos: Vector2, icon: String, extra: Dictionary = {}) -> Dictionary:
	var b := {"action": action, "label": label, "pos": pos, "icon": icon, "finger": -1}
	b.merge(extra)
	return b

func _process(delta: float) -> void:
	if not visible:
		return
	pulse += delta
	var now_blocked := _is_blocked()
	if now_blocked and not blocked:
		_release_all()
	blocked = now_blocked
	var target := 1.0
	if blocked:
		target = 0.18 if docked else 0.0
	fade = move_toward(fade, target, delta * 6.0)
	var lbl := "ACTION"
	var live := false
	if world and world.room and world.room.player and not blocked:
		var short: String = world.room.player.context_short()
		if short != "":
			lbl = short
			live = true
	if lbl != action_label or live != action_live:
		action_label = lbl
		action_live = live
	queue_redraw()

func _is_blocked() -> bool:
	if world == null:
		return false
	if world.dialogue_active() or world.transitioning:
		return true
	return world.room != null and world.room.cutscene

func _input(event: InputEvent) -> void:
	if not (event is InputEventScreenTouch or event is InputEventScreenDrag):
		return
	if not visible or blocked:
		return
	var pos: Vector2 = event.position   # already in viewport coordinates
	if event is InputEventScreenTouch:
		if event.pressed:
			if _try_press(event.index, pos):
				get_viewport().set_input_as_handled()
		elif _release(event.index):
			get_viewport().set_input_as_handled()
	elif event.index == stick_finger:
		_update_stick(pos)
		get_viewport().set_input_as_handled()

func _hit_radius(b: Dictionary) -> float:
	return BTN_R * (0.62 if b.get("small", false) else 1.0) + 7.0

func _try_press(finger: int, pos: Vector2) -> bool:
	var best: Dictionary = {}
	var best_d := INF
	for b in buttons:
		var d: float = pos.distance_to(b.pos)
		if d <= _hit_radius(b) and b.finger == -1 and d < best_d:
			best_d = d
			best = b
	if not best.is_empty():
		best.finger = finger
		_send(best.action, true)
		if best.action in ["punch", "kick", "jump"]:
			Input.vibrate_handheld(12)
		queue_redraw()
		return true
	var vs := get_viewport_rect().size
	var in_zone := pos.x < vs.x * 0.42 and (docked and deck_rect.has_point(pos) or (not docked and pos.y > vs.y * 0.35))
	if in_zone and stick_finger == -1:
		stick_finger = finger
		stick_center = pos if not docked else Vector2(clampf(pos.x, 40.0, vs.x * 0.4), clampf(pos.y, deck_rect.position.y + 20.0, deck_rect.end.y - 20.0))
		_update_stick(pos)
		return true
	return false

func _release(finger: int) -> bool:
	var handled := false
	if finger == stick_finger:
		stick_finger = -1
		stick_vec = Vector2.ZERO
		_apply_stick()
		stick_center = stick_home
		handled = true
	for b in buttons:
		if b.finger == finger:
			b.finger = -1
			_send(b.action, false)
			handled = true
	queue_redraw()
	return handled

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
			_send(pair[0], true, clampf(pair[1] * 1.25, 0.0, 1.0))
		elif Input.is_action_pressed(pair[0]):
			_send(pair[0], false)

## Dispatches a real InputEventAction so both polling (gameplay) and event handlers (menus, dialogue) see it.
func _send(action: String, pressed: bool, strength: float = 1.0) -> void:
	var ev := InputEventAction.new()
	ev.action = action
	ev.pressed = pressed
	ev.strength = strength if pressed else 0.0
	Input.parse_input_event(ev)

func _release_all() -> void:
	if stick_finger != -1 or stick_vec != Vector2.ZERO:
		stick_finger = -1
		stick_vec = Vector2.ZERO
		_apply_stick()
		stick_center = stick_home
	for b in buttons:
		if b.finger != -1:
			b.finger = -1
			_send(b.action, false)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_release_all()

func _draw() -> void:
	if not visible:
		return
	if docked:
		# a dedicated control deck below the street
		draw_rect(deck_rect, Color(0.07, 0.05, 0.09, 1.0))
		draw_rect(Rect2(deck_rect.position, Vector2(deck_rect.size.x, 2)), Color(0.91, 0.85, 0.69, 0.55))
	if fade <= 0.01:
		return
	var a := fade
	var base := SpriteLib.ui("touch_stick_base")
	var knob := SpriteLib.ui("touch_stick_knob")
	if base:
		draw_texture(base, stick_center - base.get_size() / 2.0, Color(1, 1, 1, 0.65 * a))
	else:
		draw_arc(stick_center, STICK_R, 0, TAU, 32, Color(1, 1, 1, 0.4 * a), 2.0)
	var kp := stick_center + stick_vec * STICK_R
	if knob:
		draw_texture(knob, kp - knob.get_size() / 2.0, Color(1, 1, 1, 0.85 * a))
	else:
		draw_circle(kp, 16, Color(1, 1, 1, 0.4 * a))
	var f := UIKit.font_small
	for b in buttons:
		var pressed: bool = b.finger != -1
		var tex := SpriteLib.ui(b.icon)
		if tex == null:
			tex = SpriteLib.ui(b.icon.replace("_bare", ""))
		var small: bool = b.get("small", false)
		var alpha := (0.95 if pressed else 0.72) * a
		var tint := Color(1.25, 1.15, 0.8, alpha) if pressed else Color(1, 1, 1, alpha)
		var is_action: bool = b.action == "interact"
		if is_action and action_live:
			var glow := 0.5 + 0.5 * sin(pulse * 6.0)
			draw_arc(b.pos, BTN_R + 3.0, 0, TAU, 40, Color(0.94, 0.75, 0.25, (0.45 + 0.4 * glow) * a), 2.0)
		if tex:
			draw_texture(tex, b.pos - tex.get_size() / 2.0, tint)
		if small or f == null:
			continue
		var text: String = action_label if is_action else str(b.label)
		var col := Color(0.94, 0.75, 0.25, a) if is_action and action_live else Color(LABEL_COL.r, LABEL_COL.g, LABEL_COL.b, a)
		var w: float = f.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, 8).x
		var tp: Vector2 = b.pos + Vector2(-w / 2.0, (BTN_R + 9.0) if labels_below else 15.0)
		draw_string_outline(f, tp, text, HORIZONTAL_ALIGNMENT_LEFT, -1, 8, 3, Color(0.07, 0.05, 0.09, a))
		draw_string(f, tp, text, HORIZONTAL_ALIGNMENT_LEFT, -1, 8, col)
