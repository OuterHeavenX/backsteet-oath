extends Node
## Understandable progression: previews must be true and free.
## - what a preview says will happen equals what the game state becomes when the purchase / allocation is
##   really made (food incl. capped and full-HP cases, stat points, workbench tiers, weapon mastery)
## - preview numbers equal real hits landed in a real room (so the throwaway-actor bench cannot drift)
## - a preview leaves GameState byte-identical, emits no signal and makes no sound
## - the price shown is the price charged, with and without a standing discount
## - buying a manual arms its reminder; looking at a manual costs nothing
## Run: godot --headless --fixed-fps 60 res://tests/progression_tests.tscn

var w: Node
var fails := 0
var passes := 0
var signals_seen := 0

func check(c: bool, n: String) -> void:
	if c:
		passes += 1
	else:
		fails += 1
		print("FAIL: ", n)

func act(a: String, on: bool) -> void:
	var ev := InputEventAction.new()
	ev.action = a
	ev.pressed = on
	ev.strength = 1.0 if on else 0.0
	Input.parse_input_event(ev)

func frames(n: int) -> void:
	for i in n:
		await get_tree().process_frame

## GameState as it would be saved, minus the play clock (which runs by itself between frames).
func state_bytes() -> PackedByteArray:
	var d := GameState.to_dict().duplicate(true)
	d.stats.erase("playtime")
	return var_to_bytes(d)

## Current HP, max HP, stats and food bonuses: the same shape as Preview.food's before / after.
func vitals() -> Dictionary:
	var out := {"hp": GameState.hp, "max_hp": GameState.max_hp(), "food": GameState.food.duplicate()}
	for s in GameState.STATS:
		if s != "hp":
			out[s] = GameState.stat(s)
	return out

## A mid-game character with a bit of everything, so previews have something to disturb.
func midgame() -> void:
	GameState.reset_new_game()
	GameState.level = 7
	GameState.cash = 500
	GameState.points = 2
	GameState.alloc = {"hp": 1, "atk": 2, "def": 1, "agi": 0, "tec": 1}
	GameState.food = {"hp": 6, "atk": 3, "def": 0, "agi": 2, "tec": 1}
	GameState.gear = ["champion_wraps"]
	GameState.skills = ["shoulder", "rising"]
	GameState.bag = ["coffee", "tonic"]
	GameState.upgrades = {"grip": 1}
	GameState.mastery = {"long": 55, "chain": 10}
	GameState.flags = {"intro_done": true, "act1_done": true}
	GameState.quests = {"dog": {"state": "active", "step": 1, "data": {"seen": true}}}
	GameState.visited = {"oq_kettle": true, "cm_gate": true}
	GameState.room_visit = {"oq_kettle": 1, "cm_gate": 2}
	GameState.hp = 31

func start_world(setup: Callable) -> void:
	if w and is_instance_valid(w):
		w.queue_free()
		await frames(2)
	for a in ["move_left", "move_right", "move_up", "move_down", "punch", "kick", "guard", "interact", "run", "jump"]:
		act(a, false)
	get_tree().paused = false
	GameState.reset_new_game()
	Story.busy = false
	setup.call()
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await frames(10)

