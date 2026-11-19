class_name Preview
extends RefCounted
## Truthful before/after numbers for shops and the Status menu.
##
## Nothing here re-implements a gameplay formula. A hypothetical purchase or stat point is applied to GameState
## with the same call the real action makes (GameState.consume, spend_point, add_mastery, the workbench tier
## write), the numbers are then produced by the game's own code running on throwaway actors that are never
## added to the scene (Player.calc_raw / projectile_raw / refresh_stats / perfect_window / _recovery_ticks /
## dizzy_mult / equip_weapon, Enemy.setup_enemy / calc_raw, Actor.take_damage_and_react), and GameState is put
## back exactly as it was. While a Bench is open GameState's signals are blocked and sound effects are muted,
## so nothing on screen, in the save or in the speakers can tell that a preview happened.
##
## Damage always depends on who is hit, so every damage number is quoted against a named reference fighter
## (see ref_fighter()): UI text must show that name next to the number.

const PROBE_HP := 1000000
## The enemy attacks used for "damage taken": [archetype, attack id, how the UI names it].
const TAKEN := {"hook": ["brawler", "e_hook", "hook"], "heavy": ["heavy", "e_heavy_punch", "big punch"]}

# ---------------------------------------------------------------- reference fighter
## The gang that fields the most fighters on a district's streets (from encounters.json), "" if nobody does.
static func district_gang(district: String) -> String:
	var count := {}
	var gangs: Dictionary = Content.enemies.get("gangs", {})
	for rid in Content.encounters:
		if str(Content.room(rid).get("district", "")) != district:
			continue
		for wave in Content.encounters[rid].get("waves", []):
			for e in wave.get("enemies", []):
				var eid: String = str(e[0]) if typeof(e) == TYPE_ARRAY else str(e.get("id", ""))
				var parts := eid.split("_")
				if parts.size() == 2 and gangs.has(parts[0]):
					count[parts[0]] = int(count.get(parts[0], 0)) + 1
	var best := ""
	for g in count:
		if best == "" or int(count[g]) > int(count[best]):
			best = g
	return best

## Who the damage numbers are quoted against: the street gang of the toughest district the player has set foot
## in (ties go to the one entered most recently), so the reference grows with the story and is always someone
## the player has actually met. A fresh save quotes the Old Quarter's Chain Dogs.
## Returns {district, gang, tier (district tier, before New Game+), name ("Chain Dogs"), weapon}.
static func ref_fighter() -> Dictionary:
	var best_d := ""
	var best_t := -1
	var best_v := -1
	var rooms: Array = GameState.visited.keys()
	rooms.append(GameState.room)
	for rid in rooms:
		var d := str(Content.room(str(rid)).get("district", ""))
		if d == "" or district_gang(d) == "":
			continue
		var t := Content.tier_for_district(d)
		var v := int(GameState.room_visit.get(rid, 0))
		if t > best_t or (t == best_t and v > best_v):
			best_d = d
			best_t = t
			best_v = v
	var gang := district_gang(best_d) if best_d != "" else ""
	if gang == "":
		best_d = "old_quarter"
		gang = "dogs"
		best_t = Content.tier_for_district(best_d)
	var g: Dictionary = Content.enemies.get("gangs", {}).get(gang, {})
	var weapon := ""
	for w in g.get("weapons", []):
		if str(Content.weapon(str(w)).get("attack", "")) != "":
			weapon = str(w)
			break
	return {"district": best_d, "gang": gang, "tier": best_t, "name": str(g.get("name", gang.capitalize())), "weapon": weapon}

## "Chain Dogs brawler": how the UI names the reference target.
static func ref_label(arche: String = "brawler") -> String:
	return "%s %s" % [str(ref_fighter().name).trim_prefix("The "), arche]

## The attack id a technique performs ("" for automatic techniques such as Quick Hands).
static func technique_attack(skill_id: String) -> String:
	for a in Tutor.SKILL_ATTACKS:
		if str(Tutor.SKILL_ATTACKS[a]) == skill_id:
			return str(a)
	return ""

## The technique whose damage stands for "technique damage": the first learned one that strikes, otherwise the
## first one on Benny's shelf. Returns {skill, attack, learned}.
static func ref_technique() -> Dictionary:
	var first := ""
	for sid in Content.skills:
		if technique_attack(str(sid)) == "":
			continue
		if first == "":
			first = str(sid)
		if GameState.has_skill(str(sid)):
			return {"skill": str(sid), "attack": technique_attack(str(sid)), "learned": true}
	return {"skill": first, "attack": technique_attack(first), "learned": false}

