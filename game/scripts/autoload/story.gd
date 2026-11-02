extends Node
## Story director: objectives, cutscenes, room events, boss fights, NPC conversations,
## followers (Biscuit, Mr. Hollis, Jett), the Alley Cat Cup and the ending.
## Cutscenes are coroutines; they bail out safely if the room changes underneath them.

var world: Node
var credits_return := "title"
var busy := false
var cup_timer := 0.0
var cup_round := 0
var cup_room: Node = null
var held_weapon_for_cup := ""

const TOKENS := ["punch", "kick", "jump", "guard", "interact", "run", "status", "pause"]

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE

# ---------------------------------------------------------------- text helpers
func format_text(s: String) -> String:
	if not "{" in s:
		return s
	for t in TOKENS:
		s = s.replace("{" + t + "}", InputPrompts.tag(t))
	s = s.replace("{move}", InputPrompts.move_label())
	return s

func objective_text() -> String:
	return format_text(str(Content.story.get("objectives", {}).get(GameState.stage, "Explore Bellwether.")))

func objective_detail() -> String:
	return format_text(str(Content.story.get("details", {}).get(GameState.stage, "")))

func new_game() -> void:
	GameState.stage = "intro"
	busy = false

func _valid(room) -> bool:
	return room != null and is_instance_valid(room) and room.is_inside_tree() and world != null and is_instance_valid(world) and world.room == room

func _wait(room, sec: float) -> bool:
	var t := get_tree().create_timer(sec, false)
	await t.timeout
	return _valid(room)

func _say(id: String) -> void:
	if world:
		await world.say(id)

func _set_stage(s: String) -> void:
	GameState.set_stage(s)
	if world:
		world.hud.refresh_objective()
		world.toast("Objective: " + objective_text(), UIKit.MUSTARD)

func _note(n: String) -> void:
	GameState.add_note(n)

# ---------------------------------------------------------------- room lifecycle
func on_room_enter(room: Node, _first: bool) -> void:
	busy = false
	_spawn_followers(room)
	if GameState.has_flag("game_complete") and not GameState.has_flag("postgame_welcomed") and room.room_id == "int_diner":
		GameState.set_flag("postgame_welcomed")
		await get_tree().create_timer(0.6, false).timeout
		if _valid(room):
			await _say("postgame_welcome")
	await get_tree().process_frame

func on_room_exit(_room: Node) -> void:
	pass

## Called by Room when the player reaches an encounter event marker.
func on_event(room: Node, id: String) -> void:
	match id:
		"intro": await _intro(room)
		"mara_meet": await _mara_meet(room)
		"jett_duel": await _jett_duel(room)
		"act2_card":
			GameState.set_flag("act2_card_seen")
			await _say("act2_card")
		"switch_fight": await _switch_fight(room)
		"arcade_jett": await _arcade_jett(room)
		"setback_arrive": await _setback_arrive(room)
		"setback_garage": await _setback_garage(room)
		"alliance": await _alliance(room)
		"price_meet": await _price_meet(room)
		"mara_arrives": await _mara_arrives(room)
		"escort_arrive": _escort_arrive(room)
		"cup_start": await _cup_start(room)

# ---------------------------------------------------------------- helpers for scripted fights
func _spawn_from_side(room: Node, id: String, side: int, opts: Dictionary = {}) -> Enemy:
	var x: float = room.cam_right() + 24.0 if side > 0 else room.cam_left() - 24.0
	x = clampf(x, 10.0, room.width - 10.0)
	var y: float = room.free_y(x)
	var e: Enemy = room.spawn_enemy(id, Vector2(x, y), opts)
	e.entering = not room.on_screen(e, 20)
	e.leash = true
	return e

## Spawns a group, locks exits, and waits until they're all down. Returns false if the room went away.
func _fight(room: Node, ids: Array, lock_text: String = "", sides: Array = [1]) -> bool:
	if lock_text != "":
		room.lock_exits(true, lock_text)
	var list: Array = []
	var i := 0
	for id in ids:
		var opts: Dictionary = {}
		var eid := ""
		if typeof(id) == TYPE_DICTIONARY:
			opts = id.duplicate()
			eid = str(opts.id)
		else:
			eid = str(id)
		list.append(_spawn_from_side(room, eid, sides[i % sides.size()], opts))
		i += 1
		if not await _wait(room, 0.35):
			return false
	while _valid(room):
		var alive := false
		for e in list:
			if is_instance_valid(e) and not e.dead:
				alive = true
		if not alive:
			break
		await get_tree().physics_frame
	if not _valid(room):
		return false
	if lock_text != "":
		room.lock_exits(false)
	return true

func _spawn_ally(room: Node, id: String, pos: Vector2) -> Enemy:
	var e: Enemy = room.spawn_enemy(id, pos, {"ally": true})
	e.team = Actor.TEAM_PLAYER
	e.ally = true
	e.max_hp = 9999
	e.hp = 9999
	e.power_mult *= 0.45
	e.aggression = 0.55
	e.xp_reward = 0
	e.cash_range = [0, 0]
	return e

