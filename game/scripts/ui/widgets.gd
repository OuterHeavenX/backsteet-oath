class_name Widgets
extends RefCounted
## Small reusable controls: option cycler, slider row, confirm dialog factory.

## A button that cycles through options with confirm or left/right.
static func cycler(label_text: String, options: Array, current: int, on_change: Callable, width: float = 260.0) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(width, 0)
	b.set_meta("idx", current)
	var refresh := func():
		b.text = "%s:  < %s >" % [label_text, str(options[int(b.get_meta("idx"))])]
	refresh.call()
	var step := func(d: int):
		var i := (int(b.get_meta("idx")) + d + options.size()) % options.size()
		b.set_meta("idx", i)
		refresh.call()
		Audio.sfx("ui_move", -8.0, 0.0)
		on_change.call(i)
	b.pressed.connect(func(): step.call(1))
	b.gui_input.connect(func(ev: InputEvent):
		if ev.is_action_pressed("ui_left"):
			step.call(-1)
			b.accept_event()
		elif ev.is_action_pressed("ui_right"):
			step.call(1)
			b.accept_event())
	b.focus_entered.connect(func(): Audio.sfx("ui_move", -10.0, 0.0))
	return b

## Volume-style slider row (0..1). Left/right adjust in 10% steps.
static func slider(label_text: String, value: float, on_change: Callable, width: float = 260.0) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_ALL
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	b.custom_minimum_size = Vector2(width, 0)
	b.set_meta("v", value)
	var refresh := func():
		var v: float = b.get_meta("v")
		var n := int(round(v * 10.0))
		b.text = "%s:  %s%s %d%%" % [label_text, "#".repeat(n), ".".repeat(10 - n), int(round(v * 100))]
	refresh.call()
	var step := func(d: float):
		var v: float = clampf(snappedf(float(b.get_meta("v")) + d, 0.1), 0.0, 1.0)
		b.set_meta("v", v)
		refresh.call()
		on_change.call(v)
		Audio.sfx("ui_move", -6.0, 0.0)
	b.pressed.connect(func(): step.call(0.1 if float(b.get_meta("v")) < 0.99 else -1.0))
	b.gui_input.connect(func(ev: InputEvent):
		if ev.is_action_pressed("ui_left"):
			step.call(-0.1)
			b.accept_event()
		elif ev.is_action_pressed("ui_right"):
			step.call(0.1)
			b.accept_event())
	return b
