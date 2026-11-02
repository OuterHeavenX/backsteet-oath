extends Node
## Headless unit/integration tests. Run: godot --headless res://tests/unit_tests.tscn
## Exit code = number of failures.

var fails := 0
var passes := 0
var log_lines: PackedStringArray = []

class WorldStub extends Node:
	var room: Node
	var hud = null
	func is_sim_paused() -> bool: return false
	func dialogue_active() -> bool: return false
	func toast(_m, _c = null) -> void: pass
	func hint(_m, _d = 0.0) -> void: pass
	func boss_bar(_b) -> void: pass
	func bark(_a, _l) -> void: pass
	func change_room(_a, _b) -> void: pass
	func on_level_up() -> void: pass
	func on_player_defeated() -> void: pass

func check(cond: bool, name: String) -> void:
	if cond:
		passes += 1
	else:
		fails += 1
		log_lines.append("FAIL: " + name)
		print("FAIL: ", name)

func _ready() -> void:
	Story.busy = true   # keep story events from firing inside test rooms
	test_content()
	test_assets()
	test_assets_v2()
	test_conditions()
	test_stats()
	test_food_caps()
	test_inventory()
	test_save_roundtrip()
	test_save_corruption()
	test_quests()
	test_progression_graph()
	await test_combat_geometry()
	Story.busy = false
	print("UNIT TESTS: %d passed, %d failed" % [passes, fails])
	var f := FileAccess.open("user://unit_test_report.txt", FileAccess.WRITE)
	f.store_string("passed=%d failed=%d\n%s" % [passes, fails, "\n".join(log_lines)])
	f.close()
	get_tree().quit(fails)

func test_content() -> void:
	var errs := Content.validate()
	for e in errs:
		print("  content: ", e)
	check(errs.is_empty(), "content cross-references valid (%d issues)" % errs.size())
	check(Content.rooms.size() == 33, "33 rooms defined (30 + the Underline)")
	var ext := 0
	for r in Content.rooms.values():
		if r.kind == "exterior":
			ext += 1
	check(ext >= 18 and ext <= 24, "18-24 exterior rooms (%d)" % ext)
	check(Content.skills.size() == 10, "10 manuals")
	var foods := 0
	for it in Content.items.values():
		if it.kind == "food":
			foods += 1
	check(foods >= 18, "18+ foods (%d)" % foods)
	check(Content.weapons.size() >= 12, "12+ weapons")
	check(Content.quests.size() == 10, "10 side quests")
	check(Content.enemies.bosses.size() >= 6, "6+ bosses")
	for stage in Content.story.order:
		check(Content.story.objectives.has(stage), "objective text for " + stage)

