class_name PreviewText
extends RefCounted
## Words for the numbers in Preview: what a dish, a stat point, a workbench tier, a mastery level or a manual
## will change, written as "now -> after". Every damage number names the fighter it was measured against.
## (The UI fonts have no arrow glyph, hence "->".)

const STAT_NAME := {"hp": "Max HP", "atk": "ATK", "def": "DEF", "agi": "AGI", "tec": "TEC"}

static func ab(a: Variant, b: Variant, fmt: String = "%d") -> String:
	var sa := fmt % a
	var sb := fmt % b
	return sa + " (no change)" if sa == sb else "%s -> %s" % [sa, sb]

static func _target() -> String:
	return "a " + Preview.ref_label()

static func _cap(s: String) -> String:
	return s.left(1).to_upper() + s.substr(1)

# ---------------------------------------------------------------- prices
## "$8", or "$8 (was $10)" while the shop's standing discount applies. The number is GameState.price_for's.
static func price(shop_id: String, base: int) -> String:
	var p := GameState.price_for(shop_id, base)
	return "$%d (was $%d)" % [p, base] if p != base else "$%d" % p

## The shop's discount note while its discount applies, otherwise "".
static func discount_note(shop_id: String) -> String:
	var d = Content.shops.get(shop_id, {}).get("discount", {})
	if typeof(d) != TYPE_DICTIONARY or GameState.price_for(shop_id, 1000) == 1000:
		return ""
	return str(d.get("note", "Prices are reduced here."))

# ---------------------------------------------------------------- food
## {text, no_effect}: what eating the item right now changes.
static func food(item_id: String) -> Dictionary:
	var it: Dictionary = Content.item(item_id)
	if it.get("revive", false):
		return {"text": "Goes in your bag. If you are knocked out it is used up and you stand back up with half your HP.", "no_effect": false}
	var p := Preview.food(item_id)
	var b: Dictionary = p.before
	var a: Dictionary = p.after
	var parts: Array = []
	if int(it.get("heal", 0)) > 0 or int(a.hp) != int(b.hp):
		if int(a.hp) == int(b.hp) and int(a.max_hp) == int(b.max_hp):
			parts.append("HP stays %d/%d (already full)" % [int(b.hp), int(b.max_hp)])
		else:
			parts.append("HP %d/%d -> %d/%d" % [int(b.hp), int(b.max_hp), int(a.hp), int(a.max_hp)])
	for s in it.get("bonus", {}):
		var cap := int(Content.food_caps.get(s, 8))
		var fb := int(b.food.get(s, 0))
		var fa := int(a.food.get(s, 0))
		var nm: String = STAT_NAME.get(s, str(s).to_upper())
		if fa > fb:
			parts.append("%s +%d for good: %d -> %d (food bonus %d -> %d of %d%s)" % [nm, fa - fb, int(b[s]), int(a[s]), fb, fa, cap,
				", the cap" if fa >= cap else ""])
		else:
			parts.append("%s stays %d (its food bonus is maxed: %d of %d)" % [nm, int(b[s]), fb, cap])
	if p.no_effect:
		return {"text": "No effect right now: " + "; ".join(parts) + ".", "no_effect": true}
	return {"text": "Eat now: " + "; ".join(parts) + ".", "no_effect": false}

# ---------------------------------------------------------------- stat points
## What one more point in a stat changes, in the game's own numbers.
static func stat_point(stat: String, weapon: String = "") -> String:
	var p := Preview.stat_point(stat, weapon)
	var b: Dictionary = p.before
	var a: Dictionary = p.after
	var who := _target()
	var head := "Next point: %s %s. " % [STAT_NAME.get(stat, stat), ab(b.max_hp if stat == "hp" else b[stat], a.max_hp if stat == "hp" else a[stat])]
	var wname := str(Content.weapon(str(b.weapon_id)).get("name", "weapon"))
	match stat:
		"hp":
			return head + "Your HP goes %s right away." % ab(b.hp, a.hp)
		"atk":
			return head + "Against %s: jab %s, 3-hit punch combo %s, kick %s, %s swing %s." % [who, ab(b.jab, a.jab),
				ab(b.combo, a.combo), ab(b.kick, a.kick), wname, ab(b.weapon, a.weapon)]
		"def":
			var parts: Array = []
			for k in Preview.TAKEN:
				var spec: Array = Preview.TAKEN[k]
				parts.append("a %s's %s costs you %s HP" % [Preview.ref_label(str(spec[0])), str(spec[2]), ab(b[k], a[k])])
			return head + _cap(", ".join(parts)) + "."
		"agi":
			return head + "Walk speed %s, run speed %s. Recovery after a jab %s frames, after a finisher %s. Get-up protection %s frames. (60 frames = 1 second.)" % [
				ab(b.walk, a.walk, "%.1f"), ab(b.run, a.run, "%.1f"), ab(b.jab_recovery, a.jab_recovery),
				ab(b.finisher_recovery, a.finisher_recovery), ab(b.getup, a.getup)]
		"tec":
			var tname := str(Content.skill(str(b.tech_id)).get("name", "technique"))
			return head + "Against %s: %s %s, %s swing %s. Perfect-guard window %s frames. A jab fills %s of the %d that dizzies them." % [who,
				tname, ab(b.tech, a.tech), wname, ab(b.weapon, a.weapon), ab(b.perfect, a.perfect),
				ab(b.jab_dizzy, a.jab_dizzy, "%.1f"), int(b.dizzy_at)]
	return head

