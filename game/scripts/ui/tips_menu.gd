class_name TipsMenu
extends Menu
## Reference page for everything the opening teaches, plus the inputs of techniques already learned.
## Always available from the pause menu, shown with the current device's bindings.

func build() -> void:
	var c := make_frame("FIGHTING TIPS", Vector2(430, 0))
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(420, 236)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.follow_focus = true
	c.add_child(scroll)
	var v := UIKit.vbox(4)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(v)
	var tut = host.get("tutor") if host else null
	var lines: Array = tut.reference_lines() if tut != null else []
	v.add_child(UIKit.label("BASICS", UIKit.MUSTARD))
	for l in lines:
		v.add_child(UIKit.wrap_label("- " + str(l), 400, UIKit.CREAM))
	if not GameState.skills.is_empty():
		v.add_child(UIKit.spacer(2))
		v.add_child(UIKit.label("YOUR TECHNIQUES", UIKit.MUSTARD))
		for sid in GameState.skills:
			var sk: Dictionary = Content.skill(sid)
			v.add_child(UIKit.wrap_label("- %s: %s" % [sk.get("name", sid), Story.format_text(Tutor.input_text(sk))], 400, UIKit.CREAM))
			v.add_child(UIKit.wrap_label("   " + str(sk.get("desc", "")), 400, UIKit.DIM))
	var row := UIKit.hbox(6)
	c.add_child(row)
	var hints := UIKit.button("Tips while playing: %s" % ("On" if Settings.show_hints else "Off"), _toggle_hints, 200)
	row.add_child(hints)
	if tut != null and tut.any_armed():
		row.add_child(UIKit.button("Skip waiting tips", func():
			tut.skip_all()
			rebuild(), 150))
	first_focus = hints

func _toggle_hints() -> void:
	Settings.show_hints = not Settings.show_hints
	Settings.save_settings()
	rebuild()