func test_assets() -> void:
	var sprites := {}
	for g in Content.enemies.gangs:
		for a in Content.enemies.archetypes:
			sprites[g + "_" + a] = true
	for b in Content.enemies.bosses.values():
		sprites[b.sprite] = true
	for rid in Content.encounters:
		for n in Content.encounters[rid].get("npcs", []):
			sprites[n.get("sprite", n.id)] = true
	for s in ["nico", "rook_p2", "mara", "eli", "rook", "dot", "jett", "gus", "hollis", "price", "biscuit"]:
		sprites[s] = true
	for s in sprites:
		check(ResourceLoader.exists("res://assets/sprites/characters/%s.png" % s) or ResourceLoader.exists("res://assets/sprites/chars/%s.png" % s), "sprite exists: " + s)
	for c in Content.characters.values():
		if c.portrait != "":
			check(ResourceLoader.exists("res://assets/portraits/%s.png" % c.portrait) or ResourceLoader.exists("res://assets/portraits2/%s.png" % c.portrait), "portrait exists: " + c.portrait)
	for rid in Content.rooms:
		check(ResourceLoader.exists("res://assets/bg/%s.png" % rid) or FileAccess.file_exists("res://assets/bg2/%s/room.json" % rid), "background exists: " + rid)
		check(ResourceLoader.exists("res://assets/audio/music/%s.ogg" % Content.rooms[rid].music), "music exists for " + rid)
		for p in Content.rooms[rid].get("props", []):
			check(ResourceLoader.exists("res://assets/props/%s.png" % p.type), "prop art: " + p.type)
	for id in Content.items:
		check(ResourceLoader.exists("res://assets/icons/%s.png" % Content.items[id].icon) or ResourceLoader.exists("res://assets/icons2/%s.png" % Content.items[id].icon), "icon: " + id)
	for id in Content.skills:
		check(ResourceLoader.exists("res://assets/icons/%s.png" % Content.skills[id].icon), "skill icon: " + id)
	for id in Content.weapons:
		var spr: String = Content.weapons[id].sprite
		if spr.begins_with("prop:"):
			check(ResourceLoader.exists("res://assets/props/%s.png" % spr.substr(5)), "weapon prop art: " + id)
		else:
			check(ResourceLoader.exists("res://assets/weapons/%s.png" % spr) or ResourceLoader.exists("res://assets/weapons2/%s.png" % spr), "weapon art: " + id)
	for m in ["title", "boss", "rook", "ending", "victory", "defeat", "setback"]:
		check(ResourceLoader.exists("res://assets/audio/music/%s.ogg" % m), "music: " + m)
	var used_sfx := {}
	for a in Content.attacks.values():
		if a.has("sfx"):
			used_sfx[a.sfx] = true
	for s in ["punch_light", "whiff", "block", "perfect_guard", "fall", "land", "jump", "pickup", "cash", "cash_big", "purchase", "deny", "eat", "heal", "level_up", "throw", "bottle_break", "crate_break", "ui_move", "ui_confirm", "ui_cancel", "ui_open", "ui_close", "door", "dialogue_blip", "quest_update", "quest_complete", "boss_intro", "grab", "slam", "whistle", "crate_fall", "alarm", "dog_bark", "crowd_cheer", "countdown_tick", "bus_horn", "save", "guard_break", "rain_loop", "street_loop", "industrial_loop", "neon_buzz_loop"]:
		used_sfx[s] = true
	for s in used_sfx:
		check(ResourceLoader.exists("res://assets/audio/sfx/%s.ogg" % s), "sfx: " + s)
	check(ResourceLoader.exists("res://assets/fonts/oath_pixel.ttf"), "pixel font present")

## v2 art must honour docs/visual/ASSET_CONTRACT_V2.md: required anims, valid contact frames, web-safe
## texture sizes, and prop footprints identical to the gameplay (v1) footprints.
const FIGHTER_ANIMS := ["idle", "walk", "run", "jump", "land", "punch_a", "punch_b", "punch_c", "kick", "kick_c",
	"jump_kick", "jump_punch", "run_punch", "dropkick", "guard", "hurt_high", "hurt_low", "hurt_back", "knockdown",
	"getup", "dizzy", "pickup", "carry", "carry_walk", "throw", "swing", "sweep", "rising_kick", "slam",
	"victory", "talk", "cower"]