func _spawn_followers(room: Node) -> void:
	var p: Player = room.player
	if GameState.has_flag("follower_biscuit") and room.room_id != "nm_backalley":
		var b: NPC = room.spawn_npc("biscuit", "biscuit", room.clamp_ground(p.position + Vector2(-26 * p.facing, 6)), {"mode": "follow", "talk": true, "label": "Pet Biscuit"})
		b.follow_target = p
	if Quests.is_active("escort"):
		if Content.room(room.room_id).get("district", "") != "canal_market":
			Quests.fail("escort")
			world.toast("Mr. Hollis wouldn't leave the market and went home. Talk to him to try again.")
		else:
			var h: NPC = room.spawn_npc("hollis", "hollis", room.clamp_ground(p.position + Vector2(-30 * p.facing, -8)), {"mode": "follow", "escort": true, "hp": 70, "talk": true, "label": "Talk to Mr. Hollis"})
			h.follow_target = p
	if GameState.has_flag("alliance") and not GameState.has_flag("boss_sabine") and room.room_id in ["fr_pumpstation", "fr_dockgate"]:
		var j := _spawn_ally(room, "jett", room.clamp_ground(p.position + Vector2(-34 * p.facing, 10)))
		j.display_name = "Jett"

# ---------------------------------------------------------------- prologue
func _intro(room: Node) -> void:
	busy = true
	var p: Player = room.player
	room.set_cutscene(true)
	var dot: NPC = room.spawn_npc("dot", "dot", Vector2(470, 232), {"mode": "cower", "talk": false})
	var t1: Enemy = room.spawn_enemy("dogs_brawler", Vector2(520, 240), {"hp_mult": 0.7})
	var t2: Enemy = room.spawn_enemy("dogs_brawler", Vector2(540, 268), {"hp_mult": 0.7})
	for t in [t1, t2]:
		t.facing = -1
	if not GameState.has_flag("intro_seen"):
		p.position = Vector2(30, 280)
		world.hud.show_card("Kettle Street", "Old Quarter  -  Bellwether, 1988", UIKit.MUSTARD)
		room.focus_camera(470)
		await room.walk_to(p, Vector2(330, 270), 80.0)
		if not _valid(room):
			return
		await _say("intro_1")
		room.release_camera()
		GameState.set_flag("intro_seen")
	room.set_cutscene(false)
	if not _valid(room):
		return
	world.hint("Move with {move}.  {punch} Punch  {kick} Kick  {jump} Jump.  Punch three times for a combo!", 9.0)
	room.lock_exits(true, "Help Dot first!")
	while _valid(room) and (is_instance_valid(t1) and not t1.dead) and (is_instance_valid(t2) and not t2.dead):
		await get_tree().physics_frame
	if not _valid(room):
		return
	world.hint("Hold {guard} to Guard. Tap it right before a hit for a PERFECT guard!", 7.0)
	while _valid(room) and ((is_instance_valid(t1) and not t1.dead) or (is_instance_valid(t2) and not t2.dead)):
		await get_tree().physics_frame
	if not _valid(room):
		return
	world.hint("One more! Grab the trash can with {interact} and throw it with {interact} or {punch}.", 8.0)
	var ok := await _fight(room, [{"id": "dogs_flanker", "hp_mult": 0.8}], "Help Dot first!")
	if not ok:
		return
	room.lock_exits(false)
	await _wait(room, 0.6)
	if not _valid(room):
		return
	dot.mode = "idle"
	dot.set_state("idle")
	room.set_cutscene(true)
	await room.walk_to(p, Vector2(430, 252), 80.0)
	p.facing = 1
	await _say("intro_2")
	room.set_cutscene(false)
	GameState.set_flag("intro_done")
	_note("eli_missing")
	_set_stage("find_mara")
	world.hint("Walk up into doorways to go inside. Dot's diner is a safe hub: food and saving. Check your objective anytime in the Journal ({pause}).", 9.0)
	await room.walk_to(dot, Vector2(460, 222), 50.0)
	if _valid(room):
		room.remove_npc(dot)
	busy = false
	world.autosave()

func _mara_meet(room: Node) -> void:
	room.set_cutscene(true)
	var mara: NPC = room.spawn_npc("mara", "mara", Vector2(420, 250), {"mode": "behind_counter", "talk": false, "facing": 1})
	await _wait(room, 0.4)
	if not _valid(room):
		return
	await room.walk_to(room.player, Vector2(330, 280), 80.0)
	room.player.facing = 1
	mara.facing = -1
	await _say("mara_meet")
	if not _valid(room):
		return
	room.set_cutscene(false)
	GameState.add_cash(20)
	GameState.set_flag("met_mara")
	_note("eli_note")
	mara.talkable = true
	mara.shop = "garage"
	_set_stage("chain_dogs")
	world.hint("Talk to Mara any time for weapon upgrades at her workbench.", 6.0)
	world.autosave()

