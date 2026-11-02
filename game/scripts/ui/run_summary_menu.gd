class_name RunSummaryMenu
extends Menu
## End-of-game card shown after the ending, before the credits: how the run went and how the game ran on this
## device. Designed to be screenshotted and sent back as a playtest report.

func _init() -> void:
	super._init()
	back_allowed = false

func build() -> void:
	var c := make_frame("THE OATH IS KEPT", Vector2(470, 0))
	c.add_child(UIKit.label("Run summary  -  take a screenshot of this card to share your playtest.", UIKit.DIM))
	var cols := UIKit.hbox(18)
	c.add_child(cols)
	var st: Dictionary = GameState.stats
	var quests_done := 0
	for qid in GameState.quests:
		if str(GameState.quests[qid].get("state", "")) == "done":
			quests_done += 1
	var run := [
		["Play time", UIKit.fmt_time(float(st.get("playtime", 0.0)))],
		["Difficulty", Settings.difficulty.capitalize() + ("  NG+%d" % GameState.ng_cycle if GameState.ng_cycle > 0 else "")],
		["Level", str(GameState.level)],
		["Enemies defeated", str(int(st.get("defeated", 0)))],
		["Knockouts", str(int(st.get("deaths", 0)))],
		["Meals eaten", str(int(st.get("food_eaten", 0)))],
		["Cash earned", "$%d" % int(st.get("cash_earned", 0))],
		["Side jobs", "%d / %d" % [quests_done, Content.quests.size()]],
	]
	var slow := 100.0 * float(PerfStats.slow_33) / float(maxi(PerfStats.frames, 1))
	var vs := get_viewport().get_visible_rect().size
	var win := DisplayServer.window_get_size()
	var perf := [
		["Average FPS", "%d" % int(round(PerfStats.avg_fps()))],
		["Frames under 30 FPS", "%.1f%%" % slow],
		["Slowest frame", "%d ms" % int(round(PerfStats.worst_ms))],
		["Effects", Settings.effects.capitalize()],
		["Window", "%dx%d" % [win.x, win.y]],
		["View", "%dx%d" % [int(vs.x), int(vs.y)]],
		["Version", SaveService.GAME_VERSION],
	]
	cols.add_child(_column("THE RUN", run))
	cols.add_child(_column("PERFORMANCE", perf))
	var dev := UIKit.wrap_label(PerfStats.device_line(), 450, UIKit.DIM)
	c.add_child(dev)
	var b := UIKit.button("Roll credits", close, 160)
	b.alignment = HORIZONTAL_ALIGNMENT_CENTER
	var row := UIKit.hbox(0)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(b)
	c.add_child(row)
	first_focus = b

func _column(title: String, rows: Array) -> VBoxContainer:
	var v := UIKit.vbox(2)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var h := UIKit.label(title, UIKit.MUSTARD)
	if UIKit.font_big:
		h.add_theme_font_override("font", UIKit.font_big)
		h.add_theme_font_size_override("font_size", 10)
	v.add_child(h)
	var g := GridContainer.new()
	g.columns = 2
	g.add_theme_constant_override("h_separation", 10)
	g.add_theme_constant_override("v_separation", 1)
	v.add_child(g)
	for r in rows:
		var k := UIKit.label(str(r[0]), UIKit.DIM)
		k.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		g.add_child(k)
		g.add_child(UIKit.num_label(str(r[1]), UIKit.CREAM, 12))
	return v
