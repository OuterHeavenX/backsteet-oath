class_name StatusMenu
extends Menu
## Stats (with point spending + breakdown), Techniques (control cards), Bag (food/key items/gear), Weapons.

const TABS := ["Stats", "Techniques", "Bag", "Weapons"]
var tab := 0
var body: VBoxContainer
var info_label: Label
var tab_buttons: Array = []

func build() -> void:
	var c := make_frame("", Vector2(560, 300))
	var top := UIKit.hbox(4)
	c.add_child(top)
	tab_buttons.clear()
	for i in TABS.size():
		var b := UIKit.button(("[%s]" % TABS[i]) if i == tab else TABS[i], func(): _set_tab(i), 0)
		top.add_child(b)
		tab_buttons.append(b)
	var hint := UIKit.label("  %s / %s switch tabs" % ["LB" if InputPrompts.kind == "gamepad" else "Q", "RB" if InputPrompts.kind == "gamepad" else "R"], UIKit.DIM)
	top.add_child(hint)
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(540, 236)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	body = UIKit.vbox(2)
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	sc.add_child(body)
	info_label = UIKit.wrap_label("", 540, UIKit.DIM)
	c.add_child(info_label)
	match tab:
		0: _build_stats()
		1: _build_techniques()
		2: _build_bag()
		3: _build_weapons()
	first_focus = tab_buttons[tab]

func _set_tab(i: int) -> void:
	tab = i
	rebuild()

func _unhandled_input(event: InputEvent) -> void:
	if is_top():
		if event.is_action_pressed("ui_page_down") or event.is_action_pressed("status"):
			get_viewport().set_input_as_handled()
			if event.is_action_pressed("status"):
				close()
				return
			_set_tab((tab + 1) % TABS.size())
			return
		if event.is_action_pressed("ui_page_up"):
			get_viewport().set_input_as_handled()
			_set_tab((tab - 1 + TABS.size()) % TABS.size())
			return
	super._unhandled_input(event)

func _row(parts: Array, cols: Array) -> HBoxContainer:
	var h := UIKit.hbox(6)
	for i in parts.size():
		var l := UIKit.label(str(parts[i]), UIKit.CREAM if i == 0 else UIKit.DIM)
		l.custom_minimum_size = Vector2(cols[i] if i < cols.size() else 60, 0)
		h.add_child(l)
	return h

func _build_stats() -> void:
	var gs := GameState
	body.add_child(UIKit.label("Nico Vale   Level %d   XP %d / %d   Cash $%d" % [gs.level, gs.xp, gs.xp_needed(gs.level), gs.cash], UIKit.MUSTARD))
	body.add_child(UIKit.label("HP %d / %d     Unspent points: %d" % [gs.hp, gs.max_hp(), gs.points], UIKit.CREAM))
	body.add_child(_row(["STAT", "TOTAL", "BASE", "LEVEL", "POINTS", "FOOD", "GEAR"], [70, 50, 44, 44, 50, 44, 44]))
	for s in gs.STATS:
		var bd: Dictionary = gs.stat_breakdown(s)
		var h := UIKit.hbox(6)
		var b := UIKit.button(s.to_upper(), func(): _spend(s), 70)
		b.custom_minimum_size = Vector2(70, 0)
		b.focus_entered.connect(func(): info_label.text = gs.STAT_INFO[s] + ("   Confirm to spend a point (+%d)." % (gs.POINT_HP if s == "hp" else 1) if gs.points > 0 else ""))
		h.add_child(b)
		for v in [bd.total, bd.base, bd.level, bd.points, bd.food, bd.gear]:
			var l := UIKit.label(str(v), UIKit.CREAM)
			l.custom_minimum_size = Vector2(44 if v != bd.total else 50, 0)
			h.add_child(l)
		var cap: int = int(Content.food_caps.get(s, 8))
		h.add_child(UIKit.label("food cap %d" % cap, UIKit.DIM))
		body.add_child(h)
	body.add_child(UIKit.spacer(3))
	var auto_b := Widgets.cycler("Auto-spend level-up points", ["On (balanced)", "Off (choose myself)"], 0 if gs.auto_alloc else 1, func(i): gs.auto_alloc = i == 0, 360)
	auto_b.focus_entered.connect(func(): info_label.text = "Balanced auto-spend cycles ATK, DEF, TEC, AGI, HP. Turn it off to bank points and spend them here.")
	body.add_child(auto_b)
	body.add_child(UIKit.wrap_label("Each level: +7 HP, +1 ATK, +1 DEF, +0.5 AGI, +0.5 TEC and 1 stat point. Food gives small permanent boosts up to each stat's food cap. Coach Benny can refund your points later for a small fee.", 520, UIKit.DIM))
	var st: Dictionary = gs.stats
	body.add_child(UIKit.label("Enemies defeated %d   Knockouts %d   Meals %d   Playtime %s" % [int(st.get("defeated", 0)), int(st.get("deaths", 0)), int(st.get("food_eaten", 0)), UIKit.fmt_time(float(st.get("playtime", 0)))], UIKit.DIM))

