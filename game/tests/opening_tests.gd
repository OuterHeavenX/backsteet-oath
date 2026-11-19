extends Node
## The opening milestone (Kettle Street to Duke) and the systems it introduced: action-confirmed tips,
## Dot's plate, Benny's lesson and sparring, persistence and idempotence across save/load and retries.
## Run: godot --headless --fixed-fps 60 res://tests/opening_tests.tscn

var w: Node
var fails := 0
var passes := 0
var god := true
var auto_dialogue := true

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
		await get_tree().physics_frame
		if god and w and is_instance_valid(w) and w.room and w.room.player:
			w.room.player.hp = w.room.player.max_hp
			GameState.hp = GameState.max_hp()
		if auto_dialogue and w and is_instance_valid(w) and w.dialogue.active and not w.dialogue.choosing and i % 4 == 0:
			act("ui_accept", true)
			await get_tree().physics_frame
			act("ui_accept", false)

func tap(a: String, hold: int = 2) -> void:
	act(a, true)
	await frames(hold)
	act(a, false)
	await frames(1)

## Waits until cond() is true (or the frame budget runs out). Returns whether it became true.
func until(cond: Callable, max_frames: int = 600) -> bool:
	var i := 0
	while i < max_frames:
		if cond.call():
			return true
		await frames(1)
		i += 1
	return cond.call()

## Picks an option in an open choice box (waits for it to open first).
func choose(i: int) -> void:
	await until(func(): return w.dialogue.active and w.dialogue.choosing, 600)
	await frames(4)
	w.dialogue._choose(i)
	await frames(6)

func room() -> Room:
	return w.room

func tut() -> Tutor:
	return w.tutor

func start_world(setup: Callable) -> void:
	if w and is_instance_valid(w):
		w.queue_free()
		await get_tree().process_frame
		await get_tree().process_frame
	for a in ["move_left", "move_right", "move_up", "move_down", "punch", "kick", "guard", "interact", "run", "jump"]:
		act(a, false)
	get_tree().paused = false
	GameState.reset_new_game()
	Story.busy = false
	Story.sparring = false
	Story.ladder_lost = false
	setup.call()
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await frames(10)

func enemies() -> Array:
	var out: Array = []
	for a in room().actors:
		if a is Enemy and not a.dead and a.team == Actor.TEAM_ENEMY:
			out.append(a)
	return out

func kill_all() -> void:
	for e in enemies():
		e.min_hp = 0
		e.hp = 0
		e.take_damage_and_react(room().hazard_actor, {"knockdown": true, "kb": 100, "launch": 120}, 0.0, 1, false)