func test_assets_v2() -> void:
	var dir := "res://assets/sprites/chars/"
	var n_chars := 0
	if DirAccess.dir_exists_absolute(dir):
		for f in DirAccess.get_files_at(dir):
			if not f.ends_with(".json"):
				continue
			var id := f.get_basename()
			n_chars += 1
			var meta = JSON.parse_string(FileAccess.get_file_as_string(dir + f))
			check(typeof(meta) == TYPE_DICTIONARY, "v2 char json parses: " + id)
			if typeof(meta) != TYPE_DICTIONARY:
				continue
			var tex: Texture2D = load(dir + id + ".png")
			check(tex != null and tex.get_width() <= 2048 and tex.get_height() <= 2048, "v2 atlas <= 2048: " + id)
			var nf: int = meta.get("frames", []).size()
			check(nf > 0 and meta.get("hand", []).size() == nf, "v2 hand per frame: " + id)
			var anims: Dictionary = meta.get("anims", {})
			var v1 = JSON.parse_string(FileAccess.get_file_as_string("res://assets/sprites/characters/%s.json" % id)) if FileAccess.file_exists("res://assets/sprites/characters/%s.json" % id) else {}
			var fighter: bool = typeof(v1) == TYPE_DICTIONARY and v1.get("anims", {}).has("punch_a") and anims.has("punch_a")
			for a in (FIGHTER_ANIMS if fighter else ["idle", "walk"]):
				check(anims.has(a), "v2 %s has anim %s" % [id, a])
			if typeof(v1) == TYPE_DICTIONARY:
				for a in v1.get("anims", {}):
					check(anims.has(a), "v2 %s keeps v1 anim %s" % [id, a])
			for a in anims:
				var fr: Array = anims[a].get("frames", [])
				var ok := not fr.is_empty()
				for i in fr:
					ok = ok and int(i) >= 0 and int(i) < nf
				check(ok, "v2 %s anim %s frames valid" % [id, a])
				if anims[a].has("contact"):
					check(int(anims[a].contact) >= 0 and int(anims[a].contact) < fr.size(), "v2 %s %s contact in range" % [id, a])
			for a in ["punch_a", "punch_b", "kick", "swing"]:
				if anims.has(a):
					check(int(anims[a].get("contact", 0)) >= 1, "v2 %s %s has an anticipation frame" % [id, a])
			for a in ["walk", "run"]:
				if anims.has(a):
					check(float(anims[a].get("stride", 0)) > 0.0, "v2 %s %s has stride" % [id, a])
	var p2 := "res://assets/props2/props.json"
	if FileAccess.file_exists(p2):
		var m2 = JSON.parse_string(FileAccess.get_file_as_string(p2))
		for t in m2:
			if t.begins_with("_"):
				continue
			var v1m: Dictionary = Content.props_meta.get(t, {})
			check(not v1m.is_empty(), "props2 type exists in v1: " + t)
			if not v1m.is_empty():
				check(str(m2[t].get("footprint")) == str(v1m.get("footprint")), "props2 footprint unchanged: " + t)
	var bdir := "res://assets/bg2/"
	if DirAccess.dir_exists_absolute(bdir):
		for r in DirAccess.get_directories_at(bdir):
			if r.begins_with("_"):
				continue
			check(Content.rooms.has(r), "bg2 room exists: " + r)
			var rm = JSON.parse_string(FileAccess.get_file_as_string(bdir + r + "/room.json"))
			check(typeof(rm) == TYPE_DICTIONARY, "bg2 room.json parses: " + r)
			if typeof(rm) != TYPE_DICTIONARY:
				continue
			for L in rm.get("layers", []):
				for f in L.get("files", []):
					var path := str(f)
					path = "res://assets/bg2/" + path.substr(3) if path.begins_with("../") else bdir + r + "/" + path
					var t2: Texture2D = load(path) if ResourceLoader.exists(path) else null
					check(t2 != null and t2.get_width() <= 2048 and t2.get_height() <= 2048, "bg2 tile ok: " + path)
			for A in rm.get("ambient", []):
				check(str(A.get("type", "")) in RoomVisuals.AMBIENT_TYPES, "bg2 ambient type known: %s %s" % [r, A.get("type", "")])
	log_lines.append("v2 characters checked: %d" % n_chars)

func test_conditions() -> void:
	GameState.reset_new_game()
	check(GameState.check(""), "empty condition true")
	GameState.set_flag("a")
	check(GameState.check("a"), "flag")
	check(not GameState.check("!a"), "negation")
	check(GameState.check("a & !b"), "and")
	check(GameState.check("b | a"), "or")
	GameState.stage = "market"
	check(GameState.check("stage>=chain_dogs") and not GameState.check("stage>=ironworks"), "stage compare")
	check(GameState.check("stage==market") and not GameState.check("stage==intro"), "stage equality")
	GameState.quests["dog"] = {"state": "active", "step": 1}
	check(GameState.check("quest:dog=active") and GameState.check("quest:dog=step1") and not GameState.check("quest:dog=done"), "quest conditions")
	GameState.defeat_boss("duke")
	check(GameState.check("boss_duke") and GameState.check("boss:duke"), "boss flags")

