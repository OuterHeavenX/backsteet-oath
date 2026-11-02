class_name HUD
extends Control
## In-game HUD: HP/XP/level, cash, held weapon + durability, objective, context prompt,
## boss bar (only during boss fights), toasts and level-up banner. Keeps the playfield clear.

var world: Node
var hp_bar: ColorRect
var hp_back: ColorRect
var hp_label: Label
var xp_bar: ColorRect
var lvl_label: Label
var cash_label: Label
var weapon_icon: TextureRect
var weapon_label: Label
var obj_label: Label
var prompt_label: Label
var boss_box: PanelContainer
var boss_name: Label
var boss_fill: ColorRect
var boss_trail: ColorRect
var boss_hp_text: Label
var bosses: Array = []
var toast_box: VBoxContainer
var levelup: PanelContainer
var levelup_t := 0.0
var hint_label: Label
var hint_panel: PanelContainer
var hint_t := 0.0
var top_panel: PanelContainer
var timer_label: Label
var shown_hp := 0.0
var cash_flash := 0.0

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS

func _ready() -> void:
	UIKit.apply(self)
	top_panel = PanelContainer.new()
	top_panel.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.1, 0.07, 0.12, 0.78), Color(0.9, 0.85, 0.7, 0.8), 1))
	top_panel.position = Vector2(4, 4)
	top_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(top_panel)
	var v := UIKit.vbox(1)
	top_panel.add_child(v)
	var row := UIKit.hbox(4)
	v.add_child(row)
	lvl_label = UIKit.label("NICO  Lv 1", UIKit.MUSTARD)
	row.add_child(lvl_label)
	cash_label = UIKit.label("$0", UIKit.CASHC)
	row.add_child(cash_label)
	var hp_row := UIKit.hbox(3)
	v.add_child(hp_row)
	hp_row.add_child(UIKit.label("HP", UIKit.CREAM))
	hp_back = ColorRect.new()
	hp_back.color = Color(0.25, 0.08, 0.1)
	hp_back.custom_minimum_size = Vector2(96, 7)
	hp_row.add_child(hp_back)
	hp_bar = ColorRect.new()
	hp_bar.color = Color(0.9, 0.3, 0.3)
	hp_bar.size = Vector2(96, 7)
	hp_back.add_child(hp_bar)
	hp_label = UIKit.label("60/60", UIKit.CREAM)
	hp_row.add_child(hp_label)
	var xp_row := UIKit.hbox(3)
	v.add_child(xp_row)
	xp_row.add_child(UIKit.label("XP", UIKit.XPC))
	var xp_back := ColorRect.new()
	xp_back.color = Color(0.08, 0.2, 0.22)
	xp_back.custom_minimum_size = Vector2(96, 3)
	xp_back.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	xp_row.add_child(xp_back)
	xp_bar = ColorRect.new()
	xp_bar.color = UIKit.XPC
	xp_bar.size = Vector2(0, 3)
	xp_back.add_child(xp_bar)
	var w_row := UIKit.hbox(3)
	v.add_child(w_row)
	weapon_icon = UIKit.icon_rect(null, 12)
	weapon_icon.custom_minimum_size = Vector2(12, 12)
	weapon_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	weapon_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	w_row.add_child(weapon_icon)
	weapon_label = UIKit.label("Fists", UIKit.DIM)
	w_row.add_child(weapon_label)

	obj_label = UIKit.label("", UIKit.CREAM)
	UIKit.place(obj_label, Control.PRESET_TOP_RIGHT, -264, 6, 258, 24)
	obj_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	obj_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	obj_label.add_theme_color_override("font_outline_color", UIKit.INK)
	obj_label.add_theme_constant_override("outline_size", 4)
	add_child(obj_label)

	prompt_label = UIKit.label("", Color.WHITE, 0, HORIZONTAL_ALIGNMENT_CENTER)
	UIKit.place(prompt_label, Control.PRESET_CENTER_BOTTOM, -150, -48, 300, 12)
	prompt_label.add_theme_color_override("font_outline_color", UIKit.INK)
	prompt_label.add_theme_constant_override("outline_size", 4)
	add_child(prompt_label)

	hint_panel = PanelContainer.new()
	hint_panel.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.1, 0.07, 0.12, 0.82), UIKit.MUSTARD, 1))
	UIKit.place(hint_panel, Control.PRESET_CENTER_TOP, -200, 60, 400, 0)
	hint_panel.custom_minimum_size = Vector2(400, 0)
	hint_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hint_panel.visible = false
	add_child(hint_panel)
	hint_label = UIKit.wrap_label("", 384, UIKit.MUSTARD)
	hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint_panel.add_child(hint_label)

	boss_box = PanelContainer.new()
	boss_box.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.1, 0.07, 0.12, 0.85), UIKit.DANGER, 1))
	UIKit.place(boss_box, Control.PRESET_CENTER_BOTTOM, -150, -32, 300, 0)
	boss_box.custom_minimum_size = Vector2(300, 0)
	boss_box.visible = false
	boss_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(boss_box)
	var bv := UIKit.vbox(1)
	boss_box.add_child(bv)
	var bh := UIKit.hbox(4)
	bv.add_child(bh)
	boss_name = UIKit.label("BOSS", UIKit.DANGER)
	bh.add_child(boss_name)
	boss_hp_text = UIKit.label("", UIKit.CREAM)
	boss_hp_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	boss_hp_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	bh.add_child(boss_hp_text)
	var bb := ColorRect.new()
	bb.color = Color(0.2, 0.06, 0.08)
	bb.custom_minimum_size = Vector2(284, 6)
	bv.add_child(bb)
	boss_trail = ColorRect.new()
	boss_trail.color = Color(1, 0.9, 0.6)
	boss_trail.size = Vector2(284, 6)
	bb.add_child(boss_trail)
	boss_fill = ColorRect.new()
	boss_fill.color = UIKit.DANGER
	boss_fill.size = Vector2(284, 6)
	bb.add_child(boss_fill)

	timer_label = UIKit.heading("", UIKit.MUSTARD)
	UIKit.place(timer_label, Control.PRESET_CENTER_TOP, -60, 8, 120, 16)
	timer_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	timer_label.add_theme_color_override("font_outline_color", UIKit.INK)
	timer_label.add_theme_constant_override("outline_size", 4)
	add_child(timer_label)

	toast_box = UIKit.vbox(2)
	UIKit.place(toast_box, Control.PRESET_CENTER_TOP, -160, 34, 320, 0)
	toast_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(toast_box)

	levelup = PanelContainer.new()
	levelup.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.08, 0.16, 0.18, 0.92), UIKit.XPC, 2))
	UIKit.place(levelup, Control.PRESET_CENTER, -90, -70, 180, 0)
	levelup.custom_minimum_size = Vector2(180, 0)
	levelup.visible = false
	levelup.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(levelup)

	GameState.stats_changed.connect(refresh)
	GameState.cash_changed.connect(func(_a, _d): cash_flash = 0.5; refresh())
	GameState.xp_changed.connect(refresh)
	GameState.stage_changed.connect(func(_s): refresh_objective())
	GameState.flag_changed.connect(func(_f): refresh_objective())
	Settings.changed.connect(func():
		UIKit.apply(self)
		refresh_objective())
	shown_hp = float(GameState.hp)
	refresh()
	refresh_objective()