# ---------------------------------------------------------------- bosses
func start_boss(room: Node, cfg: Dictionary) -> void:
	busy = true
	var p: Player = room.player
	var ids: Array = cfg.get("bosses", [cfg.id])
	var bosses: Array = []
	var bx := clampf(p.position.x + 170.0, 80.0, room.width - 60.0)
	for i in ids.size():
		var b: Enemy = room.spawn_enemy(ids[i], Vector2(bx + i * 30, room.walk_top + 40 + i * 50), {})
		b.facing = -1
		b.leash = true
		bosses.append(b)
	if bosses.size() == 2:
		bosses[0].partner = bosses[1]
		bosses[1].partner = bosses[0]
	room.lock_exits(true, "No running now!")
	var seen_flag: String = cfg.id + "_intro_seen"
	if not GameState.has_flag(seen_flag):
		room.set_cutscene(true)
		Audio.sfx("boss_intro")
		room.focus_camera((p.position.x + bx) * 0.5)
		await _wait(room, 0.6)
		if not _valid(room):
			return
		await _say(cfg.get("intro", ""))
		GameState.set_flag(seen_flag)
		room.release_camera()
		room.set_cutscene(false)
	if not _valid(room):
		return
	Audio.play_music(cfg.get("music", "boss"), 0.4)
	room.begin_boss_fight(cfg, bosses)
	_boss_tip(cfg.id)
	busy = false

func _boss_tip(id: String) -> void:
	var tips := {
		"duke": "Duke's chain has long reach. Watch for the red flash, then step out of his lane.",
		"pikes": "Rhea's pole outranges you and Lou throws from afar. Split them up and use the depth of the street.",
		"otto": "Otto's slam sends a shockwave along the ground. Jump over it! He's winded after big moves.",
		"jett": "Jett dodges predictable attacks. Punish him when he lands from a flip or dash.",
		"sabine": "Sabine counters blocked hits. Sweep, throw, or hit her from behind, and dodge the shield charge.",
		"rook": "Rook blocks and counters. Bait his attacks, guard, and punish the openings."
	}
	if tips.has(id):
		world.hint(tips[id], 8.0)

func boss_defeated(room: Node, cfg: Dictionary, _ids: Array) -> void:
	busy = true
	Audio.play_music("victory", 0.2)
	var beaten: Array = []
	for a in room.actors:
		if a is Boss and a.dead:
			beaten.append(a)
	await _wait(room, 1.4)
	if not _valid(room):
		return
	for b in beaten:
		if is_instance_valid(b):
			b.dead = true
			b.state = "cutscene"
			b.lying = false
			b.visible = true
			b.scripted_anim = "dizzy"
			b.set_meta("scripted_freeze", true)
			b.frozen = true
	room.set_cutscene(true)
	match cfg.id:
		"duke":
			await _say("duke_defeat")
			GameState.defeat_boss("duke")
			_note("gray_coat")
			_set_stage("market")
			await _say("bus_unlocked")
		"pikes":
			await _say("pikes_defeat")
			GameState.defeat_boss("pikes")
			GameState.defeat_boss("rhea")
			GameState.defeat_boss("lou")
			for k in ["satchel", "manifest", "photo"]:
				GameState.give_key(k)
			GameState.set_flag("act1_done")
			GameState.set_flag("act2_started")
			_note("satchel")
			_set_stage("ironworks")
		"otto":
			await _say("otto_defeat")
			GameState.defeat_boss("otto")
			GameState.give_key("payroll_pages")
			_note("rook_name")
			_set_stage("neon")
			world.toast("The rail tunnel between the Rail Spur and Brickrow Lane is open.")
		"jett":
			await _say("jett_defeat")
			GameState.defeat_boss("jett")
			GameState.give_key("count_book")
			GameState.give_key("eviction_notice")
			GameState.give_gear("lucky_bandana")
			_note("count_book")
			_set_stage("return_home")
		"sabine":
			await _say("sabine_defeat")
			GameState.defeat_boss("sabine")
			GameState.give_key("gate_key")
			_set_stage("warehouse")
		"rook":
			await _rook_ending(room)
			return
	if not _valid(room):
		return
	for b in beaten:
		if is_instance_valid(b):
			b.set_meta("scripted_freeze", false)
			b.frozen = false
			b.scripted_anim = "walk"
			b.state = "cutscene"
			var tgt := Vector2(room.width + 60, b.position.y)
			_walk_off(room, b, tgt)
	room.set_cutscene(false)
	room.release_camera()
	room.lock_exits(false)
	Audio.play_music(Content.room(room.room_id).get("music", "old_quarter"), 1.2)
	busy = false
	world.autosave()

func _walk_off(room: Node, a: Actor, tgt: Vector2) -> void:
	var guard := 0
	while _valid(room) and is_instance_valid(a) and absf(a.position.x - tgt.x) > 4 and guard < 400:
		var d := signf(tgt.x - a.position.x)
		a.position.x += d * 1.4
		a.facing = int(d)
		a._update_visual()
		guard += 1
		await get_tree().physics_frame
	if _valid(room) and is_instance_valid(a):
		room.remove_actor(a)

func boss_retreat(room: Node, b: Boss) -> void:
	# Jett at the Canal Walk: he leaves at half health
	if not _valid(room):
		return
	b.invuln = 9999
	b.set_meta("scripted_freeze", true)
	room.boss_actors.clear()
	room.boss_active = false
	world.boss_bar(null)
	for t in room.actors.duplicate():
		if t is Enemy and not t.is_boss and t.team == Actor.TEAM_ENEMY:
			room.remove_actor(t)
	room.set_cutscene(true)
	await _wait(room, 0.8)
	if not _valid(room):
		return
	b.frozen = true
	b.state = "cutscene"
	b.scripted_anim = "victory"
	await _say("jett_retreat")
	if not _valid(room):
		return
	b.frozen = false
	b.scripted_anim = "jump"
	var tw := create_tween()
	tw.tween_property(b, "position", b.position + Vector2(140, -40), 0.6)
	tw.tween_callback(func():
		if _valid(room) and is_instance_valid(b):
			room.remove_actor(b))
	GameState.add_xp(60)
	room.float_text(room.player.position + Vector2(0, -60), "+60 XP", UIKit.XPC)
	GameState.set_flag("met_jett")
	room.set_cutscene(false)
	room.lock_exits(false)
	Audio.play_music(Content.room(room.room_id).get("music", "canal_market"), 1.0)
	_set_stage("pikes")
	busy = false
	world.autosave()