func _spend(s: String) -> void:
	if GameState.spend_point(s):
		Audio.sfx("level_up", -8.0)
		rebuild()
	else:
		Audio.sfx("deny", -6.0)
		info_label.text = "No unspent points. You earn one every level."

func _build_techniques() -> void:
	body.add_child(UIKit.label("BASIC MOVES", UIKit.MUSTARD))
	var t := InputPrompts
	var basics := [
		["Punch combo", "%s %s %s" % [t.tag("punch"), t.tag("punch"), t.tag("punch")]],
		["Heavy finisher", "%s %s %s  (or Punch, Punch, Kick)" % [t.tag("punch"), t.tag("punch"), t.tag("kick")]],
		["Kick", t.tag("kick")],
		["Jump / jump kick", "%s then %s or %s" % [t.tag("jump"), t.tag("kick"), t.tag("punch")]],
		["Run", "Hold %s or double-tap left/right" % t.tag("run")],
		["Running punch / dropkick", "While running: %s / %s" % [t.tag("punch"), t.tag("kick")]],
		["Guard / perfect guard", "Hold %s. Press it just before a hit for a PERFECT guard." % t.tag("guard")],
		["Grab / pick up / throw", "%s near a weapon, crate, or a dizzy or downed foe" % t.tag("interact")],
		["Drop held item", "Hold %s + press %s" % [t.tag("guard"), t.tag("interact")]],
	]
	for b in basics:
		body.add_child(_row([b[0], b[1]], [170, 360]))
	body.add_child(UIKit.spacer(3))
	body.add_child(UIKit.label("TECHNIQUES LEARNED (%d / %d)" % [GameState.skills.size(), Content.skills.size()], UIKit.MUSTARD))
	if GameState.skills.is_empty():
		body.add_child(UIKit.label("None yet. Buy fighting manuals at Benny's Rec Center and Hollis Books.", UIKit.DIM))
	for sid in Content.skills:
		var s: Dictionary = Content.skills[sid]
		var owned := GameState.has_skill(sid)
		var h := UIKit.hbox(6)
		h.add_child(UIKit.icon_rect(SpriteLib.icon(s.get("icon", "skill")), 16))
		var b := UIKit.button(s.name if owned else "??? (not learned)", func(): pass, 150)
		var how := Story.format_text(s.get("how", ""))
		b.focus_entered.connect(func(): info_label.text = ("%s: %s  %s" % [s.name, how, s.desc]) if owned else "Find this manual in a shop.")
		h.add_child(b)
		h.add_child(UIKit.label(how if owned else "", UIKit.CREAM))
		body.add_child(h)