# ---------------------------------------------------------------- weapons
static func _weapon_now(wid: String, s: Dictionary) -> String:
	var w: Dictionary = Content.weapon(wid)
	if int(s.swing) >= 0:
		return "%s swing %d, lasts %d hits" % [w.get("name", wid), int(s.swing), int(s.uses)]
	var t := "%s thrown %d" % [w.get("name", wid), int(s["throw"])]
	if w.get("carry", false):
		t += ", carried at speed %.0f" % float(s.carry)
	return t

static func _weapon_change(wid: String, b: Dictionary, a: Dictionary) -> String:
	var w: Dictionary = Content.weapon(wid)
	if int(b.swing) >= 0:
		var t := "%s swing %s" % [w.get("name", wid), ab(b.swing, a.swing)]
		if int(a.uses) != int(b.uses):
			t += ", lasts %s hits" % ab(b.uses, a.uses)
		return t
	var t2 := "%s thrown %s" % [w.get("name", wid), ab(b["throw"], a["throw"])]
	if w.get("carry", false):
		t2 += ", carried at speed %s" % ab(b.carry, a.carry, "%.0f")
	return t2

## What the next tier of a workbench line changes, on one reference weapon per family it covers.
static func workbench(line: String) -> String:
	var p := Preview.workbench(line)
	var parts: Array = []
	var maxed := int(p.tier) >= int(p.max)
	for e in p.weapons:
		parts.append(_weapon_now(e.id, e.before) if maxed else _weapon_change(e.id, e.before, e.after))
	var head := "Fully upgraded. Now" if maxed else "Tier %d" % (int(p.tier) + 1)
	return "%s, against %s: %s." % [head, _target(), "; ".join(parts)]

## What the next mastery level of a weapon family changes.
static func mastery(family: String, weapon: String = "") -> String:
	var p := Preview.mastery(family, weapon)
	var wid := str(p.id)
	if wid == "":
		return ""
	if int(p.before.swing) < 0:
		return "%s against %s. Mastery only grows by swinging, so objects that can only be thrown stay at level 0." % [
			_cap(_weapon_now(wid, p.before)), _target()]
	if int(p.hits) <= 0:
		return "Mastered. %s against %s." % [_weapon_now(wid, p.before), _target()]
	return "Level %d in %d more hits: %s against %s." % [int(p.level) + 1, int(p.hits), _weapon_change(wid, p.before, p.after), _target()]

# ---------------------------------------------------------------- techniques
## Short fact lines about a technique, measured against the reference fighter.
static func technique(skill_id: String) -> Array:
	var t := Preview.technique(skill_id)
	var out: Array = []
	if str(t.attack) == "":
		out.append("Nothing to press: once learned it is always on.")
		return out
	var who := _target()
	if int(t["throw"]) > 0:
		out.append("Damage against %s: %d to everyone the spin touches, then %d where the body lands (your jab does %d)." % [who, int(t.damage), int(t["throw"]), int(t.jab)])
	elif int(t.hits) > 1:
		out.append("Damage against %s: %d hits of %d (your jab does %d)." % [who, int(t.hits), int(t.damage), int(t.jab)])
	else:
		out.append("Damage against %s: %d (your jab does %d)." % [who, int(t.damage), int(t.jab)])
	if not t.flags.is_empty():
		out.append(_cap(", ".join(t.flags)) + ".")
	return out

## A technique's input for the device in use, e.g. "While running: [Shift] + [J]".
static func technique_input(skill_id: String) -> String:
	return Story.format_text(Tutor.input_text(Content.skill(skill_id)))
