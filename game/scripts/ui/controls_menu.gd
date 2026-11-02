class_name ControlsMenu
extends Menu
## Shows the actual current bindings and lets players rebind keyboard keys / pad buttons.

var waiting_action := ""
var waiting_slot := 0
var waiting_pad := false
var info: Label
var listen_cd := 0

func build() -> void:
	var c := make_frame("CONTROLS", Vector2(520, 0))
	if InputPrompts.kind == "touch" or Settings.touch_controls == "on":
		c.add_child(UIKit.label("TOUCH", UIKit.MUSTARD))
		c.add_child(UIKit.wrap_label("Left pad: move along the street and its depth. PUNCH, KICK, JUMP, GUARD (hold), RUN (hold). ACTION does what its label says: TALK, ENTER, PICK UP, LIFT, GRAB a dizzy foe, THROW. Tap the street or the text box to continue a conversation; SKIP ends it. BAG opens status, PAUSE opens the menu. On tablets the controls get their own deck under the street.", 500, UIKit.CREAM))
		c.add_child(UIKit.label("KEYBOARD & CONTROLLER", UIKit.MUSTARD))
	c.add_child(UIKit.wrap_label("Select a binding and press the new key or controller button. Esc/B cancels. Movement: %s, or left stick / D-pad." % "WASD or arrow keys", 500, UIKit.DIM))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(500, 210)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	var v := UIKit.vbox(2)
	sc.add_child(v)
	var hdr := UIKit.hbox(6)
	for t in [["ACTION", 150], ["KEY 1", 100], ["KEY 2", 100], ["PAD", 110]]:
		var l := UIKit.label(t[0], UIKit.MUSTARD)
		l.custom_minimum_size = Vector2(t[1], 0)
		hdr.add_child(l)
	v.add_child(hdr)
	var first: Control = null
	for a in Settings.GAME_ACTIONS:
		var h := UIKit.hbox(6)
		var l := UIKit.label(Settings.ACTION_LABELS[a], UIKit.CREAM)
		l.custom_minimum_size = Vector2(150, 0)
		h.add_child(l)
		var keys := Settings.key_names(a)
		for slot in 2:
			var kt := keys[slot] if slot < keys.size() else "-"
			var b := UIKit.button(kt, func(): _listen(a, slot, false), 100)
			h.add_child(b)
			if first == null:
				first = b
		var pads: Array = Settings.pad_buttons(a)
		var pt := InputPrompts.PAD_NAMES.get(int(pads[0]), "Btn %d" % int(pads[0])) if pads.size() > 0 else "-"
		if a.begins_with("move_"):
			pt += " / L-Stick"
		elif a == "guard":
			pt += " / LT"
		elif a == "run":
			pt += " / RT"
		var pb := UIKit.button(pt, func(): _listen(a, 0, true), 110)
		h.add_child(pb)
		v.add_child(h)
	info = UIKit.wrap_label("", 500, UIKit.MUSTARD)
	c.add_child(info)
	var row := UIKit.hbox(6)
	row.add_child(UIKit.button("Reset to defaults", _reset, 160))
	row.add_child(UIKit.button("Back", close, 100))
	c.add_child(row)
	first_focus = first

func _listen(a: String, slot: int, pad: bool) -> void:
	waiting_action = a
	waiting_slot = slot
	waiting_pad = pad
	listen_cd = 8
	back_allowed = false
	info.text = "Press a %s for %s..." % ["controller button" if pad else "key", Settings.ACTION_LABELS[a]]

func _process(_d: float) -> void:
	if listen_cd > 0:
		listen_cd -= 1

func _input(event: InputEvent) -> void:
	if waiting_action == "" or listen_cd > 0 or not is_top():
		return
	if not event.is_pressed() or event.is_echo():
		return
	if (event is InputEventKey and event.physical_keycode == KEY_ESCAPE) or (event is InputEventJoypadButton and event.button_index == JOY_BUTTON_B and not waiting_pad):
		_cancel_listen("Cancelled.")
		get_viewport().set_input_as_handled()
		return
	if waiting_pad and event is InputEventJoypadButton:
		Settings.rebind(waiting_action, event)
		get_viewport().set_input_as_handled()
		_done()
	elif not waiting_pad and event is InputEventKey:
		if event.physical_keycode in [KEY_ESCAPE, KEY_F11]:
			return
		Settings.rebind(waiting_action, event, waiting_slot)
		get_viewport().set_input_as_handled()
		_done()

func _cancel_listen(msg: String) -> void:
	waiting_action = ""
	back_allowed = true
	info.text = msg

func _done() -> void:
	waiting_action = ""
	Audio.sfx("ui_confirm", -6.0, 0.0)
	await get_tree().process_frame
	back_allowed = true
	rebuild()

func _reset() -> void:
	var yes: bool = await ConfirmMenu.ask(host, "Reset all bindings to defaults?")
	if yes:
		Settings.reset_bindings()
		rebuild()
