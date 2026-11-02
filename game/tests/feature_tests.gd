extends Node
## Exercises rarely-hit code paths in the real world scene: every technique via its input chord,
## every weapon family (swing / throw / carry), and every boss AI. Fails on script errors or
## when a feature produces no effect. Run: godot --headless --fixed-fps 60 res://tests/feature_tests.tscn

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
		if god and w and w.room and w.room.player:
			w.room.player.hp = w.room.player.max_hp
			GameState.hp = GameState.max_hp()
		if w and w.dialogue.active and i % 4 == 0:
			act("ui_accept", true)
			await get_tree().physics_frame
			act("ui_accept", false)

func tap(a: String, hold: int = 2) -> void:
	act(a, true)
	await frames(hold)
	act(a, false)
	await frames(1)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	GameState.reset_new_game()
	for f in ["intro_done", "intro_seen", "met_mara"]:
		GameState.set_flag(f)
	GameState.stage = "chain_dogs"
	GameState.room = "oq_brickrow"
	GameState.spawn = "west"
	for s in Content.skills:
		GameState.learn(s)
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await test_techniques()
	await test_weapons()
	await test_bosses()
	print("FEATURE TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

func room() -> Room:
	return w.room

func setup_target(dx: float = 30.0, id: String = "yard_heavy") -> Enemy:
	var r := room()
	for a in r.actors.duplicate():
		if a is Enemy:
			r.remove_actor(a)
	var p: Player = r.player
	p.position = Vector2(600, 290)
	p.facing = 1
	p.set_state("idle")
	var e: Enemy = r.spawn_enemy(id, Vector2(600 + dx, 290), {})
	e.max_hp = 9999
	e.hp = 9999
	e.set_meta("scripted_freeze", true)
	e.frozen = true
	e.facing = -1
	return e

func test_techniques() -> void:
	var p: Player = room().player
	var cases := [
		["rising_kick", func(): act("guard", true); await frames(3); await tap("kick"); act("guard", false)],
		["spin_sweep", func(): act("guard", true); await frames(3); await tap("punch"); act("guard", false)],
		["heel_drop", func(): await tap("jump"); await frames(10); await tap("punch")],
		["slam_land", func(): await tap("jump"); await frames(12); await tap("guard")],
		["shoulder", func(): act("run", true); act("move_right", true); await frames(16); await tap("punch"); act("run", false); act("move_right", false)],
		["dropkick", func(): act("run", true); act("move_left", true); await frames(16); await tap("kick"); act("run", false); act("move_left", false)],
		["punch_rapid", func():
			for i in 6:
				await tap("punch")
				await frames(4)],
		["oath_breaker", func(): act("kick", true); await frames(60); act("kick", false)],
	]
	for c in cases:
		var e := setup_target(30.0 if c[0] != "dropkick" else -60.0)
		if c[0] == "dropkick":
			p.facing = -1
		var hp0 := e.hp
		var seen := [false]
		var cb: Callable = c[1]
		var watcher := func():
			for i in 120:
				if p.atk_id == c[0]:
					seen[0] = true
				await get_tree().physics_frame
		watcher.call()
		await cb.call()
		await frames(70)
		check(seen[0], "technique %s triggers from its input" % c[0])
		check(e.hp < hp0, "technique %s deals damage" % c[0])
	# giant swing: grab a dizzy enemy and spin
	var g := setup_target(16.0, "dogs_brawler")
	g.frozen = false
	g.set_meta("scripted_freeze", false)
	g.start_dizzy()
	await frames(2)
	var other: Enemy = room().spawn_enemy("dogs_brawler", Vector2(560, 290), {})
	other.max_hp = 999; other.hp = 999
	other.set_meta("scripted_freeze", true)
	other.frozen = true
	await tap("interact")
	await frames(14)
	check(p.carried_actor == g, "grab dizzy enemy")
	var ohp: int = other.hp
	await tap("punch")
	await frames(90)
	check(p.carried_actor == null and g.state != "carried", "giant swing releases the enemy")
	check(other.hp < ohp, "giant swing hits bystanders")
	# guard counter after perfect guard
	var atk := setup_target(26.0, "dogs_brawler")
	atk.frozen = false
	atk.set_meta("scripted_freeze", false)
	p.facing = 1
	atk.facing = -1
	atk.start_attack("e_jab")
	await frames(int(Content.attack("e_jab").startup) - 3)
	act("guard", true)
	await frames(6)
	check(p.perfect_counter_t > 0, "perfect guard registers")
	await tap("punch")
	act("guard", false)
	await frames(10)
	check(p.atk_id == "guard_counter", "guard counter after perfect guard")
	await frames(40)

func test_weapons() -> void:
	var r := room()
	var p: Player = r.player
	for wid in Content.weapons:
		var e := setup_target(34.0)
		var hp0 := e.hp
		p.equip_weapon(wid)
		var wdef: Dictionary = Content.weapon(wid)
		await frames(2)
		await tap("punch")
		await frames(80)
		check(e.hp < hp0, "weapon %s damages (swing or throw)" % wid)
		if p.held != "":
			await tap("interact")
			await frames(80)
		check(p.held == "" or wdef.get("attack", "") != "", "weapon %s can be thrown/released" % wid)
		for pr in r.projectiles.duplicate():
			r.remove_projectile(pr)
		for pk in r.pickups.duplicate():
			r.remove_pickup(pk)
	# lift a crate prop and throw it
	var e2 := setup_target(60.0)
	var crate := Prop.new()
	r.world_node.add_child(crate)
	crate.setup(r, "crate", Vector2(612, 290), 999, {})
	r.props.append(crate)
	p.position = Vector2(600, 290)
	await frames(2)
	await tap("interact")
	await frames(14)
	check(p.held == "crate", "lift crate prop")
	var hp1 := e2.hp
	await tap("punch")
	await frames(60)
	check(p.held == "" and e2.hp < hp1, "thrown crate hits")
	# Lou's lobbed crate lands with area damage
	god = false
	var lou: Enemy = r.spawn_enemy("lou", Vector2(760, 290), {})
	var php := p.hp
	r.spawn_lob(lou, "crate", p.position)
	await frames(80)
	check(p.hp < php, "lobbed crate damages on landing")
	r.remove_actor(lou)
	god = true
	await frames(20)

func test_bosses() -> void:
	var r := room()
	var p: Player = r.player
	for a in r.actors.duplicate():
		if a is Enemy:
			r.remove_actor(a)
	for bid in ["duke", "rhea", "lou", "otto", "jett", "sabine", "sergeant", "rook"]:
		p.position = Vector2(500, 290)
		p.set_state("idle")
		var b: Enemy = r.spawn_enemy(bid, Vector2(620, 290), {})
		var used := {}
		for i in 60 * 25:
			await get_tree().physics_frame
			p.hp = p.max_hp
			GameState.hp = GameState.max_hp()
			if p.state in ["knockdown", "hurt"] and i % 60 == 0:
				p.position.x = clampf(p.position.x, 100, 1600)
			if b.state == "attack":
				used[b.atk_id] = true
			if w.dialogue.active and i % 6 == 0:
				act("ui_accept", true)
				await get_tree().physics_frame
				act("ui_accept", false)
			if bid == "rook" and i == 600:
				b.hp = int(b.max_hp * 0.45)
		check(used.size() >= 3, "boss %s uses 3+ attacks (%s)" % [bid, str(used.keys())])
		if bid == "rook":
			check(b.phase == 2 and b.held == "pipe", "rook enters phase 2 with pipe")
		for a in r.actors.duplicate():
			if a is Enemy:
				r.remove_actor(a)
		await frames(10)