func _build_bag() -> void:
	body.add_child(UIKit.label("TAKEOUT BAG (%d / %d)  -  eat any time, even mid-fight from this menu" % [GameState.bag.size(), Content.bag_size], UIKit.MUSTARD))
	if GameState.bag.is_empty():
		body.add_child(UIKit.label("Empty. Shops let you take some food to go.", UIKit.DIM))
	for i in GameState.bag.size():
		var id: String = GameState.bag[i]
		var it: Dictionary = Content.item(id)
		var h := UIKit.hbox(6)
		h.add_child(UIKit.icon_rect(SpriteLib.icon(it.get("icon", id)), 16))
		var b := UIKit.button("Use %s" % it.get("name", id), func(): _use(i), 200)
		b.focus_entered.connect(func(): info_label.text = it.get("desc", "") + "  " + ShopMenu.effect_text(id))
		h.add_child(b)
		h.add_child(UIKit.label(ShopMenu.effect_text(id), UIKit.DIM))
		body.add_child(h)
	body.add_child(UIKit.spacer(3))
	body.add_child(UIKit.label("KEY ITEMS", UIKit.MUSTARD))
	if GameState.key_items.is_empty():
		body.add_child(UIKit.label("None.", UIKit.DIM))
	for k in GameState.key_items:
		var it2: Dictionary = Content.item(k)
		var h2 := UIKit.hbox(6)
		h2.add_child(UIKit.icon_rect(SpriteLib.icon(it2.get("icon", k)), 16))
		var n := int(GameState.key_items[k])
		var b2 := UIKit.button(it2.get("name", k) + (" x%d" % n if n > 1 else ""), func(): pass, 200)
		b2.focus_entered.connect(func(): info_label.text = it2.get("desc", ""))
		h2.add_child(b2)
		h2.add_child(UIKit.wrap_label(it2.get("desc", ""), 300, UIKit.DIM))
		body.add_child(h2)
	body.add_child(UIKit.spacer(3))
	body.add_child(UIKit.label("GEAR (always active)", UIKit.MUSTARD))
	if GameState.gear.is_empty():
		body.add_child(UIKit.label("None yet. Some side jobs reward gear.", UIKit.DIM))
	for g in GameState.gear:
		var it3: Dictionary = Content.item(g)
		var h3 := UIKit.hbox(6)
		h3.add_child(UIKit.icon_rect(SpriteLib.icon(it3.get("icon", g)), 16))
		h3.add_child(UIKit.label(it3.get("name", g), UIKit.CREAM))
		h3.add_child(UIKit.label(it3.get("desc", ""), UIKit.DIM))
		body.add_child(h3)

func _use(i: int) -> void:
	if i >= GameState.bag.size():
		return
	var id: String = GameState.bag[i]
	var it: Dictionary = Content.item(id)
	if it.get("revive", false):
		info_label.text = "Smelling salts work automatically when you're knocked out. Keep them in the bag."
		Audio.sfx("deny", -6.0)
		return
	if GameState.hp >= GameState.max_hp() and it.get("bonus", {}).is_empty():
		info_label.text = "You're already at full HP."
		Audio.sfx("deny", -6.0)
		return
	GameState.remove_from_bag(i)
	var res := GameState.consume(id)
	Audio.sfx("eat")
	var w = host
	if w and w.get("room") and w.room and w.room.player:
		w.room.player.hp = GameState.hp
	info_label.text = "Ate %s: +%d HP." % [it.get("name", id), int(res.heal)]
	rebuild()

func _build_weapons() -> void:
	body.add_child(UIKit.label("WEAPON MASTERY  -  using a weapon family makes it stronger (max 5)", UIKit.MUSTARD))
	for fam in Content.weapon_families:
		var f: Dictionary = Content.weapon_families[fam]
		var lv := GameState.mastery_level(fam)
		var h := UIKit.hbox(6)
		var b := UIKit.button(f.name, func(): pass, 170)
		b.focus_entered.connect(func(): info_label.text = f.desc)
		h.add_child(b)
		h.add_child(UIKit.label("*".repeat(lv) + ".".repeat(5 - lv) + "  Lv %d  (+%d%% damage)" % [lv, lv * 6], UIKit.CREAM))
		body.add_child(h)
	body.add_child(UIKit.spacer(3))
	body.add_child(UIKit.label("MARA'S WORKBENCH UPGRADES", UIKit.MUSTARD))
	for line in Content.upgrades:
		var u: Dictionary = Content.upgrades[line]
		var tier := GameState.upgrade_tier(line)
		body.add_child(_row([u.name, "Tier %d / 3" % tier, u.desc], [130, 70, 330]))
	body.add_child(UIKit.spacer(3))
	body.add_child(UIKit.label("WEAPON GUIDE", UIKit.MUSTARD))
	for wid in Content.weapons:
		var w: Dictionary = Content.weapons[wid]
		var fam_name: String = Content.weapon_families[w.family].name
		var h2 := UIKit.hbox(6)
		h2.add_child(UIKit.icon_rect(SpriteLib.icon(w.get("icon", "w_" + wid)), 16))
		h2.add_child(UIKit.label("%s  -  %s  (power %d, uses %d)" % [w.name, fam_name, int(w.get("power", 0)) if w.get("attack", "") != "" else int(w.get("throw_power", 0)), int(w.get("durability", 1))], UIKit.CREAM))
		body.add_child(h2)