## The first weapon of a family in weapons.json order ("" if none): the family's stated reference weapon.
## With swingable = true the first one that can be swung is preferred (mastery only grows by swinging).
static func family_weapon(family: String, swingable: bool = false) -> String:
	var first := ""
	for wid in Content.weapons:
		var w: Dictionary = Content.weapons[wid]
		if str(w.get("family", "")) != family:
			continue
		if first == "":
			first = str(wid)
		if not swingable or str(w.get("attack", "")) != "":
			return str(wid)
	return first

## Families a workbench line improves, in weapons.json order.
static func upgrade_families(line: String) -> Array:
	var out: Array = []
	for fam in Content.weapon_families:
		if str(Content.weapon_families[fam].get("upgrade", "")) == line:
			out.append(str(fam))
	return out

# ---------------------------------------------------------------- hypothetical changes
# Each of these changes GameState exactly as the real action does (eating is GameState.consume itself). The
# workbench calls upgrade() for the real purchase too, so a preview and the purchase it describes can never
# take different paths.

## Spends one stat point. A preview may look at the next point before it has been earned.
static func point(stat: String, lend: bool = false) -> bool:
	if lend and GameState.points <= 0:
		GameState.points = 1
	return GameState.spend_point(stat)

static func upgrade(line: String) -> void:
	GameState.upgrades[line] = GameState.upgrade_tier(line) + 1

## Uses a weapon family until its mastery goes up one level. Returns the hits that took (0 at the maximum).
static func master(family: String) -> int:
	var hits := 0
	while hits < 2000:
		hits += 1
		if GameState.add_mastery(family, 1):
			return hits
	return 0

# ---------------------------------------------------------------- the bench
## Stands in for the Room while a probe hit lands: accepts the presentation calls a hit makes and does nothing.
class Quiet extends Node:
	var actors: Array = []
	func do_hitstop(_a = null) -> void: pass
	func impulse(_a = null, _b = null) -> void: pass
	func shake(_a = null) -> void: pass
	func spawn_fx(_a = null, _b = null, _c = null, _d = null, _e = null, _f = null) -> void: pass
	func spawn_directional_debris(_a = null, _b = null, _c = null, _d = null, _e = null) -> void: pass
	func spawn_debris(_a = null, _b = null) -> void: pass
	func float_text(_a = null, _b = null, _c = null) -> void: pass
	func tutor_event(_a = null) -> void: pass
	func on_player_damaged(_a = null) -> void: pass
	func notify_attack(_a = null) -> void: pass

## A real Enemy set up by the real setup_enemy(), minus the sprite sheet (a number does not need a texture).
class Dummy extends Enemy:
	func setup_visual(id: String) -> void:
		char_id = id

