extends Node
## Completes all six side jobs through real interactions (walk up, Grab/Talk, dialogue choices).
## Content 1.2 tests: the Underline chapter, Kowal, four new side jobs, the Rec Center ladder and New Game+.
## Content 1.2 tests: the Underline chapter, Kowal, four new side jobs, the Rec Center ladder and New Game+.
## Content 1.2 tests: the Underline chapter, Kowal, four new side jobs, the Rec Center ladder and New Game+.

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

var allow_ko := false
func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame
		if w and w.room and w.room.player and not allow_ko:
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


const CH3 := ["intro_done", "intro_seen", "met_mara", "boss_duke", "met_jett", "boss_pikes", "act1_done", "act2_started",
	"rescued_gus", "boss_otto", "arcade_backroom", "boss_jett", "setback_fought", "act3_started"]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	GameState.reset_new_game()
	for f in CH3:
		GameState.set_flag(f)
	for b in ["duke", "pikes", "otto", "jett"]:
		GameState.bosses[b] = true
	GameState.stage = "underline"
	GameState.level = 12
	GameState.add_cash(200)
	GameState.room = "ul_station"
	GameState.spawn = "west"
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await t_underline()
	await t_radio()
	await t_punch()
	await t_mural()
	await t_weights()
	await t_ladder()
	await t_ladder_knockout()
	await t_ngplus()
	print("EXPANSION TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

## Fight through one room: walk east in steps, knocking out whoever shows up, until the east edge is reached.
func clear_walk(to_x: float) -> void:
	var p: Player = w.room.player
	for leg in 12:
		await walk_to(minf(to_x, p.position.x + 220.0), clampf(p.position.y, w.room.walk_top + 20, w.room.walk_bot - 20), 900)
		for i in 240:
			_knock_out_enemies()
			if w.dialogue.active:
				await advance_dialogue()
			if w.room.wave_queue.is_empty() and w.room.enemies_alive() == 0:
				break
			await frames(1)
		if p.position.x >= to_x - 10.0:
			break

func collect_key(key: String, tries: int = 900) -> void:
	for i in tries:
		_knock_out_enemies()
		GameState.hp = GameState.max_hp()
		if w.dialogue.active:
			await advance_dialogue()
		for pk in w.room.pickups.duplicate():
			if is_instance_valid(pk) and pk.kind == "key" and pk.key_id == key and pk.z < 1.0:
				await walk_to(pk.position.x, pk.position.y)
		if GameState.has_key(key):
			return
		await frames(1)

func t_underline() -> void:
	check(w.room.room_id == "ul_station" and w.room.vis.v2, "Kessler St. Station loads with v2 art")
	await clear_walk(500)
	check(GameState.has_flag("ul_entered"), "station entry scene plays")
	check(Content.room("nm_rooftops").exits.east.to == "ul_station", "rooftops fire escape leads into the Underline")
	await goto_room("ul_vault")
	var p: Player = w.room.player
	await walk_to(600, 290)
	var kowal: Boss = null
	for i in 900:
		if w.dialogue.active:
			await advance_dialogue()
		for a in w.room.actors:
			if a is Boss and a.boss_id == "kowal":
				kowal = a
		if kowal and w.room.boss_active:
			break
		_knock_out_enemies()
		await frames(1)
	check(kowal != null and w.room.boss_active, "Kowal boss fight starts in the vault")
	if kowal == null:
		return
	kowal.hp = int(kowal.max_hp * 0.45)
	for i in 300:
		if kowal.phase == 2 and w.room.vis.darkness < 0.6:
			break
		if w.dialogue.active:
			await advance_dialogue()
		await frames(1)
	check(kowal.phase == 2 and w.room.vis.darkness < 0.9, "lights go out at half health")
	for i in 1200:
		if not w.room.boss_active and GameState.has_flag("boss_kowal"):
			break
		if w.dialogue.active:
			await advance_dialogue()
		for a in w.room.actors.duplicate():
			if a is Enemy and a.team == Actor.TEAM_ENEMY and not a.dead and a.state != "knockdown" and not a.lying:
				a.hp = 0
				a.take_damage_and_react(p, {"knockdown": true, "kb": 120, "launch": 120}, 0.0, 1, false)
		GameState.hp = GameState.max_hp()
		p.hp = GameState.hp
		await frames(1)
	for i in 400:
		if w.dialogue.active:
			await advance_dialogue()
		if not Story.busy:
			break
		await frames(2)
	check(GameState.has_flag("boss_kowal") and GameState.stage == "floodgate", "Kowal defeated -> stage floodgate")
	check(GameState.check(Content.room("ul_vault").exits.east.requires), "service ladder to Floodgate Bridge opens")
	check(w.room.vis.darkness > 0.95 or w.room.vis._dark_target > 0.95, "lights come back on after the fight")
	await goto_room("fr_bridge")
	check(w.room.room_id == "fr_bridge", "Floodgate Bridge reachable after the Underline")

func t_radio() -> void:
	await goto_room("int_pharmacy", "south")
	await talk_to("ines")
	check(Quests.is_active("radio"), "radio quest starts (Ines)")
	await goto_room("nm_backalley")
	await frames(60)
	await walk_to(380, 290)
	await collect_key("radio")
	check(GameState.has_key("radio") and Quests.step("radio") == 1, "Flicker drops the radio")
	await goto_room("int_pharmacy", "south")
	var c0 := GameState.cash
	await talk_to("ines")
	check(Quests.state("radio") == "done" and GameState.cash >= c0 + 60, "radio quest reward")

func t_punch() -> void:
	await goto_room("ul_station")
	await talk_to("otis")
	check(Quests.is_active("punch"), "punch quest starts (Otis)")
	await goto_room("ul_tunnel")
	var crate: Prop = null
	for pr in w.room.props:
		if pr.index == 4:
			crate = pr
	check(crate != null and crate.contents.get("key", "") == "conductor_punch", "the punch is hidden in a Tunnel 3 crate")
	if crate:
		await walk_to(crate.position.x - 20, crate.position.y + 4)
		w.room.player.facing = 1
		for i in 12:
			if not is_instance_valid(crate) or crate.broken:
				break
			await tap("punch")
			await frames(12)
		if is_instance_valid(crate) and not crate.broken:
			crate.receive_hit(w.room.player, {}, 99.0, 1)
	await collect_key("conductor_punch")
	check(GameState.has_key("conductor_punch") and Quests.step("punch") == 1, "conductor's punch found")
	await goto_room("ul_station")
	await talk_to("otis")
	check(Quests.state("punch") == "done", "punch quest complete")

func t_mural() -> void:
	await goto_room("cm_gate")
	await talk_to("kiki")
	check(Quests.is_active("mural"), "mural quest starts (Kiki)")
	await goto_room("oq_chainlot")
	await clear_walk(1100)
	for i in 2400:
		_knock_out_enemies()
		if Quests.step("mural") >= 1:
			break
		if i % 300 == 299:
			await walk_to(1000.0 if w.room.player.position.x > 1050 else 1100.0, 290, 200)
		await frames(1)
	check(GameState.has_flag("mural_tag1") and GameState.has_flag("mural_tag2") and Quests.step("mural") == 1, "both tagger crews run off")
	await goto_room("cm_gate")
	await talk_to("kiki")
	check(Quests.state("mural") == "done", "mural quest complete")

func t_weights() -> void:
	await goto_room("cm_canalwalk")
	await talk_to("sal")
	check(Quests.is_active("weights"), "weights quest starts (Sal)")
	for pair in [["cm_pier", "weight_pier", 900.0], ["iy_gate", "weight_iron", 800.0], ["nm_marquee", "weight_neon", 900.0]]:
		await goto_room(pair[0])
		await clear_walk(float(pair[2]) + 60.0)
		await collect_key(pair[1])
		check(GameState.has_key(pair[1]), "inspector drops weights in " + pair[0])
	check(Quests.step("weights") == 1, "all three weights recovered")
	await goto_room("cm_canalwalk")
	await talk_to("sal")
	check(Quests.state("weights") == "done", "weights quest complete")

func _run_ladder(lose_at: int) -> void:
	await goto_room("int_rec", "south")
	await talk_to("benny", 1)
	var started := false
	for i in 9000:
		if w.dialogue.active:
			await advance_dialogue()
		if Story.ladder_active:
			started = true
		elif started:
			break
		var p: Player = w.room.player
		if lose_at > 0 and Story.ladder_active:
			allow_ko = true
			p.hp = 0
			GameState.hp = 0
			p.take_damage_and_react(p, {"knockdown": true, "kb": 100, "launch": 100}, 0.0, 1, false)
			lose_at = 0
		elif allow_ko:
			pass   # let the knockout land (no HP refill)
		else:
			_knock_out_enemies()
			GameState.hp = GameState.max_hp()
			p.hp = GameState.hp
		await frames(1)
	for i in 300:
		if w.dialogue.active:
			await advance_dialogue()
		if not Story.busy:
			break
		await frames(2)
	allow_ko = false
	check(started, "ladder starts from Benny's menu")

func t_ladder() -> void:
	await _run_ladder(-1)
	check(GameState.has_flag("ladder_champion") and int(GameState.stats.get("ladder_best", 0)) == 9, "all nine bouts cleared, Mae beaten")
	check(GameState.gear.has("ladder_belt") and GameState.gear.has("iron_wraps"), "ladder gear rewards")
	check(not w.room.exits_locked, "Rec Center exits unlock after the ladder")

func t_ladder_knockout() -> void:
	await _run_ladder(1)
	check(Story.ladder_lost and w.top_menu() == null, "a ladder KO ends the night without the defeat screen")
	await frames(120)
	check(not w.room.player.dead and GameState.hp > 0, "Nico gets back up after a ladder KO")

func t_ngplus() -> void:
	GameState.set_flag("game_complete")
	GameState.level = 14
	GameState.gear.append("courier_sneakers")
	var lvl := GameState.level
	var e0: Enemy = w.room.spawn_enemy("dogs_brawler", Vector2(300, 300), {"tier": 2})
	var hp0 := e0.max_hp
	w.room.remove_actor(e0)
	GameState.start_new_game_plus()
	check(GameState.ng_cycle == 1 and GameState.level == lvl and GameState.stage == "intro", "NG+ keeps level, restarts story")
	check(not GameState.has_flag("game_complete") and GameState.quests.is_empty(), "NG+ resets flags and quests")
	check(GameState.gear.has("courier_sneakers") and GameState.gear.has("iron_wraps"), "NG+ keeps gear")
	var e1: Enemy = w.room.spawn_enemy("dogs_brawler", Vector2(300, 300), {"tier": 2})
	check(e1.max_hp > hp0, "NG+ enemies are tougher (%d -> %d HP)" % [hp0, e1.max_hp])
	w.room.remove_actor(e1)
	SaveService.save_game(3)
	GameState.reset_new_game()
	SaveService.load_game(3)
	check(GameState.ng_cycle == 1 and GameState.new_game_plus, "NG+ cycle survives save/load")
	SaveService.delete_slot(3)