func _jett_duel(room: Node) -> void:
	busy = true
	room.set_cutscene(true)
	var p: Player = room.player
	var j: Enemy = room.spawn_enemy("jett_cm", Vector2(clampf(p.position.x + 150, 0, room.width - 40), p.position.y), {})
	j.facing = -1
	j.leash = true
	if not GameState.has_flag("jett_intro_seen"):
		await _wait(room, 0.4)
		if not _valid(room):
			return
		await _say("jett_intro")
		GameState.set_flag("jett_intro_seen")
	room.set_cutscene(false)
	if not _valid(room):
		return
	Audio.play_music("boss", 0.4)
	room.lock_exits(true, "Jett's blocking the walk!")
	room.boss_actors = [j]
	room.boss_active = true
	world.boss_bar([j])
	busy = false

func rook_phase_two(room: Node, b: Boss) -> void:
	if not _valid(room):
		return
	room.set_cutscene(true)
	b.set_meta("cutscene_active", true)
	await _wait(room, 0.3)
	if not _valid(room):
		return
	await _say("rook_phase2")
	if not _valid(room) or not is_instance_valid(b):
		return
	b.become_phase_two()
	b.set_meta("cutscene_active", false)
	room.set_cutscene(false)
	Audio.sfx("alarm")
	room.shake(3)
	_rook_barks(room, b)

func _rook_barks(room: Node, b: Boss) -> void:
	var said := {}
	while _valid(room) and is_instance_valid(b) and not b.dead:
		var f := float(b.hp) / float(b.max_hp)
		for pair in [[0.4, "rook_bark_2"], [0.2, "rook_bark_3"]]:
			if f <= pair[0] and not said.has(pair[1]):
				said[pair[1]] = true
				world.bark(b, pair[1])
		await get_tree().create_timer(0.5, false).timeout

# ---------------------------------------------------------------- act II
func _switch_fight(room: Node) -> void:
	busy = true
	await _wait(room, 0.4)
	if not _valid(room):
		return
	await _say("switch_hint")
	var ok := await _fight(room, ["yard_brawler", "yard_heavy", "yard_weapon", "yard_thrower"], "Clear out Otto's boys first!", [1, 1, -1, 1])
	if not ok:
		return
	await _wait(room, 0.6)
	if not _valid(room):
		return
	var gus: NPC = room.find_npc("gus")
	room.set_cutscene(true)
	if gus:
		gus.mode = "idle"
		gus.set_state("idle")
		await room.walk_to(room.player, gus.position + Vector2(-40, 6), 80.0)
		room.player.facing = 1
		gus.facing = -1
		room.focus_camera(gus.position.x - 20.0)
	await _say("gus_rescue")
	if not _valid(room):
		return
	room.release_camera()
	GameState.set_flag("rescued_gus")
	_note("greyline")
	_set_stage("foundry")
	room.set_cutscene(false)
	if gus:
		await room.walk_to(gus, Vector2(80, room.walk_bot - 4), 70.0)
		if _valid(room) and is_instance_valid(gus):
			room.remove_npc(gus)
	busy = false
	world.autosave()

func _arcade_jett(room: Node) -> void:
	busy = true
	room.set_cutscene(true)
	var j: NPC = room.spawn_npc("jett", "jett", Vector2(700, 250), {"mode": "idle", "talk": false})
	await _wait(room, 0.5)
	if not _valid(room):
		return
	await _say("arcade_jett")
	if not _valid(room):
		return
	j.scripted_anim = "run"
	var tw := create_tween()
	tw.tween_property(j, "position", Vector2(90, room.walk_bot), 0.7)
	await tw.finished
	if _valid(room) and is_instance_valid(j):
		room.remove_npc(j)
	if not _valid(room):
		return
	GameState.set_flag("arcade_backroom")
	_set_stage("rooftops")
	room.set_cutscene(false)
	busy = false
	world.autosave()

# ---------------------------------------------------------------- setback
func _setback_arrive(room: Node) -> void:
	busy = true
	Audio.play_music("setback", 0.6)
	room.set_cutscene(true)
	room.focus_camera(640)
	var mott_preview: Enemy = room.spawn_enemy("sergeant", Vector2(700, 280), {})
	mott_preview.facing = -1
	await _wait(room, 0.8)
	if not _valid(room):
		return
	if not GameState.has_flag("setback_seen"):
		await _say("setback_arrive")
		GameState.set_flag("setback_seen")
	if not _valid(room):
		return
	room.release_camera()
	room.set_cutscene(false)
	Audio.play_music("boss", 0.5)
	room.boss_actors = [mott_preview]
	room.boss_active = true
	world.boss_bar([mott_preview])
	room.lock_exits(true, "Save the garage!")
	var ok := await _fight(room, [{"id": "grays_brawler", "tier": 4}, {"id": "grays_blocker", "tier": 4}, {"id": "grays_weapon", "tier": 4}], "", [1, -1, 1])
	if not ok:
		return
	while _valid(room) and is_instance_valid(mott_preview) and not mott_preview.dead:
		await get_tree().physics_frame
	if not _valid(room):
		return
	room.boss_active = false
	room.boss_actors.clear()
	world.boss_bar(null)
	room.lock_exits(false)
	GameState.set_flag("setback_fought")
	Audio.play_music("setback", 0.8)
	world.toast("Get inside the garage!", UIKit.MUSTARD)
	busy = false
	world.autosave()