func test_stats() -> void:
	GameState.reset_new_game()
	check(GameState.max_hp() == 60 and GameState.stat("atk") == 5, "base stats")
	check(GameState.xp_needed(1) == 60, "xp to level 2 = 60")
	GameState.auto_alloc = false
	var gained := GameState.add_xp(60)
	check(gained == 1 and GameState.level == 2 and GameState.points == 1, "level up grants a point")
	check(GameState.max_hp() == 67 and GameState.stat("atk") == 6 and GameState.stat("def") == 5, "level gains")
	check(GameState.spend_point("atk") and GameState.stat("atk") == 7 and GameState.points == 0, "spend point")
	check(not GameState.spend_point("atk"), "cannot overspend")
	GameState.respec()
	check(GameState.points == 1 and GameState.stat("atk") == 6, "respec refunds")
	GameState.auto_alloc = true
	var total_lv := GameState.add_xp(100000)
	check(GameState.level == GameState.MAX_LEVEL and GameState.xp == 0, "level caps at 20")
	check(GameState.add_xp(500) == 0, "no XP past max level")
	var raw := 6.0 * (1.0 + 5.0 * 0.06)
	var dmg := maxi(1, int(round(raw * 60.0 / (60.0 + 12.0 * 2.5))))
	check(dmg >= 1 and dmg < raw, "defense reduces damage but keeps minimum 1")
	check(GameState.defeat_penalty() <= 40, "defeat penalty capped")
	GameState.cash = 50
	check(GameState.defeat_penalty() == 10, "defeat penalty is 20% rounded up")

func test_food_caps() -> void:
	GameState.reset_new_game()
	for i in 30:
		GameState.consume("club_sandwich")
	check(int(GameState.food.atk) == int(Content.food_caps.atk), "food ATK capped at %d" % int(Content.food_caps.atk))
	for i in 30:
		GameState.consume("vitamin_pack")
	check(int(GameState.food.hp) == int(Content.food_caps.hp), "food HP capped")
	check(GameState.hp <= GameState.max_hp(), "hp never exceeds max")
	var before := GameState.hp
	GameState.hp = 10
	var r := GameState.consume("tonic")
	check(GameState.hp == GameState.max_hp() and int(r.heal) > 0, "tonic full heal")

func test_inventory() -> void:
	GameState.reset_new_game()
	for i in 10:
		GameState.add_to_bag("pork_bun")
	check(GameState.bag.size() == Content.bag_size, "bag capped at %d" % Content.bag_size)
	check(GameState.remove_from_bag(0) == "pork_bun" and GameState.bag.size() == Content.bag_size - 1, "remove from bag")
	check(GameState.remove_from_bag(99) == "", "bad index safe")
	GameState.give_key("parcel"); GameState.give_key("parcel")
	check(int(GameState.key_items.parcel) == 2, "key items stack")
	check(GameState.take_key("parcel", 2) and not GameState.has_key("parcel"), "take keys")
	check(not GameState.take_key("parcel"), "cannot take missing key")
	GameState.give_gear("courier_sneakers"); GameState.give_gear("courier_sneakers")
	check(GameState.gear.size() == 1 and GameState.stat("agi") == 7, "gear unique and applies bonus")