func refresh() -> void:
	var mx := GameState.max_hp()
	lvl_label.text = "NICO  Lv %d" % GameState.level
	cash_label.text = "$%d" % GameState.cash
	hp_label.text = "%d/%d" % [GameState.hp, mx]
	hp_bar.color = Color(0.9, 0.3, 0.3) if float(GameState.hp) / mx > 0.3 else Color(1.0, 0.55, 0.2)
	var need := GameState.xp_needed(GameState.level)
	xp_bar.size.x = 96.0 * (float(GameState.xp) / float(need) if GameState.level < GameState.MAX_LEVEL else 1.0)
	if GameState.points > 0:
		lvl_label.text += "  +%d pt" % GameState.points

func refresh_objective() -> void:
	obj_label.text = "> " + Story.objective_text()

func set_prompt(t: String) -> void:
	if prompt_label.text != t:
		prompt_label.text = t

func _process(delta: float) -> void:
	var mx := float(GameState.max_hp())
	shown_hp = lerpf(shown_hp, float(GameState.hp), 0.25)
	hp_bar.size.x = 96.0 * clampf(float(GameState.hp) / mx, 0.0, 1.0)
	if cash_flash > 0.0:
		cash_flash -= delta
		cash_label.modulate = Color(1.4, 1.4, 1.4) if int(cash_flash * 10) % 2 == 0 else Color.WHITE
	else:
		cash_label.modulate = Color.WHITE
	var p: Player = world.room.player if world and world.room else null
	if p:
		if p.held != "":
			var w := Content.weapon(p.held)
			weapon_icon.texture = SpriteLib.icon(w.get("icon", "w_" + p.held))
			var pips := ""
			if int(w.get("durability", 1)) > 1:
				var n := int(ceil(10.0 * float(p.held_dur) / float(maxi(p.held_max, 1))))
				pips = "  " + "|".repeat(n)
			weapon_label.text = w.get("name", p.held) + pips
			weapon_label.add_theme_color_override("font_color", UIKit.CREAM)
		else:
			weapon_icon.texture = SpriteLib.icon("stat_atk")
			weapon_label.text = "Fists"
			weapon_label.add_theme_color_override("font_color", UIKit.DIM)
		set_prompt(p.current_context_text() if not world.dialogue_active() else "")
	_update_boss()
	if levelup.visible:
		levelup_t -= delta
		if levelup_t <= 0.0:
			levelup.visible = false
	if hint_t > 0.0:
		hint_t -= delta
		hint_panel.modulate.a = clampf(hint_t, 0.0, 1.0)
		if hint_t <= 0.0:
			hint_label.text = ""
			hint_panel.visible = false

