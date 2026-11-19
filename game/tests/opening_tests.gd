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