func _setback_garage(room: Node) -> void:
	busy = true
	Audio.play_music("setback", 0.6)
	room.set_cutscene(true)
	var mara: NPC = room.find_npc("mara")
	if mara == null:
		mara = room.spawn_npc("mara", "mara", Vector2(400, 246), {"mode": "idle", "talk": false})
	await _wait(room, 0.3)
	if not _valid(room):
		return
	await room.walk_to(room.player, Vector2(320, 284), 80.0)
	room.player.facing = 1
	await _say("setback_garage")
	if not _valid(room):
		return
	var rook: NPC = room.spawn_npc("rook", "rook", Vector2(80, room.walk_bot - 4), {"mode": "idle", "talk": false})
	await room.walk_to(rook, Vector2(180, 290), 50.0)
	if not _valid(room):
		return
	room.player.facing = -1
	await _say("rook_garage")
	if not _valid(room):
		return
	await room.walk_to(rook, Vector2(60, room.walk_bot - 2), 60.0)
	if _valid(room) and is_instance_valid(rook):
		room.remove_npc(rook)
	GameState.give_key("cassette")
	GameState.set_flag("act3_started")
	_note("setback")
	_note("cassette")
	_set_stage("floodgate")
	await _say("act3_card")
	if not _valid(room):
		return
	room.set_cutscene(false)
	Audio.play_music("safe_hub", 1.0)
	busy = false
	world.autosave()

# ---------------------------------------------------------------- act III
func _alliance(room: Node) -> void:
	busy = true
	room.set_cutscene(true)
	var p: Player = room.player
	var allies: Array = []
	var spots := [["jett", Vector2(380, 250)], ["saints_flanker", Vector2(410, 300)], ["lou", Vector2(440, 236)], ["rhea", Vector2(470, 280)], ["duke", Vector2(350, 320)]]
	for s in spots:
		var a := _spawn_ally(room, s[0], s[1])
		a.facing = -1
		allies.append(a)
	await _wait(room, 0.5)
	if not _valid(room):
		return
	if not GameState.has_flag("alliance_seen"):
		await _say("alliance")
		GameState.set_flag("alliance_seen")
	if not _valid(room):
		return
	room.set_cutscene(false)
	Audio.play_music("boss", 0.4)
	var waves := [
		[{"id": "grays_brawler"}, {"id": "grays_flanker"}, {"id": "grays_thrower"}, {"id": "grays_brawler"}],
		[{"id": "grays_blocker"}, {"id": "grays_weapon"}, {"id": "grays_flanker"}, {"id": "grays_thrower"}],
		[{"id": "grays_heavy"}, {"id": "grays_blocker"}, {"id": "grays_weapon"}, {"id": "grays_brawler"}],
	]
	for w in waves:
		var ok := await _fight(room, w, "Hold the bridge!", [1, -1, 1, 1])
		if not ok:
			return
		if not await _wait(room, 0.8):
			return
	room.set_cutscene(true)
	await _say("alliance_done")
	if not _valid(room):
		return
	for a in allies:
		if is_instance_valid(a) and a.enemy_id != "jett":
			a.set_meta("scripted_freeze", true)
	room.set_cutscene(false)
	GameState.set_flag("alliance")
	_set_stage("dockgate")
	Audio.play_music("floodgate", 1.0)
	busy = false
	world.autosave()

func _price_meet(room: Node) -> void:
	var price: NPC = room.find_npc("price")
	room.set_cutscene(true)
	if price:
		await room.walk_to(room.player, price.position + Vector2(-40, 8), 80.0)
		room.player.facing = 1
	if not _valid(room):
		return
	await _say("price_meet")
	GameState.set_flag("met_price")
	_note("ledger_needed")
	room.set_cutscene(false)

func _mara_arrives(room: Node) -> void:
	busy = true
	GameState.set_flag("mara_arrived")
	room.set_cutscene(true)
	Audio.sfx("crate_break")
	room.shake(5)
	var mara: NPC = room.spawn_npc("mara", "mara", Vector2(40, 300), {"mode": "idle", "talk": false})
	await room.walk_to(mara, room.player.position + Vector2(-40, 10), 90.0)
	if not _valid(room):
		return
	room.player.facing = -1
	await _say("mara_arrives")
	if not _valid(room):
		return
	await room.walk_to(mara, Vector2(30, 300), 90.0)
	if _valid(room) and is_instance_valid(mara):
		room.remove_npc(mara)
	room.set_cutscene(false)
	busy = false

func on_wave_clear(room: Node, wid: String) -> void:
	if room.room_id == "rw_office" and wid == "o1":
		await _eli_found(room)