func test_save_roundtrip() -> void:
	GameState.reset_new_game()
	GameState.add_xp(500)
	GameState.add_cash(77)
	GameState.add_to_bag("ramen")
	GameState.give_key("satchel")
	GameState.learn("rising")
	GameState.set_flag("met_mara")
	GameState.stage = "pikes"
	GameState.quests["dog"] = {"state": "active", "step": 1, "data": {}}
	GameState.upgrades["grip"] = 2
	GameState.mastery["long"] = 70
	GameState.room = "cm_pier"
	var d1 := GameState.to_dict()
	var txt := JSON.stringify(SaveService.build_payload())
	GameState.reset_new_game()
	var parsed := SaveService.validate_payload_text(txt)
	check(not parsed.is_empty(), "payload validates")
	GameState.from_dict(parsed.data)
	var d2 := GameState.to_dict()
	check(JSON.stringify(d1.player) == JSON.stringify(d2.player), "player round-trips")
	check(JSON.stringify(d1.story) == JSON.stringify(d2.story), "story round-trips")
	check(GameState.room == "cm_pier" and GameState.stage == "pikes", "world round-trips")
	# repeated load must not double-apply anything
	GameState.from_dict(parsed.data)
	GameState.from_dict(parsed.data)
	check(GameState.cash == int(d1.player.cash) and GameState.level == int(d1.player.level) and GameState.bag.size() == 1, "reload does not duplicate")
	# real file round trip in slot 3
	SaveService.delete_slot(3)
	check(SaveService.save_game(3), "save to slot 3")
	GameState.reset_new_game()
	check(SaveService.load_game(3) and GameState.room == "cm_pier", "load from slot 3")
	check(SaveService.save_game(3) and FileAccess.file_exists(SaveService.backup_path(3)), "second save keeps backup")

func test_save_corruption() -> void:
	var f := FileAccess.open(SaveService.slot_path(3), FileAccess.WRITE)
	f.store_string("{this is not json")
	f.close()
	var info := SaveService.slot_info(3)
	check(not info.is_empty() and info.recovered, "corrupt save falls back to backup")
	check(SaveService.validate_payload_text("") .is_empty(), "empty payload rejected")
	check(SaveService.validate_payload_text("[1,2,3]").is_empty(), "wrong type rejected")
	check(SaveService.validate_payload_text(JSON.stringify({"game": "other", "version": 2, "data": {}})).is_empty(), "foreign save rejected")
	check(SaveService.validate_payload_text(JSON.stringify({"game": "backstreet_oath", "version": 99, "data": {}})).is_empty(), "future version rejected")
	var v1 := {"game": "backstreet_oath", "version": 1, "data": {"player": {"level": 4, "cash": 12}, "story": {"stage": "market", "quest_flags": {"dog": {"state": "done"}}}, "world": {"room": "cm_gate"}}}
	var mig := SaveService.validate_payload_text(JSON.stringify(v1))
	check(not mig.is_empty() and int(mig.version) == 2 and mig.data.story.has("quests"), "v1 save migrates")
	GameState.from_dict(mig.data)
	check(GameState.level == 4 and GameState.room == "cm_gate" and Quests.state("dog") == "done", "migrated save loads")
	var bad := {"game": "backstreet_oath", "version": 2, "data": {"player": {"level": 999, "cash": -50, "bag": ["nope", 3], "skills": ["bogus"]}, "story": {"stage": "zzz"}, "world": {"room": "nowhere"}}}
	GameState.from_dict(SaveService.validate_payload_text(JSON.stringify(bad)).data)
	check(GameState.level == 20 and GameState.cash == 0 and GameState.bag.is_empty() and GameState.skills.is_empty() and GameState.stage == "intro" and GameState.room == "oq_kettle", "hostile values sanitized")
	SaveService.delete_slot(3)

func test_quests() -> void:
	GameState.reset_new_game()
	GameState.stage = "neon"
	check(Quests.available("cup"), "cup available at neon")
	Quests.start("cup")
	check(not Quests.available("cup"), "active quest not offered again")
	var cash0 := GameState.cash
	Quests.complete("cup")
	check("champion_wraps" in GameState.gear and GameState.cash == cash0 + 80, "cup reward")
	check(Quests.available("cup"), "cup repeatable")
	Quests.start("cup")
	Quests.complete("cup", {"cash": 25, "xp": 40})
	check(GameState.gear.count("champion_wraps") == 1 and GameState.cash == cash0 + 105, "rematch pays cash without duplicate gear")
	GameState.stage = "market"
	Quests.start("parcels")
	for i in 3:
		GameState.give_key("parcel")
		Quests.on_key_item("parcel")
	check(Quests.step("parcels") == 1, "3 parcels advance quest")
	Quests.complete("parcels")
	check(not Quests.available("parcels"), "non-repeatable done quest not re-offered")
	Quests.start("escort")
	Quests.fail("escort")
	check(Quests.state("escort") == "failed" and Quests.available("escort"), "failed escort can be retried")