## An open Bench holds a snapshot of GameState. Anything may be done to GameState while it is open; close()
## (or simply dropping the last reference, also on an early return or a script error) puts every property back,
## byte for byte, keeping the identity of every container that did not change.
class Bench extends RefCounted:
	var _bytes: Dictionary = {}     # container property -> var_to_bytes at open
	var _orig: Dictionary = {}      # container property -> the container object itself
	var _plain: Dictionary = {}     # scalar property -> value
	var _blocked := false
	var _audio := true
	var _open := false
	var ref: Dictionary = {}
	var room: Node
	var nico: Player
	var foes: Dictionary = {}       # archetype -> Dummy

	func _init() -> void:
		for p in GameState.get_script().get_script_property_list():
			if int(p.usage) & PROPERTY_USAGE_SCRIPT_VARIABLE == 0:
				continue
			var v = GameState.get(p.name)
			if typeof(v) == TYPE_DICTIONARY or typeof(v) == TYPE_ARRAY:
				_orig[p.name] = v
				_bytes[p.name] = var_to_bytes(v)
			else:
				_plain[p.name] = v
		_blocked = GameState.is_blocking_signals()
		GameState.set_block_signals(true)
		_audio = Audio.unlocked
		Audio.unlocked = false
		_open = true

	func _notification(what: int) -> void:
		if what == NOTIFICATION_PREDELETE:
			close()

	func close() -> void:
		if not _open:
			return
		_open = false
		if nico:
			if nico.weapon_spr:
				nico.weapon_spr.free()
			nico.free()
		for k in foes:
			foes[k].free()
		foes.clear()
		if room:
			room.free()
		for n in _orig:
			var o = _orig[n]
			if var_to_bytes(o) != _bytes[n]:
				var want = bytes_to_var(_bytes[n])
				o.clear()
				if typeof(o) == TYPE_DICTIONARY:
					o.merge(want)
				else:
					o.append_array(want)
			if not is_same(GameState.get(n), o):
				GameState.set(n, o)
		for n in _plain:
			GameState.set(n, _plain[n])
		Audio.unlocked = _audio
		GameState.set_block_signals(_blocked)

	func _probes() -> void:
		if nico != null:
			return
		ref = Preview.ref_fighter()
		room = Quiet.new()
		nico = Player.new()
		nico.room = room
		nico.weapon_spr = Sprite2D.new()

	func foe(arche: String = "brawler") -> Enemy:
		_probes()
		if not foes.has(arche):
			var e := Dummy.new()
			e.room = room
			e.setup_enemy("%s_%s" % [ref.gang, arche], int(ref.tier))
			foes[arche] = e
		return foes[arche]

	## HP the target loses when a hit of `raw` lands on it unguarded: the game's own take_damage_and_react.
	func land(attacker: Actor, target: Actor, d: Dictionary, raw: float) -> int:
		var gs_hp := GameState.hp
		target.state = "idle"
		target.combo_hits = 0
		target.dizzy_meter = 0.0
		target.lying = false
		target.dead = false
		target.z = 0.0
		target.vz = 0.0
		target.min_hp = 0
		target.hp = Preview.PROBE_HP
		target.take_damage_and_react(attacker, d, raw, 1, false)
		GameState.hp = gs_hp
		return Preview.PROBE_HP - target.hp

	## Damage of one of Nico's attacks (attacks.json id) on the reference brawler.
	func strike(attack_id: String) -> int:
		_probes()
		var d: Dictionary = Content.attack(attack_id)
		nico.atk_id = attack_id
		nico.atk = d
		nico.held = ""
		return land(nico, foe(), d, nico.calc_raw(d))

	## Damage of one swing of a weapon on the reference brawler (-1 if the weapon cannot be swung).
	func swing(weapon_id: String) -> int:
		_probes()
		var aid := str(Content.weapon(weapon_id).get("attack", ""))
		if aid == "":
			return -1
		var d: Dictionary = Content.attack(aid)
		nico.atk_id = aid
		nico.atk = d
		nico.held = weapon_id
		var raw := nico.calc_raw(d)
		nico.held = ""
		return land(nico, foe(), d, raw)

	## Damage of a thrown weapon or object on the reference brawler.
	func hurl(weapon_id: String) -> int:
		_probes()
		var raw := nico.projectile_raw(weapon_id)
		return land(nico, foe(), {"power": raw, "knockdown": bool(Content.weapon(weapon_id).get("knockdown", false)), "weapon": weapon_id}, raw)

	## Swings a picked-up weapon survives (workbench durability included).
	func uses(weapon_id: String) -> int:
		_probes()
		nico.equip_weapon(weapon_id)
		var n := nico.held_max
		nico.held = ""
		return n

	## Walking speed while holding the weapon or carrying the object.
	func carry_speed(weapon_id: String) -> float:
		_probes()
		nico.refresh_stats()
		nico.held = weapon_id
		var sp := nico._move_speed()
		nico.held = ""
		return sp

	## HP Nico loses to one of the reference gang's attacks (see TAKEN).
	func taken(key: String) -> int:
		_probes()
		var spec: Array = Preview.TAKEN[key]
		var e := foe(str(spec[0]))
		var d: Dictionary = Content.attack(str(spec[1]))
		e.atk_id = str(spec[1])
		e.atk = d
		nico.refresh_stats()
		return land(e, nico, d, e.calc_raw(d))

	## Every derived number the Status menu quotes, for GameState as it is right now.
	func sheet(weapon: String = "") -> Dictionary:
		_probes()
		var gs := GameState
		nico.refresh_stats()
		var out := {"hp": gs.hp, "max_hp": gs.max_hp(), "points": gs.points,
			"walk": nico.walk_speed, "run": nico.run_speed, "getup": nico.getup_invuln}
		for s in gs.STATS:
			out[s] = gs.stat(s)
		out["jab"] = strike("punch_a")
		out["jab_dizzy"] = foe().dizzy_meter
		out["dizzy_at"] = foe().dizzy_threshold
		out["combo"] = int(out.jab) + strike("punch_b") + strike("punch_c")
		out["kick"] = strike("kick")
		nico.atk = Content.attack("punch_a")
		out["jab_recovery"] = nico._recovery_ticks()
		nico.atk = Content.attack("punch_c")
		out["finisher_recovery"] = nico._recovery_ticks()
		out["perfect"] = nico.perfect_window()
		out["dizzy_mult"] = nico.dizzy_mult()
		var w := weapon if str(Content.weapon(weapon).get("attack", "")) != "" else str(ref.weapon)
		out["weapon_id"] = w
		out["weapon"] = swing(w)
		var t := Preview.ref_technique()
		out["tech_id"] = t.skill
		out["tech"] = strike(str(t.attack))
		for k in Preview.TAKEN:
			out[k] = taken(k)
		return out

	## What a weapon does right now: {swing (-1 if it cannot be swung), throw, uses, carry (walk speed held)}.
	func weapon_sheet(weapon_id: String) -> Dictionary:
		return {"swing": swing(weapon_id), "throw": hurl(weapon_id), "uses": uses(weapon_id), "carry": carry_speed(weapon_id)}

	## What a technique does: {attack, damage (per hit), hits, jab, flags}. Automatic techniques have attack "".
	func technique_sheet(skill_id: String) -> Dictionary:
		var aid := Preview.technique_attack(skill_id)
		var out := {"attack": aid, "damage": 0, "hits": 0, "jab": strike("punch_a"), "throw": 0, "flags": []}
		if aid == "":
			return out
		var d: Dictionary = Content.attack(aid)
		out.damage = strike(aid)
		out.hits = int(d.get("hits", 1))
		if aid == "giant_spin":
			out.throw = strike("thrown_body")
		var flags: Array = out.flags
		if d.get("knockdown", false):
			flags.append("knocks down")
		if d.get("multi", false):
			flags.append("hits everyone in reach")
		if d.has("invuln"):
			flags.append("cannot be hit for its first %d frames" % (int(d.invuln[1]) - int(d.invuln[0]) + 1))
		if d.has("armor"):
			flags.append("light hits do not stop it for %d frames" % (int(d.armor[1]) - int(d.armor[0]) + 1))
		if d.get("guard_break", false):
			flags.append("breaks a guard")
		if d.get("low", false):
			flags.append("low: street fighters cannot block it")
		return out

	## Current HP, max HP, every stat and the food bonuses eaten so far.
	func vitals() -> Dictionary:
		var out := {"hp": GameState.hp, "max_hp": GameState.max_hp(), "food": GameState.food.duplicate()}
		for s in GameState.STATS:
			out[s] = GameState.stat(s)
		return out