func save_roundtrip() -> void:
	var text := JSON.stringify(SaveService.build_payload())
	var d: Dictionary = JSON.parse_string(text)
	GameState.from_dict(d.data)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.show_hints = true
	Settings.difficulty = "normal"
	await test_intro_tips()
	await test_intro_without_tips()
	await test_tip_persistence()
	await test_dot_meal()
	await test_benny_lesson()
	await test_sparring_knockout()
	await test_old_saves()
	await test_guard_break_rules()
	await test_reference_and_devices()
	await test_combat_camera()
	await test_guides_and_tells()
	await test_lieutenants()
	await test_duke_and_street()
	await test_playtest_log()
	print("OPENING TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

# ---------------------------------------------------------------- the opening fight
func test_intro_tips() -> void:
	await start_world(func():
		GameState.set_flag("intro_seen"))
	var r := room()
	var p: Player = r.player
	await until(func(): return enemies().size() == 2, 240)
	check(enemies().size() == 2, "intro spawns two Chain Dogs")
	check(tut().is_pending("move") and tut().is_pending("combo") and tut().is_pending("guard") and tut().is_pending("throw"), "opening tips are armed")
	check(GameState.has_flag("tutor_v2"), "new opening is flagged on the save")
	await frames(40)
	check(tut().shown == "move", "one tip at a time: move is shown first (got '%s')" % tut().shown)
	check(w.hud.lesson_text.contains("Move with"), "tip text reaches the HUD")
	# the Dogs keep leaning on Dot: nobody attacks while the player has not approached
	var hp0 := p.hp
	god = false
	await frames(240)
	check(p.hp == hp0 and enemies()[0].hold and enemies()[1].hold, "Dogs hold back until approached")
	check(tut().shown == "move", "the tip persists instead of timing out")
	god = true
	# line up with a Dog: the tip completes on the real action
	var e: Enemy = enemies()[0]
	p.position = Vector2(e.position.x - 40.0, e.position.y)
	await frames(8)
	check(tut().is_learned("move"), "lining up with an enemy completes the move tip")
	check(not enemies().is_empty() and not enemies()[0].hold, "Dogs are released once the player walks up")
	check(w.hud.lesson_done, "the HUD acknowledges the success")
	await frames(120)
	check(tut().shown == "combo", "next tip is the combo (got '%s')" % tut().shown)
	# land a full combo on a frozen Dog
	e = enemies()[0]
	e.frozen = true
	e.set_meta("scripted_freeze", true)
	e.max_hp = 9999
	e.hp = 9999
	for o in enemies():
		if o != e:
			o.hold = true
	p.position = Vector2(e.position.x - 24.0, e.position.y)
	p.facing = 1
	for i in 3:
		await tap("punch")
		await frames(9)
	await frames(30)
	check(tut().is_learned("combo"), "the third hit of a combo completes the combo tip")
	# guard: a real blocked hit
	e.frozen = false
	e.set_meta("scripted_freeze", false)
	e.hold = false
	check(tut().is_pending("guard"), "guard tip still waiting")
	act("guard", true)
	p.facing = 1 if e.position.x > p.position.x else -1
	var ok := await until(func():
		if is_instance_valid(e) and not e.dead:
			p.facing = 1 if e.position.x > p.position.x else -1
		return tut().is_learned("guard"), 900)
	act("guard", false)
	check(ok, "blocking a real hit completes the guard tip")
	# finish the two Dogs: one drops a bottle and a third Dog arrives
	kill_all()
	await until(func(): return enemies().size() == 1 and (enemies()[0] as Enemy).arche_id == "flanker", 400)
	check(enemies().size() == 1, "the third Dog arrives")
	await frames(6)
	var bottle = null
	for pk in r.pickups:
		if pk.kind == "weapon" and pk.weapon_id == "bottle":
			bottle = pk
	check(bottle != null, "the first Dog drops a bottle to throw")
	await frames(140)
	check(tut().shown == "throw", "throw tip is shown when there is something to throw (got '%s')" % tut().shown)
	if bottle != null:
		p.position = bottle.position + Vector2(-4, 0)
		p.set_state("idle")
		await frames(4)
		await tap("interact")
		await frames(16)
		check(p.held == "bottle", "picked the bottle up")
		check(tut().is_pending("throw"), "picking up alone does not complete the throw tip")
		await tap("interact")
		await frames(10)
		check(tut().is_learned("throw"), "throwing completes the throw tip")
	kill_all()
	await until(func(): return GameState.has_flag("intro_done"), 900)
	check(GameState.has_flag("intro_done") and GameState.stage == "find_mara", "the fight ends in the usual story beat")
	check(tut().is_pending("door") and tut().is_pending("eat"), "door and meal tips are armed after the fight")
	check(not r.exits_locked and r.token_cap == -1, "exits unlocked and attacker cap restored")

func test_intro_without_tips() -> void:
	Settings.show_hints = false
	await start_world(func():
		GameState.set_flag("intro_seen"))
	await until(func(): return enemies().size() == 2, 240)
	await frames(30)
	check(enemies().size() == 2 and not enemies()[0].hold, "with tips off the Dogs do not wait")
	check(w.hud.lesson_text == "", "with tips off nothing is shown")
	kill_all()
	await until(func(): return enemies().size() == 1, 400)
	kill_all()
	await until(func(): return GameState.has_flag("intro_done"), 900)
	check(GameState.has_flag("intro_done"), "the opening completes with tips off")
	Settings.show_hints = true
	# skipping everything from the pause menu also releases the Dogs and never blocks progress
	await start_world(func():
		GameState.set_flag("intro_seen"))
	await until(func(): return enemies().size() == 2, 240)
	await frames(30)
	tut().skip_all()
	await frames(10)
	check(not tut().any_armed(), "skip clears every waiting tip")
	check(not enemies()[0].hold, "skipping the move tip releases the Dogs")
	kill_all()
	await until(func(): return enemies().size() == 1, 400)
	kill_all()
	await until(func(): return GameState.has_flag("intro_done"), 900)
	check(GameState.has_flag("intro_done"), "the opening completes after skipping every tip")

func test_tip_persistence() -> void:
	await start_world(func():
		GameState.set_flag("intro_seen"))
	await until(func(): return enemies().size() == 2, 240)
	tut().notify("combo3")
	tut().skip("guard")
	save_roundtrip()
	check(tut().is_learned("combo"), "a learned tip survives save/load")
	check(tut().state("guard") == Tutor.SKIPPED, "a skipped tip survives save/load")
	check(tut().is_pending("move"), "a waiting tip survives save/load")
	tut().arm("combo")
	tut().arm("guard")
	check(tut().is_learned("combo") and tut().state("guard") == Tutor.SKIPPED, "re-arming never resurrects a learned or skipped tip")
	# defeat + retry mid-tutorial: the fight restarts, learned tips stay learned, nothing is duplicated
	kill_all()
	await until(func(): return enemies().size() == 1, 400)
	GameState.set_flag("intro_seen")
	w._load_room("oq_kettle", "west")
	await frames(90)
	await until(func(): return enemies().size() == 2, 240)
	check(enemies().size() == 2, "re-entering mid-intro restarts the fight cleanly")
	check(tut().is_learned("combo"), "retrying keeps what was learned")
	kill_all()
	await until(func(): return enemies().size() == 1, 400)
	kill_all()
	await until(func(): return GameState.has_flag("intro_done"), 900)
	check(GameState.has_flag("intro_done"), "the restarted opening still completes")

# ---------------------------------------------------------------- Dot's plate
func _in_room(id: String, flags: Array, stage: String) -> Callable:
	return func():
		for f in flags:
			GameState.set_flag(f)
		GameState.stage = stage
		GameState.room = id
		GameState.spawn = "south"

func talk_to(npc_id: String) -> void:
	var n := room().find_npc(npc_id)
	room().talk_to(n)

func test_dot_meal() -> void:
	await start_world(_in_room("int_diner", ["intro_seen", "intro_done", "tutor_v2"], "find_mara"))
	tut().arm("eat")
	GameState.hp = 31
	room().player.refresh_stats()
	god = false
	var max0 := GameState.max_hp()
	var eaten0 := int(GameState.stats.get("food_eaten", 0))
	talk_to("dot")
	await until(func(): return GameState.has_flag("dot_meal_done"), 600)
	await until(func(): return not w.dialogue.active and not Story.busy, 600)
	check(GameState.has_flag("dot_meal_done"), "Dot serves the plate on the first talk")
	check(GameState.max_hp() == max0 + 2, "the plate gives its permanent bonus (max HP %d -> %d)" % [max0, GameState.max_hp()])
	check(GameState.hp > 31, "the plate heals")
	check(room().player.hp == GameState.hp and room().player.max_hp == GameState.max_hp(), "the player actor is refreshed")
	check(tut().is_learned("eat"), "eating completes the meal tip")
	check(int(GameState.stats.get("food_eaten", 0)) == eaten0 + 1, "counted as one meal")
	var cash0 := GameState.cash
	# second talk: the normal hub menu, no second plate
	talk_to("dot")
	await until(func(): return w.dialogue.active and w.dialogue.choosing, 600)
	check(w.dialogue.choosing, "second talk opens Dot's usual menu")
	await choose(3)
	await until(func(): return not Story.busy, 300)
	check(GameState.max_hp() == max0 + 2 and GameState.cash == cash0, "no second free plate")
	# save -> load -> talk again: still served only once
	save_roundtrip()
	check(GameState.has_flag("dot_meal_done") and GameState.max_hp() == max0 + 2, "the plate is remembered across save/load")
	# full health: the bonus still lands and the message path does not break
	await start_world(_in_room("int_diner", ["intro_seen", "intro_done", "tutor_v2"], "find_mara"))
	var m1 := GameState.max_hp()
	talk_to("dot")
	await until(func(): return GameState.has_flag("dot_meal_done"), 600)
	await until(func(): return not w.dialogue.active and not Story.busy, 600)
	check(GameState.max_hp() == m1 + 2 and GameState.hp == GameState.max_hp(), "at full health the bonus still applies and HP follows the new maximum")
	# capped food bonus (a New Game+ save): nothing breaks and the flag is still set
	await start_world(func():
		_in_room("int_diner", ["intro_seen", "intro_done", "tutor_v2"], "find_mara").call()
		GameState.food["hp"] = int(Content.food_caps.get("hp", 30)))
	var m2 := GameState.max_hp()
	talk_to("dot")
	await until(func(): return GameState.has_flag("dot_meal_done"), 600)
	await until(func(): return not w.dialogue.active and not Story.busy, 600)
	check(GameState.max_hp() == m2 and GameState.has_flag("dot_meal_done"), "a capped bonus is handled")
	god = true

# ---------------------------------------------------------------- Benny's lesson
func test_benny_lesson() -> void:
	await start_world(_in_room("int_rec", ["intro_seen", "intro_done", "tutor_v2", "met_mara"], "chain_dogs"))
	var xp0 := GameState.xp
	var lvl0 := GameState.level
	var cash0 := GameState.cash
	var def0 := int(GameState.stats.get("defeated", 0))
	talk_to("benny")
	await choose(0)   # Take the lesson
	check(GameState.has_skill("shoulder") and GameState.has_flag("benny_lesson_done"), "Benny teaches Shoulder Charge for free")
	check(GameState.cash == cash0, "the lesson costs nothing")
	await until(func(): return enemies().size() == 1, 400)
	check(enemies().size() == 1 and Story.sparring and room().exits_locked, "a sparring partner steps in and the round is contained")
	await frames(60)
	check(tut().shown in ["run", "shoulder"], "the lesson tips are showing (got '%s')" % tut().shown)
	# do the move for real: run, then punch
	var p: Player = room().player
	var e: Enemy = enemies()[0]
	e.hold = true
	p.position = Vector2(e.position.x - 150.0, e.position.y)
	p.facing = 1
	act("run", true)
	act("move_right", true)
	await frames(14)
	check(tut().is_learned("run"), "running completes the run tip")
	await tap("punch")
	act("move_right", false)
	act("run", false)
	await frames(30)
	check(tut().is_learned("shoulder"), "using the technique completes its tip")
	# the partner cannot be knocked out, gives nothing, and taps out
	e.hold = false
	e.hp = 1
	e.take_damage_and_react(p, {"knockdown": true, "kb": 100, "launch": 120, "power": 99}, 99.0, 1, false)
	check(e.hp >= 1 and not e.dead, "sparring partners are never knocked out")
	await until(func(): return w.dialogue.active or enemies().is_empty(), 600)
	await until(func(): return enemies().size() == 1 and (enemies()[0] as Enemy).arche_id == "blocker", 900)
	check(enemies().size() == 1 and (enemies()[0] as Enemy).arche_id == "blocker", "round two is a blocker")
	var tire := false
	for pk in room().pickups:
		if pk.kind == "weapon" and pk.weapon_id == "tire":
			tire = true
	check(tire, "something heavy to throw is provided")
	await frames(60)
	check(tut().shown == "blocker", "the blocker tip is showing (got '%s')" % tut().shown)
	# break the guard with a finisher
	var b: Enemy = enemies()[0]
	b.hold = true
	b.set_state("guard")
	b.guard_t = 99
	b.guard_hold = 600
	b.facing = -1
	p.position = Vector2(b.position.x - 24.0, b.position.y)
	p.facing = 1
	p.set_state("idle")
	p.start_attack("punch_c")
	await frames(20)
	check(tut().is_learned("blocker"), "breaking the guard completes the blocker tip")
	await until(func(): return not Story.sparring and not Story.busy and not w.dialogue.active, 1500)
	check(not Story.sparring and not room().exits_locked, "the session ends and the exits unlock")
	check(enemies().is_empty(), "no sparring partner is left behind")
	var tire_left := false
	for pk in room().pickups:
		if pk.kind == "weapon" and pk.weapon_id == "tire":
			tire_left = true
	check(not tire_left and p.held != "tire", "the practice tire is cleared away")
	check(GameState.xp == xp0 and GameState.level == lvl0 and GameState.cash == cash0, "sparring gives no XP or cash")
	check(int(GameState.stats.get("defeated", 0)) == def0, "sparring partners do not count as defeated enemies")
	# second talk: no second lesson; the menu offers sparring
	talk_to("benny")
	await until(func(): return w.dialogue.active and w.dialogue.choosing, 600)
	check(GameState.skills.count("shoulder") == 1, "the technique is not granted twice")
	await choose(3)
	await until(func(): return not Story.busy, 300)
	# "just teach me the move": no sparring, a reminder is armed instead
	await start_world(_in_room("int_rec", ["intro_seen", "intro_done", "tutor_v2", "met_mara"], "chain_dogs"))
	talk_to("benny")
	await choose(1)
	await until(func(): return not Story.busy and not w.dialogue.active, 600)
	check(GameState.has_skill("shoulder") and enemies().is_empty() and not Story.sparring, "the quick option teaches the move without a fight")
	check(tut().state("skill_shoulder") == Tutor.ARMED, "a reminder for the new move is armed")
	# "not now": nothing is taken, the offer stays
	await start_world(_in_room("int_rec", ["intro_seen", "intro_done", "tutor_v2", "met_mara"], "chain_dogs"))
	talk_to("benny")
	await choose(2)
	await choose(3)
	await until(func(): return not Story.busy and not w.dialogue.active, 600)
	check(not GameState.has_skill("shoulder") and not GameState.has_flag("benny_lesson_done"), "declining keeps the offer for later")
	# while the free lesson is on offer, the shop will not sell the same technique
	GameState.cash = 100
	var sm := ShopMenu.new()
	sm.shop_id = "rec"
	w.push_menu(sm)
	await get_tree().process_frame
	await get_tree().process_frame
	check(sm._free_lesson("shoulder") and not sm._free_lesson("rising"), "the shop marks Shoulder Charge as Benny's free lesson")
	await sm._buy_skill("shoulder", "")
	check(GameState.cash == 100 and not GameState.has_skill("shoulder") and w.menus.size() == 1, "and refuses to charge for it")
	GameState.set_flag("benny_lesson_done")
	check(not sm._free_lesson("shoulder"), "once the offer is gone it is an ordinary manual again")
	GameState.set_flag("benny_lesson_done", false)
	w.close_all_menus()
	await frames(4)
	# already owned (older save / New Game+): no duplicate, the offer retires
	await start_world(func():
		_in_room("int_rec", ["intro_seen", "intro_done", "tutor_v2", "met_mara"], "chain_dogs").call()
		GameState.learn("shoulder"))
	talk_to("benny")
	await until(func(): return w.dialogue.active and w.dialogue.choosing, 900)
	check(GameState.has_flag("benny_lesson_done") and GameState.skills.count("shoulder") == 1, "an owned technique retires the offer without a duplicate")
	await choose(3)
	await until(func(): return not Story.busy, 300)

func test_sparring_knockout() -> void:
	await start_world(func():
		_in_room("int_rec", ["intro_seen", "intro_done", "tutor_v2", "met_mara", "benny_lesson_done"], "chain_dogs").call()
		GameState.cash = 50)
	talk_to("benny")
	await choose(1)   # Spar a round
	await until(func(): return enemies().size() == 1, 400)
	check(Story.sparring, "free sparring starts from Benny's menu")
	god = false
	var p: Player = room().player
	var deaths0 := int(GameState.stats.get("deaths", 0))
	p.hp = 1
	GameState.hp = 1
	p.take_damage_and_react(enemies()[0], {"knockdown": true, "kb": 100, "launch": 120, "power": 50}, 50.0, -1, false)
	await until(func(): return not Story.sparring and not Story.busy and not w.dialogue.active, 1500)
	check(not w.defeated and w.menus.is_empty(), "a sparring knockout shows no defeat screen")
	check(GameState.cash == 50 and int(GameState.stats.get("deaths", 0)) == deaths0, "a sparring knockout costs nothing and is not counted as a knockout")
	check(not p.dead and GameState.hp > 1, "Nico gets back up")
	check(not room().exits_locked and enemies().is_empty(), "the room is left clean after a sparring knockout")
	god = true

# ---------------------------------------------------------------- saves from before this opening
func test_old_saves() -> void:
	# a 1.3 save past the intro: no tips armed, nothing forced
	await start_world(_in_room("oq_kettle", ["intro_seen", "intro_done", "met_mara"], "chain_dogs"))
	await frames(60)
	check(not tut().any_armed() and w.hud.lesson_text == "", "older saves get no opening tips")
	check(Story._dot_meal_due() and Story._benny_lesson_due(), "older saves still in the Old Quarter may take the favours")
	# a 1.3 save past Duke: the favours are not offered
	await start_world(_in_room("int_diner", ["intro_seen", "intro_done", "met_mara", "boss_duke"], "market"))
	check(not Story._dot_meal_due() and not Story._benny_lesson_due(), "older saves past Duke are not offered the opening favours")
	var m0 := GameState.max_hp()
	talk_to("dot")
	await until(func(): return w.dialogue.active and w.dialogue.choosing, 600)
	check(w.dialogue.choosing and GameState.max_hp() == m0, "Dot opens her usual menu for an older save")
	await choose(3)
	await until(func(): return not Story.busy, 300)
	# a new-opening save keeps the favours available after Duke
	await start_world(_in_room("int_diner", ["intro_seen", "intro_done", "tutor_v2", "met_mara", "boss_duke"], "market"))
	check(Story._dot_meal_due(), "a new-opening save can still collect the plate later")

# ---------------------------------------------------------------- guard-break rules
func _blocker_at(dx: float) -> Enemy:
	var r := room()
	for a in r.actors.duplicate():
		if a is Enemy:
			r.remove_actor(a)
	var p: Player = r.player
	p.position = Vector2(700, 290)
	p.facing = 1
	p.set_state("idle")
	var e: Enemy = r.spawn_enemy("dogs_blocker", Vector2(700 + dx, 290), {})
	e.max_hp = 9999
	e.hp = 9999
	e.hold = true
	e.facing = -1
	e.set_state("guard")
	e.guard_t = 99
	e.guard_hold = 9999
	return e

func test_guard_break_rules() -> void:
	await start_world(_in_room("oq_chainlot", ["intro_seen", "intro_done", "met_mara", "duke_intro_seen"], "chain_dogs"))
	GameState.spawn = "west"
	var p: Player = room().player
	# a jab is blocked
	var e := _blocker_at(24.0)
	var hp0 := e.hp
	p.start_attack("punch_a")
	await frames(14)
	check(e.hp == hp0, "a jab is blocked by a raised guard")
	# a thrown bottle is blocked too
	e = _blocker_at(120.0)
	hp0 = e.hp
	p.equip_weapon("bottle")
	p.throw_held()
	await frames(50)
	check(e.hp == hp0, "a thrown bottle is blocked by a raised guard")
	# a heavy thrown object breaks the guard and floors the blocker
	e = _blocker_at(120.0)
	hp0 = e.hp
	p.equip_weapon("trash_can")
	p.throw_held()
	await until(func(): return e.hp < hp0, 90)
	check(e.hp < hp0 and e.state == "knockdown", "a heavy thrown object breaks a guard and knocks the blocker down")
	# enemy-thrown bricks do not break the player's guard (rule only applies to the player's throws)
	for a in room().actors.duplicate():
		if a is Enemy:
			room().remove_actor(a)
	var thrower: Enemy = room().spawn_enemy("yard_thrower", Vector2(860, 290), {})
	thrower.hold = true
	thrower.facing = -1
	god = false
	p.position = Vector2(700, 290)
	p.facing = 1
	p.set_state("guard")
	p.guard_t = 99
	act("guard", true)
	await frames(3)
	var php := p.hp
	room().spawn_projectile(thrower, "brick", Vector2(840, 290), 30.0, -1, 1)
	await frames(50)
	act("guard", false)
	check(p.hp == php, "an enemy's brick is still blocked by the player's guard")
	god = true

# ---------------------------------------------------------------- reference page and device prompts
func test_reference_and_devices() -> void:
	await start_world(_in_room("oq_kettle", ["intro_seen", "intro_done", "tutor_v2"], "find_mara"))
	tut().arm("guard", true)
	room().spawn_enemy("dogs_brawler", Vector2(400, 300), {}).hold = true
	await frames(40)
	InputPrompts.kind = "keyboard"
	await frames(4)
	var kb: String = w.hud.lesson_text
	InputPrompts.kind = "gamepad"
	await frames(4)
	var pad: String = w.hud.lesson_text
	InputPrompts.kind = "touch"
	await frames(4)
	var touch: String = w.hud.lesson_text
	InputPrompts.kind = "keyboard"
	check(kb != "" and kb != pad and pad != touch, "tip text follows the input device (%s | %s | %s)" % [kb, pad, touch])
	check(pad.contains("(LB)") and touch.contains("[GUARD]"), "pad and touch labels are used")
	var lines: Array = tut().reference_lines()
	check(lines.size() >= 8, "the tips reference page lists the basics")
	var m := TipsMenu.new()
	w.push_menu(m)
	await get_tree().process_frame
	await get_tree().process_frame
	check(w.menus.size() == 1, "the tips page opens from the world")
	w.close_all_menus()
	await frames(4)
	# a technique reminder: shows at a fight, completes on use, and never comes back
	GameState.learn("rising")
	tut().skip_all()
	tut().arm_skill("rising")
	await frames(60)
	check(tut().shown == "skill_rising" and w.hud.lesson_text.contains("Rising Kick"), "a new technique gets a reminder (got '%s')" % tut().shown)
	room().player.start_attack("rising_kick")
	await frames(4)
	check(tut().is_learned("skill_rising"), "using the technique retires its reminder")
	tut().arm_skill("rising")
	check(tut().is_learned("skill_rising"), "the reminder does not return")

# ---------------------------------------------------------------- combat camera
func _clear_enemies() -> void:
	for a in room().actors.duplicate():
		if a is Enemy:
			room().remove_actor(a)

func test_combat_camera() -> void:
	Settings.combat_camera = "close"
	await start_world(_in_room("oq_kettle", ["intro_seen", "intro_done", "met_mara"], "find_mara"))
	GameState.spawn = "west"
	var r := room()
	var p: Player = r.player
	p.position = Vector2(800, 290)
	await frames(60)
	var zc := Content.tune("camera", "combat_zoom", 1.16)
	check(is_equal_approx(r.camera.zoom.x, 1.0), "no zoom while exploring (zoom %.3f)" % r.camera.zoom.x)
	var wide_w: float = r.view_width()
	# a fight starts: the zoom eases in and never reverses while the fight lasts
	var e1: Enemy = r.spawn_enemy("dogs_brawler", Vector2(900, 290), {})
	e1.hold = true
	var last: float = r.camera.zoom.x
	var monotone := true
	for i in 240:
		await frames(1)
		if r.camera.zoom.x < last - 0.0001:
			monotone = false
		last = r.camera.zoom.x
		if i == 100:
			# one enemy goes down and another arrives: the framing must hold, not pump out and back in
			r.remove_actor(e1)
			var e2: Enemy = r.spawn_enemy("dogs_flanker", Vector2(940, 300), {})
			e2.hold = true
	check(monotone, "the zoom never pumps while fighters come and go")
	check(absf(r.camera.zoom.x - zc) < 0.01, "the fight framing settles at the tuned zoom (%.3f)" % r.camera.zoom.x)
	check(r.view_width() < wide_w - 40.0, "the visible street is narrower in a fight")
	# the street's bottom edge stays on the bottom edge of the screen
	var vs: Vector2 = r.get_viewport_rect().size
	var bottom_screen := (Room.VIEW_H - r.camera.position.y) * r.camera.zoom.x + vs.y * 0.5
	check(absf(bottom_screen - (w.playfield_top() + Room.VIEW_H)) < 1.0, "the bottom of the street stays fixed on screen when zoomed (%.1f)" % bottom_screen)
	# turning around in a fight does not swing the camera
	await frames(60)
	var cx0: float = r.cam_x
	p.facing = -p.facing
	await frames(40)
	check(absf(r.cam_x - cx0) < 3.0, "turning around mid-fight does not swing the camera (moved %.1f)" % absf(r.cam_x - cx0))
	# enemies never attack from outside the framed view
	_clear_enemies()
	p.position = Vector2(800, 290)
	god = true
	for id in ["dogs_thrower", "dogs_brawler", "dogs_weapon", "dogs_flanker"]:
		var e: Enemy = r.spawn_enemy(id, Vector2(p.position.x + (r.screen_width() * 0.5 - 6.0) * (1 if id != "dogs_flanker" else -1), 280), {})
		e.leash = true
	var offscreen_attacks := 0
	var attacks_seen := 0
	var was: Dictionary = {}
	for i in 900:
		await frames(1)
		for a in r.actors:
			if a is Enemy and not a.dead:
				var atk_now: bool = a.state == "attack"
				if atk_now and not was.get(a.get_instance_id(), false):
					attacks_seen += 1
					if a.position.x < r.cam_left() or a.position.x > r.cam_right():
						offscreen_attacks += 1
				was[a.get_instance_id()] = atk_now
	check(attacks_seen > 3, "enemies attacked during the camera test (%d attacks)" % attacks_seen)
	check(offscreen_attacks == 0, "no attack starts outside the framed view (%d did)" % offscreen_attacks)
	# after the fight the camera eases back out
	_clear_enemies()
	await frames(int(Content.tune("camera", "hold_seconds", 2.5) * 60.0) + 200)
	check(absf(r.camera.zoom.x - 1.0) < 0.01, "the camera eases back out after the fight (%.3f)" % r.camera.zoom.x)
	# the Wide setting keeps the 1.3 framing
	Settings.combat_camera = "wide"
	r.spawn_enemy("dogs_brawler", Vector2(900, 290), {}).hold = true
	await frames(120)
	check(is_equal_approx(r.camera.zoom.x, 1.0), "Combat camera: Wide never zooms")
	Settings.combat_camera = "close"
	_clear_enemies()
	# small rooms: the camera still keeps the player in view when zoomed
	await start_world(_in_room("int_rec", ["intro_seen", "intro_done", "met_mara", "benny_lesson_done"], "chain_dogs"))
	r = room()
	p = r.player
	r.spawn_enemy("dogs_brawler", Vector2(560, 320), {}).hold = true
	p.position = Vector2(40, 320)
	await frames(200)
	check(p.position.x >= r.cam_left() and p.position.x <= r.cam_right(), "in a small room the zoomed camera still shows the player")
	check(r.cam_left() >= -0.5 and r.cam_right() <= r.width + 0.5, "the zoomed camera stays inside a small room")

# ---------------------------------------------------------------- guides and tells
func test_guides_and_tells() -> void:
	Settings.combat_guides = true
	await start_world(_in_room("oq_chainlot", ["intro_seen", "intro_done", "met_mara", "duke_intro_seen", "tutor_v2"], "chain_dogs"))
	var r := room()
	var p: Player = r.player
	p.position = Vector2(700, 290)
	_clear_enemies()
	var e: Enemy = r.spawn_enemy("yard_heavy", Vector2(760, 290), {})
	e.hold = true
	await frames(6)
	check(p.keyline != null and p.keyline.visible and p.ring != null and p.ring.visible, "Nico has a keyline and a ground ring")
	check(e.ring != null and e.ring.visible, "an enemy standing in Nico's lane shows a lane ring")
	e.position.y = 330
	await frames(3)
	check(not e.ring.visible, "the lane ring hides when the enemy is in another lane")
	e.position.y = 290
	# tells by kind: shape, tint and the ground a surrounding attack covers
	e.hold = false
	e.set_state("idle")
	e._launch_attack("e_heavy_punch")
	await frames(3)
	check(e.tell != null and e.tell.visible and e.tell.kind == "heavy", "a guardable heavy attack shows the warning tell")
	check(e.ring.visible and e.ring.col.r > 0.8 and e.ring.col.g < 0.5, "the attacker's ring turns to the danger colour during wind-up")
	e.set_state("idle")
	e.cooldowns.clear()
	e._launch_attack("e_grab")
	await frames(3)
	check(e.tell.visible and e.tell.kind == "unblockable", "a grab shows the cannot-be-guarded tell")
	check(tut().state("unblockable") != 0, "the first unblockable arms its one-time tip")
	e.set_state("idle")
	e._launch_attack("sabine_bash")
	await frames(3)
	check(e.tell.visible and e.tell.kind == "break", "a guard-breaking attack shows the guard-break tell")
	e.set_state("idle")
	e._launch_attack("otto_slam")
	await frames(3)
	check(e.zone != null and e.zone.visible and e.zone.rx >= 80.0, "a surrounding attack marks the ground it will cover")
	e.set_state("idle")
	await frames(3)
	check(not e.tell.visible and not e.zone.visible, "tells clear when the wind-up ends")
	# tells keep working with flashes and guides turned down
	var flash0: float = Settings.flash
	Settings.flash = 0.0
	Settings.combat_guides = false
	e._launch_attack("e_grab")
	await frames(3)
	check(e.tell.visible, "tells do not depend on the flash or guide settings")
	check(not p.keyline.visible and not p.ring.visible and not e.ring.visible, "Combat guides: Off hides the keyline and rings")
	Settings.flash = flash0
	Settings.combat_guides = true
	# usable objects: ring when near with free hands, outline on the one Action would take
	_clear_enemies()
	var crate: Prop = null
	for pr in r.props:
		if pr.type == "crate":
			crate = pr
	if crate != null:
		p.position = crate.position + Vector2(-70, 6)
		p.set_state("idle")
		await frames(3)
		check(crate._ring != null and crate._ring.visible and (crate._key == null or not crate._key.visible), "a liftable crate nearby gets a ring")
		p.position = crate.position + Vector2(-10, 6)
		await frames(3)
		check(crate._key != null and crate._key.visible, "the object Action would lift is outlined")
		p.equip_weapon("bat")
		await frames(3)
		check(not crate._ring.visible or crate._key.visible, "with full hands only the Action target stays marked")
	# fast wind-ups hold the cocked pose instead of flashing two frames
	GameState.learn("rising")
	p.held = ""
	p.set_state("idle")
	p.start_attack("rising_kick")
	var seen: Dictionary = {}
	for i in 3:
		p.atk_t = i + 1
		seen[p._attack_frame()] = true
	check(seen.size() == 1, "a 3-tick wind-up shows one pose, not a flicker (%s)" % str(seen.keys()))

# ---------------------------------------------------------------- Duke's lieutenants (Chain Lot c3)
func test_lieutenants() -> void:
	await start_world(_in_room("oq_chainlot", ["intro_seen", "intro_done", "met_mara", "duke_intro_seen", "tutor_v2"], "chain_dogs"))
	GameState.spawn = "west"
	var r := room()
	var p: Player = r.player
	r.waves_done["c1"] = true
	r.waves_done["c2"] = true
	p.position = Vector2(812, 300)
	await until(func(): return enemies().size() == 3, 600)
	check(enemies().size() == 3, "the lieutenants wave brings three fighters")
	var thrower: Enemy = null
	var blocker: Enemy = null
	var brawler: Enemy = null
	for e in enemies():
		match (e as Enemy).arche_id:
			"thrower": thrower = e
			"blocker": blocker = e
			"brawler": brawler = e
	check(thrower != null and blocker != null and brawler != null, "a thrower, a blocker and a brawler")
	if thrower != null and blocker != null and brawler != null:
		check(blocker.protect == thrower, "the blocker is linked to cover the thrower")
		check(thrower.position.x > p.position.x and blocker.position.x > p.position.x and brawler.position.x < p.position.x, "thrower and blocker arrive from the east, the brawler from behind")
		check(r.exits_locked, "the fight is contained")
		check(tut().state("blocker") != 0, "the blocker tip is armed for players who skipped Benny")
		# while waiting, the blocker stands between the player and the thrower
		brawler.hold = true
		thrower.hold = true
		thrower.position = Vector2(1060, 290)
		p.position = Vector2(800, 290)
		p.set_state("idle")
		blocker.position = Vector2(1100, 330)
		blocker.aggression = 0.0
		blocker.intent = "wait"
		blocker.pending_attack = ""
		await frames(240)
		check(blocker.position.x > p.position.x and blocker.position.x < thrower.position.x and absf(blocker.position.y - thrower.position.y) < 14.0,
			"the blocker holds the line between the player and the thrower (%s)" % str(blocker.position))
	# the crate left for the player survives enemy bottles, and a second liftable is in reach
	var crate: Prop = null
	var can: Prop = null
	for pr in r.props:
		if pr.type == "crate":
			crate = pr
		if pr.type == "trash_can" and absf(pr.position.x - 742.0) < 1.0:
			can = pr
	check(crate != null and can != null, "a crate and a trash can are placed near the fight")
	if crate != null and thrower != null:
		r.spawn_projectile(thrower, "bottle", Vector2(crate.position.x + 60.0, crate.position.y - 4.0), 12.0, -1, 1)
		await frames(40)
		check(is_instance_valid(crate) and not crate.broken, "an enemy bottle does not smash the crate")
		r.spawn_projectile(p, "brick", Vector2(crate.position.x - 60.0, crate.position.y - 4.0), 12.0, 1, 1)
		await frames(40)
		check(not is_instance_valid(crate) or crate.broken, "the player's own throw still breaks a crate")
	kill_all()
	await until(func(): return not r.exits_locked, 600)
	check(not r.exits_locked, "clearing the lieutenants unlocks the lot")

# ---------------------------------------------------------------- Duke and the street afterwards
func _count_bosses() -> int:
	var n := 0
	for a in room().actors:
		if a is Boss:
			n += 1
	return n

func _wave_would_start(wid: String) -> bool:
	var r := room()
	return not r.waves_done.has(wid)

func test_duke_and_street() -> void:
	# before Duke: Chain Dogs patrol Kettle Street and nobody strolls there
	await start_world(_in_room("oq_kettle", ["intro_seen", "intro_done", "met_mara"], "chain_dogs"))
	GameState.spawn = "west"
	check(GameState.district_calm("old_quarter") == "", "the Old Quarter is not calm while Duke runs it")
	check(room().find_npc("oq_busrider") == null, "nobody waits for a bus that does not run")
	room().player.position = Vector2(900, 290)
	await until(func(): return enemies().size() > 0, 600)
	check(enemies().size() > 0, "Chain Dogs patrol Kettle Street before Duke")
	await frames(600)
	var strollers := 0
	for n in room().npcs:
		if n.mode == "pass":
			strollers += 1
	check(strollers == 0, "no passers-by on the home streets while the Dogs run them")
	# the fight itself: only ever one Duke, even when the player stands past the trigger line as he falls
	await start_world(_in_room("oq_chainlot", ["intro_seen", "intro_done", "met_mara", "duke_intro_seen", "tutor_v2"], "chain_dogs"))
	GameState.spawn = "west"
	var r := room()
	var p: Player = r.player
	for wid in ["c1", "c2", "c3"]:
		r.waves_done[wid] = true
	p.position = Vector2(980, 290)
	await until(func(): return r.boss_active and not r.boss_actors.is_empty(), 900)
	check(r.boss_active and _count_bosses() == 1, "Duke's fight starts")
	p.position = Vector2(1000, 290)
	var duke: Enemy = r.boss_actors[0]
	duke.hp = 1
	duke.take_damage_and_react(p, {"knockdown": true, "kb": 120, "launch": 140, "power": 99}, 99.0, 1, false)
	var max_bosses := 0
	for i in 200:
		await frames(1)
		max_bosses = maxi(max_bosses, _count_bosses())
	check(max_bosses == 1, "no second Duke appears in the pause before the defeat scene (saw %d)" % max_bosses)
	await until(func(): return GameState.has_flag("boss_duke") and not Story.busy and not w.dialogue.active, 2400)
	check(GameState.has_flag("boss_duke") and GameState.stage == "market", "Duke's defeat advances the story")
	check(r.boss_done and not r.boss_active, "the room knows its boss fight is over")
	check(r.find_npc("lot_neighbor") != null and r.find_npc("lot_kid") != null, "neighbours come out into the Chain Lot")
	check(GameState.has_flag("calm_seen_old_quarter"), "the change is announced once")
	check(GameState.district_calm("old_quarter") == "clear", "the Old Quarter is calm after Duke")
	check(not r.exits_locked, "the lot is unlocked after the scene")
	await frames(120)
	check(_count_bosses() <= 1 and enemies().is_empty(), "no fight restarts after the scene")
	# revisits: the residents are there exactly once, and the Dogs' patrols are gone for good
	w._load_room("oq_chainlot", "west")
	await frames(90)
	var n_res := 0
	for n in room().npcs:
		if n.npc_id in ["lot_neighbor", "lot_kid"]:
			n_res += 1
	check(n_res == 2, "the Chain Lot keeps its two residents on a revisit (found %d)" % n_res)
	room().player.position = Vector2(400, 290)
	await frames(240)
	check(enemies().is_empty() and room().waves_done.has("c1"), "no Chain Dog patrol in the lot after Duke")
	w._load_room("oq_kettle", "west")
	await frames(90)
	check(room().find_npc("oq_busrider") != null and room().find_npc("oq_stoop") != null, "residents are back on Kettle Street")
	room().player.position = Vector2(1300, 290)
	await frames(420)
	check(enemies().is_empty(), "no Chain Dog patrol on Kettle Street after Duke")
	var seen_pass := await until(func():
		for n in room().npcs:
			if n.mode == "pass":
				return true
		return false, 900)
	check(seen_pass, "people walk Kettle Street again")
	# survives save/load, and a save from before this change gets the same street from its boss flag alone
	save_roundtrip()
	check(GameState.district_calm("old_quarter") == "clear" and GameState.has_flag("calm_seen_old_quarter"), "the calm street survives save/load")
	GameState.reset_new_game()
	GameState.bosses["duke"] = true
	check(GameState.district_calm("old_quarter") == "clear", "an older save past Duke gets the calm street from its boss record")
	# New Game+ resets it with the story
	GameState.flags["game_complete"] = true
	GameState.start_new_game_plus()
	check(GameState.district_calm("old_quarter") == "", "New Game+ puts the Chain Dogs back on the street")
	# other districts thin out instead of clearing
	await start_world(_in_room("cm_canalwalk", ["intro_seen", "intro_done", "met_mara", "boss_duke", "boss_pikes", "act1_done"], "ironworks"))
	GameState.spawn = "west"
	check(GameState.district_calm("canal_market") == "thin", "the Canal Market thins out after the Pikes")
	var wdef: Dictionary = room()._wave_def("w1")
	var full_n := 0
	for en in wdef.get("enemies", []):
		full_n += int(en[1]) if typeof(en) == TYPE_ARRAY else 1
	room().player.position = Vector2(float(wdef.get("at", 0)) + 20.0, 290)
	await until(func(): return not room().wave_queue.is_empty() or enemies().size() > 0, 600)
	await frames(200)
	check(room().is_patrol_wave("w1"), "w1 is an ordinary patrol")
	check(full_n >= 3 and enemies().size() == full_n - 1, "a thinned patrol has one fighter fewer (%d of %d)" % [enemies().size(), full_n])

# ---------------------------------------------------------------- opt-in playtest log
func test_playtest_log() -> void:
	Settings.playtest_log = false
	await start_world(func():
		GameState.set_flag("intro_seen"))
	await until(func(): return enemies().size() == 2, 240)
	var p: Player = room().player
	var e: Enemy = enemies()[0]
	p.position = Vector2(e.position.x - 24.0, e.position.y)
	p.facing = 1
	await tap("punch")
	await frames(12)
	tut().skip("guard")
	check(not GameState.stats.has("pt"), "with the playtest log off nothing is recorded")
	check(Playtest.lines().is_empty(), "and the notes page has nothing to show")
	Settings.playtest_log = true
	GameState.stats["playtime"] = 12.5
	e = enemies()[0]
	e.frozen = true
	e.set_meta("scripted_freeze", true)
	p.position = Vector2(e.position.x - 24.0, e.position.y)
	p.facing = 1
	p.set_state("idle")
	await tap("punch")
	await frames(12)
	tut().notify("combo3")
	tut().skip("throw")
	var pt: Dictionary = GameState.stats.get("pt", {})
	check(pt.has("first_hit") and float(pt.first_hit) >= 12.5, "with the log on the first hit is timestamped in play time")
	check(pt.has("tip:combo") and pt.has("skip:throw"), "learned and skipped tips are noted")
	var first: float = float(pt.first_hit)
	GameState.stats["playtime"] = 40.0
	p.set_state("idle")
	await tap("punch")
	await frames(12)
	check(is_equal_approx(float(GameState.stats.pt.first_hit), first), "a first-time note is never overwritten")
	save_roundtrip()
	check(GameState.stats.get("pt", {}).has("first_hit"), "the notes travel with the save")
	check(Playtest.lines().size() >= 2, "the notes page lists what was recorded")
	var m := PlaytestMenu.new()
	w.push_menu(m)
	await get_tree().process_frame
	await get_tree().process_frame
	check(w.menus.size() == 1, "the playtest notes page opens")
	w.close_all_menus()
	Settings.playtest_log = false