func set_timer(t: String) -> void:
	timer_label.text = t

func show_hint(t: String, dur: float = 6.0) -> void:
	if not Settings.show_hints:
		return
	hint_label.text = t
	hint_t = dur
	hint_panel.visible = true
	hint_panel.size = Vector2(400, 0)
	hint_panel.modulate.a = 1.0

func set_bosses(list: Array) -> void:
	bosses = list.duplicate() if list else []
	boss_box.visible = not bosses.is_empty()
	if not bosses.is_empty():
		var names: Array = []
		for b in bosses:
			if names.find(b.display_name) < 0:
				names.append(b.display_name)
		boss_name.text = " & ".join(names)
		boss_trail.size.x = 284

func _update_boss() -> void:
	if bosses.is_empty():
		return
	var hp := 0
	var mx := 0
	for b in bosses:
		if is_instance_valid(b):
			hp += maxi(b.hp, 0)
			mx += b.max_hp
	if mx <= 0:
		return
	var w := 284.0 * float(hp) / float(mx)
	boss_fill.size.x = w
	boss_trail.size.x = lerpf(boss_trail.size.x, w, 0.04)
	boss_hp_text.text = "%d%%" % int(ceil(100.0 * float(hp) / float(mx)))

func toast(msg: String, col: Color = UIKit.CREAM, dur: float = 2.6) -> void:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.1, 0.07, 0.12, 0.88), Color(0.9, 0.85, 0.7, 0.6), 1))
	p.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var l := UIKit.wrap_label(msg, 300, col)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	p.add_child(l)
	toast_box.add_child(p)
	while toast_box.get_child_count() > 3:
		toast_box.get_child(0).queue_free()
		toast_box.remove_child(toast_box.get_child(0))
	var tw := p.create_tween()
	tw.tween_interval(dur)
	tw.tween_property(p, "modulate:a", 0.0, 0.4)
	tw.tween_callback(p.queue_free)

func show_level_up(level: int, gains: Dictionary) -> void:
	for c in levelup.get_children():
		c.queue_free()
	var v := UIKit.vbox(1)
	levelup.add_child(v)
	v.add_child(UIKit.heading("LEVEL UP!  Lv %d" % level, UIKit.XPC))
	var parts: Array = []
	for s in ["hp", "atk", "def", "agi", "tec"]:
		if int(gains.get(s, 0)) > 0:
			parts.append("%s +%d" % [s.to_upper(), int(gains[s])])
	v.add_child(UIKit.wrap_label("  ".join(parts), 170, UIKit.CREAM))
	if str(gains.get("auto", "")) != "":
		v.add_child(UIKit.wrap_label("Point auto-spent on %s (change in Status)." % str(gains.auto).to_upper(), 170, UIKit.DIM))
	elif GameState.points > 0:
		v.add_child(UIKit.wrap_label("+1 stat point! Spend it in Status %s." % InputPrompts.tag("status"), 170, UIKit.MUSTARD))
	levelup.visible = true
	levelup_t = 3.2
