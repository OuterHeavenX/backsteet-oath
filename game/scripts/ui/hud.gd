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
var plate: Control
var trail_hp := 0.0
var hurt_face_t := 0.0
var last_hp := -1
var boss_draw: Control
var boss_shown := 0.0
var boss_trail_v := 1.0
var boss_frac := 1.0
var boss_title := ""
var bar_top: ColorRect
var bar_bot: ColorRect
var bars := 0.0
var card: Control
var card_t := 0.0
var card_name := ""
var card_sub := ""
var flash_rect: ColorRect
const BAR_H := 30.0

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS

func _ready() -> void:
	UIKit.apply(self)
	# cinematic letterbox bars (drawn under the rest of the HUD)
	bar_top = ColorRect.new()
	bar_top.color = Color(0.02, 0.015, 0.03)
	bar_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UIKit.place(bar_top, Control.PRESET_TOP_WIDE, 0, -40, 0, 40)
	add_child(bar_top)
	bar_bot = ColorRect.new()
	bar_bot.color = Color(0.02, 0.015, 0.03)
	bar_bot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	UIKit.place(bar_bot, Control.PRESET_BOTTOM_WIDE, 0, 0, 0, 40)
	add_child(bar_bot)
	plate = Control.new()
	plate.mouse_filter = Control.MOUSE_FILTER_IGNORE
	plate.position = Vector2(6, 6)
	plate.size = Vector2(200, 56)
	plate.draw.connect(_draw_plate)
	add_child(plate)
	# Hidden legacy labels keep their text current for tests and tools that read them.
	top_panel = PanelContainer.new()
	top_panel.visible = false
	add_child(top_panel)
	var v := UIKit.vbox(1)
	top_panel.add_child(v)
	lvl_label = UIKit.label("NICO  Lv 1", UIKit.MUSTARD)
	v.add_child(lvl_label)
	cash_label = UIKit.label("$0", UIKit.CASHC)
	v.add_child(cash_label)
	hp_label = UIKit.label("60/60", UIKit.CREAM)
	v.add_child(hp_label)
	hp_back = ColorRect.new()
	v.add_child(hp_back)
	hp_bar = ColorRect.new()
	hp_back.add_child(hp_bar)
	xp_bar = ColorRect.new()
	v.add_child(xp_bar)
	weapon_icon = UIKit.icon_rect(null, 12)
	v.add_child(weapon_icon)
	weapon_label = UIKit.label("Fists", UIKit.DIM)
	v.add_child(weapon_label)

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
	boss_box.add_theme_stylebox_override("panel", StyleBoxEmpty.new())
	UIKit.place(boss_box, Control.PRESET_CENTER_BOTTOM, -170, -40, 340, 34)
	boss_box.visible = false
	boss_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(boss_box)
	boss_draw = Control.new()
	boss_draw.mouse_filter = Control.MOUSE_FILTER_IGNORE
	boss_draw.custom_minimum_size = Vector2(340, 34)
	boss_draw.draw.connect(_draw_boss)
	boss_box.add_child(boss_draw)
	boss_name = UIKit.label("BOSS", UIKit.DANGER)
	boss_hp_text = UIKit.label("", UIKit.CREAM)
	boss_trail = ColorRect.new()
	boss_fill = ColorRect.new()

	card = Control.new()
	card.mouse_filter = Control.MOUSE_FILTER_IGNORE
	card.set_anchors_preset(Control.PRESET_FULL_RECT)
	card.draw.connect(_draw_card)
	add_child(card)
	flash_rect = ColorRect.new()
	flash_rect.color = Color(1, 1, 1, 0)
	flash_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flash_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(flash_rect)

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
	if GameState.points > 0:
		lvl_label.text += "  +%d pt" % GameState.points
	if plate:
		plate.queue_redraw()

func refresh_objective() -> void:
	obj_label.text = "> " + Story.objective_text()

func set_prompt(t: String) -> void:
	if prompt_label.text != t:
		prompt_label.text = t