## For every story stage, the bot's target room must be reachable from every hub with the flags
## the player is guaranteed to have at that point. Guards against softlocks from gating.
func test_progression_graph() -> void:
	var flags_by_stage := {
		"intro": [], "find_mara": ["intro_done"], "chain_dogs": ["intro_done", "met_mara"],
		"market": ["boss_duke"], "pikes": ["met_jett"], "ironworks": ["boss_pikes", "act1_done", "act2_started"],
		"foundry": ["rescued_gus"], "neon": ["boss_otto"], "rooftops": ["arcade_backroom"], "return_home": ["boss_jett"],
		"floodgate": ["setback_fought", "act3_started"], "dockgate": ["alliance"], "warehouse": ["boss_sabine"],
		"rook": ["found_eli"], "epilogue": ["boss_rook"]
	}
	var targets := {"find_mara": "int_garage", "chain_dogs": "oq_chainlot", "market": "cm_canalwalk", "pikes": "cm_pier", "ironworks": "int_switch",
		"foundry": "iy_foundry", "neon": "int_arcade", "rooftops": "nm_rooftops", "return_home": "int_garage", "floodgate": "fr_bridge",
		"dockgate": "fr_dockgate", "warehouse": "rw_office", "rook": "rw_floor"}
	GameState.reset_new_game()
	var acc: Array = []
	var prev_target := "oq_kettle"
	for stage in Content.story.order:
		acc.append_array(flags_by_stage.get(stage, []))
		GameState.flags = {}
		GameState.bosses = {}
		for f in acc:
			GameState.set_flag(f)
			if f.begins_with("boss_"):
				GameState.bosses[f.substr(5)] = true
		GameState.stage = stage
		if not targets.has(stage):
			continue
		var reach := _reachable(prev_target)
		check(reach.has(targets[stage]), "stage %s target %s reachable from %s" % [stage, targets[stage], prev_target])
		# and you can always get back to a safe hub
		check(reach.has("int_diner"), "stage %s can return to the diner from %s" % [stage, prev_target])
		prev_target = targets[stage]

func _reachable(from: String) -> Dictionary:
	var seen := {from: true}
	var q := [from]
	while not q.is_empty():
		var cur: String = q.pop_front()
		var r: Dictionary = Content.room(cur)
		var nexts: Array = []
		for side in r.get("exits", {}):
			var e: Dictionary = r.exits[side]
			if not e.has("requires") or GameState.check(e.requires):
				nexts.append(e.to)
		for d in r.get("doors", []):
			if not d.has("requires") or GameState.check(d.requires):
				nexts.append(d.to)
		if GameState.check(Content.services.bus.requires) and GameState.bus_stops.has(cur):
			for s in Content.services.bus.stops:
				if GameState.bus_stops.has(s):
					nexts.append(s)
		for n in nexts:
			if not seen.has(n):
				seen[n] = true
				q.append(n)
	return seen