func _eli_found(room: Node) -> void:
	busy = true
	await _wait(room, 0.8)
	if not _valid(room):
		return
	room.set_cutscene(true)
	var eli: NPC = room.find_npc("eli")
	if eli == null:
		eli = room.spawn_npc("eli", "eli", Vector2(640, 250), {"mode": "cower", "talk": false})
	await room.walk_to(room.player, eli.position + Vector2(-42, 8), 80.0)
	room.player.facing = 1
	eli.mode = "idle"
	eli.set_state("idle")
	eli.facing = -1
	room.focus_camera(eli.position.x - 20.0)
	room.impulse(Vector2(0, 1), 1.0)
	var mara: NPC = room.spawn_npc("mara", "mara", Vector2(30, 300), {"mode": "idle", "talk": false})
	await room.walk_to(mara, eli.position + Vector2(-20, 24), 110.0)
	if not _valid(room):
		return
	await _say("eli_found")
	if not _valid(room):
		return
	room.release_camera()
	GameState.set_flag("found_eli")
	_note("eli_truth")
	_set_stage("rook")
	_walk_off(room, eli, Vector2(-40, eli.position.y))
	_walk_off(room, mara, Vector2(-40, mara.position.y))
	room.set_cutscene(false)
	busy = false
	world.autosave()

# ---------------------------------------------------------------- ending
func _rook_ending(room: Node) -> void:
	await _say("rook_defeat")
	if not _valid(room):
		return
	GameState.defeat_boss("rook")
	GameState.give_key("ledger")
	GameState.set_flag("game_complete")
	_note("ending")
	GameState.set_stage("epilogue")
	await SceneFlow.fade_out(1.0)
	var overlay := _ending_backdrop()
	world.ui_layer.add_child(overlay)
	world.ui_layer.move_child(overlay, 0)
	Audio.play_music("ending", 1.0)
	await SceneFlow.fade_in(0.8)
	await world.dialogue.play(Content.lines("ending_cards"))
	await SceneFlow.fade_out(0.8)
	overlay.queue_free()
	world.room.set_cutscene(false)
	world._load_room("int_diner", "south")
	var diner: Node = world.room
	diner.set_cutscene(true)
	await SceneFlow.fade_in(0.8)
	await world.dialogue.play(Content.lines("ending_diner"))
	await get_tree().create_timer(0.8).timeout
	GameState.room = "int_diner"
	GameState.spawn = "south"
	GameState.hp = GameState.max_hp()
	SaveService.save_game()
	credits_return = "world"
	await world.show_run_summary()
	busy = false
	SceneFlow.goto("res://scenes/credits.tscn", 1.0)

## The ending cards play over the dusk street from the title art, dimmed and slowly drifting.
func _ending_backdrop() -> Control:
	var root := ColorRect.new()
	root.color = Color(0.05, 0.03, 0.07)
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var i := 0
	for n in ["title_sky", "title_far", "title_mid", "title_street"]:
		var t := SpriteLib.tex("res://assets/ui2/%s.png" % n)
		if t == null:
			continue
		var r := TextureRect.new()
		r.texture = t
		r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		r.set_anchors_preset(Control.PRESET_FULL_RECT)
		r.offset_left = -20
		r.offset_right = 20
		r.modulate = Color(0.62, 0.55, 0.6)
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(r)
		var tw := r.create_tween().set_loops()
		tw.tween_property(r, "position:x", -20.0 - 6.0 * i, 9.0).set_trans(Tween.TRANS_SINE)
		tw.tween_property(r, "position:x", -20.0 + 6.0 * i, 9.0).set_trans(Tween.TRANS_SINE)
		i += 1
	return root

# ---------------------------------------------------------------- conversations
func talk(room: Node, npc: NPC) -> void:
	if busy or world.dialogue.active:
		return
	busy = true
	var id := npc.npc_id
	match id:
		"dot", "fong", "hank", "gus":
			await _hub_keeper(room, npc)
		"marv":
			if Quests.is_active("score") and not GameState.has_key("arcade_log"):
				await _say("score_marv")
				GameState.give_key("arcade_log")
				_score_clue("marv")
			else:
				await _hub_keeper(room, npc)
		"benny", "rosa":
			await _shopkeeper(room, npc)
		"hollis":
			await _hollis(room, npc)
		"mara":
			await _mara(room, npc)
		"alvarez":
			await _alvarez(room, npc)
		"biscuit":
			await _biscuit(room, npc)
		"teddy":
			await _teddy(room, npc)
		"lacey":
			await _lacey(room, npc)
		"pip":
			await _say("score_pip")
			if Quests.is_active("score"):
				_score_clue("pip")
		"townc":
			if room.room_id == "int_arcade" and Quests.is_active("score"):
				await _say("score_teen")
				_score_clue("teen")
			else:
				await _chat(npc)
		"bigmo":
			await _bigmo(room, npc)
		_:
			await _chat(npc)
	busy = false

func _chat(npc: NPC) -> void:
	var opts: Array = Content.npc_talk.get(npc.npc_id, [])
	for o in opts:
		if GameState.check(o.get("if", "")):
			await _say(o.say)
			return

