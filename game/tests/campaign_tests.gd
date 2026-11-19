extends Node
## Campaign-wide changes of the polish pass: Kowal's work-light contest, the Storage Floor crane and shutter
## run, and New Game+ composition / boss variations.
## Run: godot --headless --fixed-fps 60 res://tests/campaign_tests.tscn

var w: Node
var fails := 0
var passes := 0
var god := true

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
		if w and is_instance_valid(w) and w.dialogue.active and not w.dialogue.choosing and i % 4 == 0:
			act("ui_accept", true)
			await get_tree().physics_frame
			act("ui_accept", false)

func tap(a: String, hold: int = 2) -> void:
	act(a, true)
	await frames(hold)
	act(a, false)
	await frames(1)

func until(cond: Callable, max_frames: int = 600) -> bool:
	var i := 0
	while i < max_frames:
		if cond.call():
			return true
		await frames(1)
		i += 1
	return cond.call()

func room() -> Room:
	return w.room

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
	setup.call()
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await frames(10)

func _in_room(id: String, flags: Array, stage: String, level: int = 1) -> Callable:
	return func():
		for f in flags:
			GameState.set_flag(f)
		GameState.stage = stage
		GameState.room = id
		GameState.spawn = "west"
		GameState.level = level
		GameState.hp = GameState.max_hp()

func enemies() -> Array:
	var out: Array = []
	for a in room().actors:
		if a is Enemy and not a.dead and a.team == Actor.TEAM_ENEMY:
			out.append(a)
	return out

func kill(list: Array) -> void:
	for e in list:
		if is_instance_valid(e) and not e.dead:
			e.min_hp = 0
			e.hp = 0
			e.take_damage_and_react(room().hazard_actor, {"knockdown": true, "kb": 100, "launch": 120}, 0.0, 1, false)