# ---------------------------------------------------------------- previews
## Derived numbers now (see Bench.sheet). `weapon` is the weapon in Nico's hands, if any.
static func sheet(weapon: String = "") -> Dictionary:
	var b := Bench.new()
	var out := b.sheet(weapon)
	b.close()
	return out

## Eating an item right now: {before, after (see Bench.vitals), result (what GameState.consume reports),
## no_effect (true when nothing at all would change)}.
static func food(item_id: String) -> Dictionary:
	var b := Bench.new()
	var before := b.vitals()
	var res := GameState.consume(item_id)
	var after := b.vitals()
	b.close()
	return {"before": before, "after": after, "result": res, "no_effect": before == after}

## One more point in a stat: {before, after} sheets. Works with no unspent point (shows the next one).
static func stat_point(stat: String, weapon: String = "") -> Dictionary:
	var b := Bench.new()
	var before := b.sheet(weapon)
	point(stat, true)
	var after := b.sheet(weapon)
	b.close()
	return {"before": before, "after": after}

## The next tier of a workbench line: {tier, max, weapons: [{id, family, before, after}]} with one reference
## weapon per family the line improves (before == after once the line is at its last tier).
static func workbench(line: String) -> Dictionary:
	var tiers: Array = Content.upgrades.get(line, {}).get("tiers", [])
	var tier := GameState.upgrade_tier(line)
	var out := {"tier": tier, "max": tiers.size(), "weapons": []}
	var b := Bench.new()
	var ids: Array = []
	for fam in upgrade_families(line):
		var wid := family_weapon(fam)
		if wid != "":
			ids.append(wid)
			out.weapons.append({"id": wid, "family": fam, "before": b.weapon_sheet(wid), "after": {}})
	if tier < tiers.size():
		upgrade(line)
	for i in ids.size():
		out.weapons[i].after = b.weapon_sheet(ids[i])
	b.close()
	return out

## The next mastery level of a weapon family, on its reference weapon (or `weapon` if it belongs to the
## family): {id, level, hits (uses still needed, 0 at the maximum), before, after}.
static func mastery(family: String, weapon: String = "") -> Dictionary:
	var held: Dictionary = Content.weapon(weapon)
	var wid := weapon if str(held.get("family", "")) == family and str(held.get("attack", "")) != "" else family_weapon(family, true)
	var b := Bench.new()
	var out := {"id": wid, "level": GameState.mastery_level(family), "hits": 0, "before": b.weapon_sheet(wid), "after": {}}
	out.hits = master(family)
	out.after = b.weapon_sheet(wid)
	b.close()
	return out

## What a technique does against the reference brawler (see Bench.technique_sheet).
static func technique(skill_id: String) -> Dictionary:
	var b := Bench.new()
	var out := b.technique_sheet(skill_id)
	b.close()
	return out