func _in_room(id: String, flags: Array, stage: String) -> Callable:
	return func():
		for f in flags:
			GameState.set_flag(f)
		GameState.stage = stage
		GameState.room = id
		GameState.spawn = "south" if id.begins_with("int_") else "west"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.show_hints = true
	Settings.difficulty = "normal"
	SaveService.current_slot = 3
	GameState.stats_changed.connect(func(): signals_seen += 1)
	GameState.cash_changed.connect(func(_a, _d): signals_seen += 1)
	GameState.inventory_changed.connect(func(): signals_seen += 1)
	GameState.xp_changed.connect(func(): signals_seen += 1)
	test_previews_leave_no_trace()
	await test_abandoned_bench()
	test_food_previews()
	test_stat_point_previews()
	test_workbench_and_mastery_previews()
	test_guide_reflects_data()
	await test_bench_matches_real_hits()
	await test_shop_prices_and_manuals()
	await test_status_menu()
	if w and is_instance_valid(w):
		w.queue_free()
	get_tree().paused = false
	print("PROGRESSION TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

# ---------------------------------------------------------------- previews are free
func test_previews_leave_no_trace() -> void:
	midgame()
	var before := state_bytes()
	var food_ref: Dictionary = GameState.food
	var quest_ref: Dictionary = GameState.quests["dog"]
	var bag_ref: Array = GameState.bag
	signals_seen = 0
	Preview.sheet()
	Preview.sheet("bat")
	for id in Content.items:
		Preview.food(id)
		PreviewText.food(id)
	for s in GameState.STATS:
		Preview.stat_point(s)
		PreviewText.stat_point(s, "pipe")
	for line in Content.upgrades:
		Preview.workbench(line)
		PreviewText.workbench(line)
	for fam in Content.weapon_families:
		Preview.mastery(fam)
		PreviewText.mastery(fam, "bat")
	for sid in Content.skills:
		Preview.technique(sid)
		PreviewText.technique(sid)
		PreviewText.technique_how(sid)
	for i in BuildGuideMenu.BUILDS.size():
		BuildGuideMenu.lines(i)
	check(state_bytes() == before, "every preview leaves GameState byte-identical")
	check(is_same(GameState.food, food_ref) and is_same(GameState.quests["dog"], quest_ref) and is_same(GameState.bag, bag_ref), "previews keep the same container objects")
	check(signals_seen == 0, "previews emit no GameState signal (saw %d)" % signals_seen)
	check(Audio.unlocked and not GameState.is_blocking_signals(), "sound and signals are back on after a preview")
	GameState.add_cash(1)
	check(signals_seen == 1, "signals really are live again")

func test_abandoned_bench() -> void:
	midgame()
	var before := state_bytes()
	# a Bench that is never closed (an early return, a script error half way through a preview)
	var b := Preview.Bench.new()
	GameState.consume("iron_stew")
	GameState.cash = 3
	GameState.upgrades["links"] = 3
	GameState.flags["x"] = true
	b.sheet()
	b = null
	check(state_bytes() != before, "(the abandoned bench really changed things)")
	await frames(2)
	check(state_bytes() == before and Audio.unlocked and not GameState.is_blocking_signals(), "a bench left open is put back at the end of the frame")
	var b2 := Preview.Bench.new()
	GameState.spend_point("atk")
	GameState.hp = 1
	b2 = null
	Preview.sheet()
	check(state_bytes() == before, "the next preview first puts back a bench that was left open")

# ---------------------------------------------------------------- food
func _food_case(id: String, label: String) -> Dictionary:
	var start := vitals()
	var before := state_bytes()
	var p := Preview.food(id)
	check(state_bytes() == before, "%s: food preview changed nothing" % label)
	check(p.before == start, "%s: preview 'before' is the current state" % label)
	var res := GameState.consume(id)
	check(p.after == vitals(), "%s: preview 'after' equals the state after really eating (%s vs %s)" % [label, p.after, vitals()])
	check(p.result == res, "%s: preview reports what consume reports" % label)
	check(bool(p.no_effect) == (start == vitals()), "%s: no_effect is true exactly when eating changed nothing" % label)
	return p

func test_food_previews() -> void:
	# hurt, nothing capped: heals and adds the permanent bonus
	midgame()
	var p := _food_case("pancakes", "pancakes hurt")
	check(int(p.after.hp) > int(p.before.hp) and int(p.after.max_hp) == int(p.before.max_hp) + 2, "pancakes: heal and +2 max HP shown")
	# full HP, no bonus: a wasted purchase, and the preview says so
	midgame()
	GameState.hp = GameState.max_hp()
	p = _food_case("coffee", "coffee at full HP")
	check(p.no_effect, "coffee at full HP is flagged as no effect")
	check(PreviewText.food("coffee").text.begins_with("No effect"), "and the words say so")
	# a heal larger than the missing HP is shown clipped to max
	midgame()
	GameState.hp = GameState.max_hp() - 4
	p = _food_case("ramen", "ramen nearly full")
	check(int(p.after.hp) == int(p.after.max_hp), "heal is clipped to max HP")
	# capped stat: heals but the stat stays
	midgame()
	GameState.food["def"] = int(Content.food_caps["def"])
	p = _food_case("meatloaf", "meatloaf with DEF capped")
	check(int(p.after["def"]) == int(p.before["def"]) and int(p.after.hp) > int(p.before.hp), "capped DEF stays, HP still heals")
	check(PreviewText.food("meatloaf").text.contains("maxed"), "capped stat is called out in words")
	# partly capped: +2 wanted, room for 1
	midgame()
	GameState.food["hp"] = int(Content.food_caps["hp"]) - 1
	p = _food_case("pancakes", "pancakes one under the cap")
	check(int(p.after.max_hp) == int(p.before.max_hp) + 1 and p.result.capped.has("hp"), "partial cap gives only what fits")
	# capped and full: nothing at all
	midgame()
	GameState.food["hp"] = int(Content.food_caps["hp"])
	GameState.hp = GameState.max_hp()
	p = _food_case("vitamin_pack", "vitamins capped at full HP")
	check(p.no_effect, "capped vitamins at full HP are flagged as no effect")
	# every edible item, from a hurt state
	for id in Content.items:
		if not str(Content.items[id].get("kind", "")) in ["food", "medicine"]:
			continue
		midgame()
		_food_case(id, id)

# ---------------------------------------------------------------- stat points
func test_stat_point_previews() -> void:
	for s in GameState.STATS:
		midgame()
		var before := state_bytes()
		var now := Preview.sheet()
		var p := Preview.stat_point(s)
		check(state_bytes() == before, "%s: stat preview changed nothing" % s)
		check(p.before == now, "%s: preview 'before' is the current sheet" % s)
		check(GameState.spend_point(s), "%s: point really spent" % s)
		var real := Preview.sheet()
		check(p.after == real, "%s: preview 'after' equals the sheet after really spending (%s vs %s)" % [s, p.after, real])
		check(p.after != p.before, "%s: a point changes something" % s)
	# a point not yet earned can be previewed, and shows exactly what the next level's point will do
	midgame()
	GameState.points = 0
	var p0 := Preview.stat_point("tec")
	check(GameState.points == 0 and int(p0.after.tec) == int(p0.before.tec) + 1, "preview works with no unspent point and lends none")
	GameState.points = 1
	GameState.spend_point("tec")
	check(p0.after == Preview.sheet(), "lent-point preview equals the real next point")
	# the concrete values really are the stat's: HP point gives POINT_HP now, ATK moves a hit, DEF softens one
	midgame()
	var hp := Preview.stat_point("hp")
	check(int(hp.after.max_hp) - int(hp.before.max_hp) == GameState.POINT_HP and int(hp.after.hp) - int(hp.before.hp) == GameState.POINT_HP, "HP point: max and current HP both rise")
	var atk := Preview.stat_point("atk")
	check(int(atk.after.combo) > int(atk.before.combo) and int(atk.after.hook) == int(atk.before.hook), "ATK point: combo damage up, damage taken unchanged")
	GameState.alloc["def"] = 0
	var df := Preview.stat_point("def")
	check(int(df.after.hook) <= int(df.before.hook) and int(df.after.combo) == int(df.before.combo), "DEF point: damage taken not higher, damage dealt unchanged")
	var agi := Preview.stat_point("agi")
	check(float(agi.after.walk) > float(agi.before.walk) and float(agi.after.run) > float(agi.before.run), "AGI point: faster")
	var tec := Preview.stat_point("tec")
	check(int(tec.after.tech) >= int(tec.before.tech) and float(tec.after.jab_dizzy) > float(tec.before.jab_dizzy), "TEC point: technique and dizzy build-up")
	# relaxed difficulty changes what a hit costs, and the preview follows the setting
	Settings.difficulty = "relaxed"
	var relaxed := Preview.sheet()
	Settings.difficulty = "normal"
	check(int(relaxed.heavy) < int(Preview.sheet().heavy), "damage-taken preview follows the difficulty setting")

# ---------------------------------------------------------------- workbench and mastery
func test_workbench_and_mastery_previews() -> void:
	for line in Content.upgrades:
		midgame()
		GameState.upgrades = {}
		var tiers: int = Content.upgrades[line].tiers.size()
		for t in tiers:
			var before := state_bytes()
			var p := Preview.workbench(line)
			check(state_bytes() == before, "%s tier %d: workbench preview changed nothing" % [line, t + 1])
			check(int(p.tier) == t, "%s: preview knows the current tier" % line)
			Preview.upgrade(line)      # what the workbench does when the purchase goes through
			var b := Preview.Bench.new()
			var changed := false
			for e in p.weapons:
				var real := b.weapon_sheet(e.id)
				check(e.after == real, "%s tier %d: %s after equals the real upgraded weapon (%s vs %s)" % [line, t + 1, e.id, e.after, real])
				changed = changed or e.after != e.before
			b.close()
			check(changed, "%s tier %d changes at least one number (not a no-op purchase)" % [line, t + 1])
		var done := Preview.workbench(line)
		check(int(done.tier) == tiers and done.weapons[0].before == done.weapons[0].after, "%s: nothing more to preview once maxed" % line)
	for fam in Content.weapon_families:
		midgame()
		var before2 := state_bytes()
		var m := Preview.mastery(fam)
		check(state_bytes() == before2, "%s: mastery preview changed nothing" % fam)
		var lv := GameState.mastery_level(fam)
		check(int(m.level) == lv and int(m.hits) > 0, "%s: preview knows the level and the hits to the next" % fam)
		for i in int(m.hits) - 1:
			GameState.add_mastery(fam, 1)
		check(GameState.mastery_level(fam) == lv, "%s: one hit short is still the old level" % fam)
		GameState.add_mastery(fam, 1)
		check(GameState.mastery_level(fam) == lv + 1, "%s: the stated number of hits reaches the next level" % fam)
		var b2 := Preview.Bench.new()
		check(m.after == b2.weapon_sheet(str(m.id)), "%s: mastery 'after' equals the weapon at the real next level" % fam)
		b2.close()
	# mastery can only grow by swinging: a family with nothing to swing must say so instead of promising a level
	check(PreviewText.mastery("throwable").contains("only grows by swinging"), "throwables are honest about mastery")
	midgame()
	GameState.mastery["long"] = 100000
	check(int(Preview.mastery("long").hits) == 0, "a mastered family has no next level")

# ---------------------------------------------------------------- build guidance
func test_guide_reflects_data() -> void:
	midgame()
	GameState.flags = {}
	GameState.skills = []
	var counter := "\n".join(BuildGuideMenu.lines(2))
	check(counter.contains("Guard Counter") and counter.contains("not on the shelf yet"), "a manual that is not sold yet is called out")
	check(BuildGuideMenu.manual_status("counter").state == "later", "manual status: later")
	GameState.set_flag("act2_started")
	counter = "\n".join(BuildGuideMenu.lines(2))
	var price := GameState.price_for("rec", int(Content.skill("counter").price))
	check(counter.contains("Guard Counter $%d" % price) and not counter.contains("Guard Counter at"), "once on the shelf the guide quotes the shop's price")
	GameState.learn("counter")
	check("\n".join(BuildGuideMenu.lines(2)).contains("Guard Counter (learned)"), "a learned manual is marked learned")
	# food advice names dishes that really raise that stat, at the price the shop charges
	for s in ["atk", "def", "tec", "hp", "agi"]:
		for f in BuildGuideMenu.foods_for(s, 99):
			var it: Dictionary = Content.item(f.item)
			check(int(it.get("bonus", {}).get(s, 0)) > 0 and Content.shops[f.shop].stock.has(f.item), "%s is sold at %s and raises %s" % [f.item, f.shop, s])
			check(int(f.price) == GameState.price_for(f.shop, int(it.price)), "%s guide price is the shop price" % f.item)
	GameState.food["atk"] = int(Content.food_caps["atk"])
	check("\n".join(BuildGuideMenu.lines(0)).contains("ATK food bonus is maxed"), "a capped food stat is not recommended again")

# ---------------------------------------------------------------- the bench against a real room
func _fresh(e: Actor) -> void:
	e.hp = e.max_hp
	e.set_state("idle")
	e.invuln = 0
	e.lying = false
	e.z = 0.0
	e.vz = 0.0
	e.combo_hits = 0

func test_bench_matches_real_hits() -> void:
	await start_world(_in_room("oq_brickrow", ["intro_done", "intro_seen", "met_mara"], "chain_dogs"))
	var r = w.room
	var p: Player = r.player
	GameState.alloc = {"hp": 0, "atk": 3, "def": 2, "agi": 1, "tec": 2}
	GameState.upgrades = {"links": 1}
	GameState.mastery = {"chain": 70}
	p.refresh_stats()
	check(str(Preview.ref_fighter().gang) == "dogs", "reference fighter on Brickrow is a Chain Dog")
	var e: Enemy = r.spawn_enemy("dogs_brawler", p.position + Vector2(40, 0))
	var brute: Enemy = r.spawn_enemy("dogs_heavy", p.position + Vector2(80, 0))
	e.hold = true
	brute.hold = true
	await frames(3)
	var sh := Preview.sheet("chain")
	# Nico's hits, landed the way Actor._check_hits lands them
	for pair in [["punch_a", "jab"], ["kick", "kick"]]:
		_fresh(e)
		p.atk_id = pair[0]
		p.atk = Content.attack(pair[0])
		var hp0 := e.hp
		e.receive_hit(p, p.atk, p.calc_raw(p.atk), 1)
		check(hp0 - e.hp == int(sh[pair[1]]), "%s: preview %d equals the real hit %d" % [pair[1], int(sh[pair[1]]), hp0 - e.hp])
	var total := 0
	for a in ["punch_a", "punch_b", "punch_c"]:
		_fresh(e)
		p.atk_id = a
		p.atk = Content.attack(a)
		var h := e.hp
		e.receive_hit(p, p.atk, p.calc_raw(p.atk), 1)
		total += h - e.hp
	check(total == int(sh.combo), "combo: preview %d equals three real hits %d" % [int(sh.combo), total])
	_fresh(e)
	p.equip_weapon("chain")
	p.atk_id = "swing_chain"
	p.atk = Content.attack("swing_chain")
	var hw := e.hp
	e.receive_hit(p, p.atk, p.calc_raw(p.atk), 1)
	check(hw - e.hp == int(sh.weapon) and str(sh.weapon_id) == "chain", "weapon swing: preview %d equals the real swing %d (upgrade and mastery included)" % [int(sh.weapon), hw - e.hp])
	var b := Preview.Bench.new()
	check(b.uses("chain") == p.held_max, "weapon durability: preview %d equals the weapon in hand %d" % [b.uses("chain"), p.held_max])
	b.close()
	p.held = ""
	p.weapon_spr.visible = false
	# the gang's hits on Nico
	for pair in [[e, "e_hook", "hook"], [brute, "e_heavy_punch", "heavy"]]:
		var foe: Enemy = pair[0]
		var d: Dictionary = Content.attack(pair[1])
		foe.atk_id = pair[1]
		p.hp = p.max_hp
		GameState.hp = p.hp
		p.set_state("idle")
		p.invuln = 0
		var before := p.hp
		p.receive_hit(foe, d, foe.calc_raw(d), -1)
		check(before - p.hp == int(sh[pair[2]]), "%s taken: preview %d equals the real hit %d" % [pair[2], int(sh[pair[2]]), before - p.hp])
	p.hp = p.max_hp
	GameState.hp = p.hp
	p.set_state("idle")
	p.refresh_stats()
	check(is_equal_approx(p.walk_speed, float(sh.walk)) and is_equal_approx(p.run_speed, float(sh.run)) and p.getup_invuln == int(sh.getup), "speed and get-up protection equal the live player's")
	check(p.perfect_window() == int(sh.perfect) and is_equal_approx(p.dizzy_mult(), float(sh.dizzy_mult)), "perfect window and dizzy multiplier equal the live player's")

# ---------------------------------------------------------------- shops
func _button(m: Node, prefix: String) -> Button:
	for b in m._all_buttons(m):
		if b is Button and str(b.text).begins_with(prefix):
			return b
	return null

func _has_label(n: Node, text: String) -> bool:
	for c in n.get_children():
		if c is Label and str(c.text).contains(text):
			return true
		if _has_label(c, text):
			return true
	return false

## First "$N" in a string (the price a row or button shows).
func _shown(text: String) -> int:
	var re := RegEx.new()
	re.compile("\\$(\\d+)")
	var m := re.search(text)
	return int(m.get_string(1)) if m else -1

func _open_shop(id: String) -> ShopMenu:
	w.close_all_menus()
	await frames(2)
	w.open_shop(id)
	await frames(4)
	return w.top_menu() as ShopMenu

func _price_round(discounted: bool) -> void:
	var tag := "with a discount" if discounted else "at list price"
	GameState.cash = 500
	GameState.upgrades = {}
	GameState.skills = []
	GameState.food = {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
	GameState.hp = 20
	for sid in ["diner", "rec", "garage"]:
		if discounted:
			Content.shops[sid]["discount"] = {"requires": "test_favour", "off": 0.25, "note": "Test favour: a quarter off."}
		else:
			Content.shops[sid].erase("discount")
	GameState.set_flag("test_favour", discounted)
	# food
	var m := await _open_shop("diner")
	check(_has_label(m, "Test favour: a quarter off.") == discounted, "diner %s: discount note shown only while it applies" % tag)
	var base := int(Content.item("pancakes").price)
	var row := _button(m, "Pancake Stack")
	var shown := _shown(row.text)
	check(shown == GameState.price_for("diner", base), "pancakes %s: row shows price_for ($%d)" % [tag, shown])
	check((shown < base and row.text.contains("(was $%d)" % base)) if discounted else (shown == base and not row.text.contains("was")), "pancakes %s: list price noted only when discounted" % tag)
	row.grab_focus()
	await frames(1)
	var pv := Preview.food("pancakes")
	check(m.preview.text.contains("HP %d/%d -> %d/%d" % [int(pv.before.hp), int(pv.before.max_hp), int(pv.after.hp), int(pv.after.max_hp)]), "pancakes %s: the row's words are the preview's numbers" % tag)
	var cash := GameState.cash
	m.lock_until = 0
	await m._buy_food("pancakes")
	check(cash - GameState.cash == shown, "pancakes %s: charged $%d, shown $%d" % [tag, cash - GameState.cash, shown])
	check(pv.after.hp == GameState.hp and pv.after.max_hp == GameState.max_hp(), "pancakes %s: the shop did what the preview said" % tag)
	# a meal that would change nothing is refused and not charged
	GameState.hp = GameState.max_hp()
	GameState.food["agi"] = int(Content.food_caps["agi"])
	cash = GameState.cash
	var meals := int(GameState.stats.get("food_eaten", 0))
	m.lock_until = 0
	await m._buy_food("milkshake")
	check(cash == GameState.cash and int(GameState.stats.get("food_eaten", 0)) == meals, "milkshake %s: a no-effect meal is not charged" % tag)
	# manual: looking is free, buying charges what was shown and arms the reminder
	m = await _open_shop("rec")
	base = int(Content.skill("rising").price)
	row = _button(m, "Rising Kick")
	shown = _shown(row.text)
	check(shown == GameState.price_for("rec", base) and (shown < base) == discounted, "rising %s: row shows price_for ($%d)" % [tag, shown])
	cash = GameState.cash
	var before := state_bytes()
	m.lock_until = 0
	m._buy_skill("rising", "")
	await frames(6)
	var page := w.top_menu() as ManualPreviewMenu
	check(page != null, "rising %s: pressing the row opens the manual preview" % tag)
	check(state_bytes() == before, "rising %s: opening the preview changed nothing and charged nothing" % tag)
	check(_has_label(page, PreviewText.technique_how("rising")) and _has_label(page, str(Content.skill("rising").desc)), "the preview shows the input for this device and what the move is for")
	check(_shown(_button(page, "Buy for").text) == shown, "rising %s: the preview's Buy button shows the row's price" % tag)
	page.close()
	await frames(4)
	check(state_bytes() == before and not GameState.has_skill("rising") and w.tutor.state("skill_rising") == 0, "rising %s: 'Not now' costs nothing, teaches nothing, arms nothing" % tag)
	m = w.top_menu() as ShopMenu
	m.lock_until = 0
	m._buy_skill("rising", "")
	await frames(6)
	page = w.top_menu() as ManualPreviewMenu
	page._buy()
	await frames(8)
	check(GameState.has_skill("rising") and cash - GameState.cash == shown, "rising %s: charged $%d, shown $%d" % [tag, cash - GameState.cash, shown])
	check(w.tutor.state("skill_rising") == Tutor.ARMED, "rising %s: buying the manual arms its reminder" % tag)
	# workbench
	m = await _open_shop("garage")
	base = int(Content.upgrades["grip"].tiers[0].price)
	row = _button(m, "Grip Tape")
	shown = _shown(row.text)
	check(shown == GameState.price_for("garage", base) and (shown < base) == discounted, "grip %s: row shows price_for ($%d)" % [tag, shown])
	var wb := Preview.workbench("grip")
	cash = GameState.cash
	m.lock_until = 0
	m._buy_upgrade("grip")
	await frames(6)
	var confirm := w.top_menu() as ConfirmMenu
	check(confirm != null and _shown(confirm.question) == shown, "grip %s: the confirmation quotes the row's price" % tag)
	confirm._answer(true)
	await frames(8)
	check(GameState.upgrade_tier("grip") == 1 and cash - GameState.cash == shown, "grip %s: charged $%d, shown $%d" % [tag, cash - GameState.cash, shown])
	var bench := Preview.Bench.new()
	check(wb.weapons[0].after == bench.weapon_sheet(str(wb.weapons[0].id)), "grip %s: the bought tier does what the preview said" % tag)
	bench.close()
	# not enough cash: the preview still opens, Buy does nothing
	GameState.cash = 1
	GameState.skills = []
	m = await _open_shop("rec")
	m.lock_until = 0
	m._buy_skill("rising", "")
	await frames(6)
	page = w.top_menu() as ManualPreviewMenu
	check(page != null and _button(page, "Buy for") == null and _button(page, "Not enough cash") != null, "rising %s: too poor to buy still lets you look" % tag)
	page._buy()
	await frames(4)
	check(GameState.cash == 1 and not GameState.has_skill("rising"), "rising %s: Buy without the cash does nothing" % tag)
	w.close_all_menus()
	await frames(2)
	GameState.flags.erase("tip_skill_rising")
	GameState.flags.erase("tipt_skill_rising")

func test_shop_prices_and_manuals() -> void:
	await start_world(_in_room("int_rec", ["intro_done", "intro_seen", "met_mara"], "chain_dogs"))
	await _price_round(false)
	await _price_round(true)
	for sid in ["diner", "rec", "garage"]:
		Content.shops[sid].erase("discount")
	# an automatic technique has nothing to press, so no reminder is armed for it
	GameState.cash = 500
	GameState.set_flag("act1_done")
	var m := await _open_shop("books")
	m.lock_until = 0
	m._buy_skill("retrieve", "act1_done")
	await frames(6)
	(w.top_menu() as ManualPreviewMenu)._buy()
	await frames(8)
	check(GameState.has_skill("retrieve") and w.tutor.state("skill_retrieve") == 0, "Quick Hands is learned without a reminder (nothing to press)")
	w.close_all_menus()
	await frames(2)

# ---------------------------------------------------------------- status menu
func test_status_menu() -> void:
	GameState.points = 1
	GameState.alloc = {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
	var sm := StatusMenu.new()
	w.push_menu(sm)
	await frames(4)
	var p := Preview.stat_point("atk")
	var atk := _button(sm, "ATK")
	atk.grab_focus()
	await frames(1)
	var txt: String = sm.info_label.text
	check(txt.contains(Preview.ref_label()) and txt.contains("jab " + PreviewText.ab(p.before.jab, p.after.jab)) and txt.contains("combo " + PreviewText.ab(p.before.combo, p.after.combo)),
		"Status: the ATK row quotes the preview's numbers against the named reference fighter (%s)" % txt)
	sm._spend("atk")
	await frames(4)
	check(Preview.sheet() == p.after, "Status: spending the point gives exactly what the row promised")
	var before := state_bytes()
	var guide := _button(sm, "Build ideas")
	check(guide != null, "Status: Build ideas is reachable from the Stats tab")
	guide.pressed.emit()
	await frames(4)
	var g := w.top_menu() as BuildGuideMenu
	check(g != null and g.detail.text.contains("STATS:") and g.detail.text.contains("MANUALS:"), "Build ideas opens and shows advice")
	_button(g, "Counter fighter").grab_focus()
	await frames(1)
	check(g.detail.text.contains("TEC") and g.detail.text.contains("Guard Counter"), "focusing a build shows that build")
	check(state_bytes() == before, "reading the guide changes nothing")
	w.close_all_menus()
	await frames(2)
