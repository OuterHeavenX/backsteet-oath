extends Node
## Loads and validates all data-driven content from res://data/*.json.
## Every gameplay system reads definitions through this node so IDs stay stable.

var rooms: Dictionary = {}
var attacks: Dictionary = {}        # flat: id -> def (player, weapon and enemy sections merged)
var weapons: Dictionary = {}
var weapon_families: Dictionary = {}
var upgrades: Dictionary = {}
var items: Dictionary = {}
var food_caps: Dictionary = {}
var bag_size: int = 6
var skills: Dictionary = {}
var enemies: Dictionary = {}        # whole enemies.json
var shops: Dictionary = {}
var services: Dictionary = {}
var characters: Dictionary = {}
var dialogue: Dictionary = {}       # id -> Array of lines
var npc_talk: Dictionary = {}       # npc id -> Array of {if, say}
var encounters: Dictionary = {}
var quests: Dictionary = {}
var story: Dictionary = {}
var props_meta: Dictionary = {}
var weapon_sprites: Dictionary = {}
var fx_meta: Dictionary = {}
var pickup_meta: Dictionary = {}
var map_meta: Dictionary = {}

var load_errors: PackedStringArray = []

func _ready() -> void:
	reload()

## Releases static texture/font caches so shutdown is clean (no leak warnings on exit).
func _exit_tree() -> void:
	SpriteLib._chars.clear()
	SpriteLib._tex.clear()
	Actor._shadow_cache = null
	Actor._shader = null
	FX._fb.clear()
	UIKit._theme = null
	UIKit.font_small = null
	UIKit.font_big = null

func reload() -> void:
	load_errors.clear()
	rooms = _load("res://data/rooms.json").get("rooms", {})
	var atk := _load("res://data/attacks.json")
	attacks.clear()
	for section in ["player", "weapon", "enemy"]:
		var sec: Dictionary = atk.get(section, {})
		for k in sec:
			attacks[k] = sec[k]
	var w := _load("res://data/weapons.json")
	weapons = w.get("weapons", {})
	weapon_families = w.get("families", {})
	upgrades = w.get("upgrades", {})
	var it := _load("res://data/items.json")
	items = it.get("items", {})
	food_caps = it.get("food_caps", {})
	bag_size = int(it.get("bag_size", 6))
	skills = _load("res://data/skills.json").get("skills", {})
	enemies = _load("res://data/enemies.json")
	var sh := _load("res://data/shops.json")
	shops = sh.get("shops", {})
	services = sh.get("services", {})
	characters = _load("res://data/characters.json").get("characters", {})
	var dl := _load("res://data/dialogue.json")
	dialogue = dl.get("lines", {})
	npc_talk = dl.get("npc", {})
	encounters = _load("res://data/encounters.json").get("rooms", {})
	quests = _load("res://data/quests.json").get("quests", {})
	story = _load("res://data/story.json")
	props_meta = _load_optional("res://assets/props/props.json")
	weapon_sprites = _load_optional("res://assets/weapons/weapons.json")
	fx_meta = _load_optional("res://assets/fx/fx.json")
	pickup_meta = _load_optional("res://assets/pickups/pickups.json")
	map_meta = _load_optional("res://assets/ui/map.json")

