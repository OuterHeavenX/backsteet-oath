extends Node
## Completes all six side jobs through real interactions (walk up, Grab/Talk, dialogue choices).
## Combat inside quests is shortcut (enemies are knocked out directly) because combat is covered
## by the autoplay bot; this test verifies quest triggers, steps, rewards, journal and persistence.
## Run: godot --headless --fixed-fps 60 res://tests/quest_tests.tscn

var w: Node
var fails := 0
var passes := 0

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
		if w and w.room and w.room.player:
			w.room.player.hp = w.room.player.max_hp
			GameState.hp = GameState.max_hp()

func tap(a: String) -> void:
	act(a, true)
	await frames(2)
	act(a, false)
	await frames(2)

func goto_room(id: String, spawn: String = "west") -> void:
	w.close_all_menus()
	w.change_room(id, spawn)
	await frames(40)
	while w.transitioning:
		await frames(5)
	await frames(20)

func walk_to(x: float, y: float, limit: int = 2400) -> void:
	var p: Player = w.room.player
	var last := p.position
	var still := 0
	var detour := 0
	var dy_sign := 1.0
	for i in limit:
		if w.dialogue.active:
			await advance_dialogue()
		var d := Vector2(x, y) - p.position
		if d.length() < 6:
			break
		var want_y := d.y
		if detour > 0:
			detour -= 1
			want_y = dy_sign * 50.0
		_axis("move_right", d.x > 4); _axis("move_left", d.x < -4)
		_axis("move_down", want_y > 3); _axis("move_up", want_y < -3)
		_knock_out_enemies()
		await frames(1)
		if p.position.distance_to(last) < 0.3 and p.state in ["walk", "idle"]:
			still += 1
		else:
			still = 0
		last = p.position
		if still > 10 and detour <= 0:
			var mid: float = (w.room.walk_top + w.room.walk_bot) * 0.5
			dy_sign = 1.0 if p.position.y < mid else -1.0
			detour = 40
			still = 0
	for a in ["move_right", "move_left", "move_down", "move_up"]:
		held[a] = false
		act(a, false)
	await frames(2)

var held := {}
func _axis(a: String, on: bool) -> void:
	if on or bool(held.get(a, false)):
		held[a] = on
		act(a, on)

func _knock_out_enemies() -> void:
	for e in w.room.actors.duplicate():
		if e is Enemy and e.team == Actor.TEAM_ENEMY and not e.dead and not e.entering and w.room.on_screen(e, 0) and e.state != "knockdown" and not e.lying:
			e.hp = 0
			e.take_damage_and_react(w.room.player, {"knockdown": true, "kb": 120, "launch": 120}, 0.0, 1, false)

func advance_dialogue(choice: int = 0) -> void:
	for i in 400:
		if not w.dialogue.active:
			return
		if w.dialogue.choosing:
			for k in choice:
				await tap("ui_down")
			await tap("ui_accept")
		else:
			await tap("ui_accept")
		await frames(2)