func _hub_keeper(room: Node, npc: NPC) -> void:
	var shop: Dictionary = Content.shops.get(npc.shop, {})
	var line := [npc.npc_id, "happy", shop.get("greet", "What can I do for you?")]
	var choice: int = await world.ask(line, ["Order food", "Save game", "Chat", "Leave"])
	match choice:
		0:
			await world.open_shop(npc.shop)
		1:
			if SaveService.save_game():
				Audio.sfx("save")
				world.toast("Game saved to slot %d." % SaveService.current_slot, UIKit.CASHC)
			else:
				world.toast("Save failed: " + SaveService.last_error, UIKit.DANGER)
		2:
			await _chat(npc)

func _shopkeeper(_room: Node, npc: NPC) -> void:
	var shop: Dictionary = Content.shops.get(npc.shop, {})
	var line := [npc.npc_id, "neutral", shop.get("greet", "Take a look.")]
	var choice: int = await world.ask(line, ["Shop", "Chat", "Leave"])
	match choice:
		0: await world.open_shop(npc.shop)
		1: await _chat(npc)

func _mara(room: Node, npc: NPC) -> void:
	if Quests.is_active("tools") and GameState.has_key("toolbox"):
		await _say("tools_return")
		GameState.take_key("toolbox")
		Quests.complete("tools")
		return
	if Quests.available("tools"):
		await _say("tools_offer")
		Quests.start("tools")
		return
	await _shopkeeper(room, npc)

func _hollis(room: Node, npc: NPC) -> void:
	if npc.escort:
		await _say("escort_start")
		return
	if Quests.available("escort") or Quests.state("escort") == "failed":
		await _say("escort_offer")
		var c: int = await world.ask(["hollis", "neutral", "Will you walk me to Pier Square?"], ["Let's go", "Not right now"])
		if c == 0:
			Quests.start("escort")
			await _say("escort_start")
			room.remove_npc(npc)
			var p: Player = room.player
			var h: NPC = room.spawn_npc("hollis", "hollis", room.clamp_ground(p.position + Vector2(-30, -6)), {"mode": "follow", "escort": true, "hp": 70, "talk": true, "label": "Talk to Mr. Hollis"})
			h.follow_target = p
			world.hint("Lead Mr. Hollis east along the Canal Walk to Pier Square. Enemies will go after him!", 7.0)
		return
	await _shopkeeper(room, npc)

func escort_down(room: Node, n: NPC) -> void:
	if not Quests.is_active("escort"):
		return
	Quests.fail("escort")
	await _say("escort_fail")
	if _valid(room) and is_instance_valid(n):
		room.remove_npc(n)

func _escort_arrive(room: Node) -> void:
	if not Quests.is_active("escort"):
		return
	var h: NPC = room.find_npc("hollis")
	if h == null or h.dead:
		return
	busy = true
	await _say("escort_done")
	Quests.complete("escort")
	if _valid(room) and is_instance_valid(h):
		h.mode = "idle"
		await room.walk_to(h, Vector2(200, room.walk_top + 4), 60.0)
		if _valid(room) and is_instance_valid(h):
			room.remove_npc(h)
	busy = false

func _alvarez(room: Node, npc: NPC) -> void:
	if Quests.is_active("dog") and GameState.has_flag("follower_biscuit"):
		await _say("dog_return")
		GameState.set_flag("follower_biscuit", false)
		GameState.take_key("leash")
		Quests.complete("dog")
		var b: NPC = room.find_npc("biscuit")
		if b:
			b.mode = "idle"
			b.follow_target = null
			b.position = npc.position + Vector2(24, 4)
		return
	if Quests.available("dog"):
		await _say("dog_offer")
		Quests.start("dog")
		GameState.give_key("leash")
		return
	await _chat(npc)

func _biscuit(room: Node, npc: NPC) -> void:
	if Quests.is_active("dog") and not GameState.has_flag("dog_found"):
		await _say("dog_found")
		GameState.set_flag("dog_found")
		GameState.set_flag("follower_biscuit")
		Quests.set_step("dog", 1)
		npc.mode = "follow"
		npc.follow_target = room.player
		npc.label_override = "Pet Biscuit"
		return
	Audio.sfx("dog_bark")
	room.float_text(npc.position + Vector2(0, -30), "Arf!", Color.WHITE)

func _teddy(_room: Node, npc: NPC) -> void:
	if Quests.is_active("parcels"):
		if int(GameState.key_items.get("parcel", 0)) >= 3:
			await _say("parcels_return")
			GameState.take_key("parcel", 3)
			Quests.complete("parcels")
		else:
			await _say("parcels_waiting")
		return
	if Quests.available("parcels"):
		await _say("parcels_offer")
		Quests.start("parcels")
		return
	await _chat(npc)

func _score_clue(which: String) -> void:
	if not GameState.quests.has("score"):
		return
	var data: Dictionary = GameState.quests.score.get("data", {})
	data[which] = true
	GameState.quests.score["data"] = data
	if data.size() >= 3 and Quests.step("score") == 0:
		Quests.set_step("score", 1)
	elif Quests.step("score") == 0:
		world.toast("Clue noted (%d/3)." % data.size())