func _process(delta: float) -> void:
	var mx := float(GameState.max_hp())
	shown_hp = lerpf(shown_hp, float(GameState.hp), 0.25)
	if last_hp >= 0 and GameState.hp < last_hp:
		hurt_face_t = 0.6
	last_hp = GameState.hp
	trail_hp = maxf(float(GameState.hp), move_toward(trail_hp, float(GameState.hp), mx * delta * 0.35))
	if hurt_face_t > 0.0:
		hurt_face_t -= delta
	plate.queue_redraw()
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
		set_prompt(p.current_context_text() if not world.dialogue_active() and InputPrompts.kind != "touch" else "")
	_update_boss()
	_update_cinema(delta)
	var right_pad := 84.0 if world and world.touch and world.touch.visible and not world.touch.docked else 6.0
	if obj_label.offset_right != -right_pad:
		obj_label.offset_right = -right_pad
		obj_label.offset_left = -right_pad - 258.0
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
		boss_title = boss_name.text.to_upper()
		boss_trail_v = 1.0
		boss_frac = 1.0

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
	boss_frac = float(hp) / float(mx)
	boss_trail_v = maxf(boss_frac, lerpf(boss_trail_v, boss_frac, 0.04))
	boss_hp_text.text = "%d%%" % int(ceil(100.0 * boss_frac))
	boss_draw.queue_redraw()

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

# ---------------------------------------------------------------- custom-drawn HUD pieces
static func _skew_rect(r: Rect2, sk: float) -> PackedVector2Array:
	return PackedVector2Array([Vector2(r.position.x + sk, r.position.y), Vector2(r.end.x + sk, r.position.y),
		Vector2(r.end.x, r.end.y), Vector2(r.position.x, r.end.y)])

func _skew_bar(c: Control, r: Rect2, frac: float, trail: float, fill: Color, back: Color, sk: float) -> void:
	c.draw_colored_polygon(_skew_rect(r.grow(1.0), sk), Color(0.04, 0.03, 0.06, 0.9))
	c.draw_colored_polygon(_skew_rect(r, sk), back)
	if trail > frac:
		var tr := Rect2(r.position, Vector2(r.size.x * clampf(trail, 0.0, 1.0), r.size.y))
		c.draw_colored_polygon(_skew_rect(tr, sk), Color(1.0, 0.93, 0.8, 0.9))
	if frac > 0.0:
		var fr := Rect2(r.position, Vector2(maxf(r.size.x * clampf(frac, 0.0, 1.0), sk + 1.0), r.size.y))
		c.draw_colored_polygon(_skew_rect(fr, sk), fill)
		var hl := Rect2(fr.position, Vector2(fr.size.x, maxf(1.0, r.size.y * 0.35)))
		c.draw_colored_polygon(_skew_rect(hl, sk * 0.35), Color(1, 1, 1, 0.22))

