class_name PlaytestMenu
extends Menu
## What the opt-in playtest log has recorded so far (local to this save). For facilitators.

func build() -> void:
	var c := make_frame("PLAYTEST NOTES", Vector2(440, 0))
	c.add_child(UIKit.wrap_label("Recorded on this device only, while Settings > Playtest log is on. Times are play time.", 420, UIKit.DIM))
	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(430, 200)
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	c.add_child(scroll)
	var v := UIKit.vbox(3)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(v)
	var ls := Playtest.lines()
	if ls.is_empty():
		v.add_child(UIKit.wrap_label("Nothing recorded yet.", 410, UIKit.CREAM))
	for l in ls:
		v.add_child(UIKit.wrap_label("- " + str(l), 410, UIKit.CREAM))
	v.add_child(UIKit.wrap_label("- Play time %s, level %d, knockouts %d, meals %d, FPS avg %d (%s)" % [UIKit.fmt_time(float(GameState.stats.get("playtime", 0.0))),
		GameState.level, int(GameState.stats.get("deaths", 0)), int(GameState.stats.get("food_eaten", 0)), int(round(PerfStats.avg_fps())), PerfStats.device_line()], 410, UIKit.DIM))
	var b := UIKit.button("Back", close, 120)
	c.add_child(b)
	first_focus = b
