extends Node
## "A neighbourhood that remembers": finished side jobs and beaten gangs leave visible, persistent marks.
## Each consequence is checked from both sides (there when its source is done, absent when it is not), through a
## save round-trip, from state set directly (a save made before these changes), for double grants, in New Game+,
## and the ending is played with no side jobs done and with all of them done.
## Run: godot --headless --fixed-fps 60 res://tests/consequence_tests.tscn

var w: Node
var fails := 0
var passes := 0
var auto_dialogue := true

const STORY_FLAGS := ["intro_seen", "intro_done", "tutor_v2", "met_mara", "met_jett", "act1_done", "act2_started",
	"act2_card_seen", "rescued_gus", "arcade_backroom", "setback_seen", "setback_fought", "act3_started", "ul_entered",
	"ul_mid_seen", "alliance_seen", "alliance", "met_price", "mara_arrived", "dot_meal_done", "benny_lesson_done"]
const ALL_BOSSES := ["duke", "pikes", "otto", "jett", "kowal", "sabine"]
const SIDE_JOBS := ["dog", "tools", "escort", "score", "cup", "parcels", "radio", "punch", "mural", "weights"]
const KIT_KEY := "rw_office:pk:night_kit"

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
		if w and is_instance_valid(w) and w.room and w.room.player:
			w.room.player.hp = w.room.player.max_hp
			GameState.hp = GameState.max_hp()
		if auto_dialogue and w and is_instance_valid(w) and w.dialogue.active and not w.dialogue.choosing and i % 4 == 0:
			act("ui_accept", true)
			await get_tree().physics_frame
			act("ui_accept", false)

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

## Starts the real world scene. keep = true continues from the current GameState (like loading a save).
func start_world(setup: Callable, keep: bool = false) -> void:
	if w and is_instance_valid(w):
		w.queue_free()
		await get_tree().process_frame
		await get_tree().process_frame
	get_tree().paused = false
	if not keep:
		GameState.reset_new_game()
	Story.busy = false
	setup.call()
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await frames(10)

func enter(id: String, spawn: String = "west") -> void:
	w._load_room(id, spawn)
	await frames(30)

func save_roundtrip() -> void:
	var text := JSON.stringify(SaveService.build_payload())
	var d: Dictionary = JSON.parse_string(text)
	GameState.from_dict(d.data)

func done(qid: String) -> void:
	GameState.quests[qid] = {"state": "done", "step": 1, "data": {}, "times": 1}

## A save somewhere in the story, written the way an older build would have left it: flags, boss records and
## quest states only, none of the flags this work introduced.
func story(stage: String, bosses: Array, room_id: String, quests_done: Array = []) -> Callable:
	return func():
		for f in STORY_FLAGS:
			GameState.set_flag(f)
		for b in bosses:
			GameState.bosses[b] = true
		for q in quests_done:
			done(q)
		GameState.stage = stage
		GameState.room = room_id
		GameState.spawn = "west"

func count_npc(id: String) -> int:
	var n := 0
	for x in room().npcs:
		if is_instance_valid(x) and x.npc_id == id:
			n += 1
	return n

func layer_shown(layer_name: String) -> bool:
	for L in room().vis.layers:
		if str(L.name) == layer_name:
			return (L.node as Node2D).visible
	return false

func kit_pickup() -> Pickup:
	for pk in room().pickups:
		if is_instance_valid(pk) and pk.persist_key == KIT_KEY:
			return pk
	return null

## The line the NPC table picks right now (the same first-match rule Story._chat uses).
func chat_pick(npc_id: String) -> String:
	for o in Content.npc_talk.get(npc_id, []):
		if GameState.check(o.get("if", "")):
			return str(o.say)
	return ""