func talk_to(npc_id: String, choice: int = 0) -> void:
	var n: NPC = w.room.find_npc(npc_id)
	if n == null:
		check(false, "npc %s present in %s" % [npc_id, w.room.room_id])
		return
	var off := 24.0 if n.position.x > 60 else -24.0
	var ty: float = n.position.y + (18.0 if n.mode == "behind_counter" else 2.0)
	await walk_to(n.position.x - off, clampf(ty, w.room.walk_top, w.room.walk_bot))
	await tap("interact")
	await frames(6)
	await advance_dialogue(choice)
	await frames(6)
	while w.top_menu() != null:
		await tap("ui_cancel")
		await frames(4)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	GameState.reset_new_game()
	for f in ["intro_done", "intro_seen", "met_mara", "boss_duke", "met_jett"]:
		GameState.set_flag(f)
	GameState.bosses["duke"] = true
	GameState.stage = "neon"
	GameState.add_cash(200)
	GameState.room = "oq_brickrow"
	GameState.spawn = "west"
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await q_dog()
	await q_tools()
	await q_escort()
	await q_parcels()
	await q_score()
	await q_cup()
	# persistence: everything survives a save/load round trip
	var before := JSON.stringify(GameState.quests)
	SaveService.save_game(3)
	GameState.reset_new_game()
	SaveService.load_game(3)
	check(JSON.stringify(GameState.quests) == before, "quest state persists through save/load")
	SaveService.delete_slot(3)
	print("QUEST TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

func q_dog() -> void:
	await talk_to("alvarez")
	check(Quests.is_active("dog") and GameState.has_key("leash"), "dog quest starts with leash")
	await goto_room("iy_spur")
	await talk_to("biscuit")

	check(GameState.has_flag("follower_biscuit") and Quests.step("dog") == 1, "Biscuit found and following")
	await goto_room("oq_brickrow")
	check(w.room.find_npc("biscuit") != null, "Biscuit follows across rooms")
	var cash0 := GameState.cash
	await talk_to("alvarez")
	check(Quests.state("dog") == "done" and GameState.cash >= cash0 + 40 and GameState.bag.count("empanada") == 2, "dog quest reward")

func q_tools() -> void:
	await goto_room("int_garage", "south")
	await talk_to("mara")
	check(Quests.is_active("tools"), "tools quest starts")
	await goto_room("cm_canalwalk")
	var p: Player = w.room.player
	await walk_to(1250, 290)
	await walk_to(1360, 290)
	await frames(200)
	var seen_vic := false
	for i in 600:
		_knock_out_enemies()
		for e in w.room.actors:
			if e is Enemy and e.named == "Sticky Vic":
				seen_vic = true
		for pk in w.room.pickups.duplicate():
			if pk.kind == "key" and pk.key_id == "toolbox" and pk.z < 1.0:
				await walk_to(pk.position.x, pk.position.y)
		if GameState.has_key("toolbox"):
			break
		await frames(1)
	check(seen_vic or GameState.has_key("toolbox"), "Sticky Vic appears (or his toolbox drop was collected)")
	check(GameState.has_key("toolbox") and Quests.step("tools") == 1, "toolbox recovered")
	await goto_room("int_garage", "south")
	await talk_to("mara")
	check(Quests.state("tools") == "done" and GameState.upgrade_tier("grip") >= 1, "tools reward (grip tape)")

func q_escort() -> void:
	await goto_room("int_books", "south")
	await talk_to("hollis", 0)
	check(Quests.is_active("escort"), "escort starts")
	await goto_room("cm_gate", "door:books")
	check(w.room.find_npc("hollis") != null, "Hollis follows outside")
	await goto_room("cm_canalwalk")
	await walk_to(1880, 300)
	await goto_room("cm_pier")
	await walk_to(260, 290)
	await frames(60)
	await advance_dialogue()
	await frames(60)
	check(Quests.state("escort") == "done" and GameState.has_skill("heel"), "escort reward (Heel Drop)")

func q_parcels() -> void:
	await goto_room("cm_gate")
	await talk_to("teddy")
	check(Quests.is_active("parcels"), "parcels quest starts")
	for spot in [["cm_canalwalk", 6], ["iy_gate", 5], ["nm_marquee", 6]]:
		await goto_room(spot[0])
		var target: Prop = null
		for pr in w.room.props:
			if pr.index == spot[1]:
				target = pr
		check(target != null and target.contents.has("key"), "parcel hidden in %s" % spot[0])
		if target:
			await walk_to(target.position.x - 20, clampf(target.position.y + 4, w.room.walk_top, w.room.walk_bot))
			if target.breakable:
				target.break_open()
			else:
				target.lifted()
			await frames(40)
			for pk in w.room.pickups.duplicate():
				if pk.kind == "key":
					await walk_to(pk.position.x, pk.position.y)
			await frames(10)
	check(int(GameState.key_items.get("parcel", 0)) == 3 and Quests.step("parcels") == 1, "3 parcels collected")
	await goto_room("cm_gate")
	await talk_to("teddy")
	check(Quests.state("parcels") == "done" and "courier_sneakers" in GameState.gear, "parcels reward (sneakers)")

func q_score() -> void:
	await goto_room("int_arcade", "south")
	await talk_to("lacey")
	check(Quests.is_active("score"), "score quest starts")
	await talk_to("pip")
	await talk_to("marv")
	await talk_to("townc")
	check(Quests.step("score") == 1, "three clues gathered")
	await talk_to("lacey", 2)
	check(Quests.state("score") == "done" and "token_jacket" in GameState.gear, "score reward for correct verdict")

func q_cup() -> void:
	await goto_room("nm_arcade")
	var cash0 := GameState.cash
	await talk_to("bigmo", 0)
	check(GameState.has_flag("cup_entry"), "cup entry paid")
	await goto_room("nm_backalley", "south")
	for i in 60 * 40:
		if not GameState.has_flag("cup_running") and i > 200:
			break
		_knock_out_enemies()
		if w.dialogue.active:
			await advance_dialogue()
		await frames(1)
	await advance_dialogue()
	check(Quests.state("cup") == "done" and "champion_wraps" in GameState.gear, "cup won")
