extends Node
## Persistent game state: player progression, inventory, story flags, world memory.
## Everything here round-trips through to_dict()/from_dict() for saving.

signal stats_changed
signal cash_changed(amount: int, delta: int)
signal xp_changed
signal leveled_up(level: int, gains: Dictionary)
signal flag_changed(flag: String)
signal inventory_changed
signal stage_changed(stage: String)

const MAX_LEVEL := 20
const STATS := ["hp", "atk", "def", "agi", "tec"]
const BASE := {"hp": 60, "atk": 5, "def": 4, "agi": 5, "tec": 5}
const LEVEL_GAIN := {"hp": 7, "atk": 1.0, "def": 1.0, "agi": 0.5, "tec": 0.5}
const POINT_HP := 6
const AUTO_CYCLE := ["atk", "def", "tec", "agi", "hp"]
const STAT_INFO := {
	"hp": "Max HP: how much punishment you can take.",
	"atk": "Attack: damage of punches, kicks and weapons.",
	"def": "Defense: reduces damage you take.",
	"agi": "Agility: move speed, faster recovery, longer get-up protection.",
	"tec": "Technique: special-move and weapon damage, wider perfect-guard window, dizzies foes faster."
}

var level := 1
var xp := 0
var hp := 60
var cash := 0
var points := 0
var auto_alloc := true
var alloc := {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
var food := {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
var bag: Array = []
var key_items: Dictionary = {}
var gear: Array = []
var skills: Array = []
var mastery: Dictionary = {}       # family -> xp
var upgrades: Dictionary = {}      # line -> tier (0..3)
var flags: Dictionary = {}
var stage := "intro"
var bosses: Dictionary = {}
var quests: Dictionary = {}        # qid -> {state, step, data}
var notes: Array = []
var room := "oq_kettle"
var spawn := "west"
var hub_room := "int_diner"
var visited: Dictionary = {}
var visit_count := 0
var room_visit: Dictionary = {}    # room -> visit_count at last entry
var waves: Dictionary = {}         # room -> {wave_id: visit_count when cleared}
var collected: Dictionary = {}
var bus_stops: Dictionary = {}
var stats: Dictionary = {"defeated": 0, "deaths": 0, "cash_earned": 0, "playtime": 0.0, "food_eaten": 0}
var auto_index := 0
var new_game_plus := false
var ng_cycle := 0                 # New Game+ cycle (0 = first run)

func _process(delta: float) -> void:
	if not get_tree().paused:
		stats.playtime = float(stats.get("playtime", 0.0)) + delta

func reset_new_game() -> void:
	level = 1; xp = 0; cash = 0; points = 0; auto_alloc = true; auto_index = 0
	alloc = {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
	food = {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
	bag = []; key_items = {"postcard": 1}; gear = []; skills = []
	mastery = {}; upgrades = {}; flags = {}; stage = "intro"; bosses = {}; quests = {}; notes = []
	room = "oq_kettle"; spawn = "west"; hub_room = "int_diner"
	visited = {}; visit_count = 0; room_visit = {}; waves = {}; collected = {}; bus_stops = {}
	stats = {"defeated": 0, "deaths": 0, "cash_earned": 0, "playtime": 0.0, "food_eaten": 0}
	ng_cycle = 0
	new_game_plus = false
	hp = max_hp()
	stats_changed.emit(); cash_changed.emit(cash, 0); xp_changed.emit(); inventory_changed.emit()

# ---------------------------------------------------------------- derived stats
func level_part(stat: String) -> int:
	var g: float = LEVEL_GAIN[stat]
	return int(floor(g * float(level - 1)))

func gear_part(stat: String) -> int:
	var t := 0
	for g in gear:
		t += int(Content.item(g).get("bonus", {}).get(stat, 0))
	return t

func stat(s: String) -> int:
	if s == "hp":
		return max_hp()
	return int(BASE[s]) + level_part(s) + int(alloc.get(s, 0)) + int(food.get(s, 0)) + gear_part(s)

func max_hp() -> int:
	return int(BASE.hp) + level_part("hp") + int(alloc.get("hp", 0)) * POINT_HP + int(food.get("hp", 0)) + gear_part("hp")

func stat_breakdown(s: String) -> Dictionary:
	var a: int = int(alloc.get(s, 0)) * (POINT_HP if s == "hp" else 1)
	return {"base": int(BASE[s]), "level": level_part(s), "points": a, "food": int(food.get(s, 0)), "gear": gear_part(s), "total": stat(s)}

func run_bonus() -> float:
	var r := 0.0
	for g in gear:
		r += float(Content.item(g).get("run", 0.0))
	return r

# ---------------------------------------------------------------- xp / levels
static func xp_needed(lvl: int) -> int:
	return int(40.0 * pow(float(lvl), 1.5) + 20.0)

func add_xp(amount: int) -> int:
	if amount <= 0 or level >= MAX_LEVEL:
		return 0
	xp += amount
	var gained := 0
	while level < MAX_LEVEL and xp >= xp_needed(level):
		xp -= xp_needed(level)
		var before := {}
		for s in STATS:
			before[s] = stat(s)
		level += 1
		points += 1
		gained += 1
		var auto_stat := ""
		if auto_alloc:
			auto_stat = _auto_spend()
		var gains := {}
		for s in STATS:
			gains[s] = stat(s) - int(before[s])
		gains["auto"] = auto_stat
		hp = mini(max_hp(), hp + int(gains.hp) + int(max_hp() * 0.25))
		leveled_up.emit(level, gains)
	if level >= MAX_LEVEL:
		xp = 0
	xp_changed.emit()
	stats_changed.emit()
	return gained

func _auto_spend() -> String:
	if points <= 0:
		return ""
	var s: String = AUTO_CYCLE[auto_index % AUTO_CYCLE.size()]
	auto_index += 1
	spend_point(s)
	return s

func spend_point(s: String) -> bool:
	if points <= 0 or not alloc.has(s):
		return false
	var old_max := max_hp()
	points -= 1
	alloc[s] = int(alloc[s]) + 1
	if s == "hp":
		hp += max_hp() - old_max
	stats_changed.emit()
	return true

func respec() -> void:
	var total := 0
	for s in alloc:
		total += int(alloc[s])
		alloc[s] = 0
	points += total
	hp = mini(hp, max_hp())
	stats_changed.emit()

# ---------------------------------------------------------------- hp / cash
func heal(amount: int) -> int:
	var before := hp
	hp = clampi(hp + amount, 0, max_hp())
	stats_changed.emit()
	return hp - before

func add_cash(amount: int) -> void:
	if amount == 0:
		return
	cash = clampi(cash + amount, 0, 99999)
	if amount > 0:
		stats.cash_earned = int(stats.get("cash_earned", 0)) + amount
	cash_changed.emit(cash, amount)

func spend(amount: int) -> bool:
	if amount < 0 or cash < amount:
		return false
	cash -= amount
	cash_changed.emit(cash, -amount)
	return true

func defeat_penalty() -> int:
	return mini(int(ceil(float(cash) * 0.2)), 40)

# ---------------------------------------------------------------- food / items
## Applies an item's heal + permanent bonus with caps. Returns {heal, bonus:{stat:n}, capped:[stats]}.
func consume(item_id: String) -> Dictionary:
	var it := Content.item(item_id)
	var res := {"heal": 0, "bonus": {}, "capped": []}
	if it.is_empty():
		return res
	var old_max := max_hp()
	for s in it.get("bonus", {}):
		var want: int = int(it.bonus[s])
		var cap: int = int(Content.food_caps.get(s, 8))
		var room_left: int = cap - int(food.get(s, 0))
		var applied: int = clampi(want, 0, maxi(room_left, 0))
		if applied > 0:
			food[s] = int(food[s]) + applied
			res.bonus[s] = applied
		if applied < want:
			res.capped.append(s)
	if max_hp() > old_max:
		hp += max_hp() - old_max
	res.heal = heal(int(it.get("heal", 0)))
	stats.food_eaten = int(stats.get("food_eaten", 0)) + 1
	stats_changed.emit()
	return res

func bag_full() -> bool:
	return bag.size() >= Content.bag_size

func add_to_bag(item_id: String) -> bool:
	if bag_full():
		return false
	bag.append(item_id)
	inventory_changed.emit()
	return true

func remove_from_bag(index: int) -> String:
	if index < 0 or index >= bag.size():
		return ""
	var id: String = bag[index]
	bag.remove_at(index)
	inventory_changed.emit()
	return id

func give_key(id: String, n: int = 1) -> void:
	key_items[id] = int(key_items.get(id, 0)) + n
	inventory_changed.emit()

func take_key(id: String, n: int = 1) -> bool:
	if int(key_items.get(id, 0)) < n:
		return false
	key_items[id] = int(key_items[id]) - n
	if key_items[id] <= 0:
		key_items.erase(id)
	inventory_changed.emit()
	return true

func has_key(id: String) -> bool:
	return int(key_items.get(id, 0)) > 0

func give_gear(id: String) -> void:
	if not id in gear:
		gear.append(id)
		hp = mini(hp, max_hp())
		inventory_changed.emit()
		stats_changed.emit()

func learn(skill_id: String) -> void:
	if not skill_id in skills:
		skills.append(skill_id)
		inventory_changed.emit()

func has_skill(skill_id: String) -> bool:
	return skill_id in skills

# ---------------------------------------------------------------- weapons progression
func mastery_level(family: String) -> int:
	var x: int = int(mastery.get(family, 0))
	# 0..5 ; thresholds grow
	var lv := 0
	for t in [20, 60, 120, 200, 300]:
		if x >= t:
			lv += 1
	return lv

func add_mastery(family: String, amount: int = 1) -> bool:
	var before := mastery_level(family)
	mastery[family] = int(mastery.get(family, 0)) + amount
	return mastery_level(family) > before

func upgrade_tier(line: String) -> int:
	return int(upgrades.get(line, 0))

func weapon_upgrade_for_family(family: String) -> Dictionary:
	var line: String = Content.weapon_families.get(family, {}).get("upgrade", "")
	var tier := upgrade_tier(line)
	if tier <= 0:
		return {"power": 0, "dur": 0.0}
	var t: Dictionary = Content.upgrades.get(line, {}).get("tiers", [])[tier - 1]
	return {"power": int(t.get("power", 0)), "dur": float(t.get("dur", 0.0))}

# ---------------------------------------------------------------- flags / story
func set_flag(f: String, v: Variant = true) -> void:
	if flags.get(f) == v:
		return
	flags[f] = v
	flag_changed.emit(f)

func has_flag(f: String) -> bool:
	if f.begins_with("boss_"):
		return bool(bosses.get(f.substr(5), false)) or bool(flags.get(f, false))
	return bool(flags.get(f, false))

func defeat_boss(id: String) -> void:
	bosses[id] = true
	flags["boss_" + id] = true
	flag_changed.emit("boss_" + id)

func stage_index(s: String) -> int:
	var order: Array = Content.story.get("order", [])
	return order.find(s)

func set_stage(s: String) -> void:
	if stage_index(s) < 0:
		push_warning("unknown stage " + s)
		return
	stage = s
	stage_changed.emit(s)

func add_note(id: String) -> void:
	if not id in notes:
		notes.append(id)

## Tiny condition language: terms joined by '&' (all) or '|' (any, lower precedence).
## Terms: flag, !flag, stage>=id, stage<id, stage==id, quest:id=state, has:item, level>=n, boss:id, gear:id, skill:id
func check(cond: String) -> bool:
	cond = cond.strip_edges()
	if cond == "":
		return true
	if "|" in cond:
		for part in cond.split("|"):
			if check(part):
				return true
		return false
	for term in cond.split("&"):
		if not _term(term.strip_edges()):
			return false
	return true

func _term(t: String) -> bool:
	if t == "":
		return true
	if t.begins_with("!"):
		return not _term(t.substr(1))
	if t.begins_with("stage"):
		for op in [">=", "<=", "==", ">", "<"]:
			var i := t.find(op)
			if i > 0:
				var a := stage_index(stage)
				var b := stage_index(t.substr(i + op.length()).strip_edges())
				match op:
					">=": return a >= b
					"<=": return a <= b
					"==": return a == b
					">": return a > b
					"<": return a < b
	if t.begins_with("quest:"):
		var body := t.substr(6)
		var parts := body.split("=")
		var q: Dictionary = quests.get(parts[0], {})
		var st: String = q.get("state", "inactive")
		if parts.size() < 2:
			return st == "active"
		if parts[1].begins_with("step"):
			return st == "active" and int(q.get("step", 0)) >= int(parts[1].substr(4))
		return st == parts[1]
	if t.begins_with("has:"):
		return has_key(t.substr(4))
	if t.begins_with("gear:"):
		return t.substr(5) in gear
	if t.begins_with("skill:"):
		return t.substr(6) in skills
	if t.begins_with("boss:"):
		return bool(bosses.get(t.substr(5), false))
	if t.begins_with("level>="):
		return level >= int(t.substr(7))
	if t.begins_with("cash>="):
		return cash >= int(t.substr(6))
	return has_flag(t)

# ---------------------------------------------------------------- world memory
func enter_room(id: String) -> void:
	visit_count += 1
	room_visit[id] = visit_count
	visited[id] = true

func wave_cleared(room_id: String, wave_id: String) -> void:
	if not waves.has(room_id):
		waves[room_id] = {}
	waves[room_id][wave_id] = visit_count

## A wave is available if never cleared, or if it respawns and the player has visited 3+ rooms since.
func wave_available(room_id: String, wave_id: String, respawns: bool) -> bool:
	var w: Dictionary = waves.get(room_id, {})
	if not w.has(wave_id):
		return true
	if not respawns:
		return false
	return visit_count - int(w[wave_id]) >= 4

func is_collected(key: String) -> bool:
	return bool(collected.get(key, false))

## New Game+: keep the character (level, stats, techniques, gear, bag, cash, weapon upgrades) and restart the
## story with tougher streets. Called on a loaded, completed save.
func start_new_game_plus() -> void:
	var keep := {"level": level, "xp": xp, "cash": cash, "points": points, "auto_alloc": auto_alloc,
		"auto_index": auto_index, "alloc": alloc.duplicate(), "food": food.duplicate(), "bag": bag.duplicate(),
		"gear": gear.duplicate(), "skills": skills.duplicate(), "mastery": mastery.duplicate(),
		"upgrades": upgrades.duplicate(), "cycle": ng_cycle + 1,
		"total_time": float(stats.get("total_playtime", 0.0)) + float(stats.get("playtime", 0.0)),
		"ladder_best": int(stats.get("ladder_best", 0))}
	reset_new_game()
	level = keep.level; xp = keep.xp; cash = keep.cash; points = keep.points; auto_alloc = keep.auto_alloc
	auto_index = keep.auto_index; alloc = keep.alloc; food = keep.food; bag = keep.bag; gear = keep.gear
	skills = keep.skills; mastery = keep.mastery; upgrades = keep.upgrades
	ng_cycle = keep.cycle
	new_game_plus = true
	stats["total_playtime"] = keep.total_time
	stats["ladder_best"] = keep.ladder_best
	if not notes.has("new_game_plus"):
		notes.append("new_game_plus")
	hp = max_hp()
	stats_changed.emit(); cash_changed.emit(cash, 0); xp_changed.emit(); inventory_changed.emit()

## Multipliers for New Game+ (1.0 on a first run).
func ng_mult(kind: String) -> float:
	var n := float(ng_cycle)
	match kind:
		"hp": return 1.0 + 0.35 * n
		"power": return 1.0 + 0.25 * n
		"boss_hp": return 1.0 + 0.4 * n
		"boss_power": return 1.0 + 0.15 * n
		"reward": return 1.0 + 0.25 * n
	return 1.0

func mark_collected(key: String) -> void:
	collected[key] = true

# ---------------------------------------------------------------- serialization
func to_dict() -> Dictionary:
	return {
		"player": {
			"level": level, "xp": xp, "hp": hp, "cash": cash, "points": points, "auto_alloc": auto_alloc,
			"auto_index": auto_index, "alloc": alloc, "food": food, "bag": bag, "key_items": key_items,
			"gear": gear, "skills": skills, "mastery": mastery, "upgrades": upgrades
		},
		"story": {"stage": stage, "flags": flags, "bosses": bosses, "quests": quests, "notes": notes},
		"world": {
			"room": room, "spawn": spawn, "hub_room": hub_room, "visited": visited, "visit_count": visit_count,
			"room_visit": room_visit, "waves": waves, "collected": collected, "bus_stops": bus_stops
		},
		"stats": stats,
		"ng_cycle": ng_cycle,
	}

func from_dict(d: Dictionary) -> void:
	reset_new_game()
	ng_cycle = clampi(int(d.get("ng_cycle", 0)), 0, 9)
	new_game_plus = ng_cycle > 0
	var p: Dictionary = d.get("player", {})
	level = clampi(int(p.get("level", 1)), 1, MAX_LEVEL)
	xp = maxi(0, int(p.get("xp", 0)))
	cash = clampi(int(p.get("cash", 0)), 0, 99999)
	points = clampi(int(p.get("points", 0)), 0, MAX_LEVEL)
	auto_alloc = bool(p.get("auto_alloc", true))
	auto_index = int(p.get("auto_index", 0))
	alloc = _stat_dict(p.get("alloc", {}), 0, MAX_LEVEL)
	food = _stat_dict(p.get("food", {}), 0, 99)
	for s in food:
		food[s] = mini(int(food[s]), int(Content.food_caps.get(s, 8)))
	bag = _id_array(p.get("bag", []), Content.items).slice(0, Content.bag_size)
	key_items = {}
	var ki = p.get("key_items", {})
	if typeof(ki) == TYPE_DICTIONARY:
		for k in ki:
			if Content.items.has(k):
				key_items[k] = clampi(int(ki[k]), 0, 99)
	gear = _id_array(p.get("gear", []), Content.items)
	skills = _id_array(p.get("skills", []), Content.skills)
	mastery = _num_dict(p.get("mastery", {}))
	upgrades = _num_dict(p.get("upgrades", {}))
	for k in upgrades:
		upgrades[k] = clampi(int(upgrades[k]), 0, 3)
	var s: Dictionary = d.get("story", {})
	stage = str(s.get("stage", "intro"))
	if stage_index(stage) < 0:
		stage = "intro"
	flags = s.get("flags", {}) if typeof(s.get("flags")) == TYPE_DICTIONARY else {}
	bosses = s.get("bosses", {}) if typeof(s.get("bosses")) == TYPE_DICTIONARY else {}
	quests = {}
	var qs = s.get("quests", {})
	if typeof(qs) == TYPE_DICTIONARY:
		for qid in qs:
			var q = qs[qid]
			if typeof(q) != TYPE_DICTIONARY or not Content.quests.has(qid):
				continue
			var st := str(q.get("state", "inactive"))
			if not st in ["inactive", "active", "done", "failed"]:
				st = "inactive"
			var entry := {"state": st, "step": clampi(int(q.get("step", 0)), 0, 9), "data": q.get("data", {}) if typeof(q.get("data", {})) == TYPE_DICTIONARY else {}}
			if q.has("times"):
				entry["times"] = int(q.times)
			quests[qid] = entry
	notes = s.get("notes", []) if typeof(s.get("notes")) == TYPE_ARRAY else []
	var w: Dictionary = d.get("world", {})
	room = str(w.get("room", "oq_kettle"))
	if not Content.rooms.has(room):
		room = "oq_kettle"
	spawn = str(w.get("spawn", "west"))
	hub_room = str(w.get("hub_room", "int_diner"))
	if not Content.rooms.has(hub_room):
		hub_room = "int_diner"
	visited = w.get("visited", {}) if typeof(w.get("visited")) == TYPE_DICTIONARY else {}
	visit_count = int(w.get("visit_count", 0))
	room_visit = w.get("room_visit", {}) if typeof(w.get("room_visit")) == TYPE_DICTIONARY else {}
	waves = w.get("waves", {}) if typeof(w.get("waves")) == TYPE_DICTIONARY else {}
	collected = w.get("collected", {}) if typeof(w.get("collected")) == TYPE_DICTIONARY else {}
	bus_stops = w.get("bus_stops", {}) if typeof(w.get("bus_stops")) == TYPE_DICTIONARY else {}
	var st = d.get("stats", {})
	if typeof(st) == TYPE_DICTIONARY:
		for k in st:
			stats[k] = st[k]
	hp = clampi(int(p.get("hp", max_hp())), 1, max_hp())
	stats_changed.emit(); cash_changed.emit(cash, 0); xp_changed.emit(); inventory_changed.emit()

func _stat_dict(v, lo: int, hi: int) -> Dictionary:
	var out := {"hp": 0, "atk": 0, "def": 0, "agi": 0, "tec": 0}
	if typeof(v) == TYPE_DICTIONARY:
		for s in out:
			out[s] = clampi(int(v.get(s, 0)), lo, hi)
	return out

func _id_array(v, valid: Dictionary) -> Array:
	var out := []
	if typeof(v) == TYPE_ARRAY:
		for x in v:
			if typeof(x) == TYPE_STRING and valid.has(x):
				out.append(x)
	return out

func _num_dict(v) -> Dictionary:
	var out := {}
	if typeof(v) == TYPE_DICTIONARY:
		for k in v:
			if typeof(v[k]) in [TYPE_INT, TYPE_FLOAT]:
				out[str(k)] = int(v[k])
	return out