## Talks to an NPC through the real conversation code and returns the lines that came up first.
func said_by(npc_id: String) -> Array:
	var n := room().find_npc(npc_id)
	if n == null:
		return []
	auto_dialogue = false
	room().talk_to(n)
	await until(func(): return w.dialogue.active, 120)
	var lines: Array = w.dialogue.lines.duplicate()
	auto_dialogue = true
	await until(func(): return not Story.busy and not w.dialogue.active, 1200)
	while w.top_menu() != null:
		w.close_all_menus()
		await frames(2)
	return lines

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.show_hints = true
	Settings.difficulty = "normal"
	test_rules()
	await test_mural()
	await test_radio()
	await test_helped_people()
	await test_districts()
	await test_night_kit()
	await test_ending()
	await test_new_game_plus()
	print("CONSEQUENCE TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

# ---------------------------------------------------------------- state-only rules
func test_rules() -> void:
	GameState.reset_new_game()
	# the pharmacy's standing favour
	var bandage := int(Content.item("bandage").price)
	var tonic := int(Content.item("tonic").price)
	check(GameState.price_for("pharmacy", bandage) == bandage, "no pharmacy discount before the radio is returned")
	GameState.quests["radio"] = {"state": "active", "step": 1, "data": {}}
	check(GameState.price_for("pharmacy", tonic) == tonic, "no discount while the job is only in progress")
	done("radio")
	check(GameState.price_for("pharmacy", tonic) < tonic and GameState.price_for("pharmacy", tonic) >= int(tonic * 0.8), "the pharmacy takes a modest amount off once the radio is back (%d -> %d)" % [tonic, GameState.price_for("pharmacy", tonic)])
	check(GameState.price_for("pharmacy", 1) == 1, "a discounted price never drops to nothing")
	check(GameState.price_for("bait", bandage) == bandage and GameState.price_for("diner", 6) == 6, "other shops keep their prices")
	check(str(Content.shops.pharmacy.discount.get("note", "")) != "", "the discount carries a note the shop can show")
	save_roundtrip()
	check(GameState.price_for("pharmacy", tonic) < tonic, "the discount survives save and load")
	# the ending's guest list: fixed priority, capped, derived from quest states only
	GameState.reset_new_game()
	check(Story.ending_guests().is_empty(), "no guests when no side job is done")
	check(Story.ending_diner_lines() == Content.lines("ending_diner"), "a main-story-only ending is the scene exactly as written")
	GameState.quests["dog"] = {"state": "active", "step": 1, "data": {}}
	GameState.quests["escort"] = {"state": "failed", "step": 0, "data": {}}
	check(Story.ending_guests().is_empty(), "jobs in progress or failed bring nobody")
	done("cup")
	done("score")
	check(Story.ending_guests() == ["score", "cup"], "guests speak in the fixed order, whatever order the jobs were done in")
	for q in SIDE_JOBS:
		done(q)
	check(Story.ending_guests() == ["dog", "radio", "mural"], "with everything done only the first three speak")
	var all_lines := Story.ending_diner_lines()
	var base: Array = Content.lines("ending_diner")
	check(all_lines.size() == base.size() + 3 and all_lines[0] == base[0] and all_lines.slice(4) == base.slice(1), "the guests' lines sit after Dot's first line and nothing else moves")
	check(Content.lines("ending_diner").size() == base.size() and base.size() == 11, "building the scene never edits the stored dialogue")
	for q in Story.ENDING_FAVOURS:
		var l: Array = Content.lines("ending_guest_" + q)
		check(l.size() == 1 and str(l[0][0]) == str(Content.quests[q].giver), "the guest for '%s' is the person who was helped, with one line" % q)
	# changed lines follow their source and nothing else
	GameState.reset_new_game()
	for pair in [["ines", "radio", "ines_post"], ["rosa", "radio", "rosa_3"], ["sal", "weights", "sal_post"], ["otis", "punch", "otis_post"],
			["lacey", "score", "lacey_post"], ["pip", "score", "pip_post"], ["marv", "score", "marv_3"], ["hollis", "escort", "hollis_2"],
			["alvarez", "dog", "alvarez_post"], ["teddy", "parcels", "teddy_2"], ["kiki", "mural", "kiki_chat2"]]:
		var before := chat_pick(pair[0])
		done(pair[1])
		check(before != pair[2] and chat_pick(pair[0]) == pair[2], "%s acknowledges '%s' only once it is done" % [pair[0], pair[1]])
		GameState.quests.erase(pair[1])
	check(chat_pick("lacey") == "score_ask", "before the job Lacey still asks her question")
	GameState.bosses["duke"] = true
	done("tools")
	check(chat_pick("mara") == "mara_tools", "Mara mentions the toolbox after the job")
	GameState.bosses["otto"] = true
	check(chat_pick("mara") == "mara_3", "later story lines still take over from the toolbox line")
	GameState.reset_new_game()
	check(chat_pick("otis") == "otis_chat" and chat_pick("gus") == "gus_bait_1", "Otis and Gus keep their old lines while the gangs stand")
	GameState.bosses["kowal"] = true
	GameState.bosses["sabine"] = true
	check(chat_pick("otis") == "otis_kowal" and chat_pick("gus") == "gus_bait_3", "Otis names the Moles leaving, Gus names Holt's men leaving")
	GameState.bosses["rook"] = true
	check(chat_pick("gus") == "gus_bait_2", "Gus's epilogue line still wins after Rook")
	GameState.reset_new_game()

# ---------------------------------------------------------------- Wet Paint
func test_mural() -> void:
	# before the job: the tagged wall, Kiki at her usual spot
	await start_world(story("market", ["duke"], "cm_gate"))
	check(layer_shown("mural_tagged") and not layer_shown("mural_done"), "the wall is tagged before the job is done")
	check(count_npc("kiki") == 1 and absf(room().find_npc("kiki").position.x - 640.0) < 1.0, "Kiki waits at her usual spot")
	check(not GameState.has_flag("mural_seen"), "nothing is announced while the wall is still tagged")
	# in progress: Kiki is still there to report back to, and waiting does not finish anything
	await start_world(func():
		story("market", ["duke"], "cm_gate").call()
		GameState.quests["mural"] = {"state": "active", "step": 0, "data": {}})
	check(count_npc("kiki") == 1 and layer_shown("mural_tagged"), "an active job keeps Kiki and the tagged wall")
	var waiting := await said_by("kiki")
	check(waiting == Content.lines("mural_wait") and Quests.is_active("mural"), "talking early just gets the reminder")
	# finishing it for real: reward once, and the wall changes while Nico is still standing there
	await start_world(func():
		story("market", ["duke"], "cm_gate").call()
		GameState.quests["mural"] = {"state": "active", "step": 1, "data": {}}
		GameState.set_flag("mural_tag1")
		GameState.set_flag("mural_tag2"))
	var cash0 := GameState.cash
	var bag0 := GameState.bag.size()
	var kiki := room().find_npc("kiki")
	room().talk_to(kiki)
	await until(func(): return Quests.state("mural") == "done", 1200)
	await until(func(): return not Story.busy and not w.dialogue.active, 2400)
	var reward := int(Content.quests.mural.reward.cash)
	check(Quests.state("mural") == "done" and GameState.cash == cash0 + reward and GameState.bag.size() == bag0 + 1, "the job pays out once")
	check(layer_shown("mural_done") and not layer_shown("mural_tagged"), "the finished mural appears on the wall straight away")
	check(is_instance_valid(kiki) and absf(kiki.position.x - 640.0) > 60.0 and count_npc("kiki") == 1, "Kiki moves to stand by her wall")
	check(not room().cutscene and room().cam_focus < 0.0 and room().player.control_enabled, "the scene hands control back")
	check(GameState.has_flag("mural_seen"), "the reveal is remembered")
	var beside: Vector2 = kiki.position
	var again := await said_by("kiki")
	check(again == Content.lines("kiki_chat2") and GameState.cash == cash0 + reward and GameState.bag.size() == bag0 + 1, "talking again gets her new line and no second reward")
	# every later visit, and after a save round-trip
	await enter("cm_gate", "east")
	check(layer_shown("mural_done") and not layer_shown("mural_tagged"), "the mural is there on the next visit")
	check(count_npc("kiki") == 1 and room().find_npc("kiki").position.distance_to(beside) < 1.0, "Kiki is at the same place the scene left her")
	save_roundtrip()
	await enter("cm_gate", "west")
	check(layer_shown("mural_done") and Quests.state("mural") == "done" and GameState.cash == cash0 + reward, "mural and reward survive save and load unchanged")
	# a save from before this work: quest done, none of the new flags
	await start_world(story("ironworks", ["duke", "pikes"], "cm_gate", ["mural"]))
	check(layer_shown("mural_done") and not layer_shown("mural_tagged"), "an older save past the job shows the finished wall")
	check(count_npc("kiki") == 1 and room().find_npc("kiki").position.distance_to(beside) < 1.0, "an older save finds Kiki by the wall")
	check(GameState.has_flag("mural_seen") and GameState.cash == 0 and GameState.bag.is_empty(), "the change is pointed out once and nothing is handed out again")
	var acknowledged := await said_by("kiki")
	check(acknowledged == Content.lines("kiki_chat2") and GameState.cash == 0, "Kiki acknowledges the wall on an older save")

# ---------------------------------------------------------------- Static on the Line
func test_radio() -> void:
	await start_world(story("rooftops", ["duke", "pikes", "otto"], "int_pharmacy"))
	var plain := await said_by("ines")
	check(plain == Content.lines("radio_offer"), "before the job Ines asks for help")
	await start_world(story("rooftops", ["duke", "pikes", "otto"], "int_pharmacy", ["radio"]))
	var after := await said_by("ines")
	check(after == Content.lines("ines_post"), "after the job Ines talks about the radio being back")
	check(Quests.state("radio") == "done" and GameState.cash == 0 and GameState.bag.is_empty(), "her thanks hands out nothing a second time")
	var tonic := int(Content.item("tonic").price)
	check(GameState.price_for("pharmacy", tonic) < tonic, "and the pharmacy charges less from then on")
	# postgame keeps the favour
	GameState.bosses["rook"] = true
	GameState.set_flag("game_complete")
	check(GameState.price_for("pharmacy", tonic) < tonic and chat_pick("ines") == "ines_post", "the favour holds in the postgame")

# ---------------------------------------------------------------- people who were helped
func test_helped_people() -> void:
	await start_world(story("warehouse", ALL_BOSSES, "cm_pier"))
	check(count_npc("hollis_sister") == 0, "Mr. Hollis's sister stays in until he has made the walk")
	done("escort")
	await enter("cm_pier")
	check(count_npc("hollis_sister") == 1, "after the walk she is out at her door on Pier Square")
	var sis := await said_by("hollis_sister")
	check(sis == Content.lines("hollis_sister_1"), "and she says what changed")
	await enter("cm_pier", "east")
	check(count_npc("hollis_sister") == 1, "she is there once, however often the square is entered")
	# Biscuit at home
	await enter("oq_brickrow")
	check(count_npc("biscuit") == 0, "no Biscuit on Brickrow before he is found")
	done("dog")
	await enter("oq_brickrow")
	check(count_npc("biscuit") == 1 and room().find_npc("biscuit").context_label() == "Pet Biscuit", "Biscuit is home and can be petted")
	# the arcade: nobody re-opens a settled argument
	done("score")
	await enter("int_arcade", "south")
	var lacey := await said_by("lacey")
	check(lacey == Content.lines("lacey_post") and not w.dialogue.choosing, "Lacey no longer asks who cheated")
	var pip := await said_by("pip")
	check(pip == Content.lines("pip_post"), "Pip no longer pleads his innocence")
	check(Quests.state("score") == "done" and GameState.cash == 0, "and neither pays out again")

# ---------------------------------------------------------------- districts after their boss
func test_districts() -> void:
	await start_world(story("warehouse", [], "oq_kettle"))
	for row in [["cm_canalwalk", "canal_jogger", "pikes"], ["iy_gate", "yard_apprentice", "otto"], ["nm_marquee", "velvet_tenant", "jett"],
			["ul_station", "line_inspector", "kowal"], ["fr_pumpstation", "pump_clerk", "sabine"]]:
		var rid: String = row[0]
		var who: String = row[1]
		var boss: String = row[2]
		GameState.bosses.erase(boss)
		await enter(rid)
		check(count_npc(who) == 0, "%s: nobody comes back while %s runs the district" % [rid, boss])
		GameState.bosses[boss] = true          # the boss record alone, as an older save has it
		await enter(rid)
		check(count_npc(who) == 1, "%s: a resident is back once %s is beaten" % [rid, boss])
		check(GameState.district_calm(str(room().district)) != "", "%s: and the district really is calmer" % rid)
		var line := await said_by(who)
		check(line == Content.lines(who + "_1") and line.size() == 1, "%s: the resident says what changed" % rid)
		await enter(rid, "east")
		check(count_npc(who) == 1, "%s: still exactly one on the next visit" % rid)
	save_roundtrip()
	await enter("cm_canalwalk")
	check(count_npc("canal_jogger") == 1, "residents survive save and load")

# ---------------------------------------------------------------- the night crew's kit (radio, before Rook)
func _collect_kit() -> void:
	var pk := kit_pickup()
	if pk == null:
		return
	await until(func(): return not is_instance_valid(pk) or pk.z < 1.0, 240)
	if is_instance_valid(pk):
		room().player.position = pk.position
	await until(func(): return kit_pickup() == null, 120)

func _run_eli_scene() -> void:
	for wid in ["o0", "o1"]:
		room().waves_done[wid] = true
	Story._eli_found(room())
	await until(func(): return GameState.has_flag("found_eli") and not Story.busy and not w.dialogue.active, 3600)

func test_night_kit() -> void:
	# radio done: Mara brings the kit in when Eli is found
	await start_world(story("warehouse", ALL_BOSSES, "rw_office", ["radio"]))
	check(kit_pickup() == null, "no kit in the office before Eli is found")
	await _run_eli_scene()
	check(GameState.has_flag("found_eli") and GameState.stage == "rook" and not room().cutscene, "the scene still ends with the story moved on")
	check(kit_pickup() != null, "with the radio returned, the night crew's kit is left in the office")
	var bag0 := GameState.bag.count("bandage")
	await _collect_kit()
	check(GameState.bag.count("bandage") == bag0 + 1 and not GameState.has_key("bandage"), "picking it up puts one Bandage Roll in the bag")
	check(GameState.is_collected(KIT_KEY), "and it is remembered as taken")
	await enter("rw_office")
	check(kit_pickup() == null and GameState.bag.count("bandage") == bag0 + 1, "it is not there again after re-entering the room")
	save_roundtrip()
	await enter("rw_office", "east")
	check(kit_pickup() == null and GameState.bag.count("bandage") == bag0 + 1, "nor after a save and load")
	# radio skipped: the same scene, silent, nothing left behind
	await start_world(story("warehouse", ALL_BOSSES, "rw_office"))
	auto_dialogue = false
	for wid in ["o0", "o1"]:
		room().waves_done[wid] = true
	Story._eli_found(room())
	var heard_extra := false
	for i in 3600:
		if w.dialogue.active and w.dialogue.lines == Content.lines("eli_found_radio"):
			heard_extra = true
		if w.dialogue.active:
			w.dialogue._end()          # skipping the scene must not lose its results
		if GameState.has_flag("found_eli") and not Story.busy and not w.dialogue.active:
			break
		await frames(1)
	auto_dialogue = true
	check(not heard_extra and kit_pickup() == null, "without the radio job there is no extra line and no kit")
	check(GameState.has_flag("found_eli") and GameState.stage == "rook" and GameState.notes.has("eli_truth"), "a skipped scene still records finding Eli")
	check(GameState.bag.is_empty(), "and nothing is handed out")
	# an older save already past the scene: the kit is simply waiting; a full bag still gets the benefit, once
	await start_world(func():
		story("rook", ALL_BOSSES, "rw_office", ["radio"]).call()
		GameState.set_flag("found_eli")
		for i in Content.bag_size:
			GameState.bag.append("coffee"))
	check(kit_pickup() != null, "an older save past the scene finds the kit waiting")
	var pk := kit_pickup()
	await until(func(): return not is_instance_valid(pk) or pk.z < 1.0, 240)
	# frames() tops health up, so hurt Nico and read the result with no frame in between
	room().player.hp = 5
	GameState.hp = 5
	if is_instance_valid(pk):
		pk._auto_collect()
	var healed := mini(GameState.max_hp(), 5 + int(Content.item("bandage").heal))
	check(GameState.hp == healed and room().player.hp == healed, "with a full bag the Bandage Roll is used on the spot instead (HP 5 -> %d)" % GameState.hp)
	check(GameState.bag.size() == Content.bag_size and not GameState.has_key("bandage") and GameState.is_collected(KIT_KEY), "the bag is untouched and the kit is spent")
	await enter("rw_office")
	check(kit_pickup() == null, "and it is gone afterwards")
	# after Rook there is nothing left to patch up for
	await start_world(func():
		story("epilogue", ALL_BOSSES + ["rook"], "rw_office", ["radio"]).call()
		GameState.set_flag("found_eli")
		GameState.set_flag("game_complete"))
	check(kit_pickup() == null, "no kit in the postgame")

# ---------------------------------------------------------------- the ending
## Plays Rook's defeat through to the run summary. Returns {lines: the diner scene as played, guests: who was there}.
func _play_ending(skip_diner: bool) -> Dictionary:
	auto_dialogue = false
	Story._rook_ending(room())
	var out := {"lines": [], "guests": [], "reached": false}
	for i in 9000:
		var r: Room = w.room
		if w.dialogue.active and is_instance_valid(r) and r.room_id == "int_diner" and w.dialogue.lines.size() >= 11 and out.lines.is_empty():
			out.lines = w.dialogue.lines.duplicate()
			for n in r.npcs:
				if is_instance_valid(n):
					out.guests.append(n.npc_id)
		if w.dialogue.active:
			if not out.lines.is_empty() and not skip_diner:
				act("ui_accept", true)          # read the last scene line by line
				await get_tree().physics_frame
				act("ui_accept", false)
			else:
				w.dialogue._end()
		if w.top_menu() is RunSummaryMenu:
			out.reached = true
			break
		await get_tree().physics_frame
	auto_dialogue = true
	w.close_all_menus()
	return out

func test_ending() -> void:
	var core := ["dot", "eli", "mara", "jett"]
	# main story only
	await start_world(func():
		story("rook", ALL_BOSSES, "rw_floor").call()
		GameState.set_flag("found_eli"))
	var plain: Dictionary = await _play_ending(false)
	check(plain.reached, "a main-story-only ending plays through to the run summary")
	check(plain.lines == Content.lines("ending_diner"), "with no side jobs the diner scene is the original, line for line")
	plain.guests.sort()
	core.sort()
	check(plain.guests == core, "and only the main cast is in the diner (%s)" % str(plain.guests))
	check(GameState.has_flag("game_complete") and GameState.stage == "epilogue" and GameState.has_key("ledger"), "the story is marked complete")
	# every side job done; the last scene is skipped this time
	await start_world(func():
		story("rook", ALL_BOSSES, "rw_floor", SIDE_JOBS).call()
		GameState.set_flag("found_eli"))
	var cash0 := GameState.cash
	var bag0 := GameState.bag.size()
	var full: Dictionary = await _play_ending(true)
	check(full.reached, "the ending with every side job done also reaches the run summary, even when skipped")
	var base: Array = Content.lines("ending_diner")
	check(full.lines.size() == base.size() + 3, "three guests speak, no more (%d lines)" % full.lines.size())
	if full.lines.size() == base.size() + 3:
		check(str(full.lines[1][0]) == "alvarez" and str(full.lines[2][0]) == "ines" and str(full.lines[3][0]) == "kiki", "Mrs. Alvarez, Ines and Kiki, in that order")
		check(full.lines[0] == base[0] and full.lines.slice(4) == base.slice(1), "around them the scene is unchanged")
	for g in ["alvarez", "biscuit", "ines", "kiki"]:
		check(full.guests.has(g), "%s is in the diner for the scene" % g)
	check(full.guests.count("mara") == 1 and full.guests.count("dot") == 1, "nobody is doubled up")
	check(GameState.has_flag("game_complete") and GameState.stage == "epilogue", "skipping still completes the story")
	check(GameState.cash == cash0 and GameState.bag.size() == bag0, "the guests are a thank-you, not a payout")
	# afterwards everyone is back where they belong
	await start_world(func(): pass, true)
	check(room().room_id == "int_diner" and count_npc("alvarez") == 0 and count_npc("kiki") == 0 and count_npc("ines") == 0, "the guests have gone home in the postgame")
	check(count_npc("eli") == 1 and count_npc("mara") == 1 and count_npc("jett") == 1, "the main cast stays at the Lucky Spoon")
	await enter("cm_gate")
	check(layer_shown("mural_done") and count_npc("kiki") == 1, "in the postgame the mural and Kiki are at the Market Gate")
	await enter("fr_pumpstation")
	check(count_npc("pump_clerk") == 1, "and the districts keep their returned residents")

# ---------------------------------------------------------------- New Game+
func test_new_game_plus() -> void:
	await start_world(func():
		story("epilogue", ALL_BOSSES + ["rook"], "int_diner", SIDE_JOBS).call()
		GameState.set_flag("game_complete")
		GameState.set_flag("found_eli")
		GameState.set_flag("mural_seen")
		GameState.mark_collected(KIT_KEY)
		GameState.start_new_game_plus()
		# far enough into the new run to walk to the Market Gate again
		for f in ["intro_seen", "intro_done", "tutor_v2", "met_mara", "ngplus_card_seen"]:
			GameState.set_flag(f)
		GameState.bosses["duke"] = true
		GameState.stage = "market"
		GameState.room = "cm_gate"
		GameState.spawn = "west")
	check(GameState.ng_cycle == 1 and Quests.state("mural") == "inactive" and not GameState.has_flag("mural_seen"), "New Game+ clears the side jobs and their marks")
	check(layer_shown("mural_tagged") and not layer_shown("mural_done"), "the wall is tagged again")
	check(count_npc("kiki") == 1 and absf(room().find_npc("kiki").position.x - 640.0) < 1.0, "Kiki is back at her usual spot, ready to ask again")
	var tonic := int(Content.item("tonic").price)
	check(GameState.price_for("pharmacy", tonic) == tonic, "the pharmacy is back to full price")
	check(Story.ending_guests().is_empty() and not GameState.is_collected(KIT_KEY), "no guests are owed and the kit can be earned again")
	await enter("cm_canalwalk")
	check(count_npc("canal_jogger") == 0, "the Wharf Rats have the Canal Walk again")
	await enter("cm_pier")
	check(count_npc("hollis_sister") == 0, "and Mr. Hollis has not made his walk yet")