func non_boss() -> Array:
	return enemies().filter(func(e): return not e.is_boss)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.show_hints = true
	Settings.difficulty = "normal"
	await test_kowal_lights()
	await test_storage_crane()
	await test_shutter_run()
	await test_ngplus()
	print("CAMPAIGN TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

# ---------------------------------------------------------------- Kowal
const VAULT_FLAGS := ["intro_seen", "intro_done", "met_mara", "tutor_v2", "ul_entered", "kowal_intro_seen"]

func _start_kowal() -> Boss:
	var r := room()
	r.waves_done["uv1"] = true
	r.player.position = Vector2(620, 290)
	await until(func(): return r.boss_active and not r.boss_actors.is_empty(), 900)
	if r.boss_actors.is_empty():
		return null
	var k: Boss = r.boss_actors[0]
	await until(func(): return not Story.busy, 600)
	return k

func test_kowal_lights() -> void:
	await start_world(_in_room("ul_vault", VAULT_FLAGS, "underline", 11))
	var r := room()
	var p: Player = r.player
	var k := await _start_kowal()
	check(k != null, "Kowal's fight starts")
	if k == null:
		return
	check(r.work_lights.size() == 3 and r.lit_lights() == 3 and not r.lights_contest, "three work lights, all on, before the contest")
	check(is_equal_approx(r.vis._dark_target, 1.0), "the vault is fully lit in phase one")
	k.hold = true
	k.hp = int(k.max_hp * 0.45)
	k.hold = false
	await until(func(): return k.phase == 2, 300)
	check(k.phase == 2 and r.lights_contest, "at half health the lights become a contest")
	check(r.lit_lights() == 1, "she leaves exactly one light on (%d)" % r.lit_lights())
	check(r.vis._dark_target < 0.9 and r.vis._dark_target >= 0.45, "the vault dims but never below the readable floor (%.2f)" % r.vis._dark_target)
	check(w.hud.timer_label.text == "LIGHTS 1/3", "the light count is on screen as text (%s)" % w.hud.timer_label.text)
	check(non_boss().is_empty(), "no Moles climb out while a light is on")
	check(w.tutor.state("lights") != 0, "the lights tip is armed")
	# switching a light back on with Action
	k.hold = true
	var dark: WorkLight = r.nearest_light(p.position, false)
	p.position = Vector2(dark.position.x + 6.0, dark.position.y + 10.0)
	p.set_state("idle")
	await frames(3)
	check(r.find_context(p).get("type", "") == "light" and p.context_short() == "LIGHT", "a dark light is the Action target")
	await tap("interact")
	await frames(6)
	check(dark.lit and r.lit_lights() == 2, "Action switches the light back on")
	check(w.hud.timer_label.text == "LIGHTS 2/3" and w.tutor.is_learned("lights"), "the count updates and the tip completes on the real action")
	check(r.find_context(p).get("type", "") != "light", "a lit light is no longer a target")
	# she walks over and puts a lit light out, with a tell, and is winded afterwards
	k.hold = false
	k.snuff_cd = 0
	var before := r.lit_lights()
	var saw_tell := false
	for i in 900:
		await frames(1)
		if k.snuffing and k.tell != null and k.tell.visible:
			saw_tell = true
		if r.lit_lights() < before:
			break
	check(r.lit_lights() == before - 1, "Kowal puts a light out herself")
	check(saw_tell, "her light-kill swing is telegraphed")
	await until(func(): return k.tired > 0, 120)
	check(k.tired > 0, "she is winded after killing a light")
	# hitting her during the wind-up saves the light
	k.tired = 0
	k.snuff_cd = 0
	before = r.lit_lights()
	var interrupted := false
	for i in 900:
		await frames(1)
		if i % 150 == 0 and OS.get_environment("BO_DBG") != "":
			print("DBG kowal pos=", k.position, " state=", k.state, " target=", k.snuff_target, " tpos=", k.snuff_target.position if k.snuff_target else Vector2.ZERO, " walk=", k.snuff_walk, " cd=", k.snuff_cd, " lit=", r.lit_lights(), " intent=", k.intent, " pend=", k.pending_attack, " hold=", k.hold, " tired=", k.tired)
		if k.snuffing and k.state == "attack" and k.attack_phase() == 0:
			k.take_damage_and_react(p, {"power": 5, "kb": 60, "hitstun": 20}, 5.0, 1, false)
			interrupted = true
			break
	await frames(20)
	check(interrupted and r.lit_lights() == before and k.snuff_target == null, "hitting her in the wind-up saves the light (interrupted=%s lit %d/%d state=%s cd=%d tired=%d)" % [str(interrupted), r.lit_lights(), before, k.state, k.snuff_cd, k.tired])
	# full darkness: Moles climb out, but only up to the cap, and never while a light is on
	k.hold = true
	for wl in r.work_lights:
		wl.set_lit(false)
	r._apply_light_level(0.1)
	k.hold = false
	k.snuff_cd = 99999
	await until(func(): return non_boss().size() >= 2, 700)
	check(non_boss().size() == 2, "two Moles climb out of full darkness (%d)" % non_boss().size())
	check(r.vis._dark_target >= 0.45, "full darkness still keeps the readable floor")
	kill(non_boss())
	await until(func(): return non_boss().is_empty(), 300)
	await until(func(): return non_boss().size() >= 2, 700)
	check(k.dark_waves == 2, "a second wave comes if it stays dark")
	kill(non_boss())
	await frames(700)
	check(non_boss().is_empty() and k.dark_waves == 2, "the reinforcements are capped")
	# no light state blocks completion: beat her in the dark
	k.hp = 1
	k.take_damage_and_react(p, {"knockdown": true, "kb": 120, "launch": 140, "power": 99}, 99.0, 1, false)
	await until(func(): return GameState.has_flag("boss_kowal") and not Story.busy and not w.dialogue.active, 2400)
	check(GameState.has_flag("boss_kowal") and GameState.stage == "floodgate", "the fight ends with every light out")
	check(r.lit_lights() == 3 and not r.lights_contest and w.hud.timer_label.text == "", "afterwards the lights are back and the counter is gone")
	check(r.vis._dark_target > 0.95, "the vault is bright again")
	# relaxed: one wave only
	Settings.difficulty = "relaxed"
	await start_world(_in_room("ul_vault", VAULT_FLAGS, "underline", 11))
	r = room()
	k = await _start_kowal()
	if k != null:
		k.hp = int(k.max_hp * 0.45)
		await until(func(): return k.phase == 2, 300)
		for wl in r.work_lights:
			wl.set_lit(false)
		k.snuff_cd = 99999
		await until(func(): return non_boss().size() >= 2, 700)
		kill(non_boss())
		await frames(800)
		check(k.dark_waves == 1 and non_boss().is_empty(), "Relaxed: only one wave of Moles")
	Settings.difficulty = "normal"

# ---------------------------------------------------------------- Storage Floor
const WH_FLAGS := ["intro_seen", "intro_done", "met_mara", "tutor_v2", "mara_arrived"]

func test_storage_crane() -> void:
	await start_world(_in_room("rw_storage", WH_FLAGS, "warehouse", 13))
	var r := room()
	var p: Player = r.player
	r.waves_done["st1"] = true
	p.position = Vector2(1010, 250)
	await until(func(): return not r.crane.is_empty(), 600)
	check(not r.crane.is_empty() and r.crane.zones.size() == 2, "the lock wave runs a crane with two marked spots")
	await until(func(): return enemies().size() == 4, 600)
	check(enemies().size() == 4, "the crane wave has four fighters (was five)")
	# a fighter standing on the mark when the crate lands is hit; so would the player be
	var zone: Vector2 = r.crane.zones[int(r.crane.i) % 2]
	var victim: Enemy = enemies()[0]
	for e in enemies():
		e.hold = true
	victim.position = zone
	var hp0 := victim.hp
	p.position = Vector2(700, 250)
	await until(func(): return victim.hp < hp0, 600)
	check(victim.hp < hp0, "a crate dropped on a mark hurts the enemy standing there")
	await frames(30)
	var left_crate := false
	for pr in r.props:
		if pr.type == "crate" and pr.index >= 900 and pr.position.distance_to(zone) < 30.0:
			left_crate = true
	check(left_crate, "each drop leaves a crate to lift and throw")
	god = false
	var zone2: Vector2 = r.crane.zones[int(r.crane.i) % 2]
	p.position = zone2
	p.set_state("idle")
	var php := p.hp
	await until(func():
		if p.state in ["idle", "walk"]:
			p.position = zone2
		return p.hp < php, 700)
	check(p.hp < php, "the same crane hurts the player on a mark: it cuts both ways")
	god = true
	# marks never fill up with boxes, and the crane stops with the wave
	await frames(700)
	var n_haz := 0
	for pr in r.props:
		if pr.type == "crate" and pr.index >= 900:
			n_haz += 1
	check(n_haz <= 2, "old crates on the marks are cleared before the next drop (%d left)" % n_haz)
	kill(enemies())
	await until(func(): return r.crane.is_empty(), 600)
	check(r.crane.is_empty() and not r.exits_locked, "the crane stops when the wave is beaten")

func _to_run_start() -> void:
	var r := room()
	for wid in ["st1", "st2"]:
		r.waves_done[wid] = true
	r.player.position = Vector2(1490, 290)
	await until(func(): return w.hud.timer_label.text.begins_with("SHUTTER"), 600)

func test_shutter_run() -> void:
	# success: reach the door in time
	await start_world(_in_room("rw_storage", WH_FLAGS, "warehouse", 13))
	var r := room()
	var p: Player = r.player
	await _to_run_start()
	check(w.hud.timer_label.text.begins_with("SHUTTER"), "the shutter countdown is on screen")
	check(not r.exits_locked, "the way is open during the run")
	check(enemies().size() >= 1, "runners try to hold the lane")
	var xp0 := GameState.xp
	var lvl0 := GameState.level
	var cash0 := GameState.cash
	p.position = Vector2(r.width - 60.0, 290)
	await until(func(): return GameState.has_flag("storage_run_done"), 120)
	check(GameState.has_flag("storage_run_done"), "reaching the door in time completes the run")
	check(GameState.cash == cash0 + Story.SHUTTER_BONUS_CASH, "the cash bonus is paid once")
	check(GameState.level > lvl0 or GameState.xp == xp0 + Story.SHUTTER_BONUS_XP, "the XP bonus stands in for the skipped fight")
	check(w.hud.timer_label.text == "" and not r.exits_locked, "the counter clears and the door stays open")
	# coming back later: no second run, no second bonus
	var cash1 := GameState.cash
	w._load_room("rw_storage", "west")
	await frames(60)
	room().waves_done["st1"] = true
	room().waves_done["st2"] = true
	room().player.position = Vector2(1500, 290)
	await frames(240)
	check(w.hud.timer_label.text == "" and GameState.cash == cash1, "the run does not repeat once done")
	# failure: the shutter comes down and has to be forced
	await start_world(_in_room("rw_storage", WH_FLAGS, "warehouse", 13))
	r = room()
	p = r.player
	await _to_run_start()
	p.position = Vector2(1500, 290)
	var xp_f := GameState.xp
	var lvl_f := GameState.level
	await until(func(): return r.exits_locked, int(Story.SHUTTER_SECONDS * 60.0) + 300)
	check(r.exits_locked and not GameState.has_flag("storage_run_done"), "when time runs out the shutter is down")
	check(w.hud.timer_label.text == "", "the counter clears on failure too")
	await until(func(): return enemies().size() >= 5, 400)
	var has_block := false
	for e in enemies():
		if (e as Enemy).arche_id == "blocker":
			has_block = true
	check(has_block, "the door crew comes out")
	kill(enemies())
	await until(func(): return not r.exits_locked, 600)
	check(not r.exits_locked and GameState.has_flag("storage_run_done"), "beating the door crew raises the shutter")
	await frames(12)
	check(GameState.level > lvl_f or GameState.xp > xp_f, "the forced path pays in fight XP instead")
	# leaving mid-run never strands the counter or the flag
	await start_world(_in_room("rw_storage", WH_FLAGS, "warehouse", 13))
	await _to_run_start()
	w._load_room("rw_dock", "east")
	await frames(60)
	check(w.hud.timer_label.text == "" and not GameState.has_flag("storage_run_done"), "leaving mid-run clears the counter and keeps the run for next time")
	# a save from before this change that already rescued Eli is not sent on the run
	await start_world(_in_room("rw_storage", WH_FLAGS + ["found_eli"], "rook", 13))
	room().player.position = Vector2(1500, 290)
	await frames(200)
	check(w.hud.timer_label.text == "", "saves past the rescue never see the shutter run")
	# pausing stops the clock
	await start_world(_in_room("rw_storage", WH_FLAGS, "warehouse", 13))
	await _to_run_start()
	var t0: String = w.hud.timer_label.text
	get_tree().paused = true
	for i in 150:
		await get_tree().physics_frame
	get_tree().paused = false
	await frames(2)
	var t1: String = w.hud.timer_label.text
	check(int(t0.get_slice(" ", 1)) - int(t1.get_slice(" ", 1)) <= 1, "the countdown does not run while paused (%s -> %s)" % [t0, t1])

# ---------------------------------------------------------------- New Game+
func test_ngplus() -> void:
	GameState.reset_new_game()
	GameState.ng_cycle = 1
	var cap := int(Content.tune("ngplus", "scale_cap_cycle", 3.0))
	var m1 := GameState.ng_mult("hp")
	GameState.ng_cycle = cap
	var mc := GameState.ng_mult("hp")
	GameState.ng_cycle = 9
	check(m1 > 1.0 and mc > m1 and is_equal_approx(GameState.ng_mult("hp"), mc), "enemy scaling stops growing after cycle %d" % cap)
	check(is_equal_approx(GameState.ng_mult("reward"), 1.0 + 0.25 * cap), "rewards are capped the same way")
	GameState.ng_cycle = 0
	check(is_equal_approx(GameState.ng_mult("hp"), 1.0), "a first run is unscaled")
	# composition: a wave gains what it lacks; named quest fighters are untouched
	await start_world(func():
		_in_room("oq_kettle", ["intro_seen", "intro_done", "met_mara"], "chain_dogs", 14).call()
		GameState.ng_cycle = 1)
	var r := room()
	var base := [{"id": "dogs_brawler"}, {"id": "dogs_brawler"}, {"id": "dogs_flanker"}]
	var out: Array = r.ngplus_wave(base)
	check(out.size() == 4 and str(out[3].id) == "dogs_thrower", "a wave without a thrower gains one")
	check(base.size() == 3 and str(base[0].id) == "dogs_brawler", "the wave definition itself is not modified")
	out = r.ngplus_wave([{"id": "dogs_brawler"}, {"id": "dogs_thrower"}])
	check(str(out[2].id) == "dogs_blocker" and str(out[2].get("protects", "")) == "dogs_thrower", "with a thrower present the addition is a blocker that covers it")
	out = r.ngplus_wave([{"id": "grays_blocker", "name": "Inspector", "drops": [{"key": "weight_neon"}]}, {"id": "grays_brawler"}])
	check(str(out[0].id) == "grays_blocker" and out[0].has("name") and out.size() == 3, "named quest fighters are never changed")
	GameState.ng_cycle = 2
	out = r.ngplus_wave(base)
	var armed := 0
	for x in out:
		if str(x.id) == "dogs_weapon":
			armed += 1
	check(armed == 1, "from the second cycle one brawler comes armed")
	GameState.ng_cycle = 1
	# a real wave: one more fighter, the attacker cap unchanged
	r.player.position = Vector2(900, 290)
	await until(func(): return enemies().size() >= 4, 900)
	var kinds: Dictionary = {}
	for e in enemies():
		kinds[(e as Enemy).arche_id] = true
	check(enemies().size() == 4 and kinds.has("thrower"), "the Kettle Street patrol brings a thrower in New Game+ (%s)" % str(kinds.keys()))
	var max_tokens := 0
	for i in 600:
		await frames(1)
		max_tokens = maxi(max_tokens, r.tokens.size())
	check(max_tokens <= 2, "never more than two attackers at once (%d)" % max_tokens)
	# boss variations keep the same attacks but change thresholds
	await start_world(func():
		_in_room("oq_chainlot", ["intro_seen", "intro_done", "met_mara", "duke_intro_seen"], "chain_dogs", 14).call()
		GameState.ng_cycle = 1)
	r = room()
	for wid in ["c1", "c2", "c3"]:
		r.waves_done[wid] = true
	r.player.position = Vector2(980, 290)
	await until(func(): return r.boss_active and not r.boss_actors.is_empty(), 900)
	if not r.boss_actors.is_empty():
		var duke: Boss = r.boss_actors[0]
		await until(func(): return not Story.busy, 600)
		duke.hp = int(duke.max_hp * 0.74)
		await until(func(): return duke.summons_done.size() == 1, 200)
		check(duke.summons_done.size() == 1, "New Game+ Duke whistles earlier (at three quarters)")
		await until(func(): return non_boss().size() >= 2, 300)
		var thrower := false
		for e in non_boss():
			if (e as Enemy).arche_id == "thrower":
				thrower = true
		check(thrower, "and a bottle-thrower answers the whistle")
		check(Boss.MOVESETS.duke.size() == 4, "his attacks and tells are the same ones")
	# no opening tips in New Game+, and the flags from the last cycle are gone
	await start_world(func():
		GameState.flags["game_complete"] = true
		GameState.set_flag("dot_meal_done")
		GameState.set_flag("storage_run_done")
		GameState.learn("shoulder")
		GameState.start_new_game_plus()
		GameState.set_flag("intro_seen"))
	await until(func(): return enemies().size() == 2, 240)
	await frames(30)
	check(not w.tutor.any_armed() and not enemies()[0].hold, "New Game+ skips the opening tips and the Dogs do not wait")
	check(not GameState.has_flag("storage_run_done") and Story._dot_meal_due(), "per-cycle events reset with the story")
	check(GameState.has_skill("shoulder") and Story._benny_lesson_due(), "techniques carry over; Benny's offer is asked again but cannot duplicate one")
	GameState.ng_cycle = 0