func _draw_plate() -> void:
	var c := plate
	var mx := float(GameState.max_hp())
	var hpf := clampf(float(GameState.hp) / mx, 0.0, 1.0)
	# backing plate with a slanted right edge
	c.draw_colored_polygon(PackedVector2Array([Vector2(-6, -6), Vector2(196, -6), Vector2(182, 50), Vector2(-6, 50)]), Color(0.05, 0.035, 0.07, 0.62))
	c.draw_line(Vector2(-6, 50), Vector2(182, 50), Color(0.95, 0.72, 0.23, 0.55), 1.0)
	# portrait medallion
	var med := Rect2(0, 0, 34, 34)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.16, 0.11, 0.18)
	sb.border_color = UIKit.MUSTARD
	sb.set_border_width_all(1)
	sb.set_corner_radius_all(5)
	sb.anti_aliasing = true
	c.draw_style_box(sb, med)
	var pi := SpriteLib.portrait_info("nico")
	if pi.texture:
		var expr := 0
		if hurt_face_t > 0.0:
			expr = 3
		elif hpf < 0.3:
			expr = 4
		elif world and world.room and world.room.combat_active():
			expr = 2
		var ps := float(pi.size)
		c.draw_texture_rect_region(pi.texture, med.grow(-1.5), Rect2(expr * ps, 0, ps, ps))
	# name + level badge + cash
	var fb := UIKit.font_big
	var fn := UIKit.font_num
	c.draw_string_outline(fb, Vector2(40, 10), "NICO", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, 3, Color(0.05, 0.03, 0.07))
	c.draw_string(fb, Vector2(40, 10), "NICO", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UIKit.CREAM)
	var badge := Rect2(80, 1, 26, 10)
	c.draw_colored_polygon(_skew_rect(badge, 2.0), UIKit.MUSTARD)
	c.draw_string(fn, Vector2(84, 9.5), "LV %d" % GameState.level, HORIZONTAL_ALIGNMENT_LEFT, -1, 9, UIKit.INK)
	if GameState.points > 0:
		c.draw_string(fn, Vector2(110, 9.5), "+%d" % GameState.points, HORIZONTAL_ALIGNMENT_LEFT, -1, 9, UIKit.XPC)
	var cash_col := UIKit.CASHC.lightened(0.5) if cash_flash > 0.0 and int(cash_flash * 10) % 2 == 0 else UIKit.CASHC
	c.draw_string_outline(fn, Vector2(124, 10), "$%d" % GameState.cash, HORIZONTAL_ALIGNMENT_RIGHT, 52, 11, 3, Color(0.05, 0.03, 0.07))
	c.draw_string(fn, Vector2(124, 10), "$%d" % GameState.cash, HORIZONTAL_ALIGNMENT_RIGHT, 52, 11, cash_col)
	# HP + XP
	var hp_col := Color(0.9, 0.26, 0.28) if hpf > 0.3 else Color(1.0, 0.55, 0.2)
	_skew_bar(c, Rect2(40, 15, 112, 8), hpf, trail_hp / mx, hp_col, Color(0.25, 0.07, 0.1), 3.0)
	c.draw_string_outline(fn, Vector2(156, 23), "%d" % GameState.hp, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, 3, Color(0.05, 0.03, 0.07))
	c.draw_string(fn, Vector2(156, 23), "%d" % GameState.hp, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, UIKit.CREAM)
	var need := GameState.xp_needed(GameState.level)
	var xpf := float(GameState.xp) / float(need) if GameState.level < GameState.MAX_LEVEL else 1.0
	_skew_bar(c, Rect2(40, 26, 104, 3), xpf, 0.0, UIKit.XPC, Color(0.06, 0.16, 0.2), 1.5)
	# weapon row
	var p: Player = world.room.player if world and world.room else null
	var wname := "Fists"
	var wtex := SpriteLib.icon("stat_atk")
	var dur := -1.0
	if p and p.held != "":
		var w := Content.weapon(p.held)
		wname = str(w.get("name", p.held))
		wtex = SpriteLib.icon(w.get("icon", "w_" + p.held))
		if int(w.get("durability", 1)) > 1:
			dur = float(p.held_dur) / float(maxi(p.held_max, 1))
	if wtex:
		c.draw_texture_rect(wtex, Rect2(40, 33, 12, 12), false)
	c.draw_string_outline(UIKit.font_small, Vector2(55, 43), wname, HORIZONTAL_ALIGNMENT_LEFT, -1, 9, 3, Color(0.05, 0.03, 0.07))
	c.draw_string(UIKit.font_small, Vector2(55, 43), wname, HORIZONTAL_ALIGNMENT_LEFT, -1, 9, UIKit.CREAM if dur != -1.0 or (p and p.held != "") else UIKit.DIM)
	if dur >= 0.0:
		var n := int(ceil(10.0 * dur))
		for i in 10:
			c.draw_rect(Rect2(124 + i * 5, 37, 3.5, 5), UIKit.MUSTARD if i < n else Color(0.3, 0.25, 0.3, 0.8))