func _lacey(_room: Node, npc: NPC) -> void:
	if Quests.available("score"):
		await _say("score_offer")
		Quests.start("score")
		return
	if Quests.is_active("score"):
		if Quests.step("score") < 1:
			await _say("score_ask")
			world.toast("Talk to Pip, Marv and the kid by the back machines first.")
			return
		var c: int = await world.ask(["lacey", "neutral", "Well? Did Pip cheat, or what?"], ["Pip cheated.", "You're lying, Lacey.", "Cabinet 3's joystick is broken. Nobody cheated."])
		if c == 2:
			await _say("score_right")
			GameState.take_key("arcade_log")
			Quests.complete("score")
		else:
			await _say("score_wrong")
			GameState.take_key("arcade_log")
			Quests.complete("score", {"cash": 15, "xp": 30})
		return
	await _chat(npc)

# ---------------------------------------------------------------- Alley Cat Cup
func _bigmo(room: Node, npc: NPC) -> void:
	if GameState.has_flag("cup_entry"):
		await _say("cup_go")
		return
	if Quests.available("cup") or Quests.state("cup") == "failed":
		await _say("cup_offer" if Quests.state("cup") != "done" else "bigmo_1")
		var c: int = await world.ask(["bigmo", "happy", "Ten bucks to enter. You in?"], ["I'm in ($10)", "Maybe later"])
		if c == 0:
			if not GameState.spend(10):
				Audio.sfx("deny")
				world.toast("You need $10 for the entry fee.")
				return
			Audio.sfx("purchase")
			if Quests.state("cup") != "done":
				Quests.start("cup")
			GameState.set_flag("cup_entry")
			await _say("cup_go")
		return
	await _chat(npc)

func _cup_start(room: Node) -> void:
	busy = true
	GameState.set_flag("cup_entry", false)
	GameState.set_flag("cup_running")
	var p: Player = room.player
	if p.held != "":
		held_weapon_for_cup = p.held
		p.held = ""
		p.weapon_spr.visible = false
		world.toast("Big Mo holds onto your %s. No weapons in the Cup!" % Content.weapon(held_weapon_for_cup).get("name", "weapon"))
	room.lock_exits(true, "The Cup is on! No leaving mid-round.")
	Audio.play_music("boss", 0.4)
	for n in ["3", "2", "1", "FIGHT!"]:
		world.hud.set_timer(n)
		Audio.sfx("countdown_tick")
		if not await _wait(room, 0.7):
			return _cup_abort()
	Audio.sfx("crowd_cheer")
	cup_timer = 90.0
	cup_room = room
	var rounds := [
		["saints_brawler", "saints_brawler"],
		["saints_flanker", "saints_flanker", "saints_thrower"],
		["saints_blocker", "saints_brawler", "saints_flanker", "saints_brawler"],
	]
	var won := true
	for i in rounds.size():
		cup_round = i + 1
		world.toast("ROUND %d" % cup_round, UIKit.MUSTARD)
		var list: Array = []
		var k := 0
		for id in rounds[i]:
			list.append(_spawn_from_side(room, id, 1 if k % 2 == 0 else -1, {}))
			k += 1
		while _valid(room) and cup_timer > 0.0:
			var alive := false
			for e in list:
				if is_instance_valid(e) and not e.dead:
					alive = true
			if not alive:
				break
			cup_timer -= get_physics_process_delta_time()
			world.hud.set_timer("%d" % int(ceil(cup_timer)))
			await get_tree().physics_frame
		if not _valid(room):
			return _cup_abort()
		if cup_timer <= 0.0:
			won = false
			for e in list:
				if is_instance_valid(e) and not e.dead:
					room.remove_actor(e)
			break
	world.hud.set_timer("")
	GameState.set_flag("cup_running", false)
	room.lock_exits(false)
	_cup_return_weapon(p)
	if won:
		Audio.sfx("crowd_cheer")
		if int(GameState.quests.get("cup", {}).get("times", 0)) == 0:
			await _say("cup_win")
			Quests.complete("cup")
		else:
			await _say("cup_rematch_win")
			Quests.complete("cup", {"cash": 25, "xp": 40})
	else:
		await _say("cup_lose")
		if Quests.state("cup") != "done":
			Quests.fail("cup")
	Audio.play_music("neon_mile", 1.0)
	busy = false

func _cup_return_weapon(p: Player) -> void:
	if held_weapon_for_cup != "" and is_instance_valid(p):
		p.equip_weapon(held_weapon_for_cup)
	held_weapon_for_cup = ""

func _cup_abort() -> void:
	GameState.set_flag("cup_running", false)
	if world and world.hud:
		world.hud.set_timer("")
	busy = false

# ---------------------------------------------------------------- misc hooks
func on_enemy_defeated(_room: Node, _e: Enemy) -> void:
	pass

func on_prop_event(_e: String, _room: Node) -> void:
	pass

func can_retry_here(room: Node) -> bool:
	if room == null:
		return false
	return not Content.room(room.room_id).get("safe", false) and room.room_id != "nm_backalley"

func retry_spawn(_room: Node) -> String:
	return GameState.spawn

func on_defeat_reset() -> void:
	busy = false
	if GameState.has_flag("cup_running"):
		GameState.set_flag("cup_running", false)
		if Quests.state("cup") != "done":
			Quests.fail("cup")
		held_weapon_for_cup = ""
		if world and world.hud:
			world.hud.set_timer("")
	if Quests.is_active("escort"):
		Quests.fail("escort")