func _load(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		load_errors.append("missing data file: " + path)
		return {}
	var txt := FileAccess.get_file_as_string(path)
	var data = JSON.parse_string(txt)
	if typeof(data) != TYPE_DICTIONARY:
		load_errors.append("invalid JSON: " + path)
		push_error("Content: invalid JSON " + path)
		return {}
	return data

func _load_optional(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		return {}
	var data = JSON.parse_string(FileAccess.get_file_as_string(path))
	return data if typeof(data) == TYPE_DICTIONARY else {}

# ---------------------------------------------------------------- getters
func attack(id: String) -> Dictionary:
	return attacks.get(id, {})

func item(id: String) -> Dictionary:
	return items.get(id, {})

func weapon(id: String) -> Dictionary:
	return weapons.get(id, {})

func skill(id: String) -> Dictionary:
	return skills.get(id, {})

func room(id: String) -> Dictionary:
	return rooms.get(id, {})

func character_name(id: String) -> String:
	var c: Dictionary = characters.get(id, {})
	return c.get("name", id.capitalize())

func lines(id: String) -> Array:
	return dialogue.get(id, [])

func tier_for_district(district: String) -> int:
	return int(enemies.get("district_tier", {}).get(district, 1))

func tier_mult(table: String, tier: int) -> float:
	var arr: Array = enemies.get("tiers", {}).get(table, [1.0])
	return float(arr[clampi(tier, 0, arr.size() - 1)])

func district_name(d: String) -> String:
	return {
		"old_quarter": "Old Quarter", "canal_market": "Canal Market", "ironworks": "Ironworks Yard",
		"neon_mile": "Neon Mile", "floodgate": "Floodgate Road", "warehouse": "Rook's Warehouse",
		"underline": "The Underline"
	}.get(d, d.capitalize())

# ---------------------------------------------------------------- validation
## Returns a list of human-readable problems with cross references. Used by tests.
func validate() -> PackedStringArray:
	var errs: PackedStringArray = load_errors.duplicate()
	for rid in rooms:
		var r: Dictionary = rooms[rid]
		for side in r.get("exits", {}):
			var e: Dictionary = r.exits[side]
			if not rooms.has(e.get("to", "")):
				errs.append("room %s exit %s -> unknown room %s" % [rid, side, e.get("to", "")])
		for d in r.get("doors", []):
			if not rooms.has(d.get("to", "")):
				errs.append("room %s door %s -> unknown room %s" % [rid, d.get("id", "?"), d.get("to", "")])
			var sp: String = d.get("spawn", "")
			if sp.begins_with("door:"):
				var target: Dictionary = rooms.get(d.get("to", ""), {})
				var found := false
				for td in target.get("doors", []):
					if "door:" + td.get("id", "") == sp:
						found = true
				if not found:
					errs.append("room %s door %s spawn %s not found in target" % [rid, d.get("id", "?"), sp])
		for side in r.get("exits", {}):
			var sp2: String = r.exits[side].get("spawn", "")
			if sp2.begins_with("door:"):
				var target2: Dictionary = rooms.get(r.exits[side].get("to", ""), {})
				var found2 := false
				for td in target2.get("doors", []):
					if "door:" + td.get("id", "") == sp2:
						found2 = true
				if not found2:
					errs.append("room %s exit %s spawn %s not found in target" % [rid, side, sp2])
	for wid in weapons:
		var w: Dictionary = weapons[wid]
		if not weapon_families.has(w.get("family", "")):
			errs.append("weapon %s unknown family" % wid)
		var a: String = w.get("attack", "")
		if a != "" and not attacks.has(a):
			errs.append("weapon %s unknown attack %s" % [wid, a])
	for arch in enemies.get("archetypes", {}):
		for pair in enemies.archetypes[arch].get("attacks", []):
			if not attacks.has(pair[0]):
				errs.append("archetype %s unknown attack %s" % [arch, pair[0]])
	for sid in shops:
		var s: Dictionary = shops[sid]
		for entry in s.get("stock", []):
			var id: String = entry if typeof(entry) == TYPE_STRING else entry[0]
			match s.get("kind", ""):
				"food":
					if not items.has(id): errs.append("shop %s unknown item %s" % [sid, id])
				"skills":
					if not skills.has(id): errs.append("shop %s unknown skill %s" % [sid, id])
				"upgrades":
					if not upgrades.has(id): errs.append("shop %s unknown upgrade %s" % [sid, id])
		if not characters.has(s.get("keeper", "")):
			errs.append("shop %s unknown keeper %s" % [sid, s.get("keeper", "")])
	for rid in encounters:
		if not rooms.has(rid):
			errs.append("encounters for unknown room %s" % rid)
			continue
		var enc: Dictionary = encounters[rid]
		for wave in enc.get("waves", []):
			for e in wave.get("enemies", []):
				var eid: String = e[0] if typeof(e) == TYPE_ARRAY else e.get("id", "")
				if not _enemy_id_valid(eid):
					errs.append("room %s wave %s unknown enemy %s" % [rid, wave.get("id", "?"), eid])
		for n in enc.get("npcs", []):
			if not characters.has(n.get("id", "")):
				errs.append("room %s unknown npc %s" % [rid, n.get("id", "")])
			if n.has("shop") and not shops.has(n.shop):
				errs.append("room %s npc %s unknown shop %s" % [rid, n.get("id", ""), n.shop])
		for p in enc.get("pickups", []):
			var pid: String = p.get("weapon", "")
			if pid != "" and not weapons.has(pid):
				errs.append("room %s unknown weapon pickup %s" % [rid, pid])
	for nid in npc_talk:
		for opt in npc_talk[nid]:
			if not dialogue.has(opt.get("say", "")):
				errs.append("npc talk %s -> missing dialogue %s" % [nid, opt.get("say", "")])
	for did in dialogue:
		for line in dialogue[did]:
			if typeof(line) != TYPE_ARRAY or line.size() < 3:
				errs.append("dialogue %s malformed line" % did)
			elif not characters.has(line[0]):
				errs.append("dialogue %s unknown speaker %s" % [did, line[0]])
	for qid in quests:
		var q: Dictionary = quests[qid]
		for k in ["name", "giver", "steps", "reward"]:
			if not q.has(k):
				errs.append("quest %s missing %s" % [qid, k])
	return errs

func _enemy_id_valid(eid: String) -> bool:
	if enemies.get("bosses", {}).has(eid):
		return true
	var parts := eid.split("_")
	if parts.size() != 2:
		return false
	return enemies.get("gangs", {}).has(parts[0]) and enemies.get("archetypes", {}).has(parts[1])