func _draw_boss() -> void:
	var c := boss_draw
	var fb := UIKit.font_big
	c.draw_colored_polygon(PackedVector2Array([Vector2(0, 2), Vector2(340, 2), Vector2(332, 33), Vector2(-8, 33)]), Color(0.05, 0.03, 0.07, 0.72))
	c.draw_string_outline(fb, Vector2(6, 15), boss_title, HORIZONTAL_ALIGNMENT_LEFT, 280, 11, 3, Color(0.05, 0.03, 0.07))
	c.draw_string(fb, Vector2(6, 15), boss_title, HORIZONTAL_ALIGNMENT_LEFT, 280, 11, Color(1.0, 0.86, 0.8))
	c.draw_string(UIKit.font_num, Vector2(266, 15), boss_hp_text.text, HORIZONTAL_ALIGNMENT_RIGHT, 64, 10, UIKit.CREAM)
	_skew_bar(c, Rect2(4, 20, 324, 8), boss_frac, boss_trail_v, UIKit.DANGER, Color(0.22, 0.05, 0.08), 4.0)

# ---------------------------------------------------------------- cinematics
func _update_cinema(delta: float) -> void:
	var want := 1.0 if world and world.room and world.room.cutscene and Settings.cinematic_bars else 0.0
	bars = move_toward(bars, want, delta * 3.2)
	var e := bars * bars * (3.0 - 2.0 * bars)
	bar_top.offset_top = -BAR_H + BAR_H * e - 2.0
	bar_top.offset_bottom = BAR_H * e
	bar_bot.offset_top = -BAR_H * e
	bar_bot.offset_bottom = BAR_H - BAR_H * e + 2.0
	bar_top.visible = bars > 0.0
	bar_bot.visible = bars > 0.0
	var hud_a := 1.0 - e
	plate.modulate.a = hud_a
	obj_label.modulate.a = hud_a
	if card_t > 0.0:
		card_t -= delta
		card.queue_redraw()
	elif card.visible:
		card.visible = false
	if flash_rect.color.a > 0.0:
		flash_rect.color.a = maxf(0.0, flash_rect.color.a - delta * 2.5)

## Boss name card: slides in, holds, slides out (about 2.6 s). Purely visual.
func show_card(title: String, sub: String) -> void:
	card_name = title.to_upper()
	card_sub = sub
	card_t = 2.6
	card.visible = true
	card.queue_redraw()

func screen_flash(strength: float = 0.7) -> void:
	flash_rect.color = Color(1, 0.96, 0.9, clampf(strength * Settings.flash, 0.0, 0.85))

func _draw_card() -> void:
	if card_t <= 0.0:
		return
	var t := 2.6 - card_t
	var inn := clampf(t / 0.35, 0.0, 1.0)
	var out := clampf(card_t / 0.4, 0.0, 1.0)
	var k := minf(inn * inn * (3.0 - 2.0 * inn), out)
	var w := card.size.x
	var y := card.size.y * 0.36
	var slide := (1.0 - k) * -w * 0.5
	var band := PackedVector2Array([Vector2(slide - 20, y - 26), Vector2(slide + w * 0.62 + 30, y - 26),
		Vector2(slide + w * 0.62, y + 22), Vector2(slide - 20, y + 22)])
	card.draw_colored_polygon(band, Color(0.05, 0.03, 0.07, 0.86 * k))
	card.draw_colored_polygon(PackedVector2Array([Vector2(slide - 20, y + 22), Vector2(slide + w * 0.62, y + 22),
		Vector2(slide + w * 0.62 - 1.5, y + 25), Vector2(slide - 20, y + 25)]), Color(UIKit.DANGER, k))
	var fb := UIKit.font_big
	var tx := 28.0 + slide + (1.0 - inn) * 40.0
	card.draw_string_outline(fb, Vector2(tx, y + 4), card_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, 4, Color(0.05, 0.03, 0.07, k))
	card.draw_string(fb, Vector2(tx, y + 4), card_name, HORIZONTAL_ALIGNMENT_LEFT, -1, 24, Color(1.0, 0.9, 0.82, k))
	card.draw_string(UIKit.font_bold, Vector2(tx + 2, y + 17), card_sub.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(UIKit.MUSTARD, k))