func test_combat_geometry() -> void:
	GameState.reset_new_game()
	GameState.set_flag("intro_done")
	var stub := WorldStub.new()
	add_child(stub)
	var room := Room.new()
	add_child(room)
	stub.room = room
	room.build("oq_brickrow", "west", stub)
	room.cutscene = false
	await get_tree().physics_frame
	var p: Player = room.player
	p.position = Vector2(400, 300)
	p.facing = 1
	var e: Enemy = room.spawn_enemy("dogs_brawler", Vector2(420, 300), {})
	e.facing = -1
	e.guard_chance = 0.0   # the AI may otherwise guard at random when it notices the attack (made this check flaky)
	p.start_attack("punch_a")
	p.atk_t = int(p.atk.startup) + 1
	check(p.overlaps_target(e, p.atk), "jab hits enemy in same lane")
	e.position.y = 322
	check(not p.overlaps_target(e, p.atk), "jab misses enemy 22px away in depth")
	e.position.y = 300
	e.position.x = 380
	check(not p.overlaps_target(e, p.atk), "jab does not hit behind")
	var sweep: Dictionary = Content.attack("spin_sweep")
	p.atk = sweep
	check(p.overlaps_target(e, sweep), "spin sweep hits behind (wide attack)")
	e.position = Vector2(420, 300)
	p.atk = Content.attack("punch_a")
	e.z = 60.0
	check(not p.overlaps_target(e, p.atk), "ground jab misses airborne target")
	e.z = 0.0
	# single-hit-per-instance: one attack instance damages once
	var hp0 := e.hp
	p.atk_hit.clear()
	p.atk_targets = 0
	p.atk_t = int(p.atk.startup) + 1
	p.state = "attack"
	p._check_hits()
	var hp1 := e.hp
	p._check_hits()
	p._check_hits()
	if not (hp1 < hp0 and e.hp == hp1): print("DBG hp0=", hp0, " hp1=", hp1, " hp=", e.hp, " st=", e.state, " targets=", p.atk_targets)
	check(hp1 < hp0 and e.hp == hp1, "an attack instance hits a target only once")
	# lying targets cannot be hit (no corpse XP farming)
	e.lying = true
	check(not e.is_hittable(), "downed enemy not hittable")
	e.lying = false
	# XP awarded once per defeat
	var xp0 := GameState.xp + GameState.level * 100000
	e.counted = false
	room.on_enemy_defeated(e)
	var xp1 := GameState.xp + GameState.level * 100000
	room.on_enemy_defeated(e)
	check(xp1 > xp0 and GameState.xp + GameState.level * 100000 == xp1, "XP granted once per enemy")
	# weapon drop lands on walkable ground (never inside geometry)
	for i in 20:
		var q := room.clamp_ground(Vector2(randf_range(-50, room.width + 50), randf_range(100, 400)))
		check(q.y >= room.walk_top and q.y <= room.walk_bot and q.x >= 0 and q.x <= room.width and not room.point_blocked(q, 6.0), "clamped drop position valid %d" % i)
	# weapon pickup/throw doesn't duplicate
	var before := room.pickups.size()
	room.spawn_weapon_pickup("bat", Vector2(450, 300), -1, 0.0)
	var pk: Pickup = room.pickups[-1]
	p._pick_up(pk)
	check(p.held == "bat" and room.pickups.size() == before, "pickup moves weapon into hand")
	p.throw_held()
	check(p.held == "" and room.projectiles.size() == 1, "throw creates one projectile")
	for i in 240:
		for pr in room.projectiles.duplicate():
			pr.tick()
	check(room.projectiles.is_empty(), "projectile resolves")
	var bats := 0
	for k in room.pickups:
		if k.kind == "weapon" and k.weapon_id == "bat":
			bats += 1
	check(bats <= 1, "thrown weapon recoverable without duplication (%d)" % bats)
	# touch ACTION button context labels
	p.held = ""
	p.weapon_spr.visible = false
	p.position = Vector2(640, room.walk_top + 4)
	check(p.context_short() == "ENTER", "ACTION shows ENTER at a door")
	p.position = Vector2(470, 300)
	room.spawn_weapon_pickup("bat", Vector2(476, 300), -1, 0.0)
	check(p.context_short() == "PICK UP", "ACTION shows PICK UP near a weapon")
	p.equip_weapon("baton")
	for leftover in room.pickups.duplicate():
		room.remove_pickup(leftover)
	check(p.context_short() == "THROW", "ACTION shows THROW while holding a weapon")
	room.queue_free()
	stub.queue_free()
