class_name BuildGuideMenu
extends Menu
## Three ways to grow Nico, as advice only. Nothing here is a class, a lock or an automatic choice: it points
## at stats, dishes, manuals and workbench lines that already exist, with today's prices, where to find them,
## whether a manual is on the shelf yet, and what the favoured stat's next point does right now (Preview).

## stats: favoured stats, first one first. skills: manuals that suit the style. bench: a workbench line, if any.
const BUILDS := [
	{"name": "Brawler", "pitch": "Fists and feet, up close. Every punch and kick scales with ATK; Max HP keeps you in the scrap.",
		"stats": ["atk", "hp"], "skills": ["rapid", "shoulder", "heel"], "bench": ""},
	{"name": "Weapon specialist", "pitch": "Fight with whatever is lying around. Swings and throws use ATK and TEC together, families get stronger with use, and Mara makes them hit harder and last longer.",
		"stats": ["atk", "tec"], "skills": ["retrieve", "giant"], "bench": "grip"},
	{"name": "Counter fighter", "pitch": "Guard, punish, stay standing. TEC widens the perfect-guard window and powers techniques; DEF softens what gets through.",
		"stats": ["tec", "def"], "skills": ["counter", "rising", "sweep"], "bench": ""},
]

var detail: Label
var _shown := -1

func build() -> void:
	var c := make_frame("Build ideas", Vector2(560, 0))
	var r: Dictionary = Content.services.get("respec", {})
	var refund := "Coach Benny refunds spent stat points for $%d" % GameState.price_for("rec", int(r.get("price", 0)))
	if not GameState.check(str(r.get("requires", ""))):
		refund += " later in the story"
	c.add_child(UIKit.wrap_label("Suggestions, not classes: nothing is locked, mix them freely. %s." % refund, 540, UIKit.DIM))
	var h := UIKit.hbox(6)
	c.add_child(h)
	for i in BUILDS.size():
		var b := UIKit.button(str(BUILDS[i].name), func(): _show_build(i), 150)
		b.focus_entered.connect(func(): _show_build(i))
		h.add_child(b)
		if i == 0:
			first_focus = b
	detail = UIKit.wrap_label("", 540, UIKit.CREAM)
	detail.custom_minimum_size = Vector2(540, 11 * (UIKit.base_size() + 3))
	c.add_child(detail)
	_shown = -1
	_show_build(0)

func _show_build(i: int) -> void:
	if i == _shown:
		return
	_shown = i
	detail.text = "\n".join(lines(i))

## Where a shop is: "Lucky Spoon Diner (Old Quarter)".
static func shop_place(shop_id: String) -> String:
	var nm := str(Content.shops.get(shop_id, {}).get("name", shop_id))
	for rid in Content.encounters:
		for n in Content.encounters[rid].get("npcs", []):
			if str(n.get("shop", "")) == shop_id:
				return "%s (%s)" % [nm, Content.district_name(str(Content.room(rid).get("district", "")))]
	return nm

## The cheapest dishes on sale that raise a stat for good: [{item, shop, price}], cheapest first.
static func foods_for(stat: String, limit: int = 2) -> Array:
	var out: Array = []
	for sid in Content.shops:
		var sh: Dictionary = Content.shops[sid]
		if sh.get("kind", "") != "food":
			continue
		for id in sh.get("stock", []):
			var it: Dictionary = Content.item(str(id))
			if int(it.get("bonus", {}).get(stat, 0)) > 0:
				out.append({"item": str(id), "shop": str(sid), "price": GameState.price_for(str(sid), int(it.get("price", 0)))})
	out.sort_custom(func(a, b): return int(a.price) < int(b.price))
	return out.slice(0, limit)

## Where a manual is sold and whether it can be bought today: {shop, price, state: learned / shelf / later / none}.
static func manual_status(skill_id: String) -> Dictionary:
	for sid in Content.shops:
		var sh: Dictionary = Content.shops[sid]
		if sh.get("kind", "") != "skills":
			continue
		for entry in sh.get("stock", []):
			if str(entry[0]) != skill_id:
				continue
			var state := "shelf" if str(entry[1]) == "" or GameState.check(str(entry[1])) else "later"
			if GameState.has_skill(skill_id):
				state = "learned"
			return {"shop": str(sid), "price": GameState.price_for(str(sid), int(Content.skill(skill_id).get("price", 0))), "state": state}
	return {"shop": "", "price": 0, "state": "learned" if GameState.has_skill(skill_id) else "none"}

## The advice for one build, one paragraph per line, from today's data and save.
static func lines(i: int) -> Array:
	var b: Dictionary = BUILDS[i]
	var out: Array = [str(b.pitch)]
	var names: Array = []
	for s in b.stats:
		names.append(str(PreviewText.STAT_NAME.get(s, s)))
	out.append("STATS: favour %s. %s" % [" then ".join(names), PreviewText.stat_point(str(b.stats[0]))])
	var food_parts: Array = []
	for s in b.stats:
		var cap := int(Content.food_caps.get(s, 8))
		var have := int(GameState.food.get(s, 0))
		var nm := str(PreviewText.STAT_NAME.get(s, s))
		if have >= cap:
			food_parts.append("%s food bonus is maxed (%d of %d)" % [nm, have, cap])
			continue
		var picks: Array = []
		for f in foods_for(str(s)):
			picks.append("%s $%d at %s" % [Content.item(f.item).get("name", f.item), int(f.price), shop_place(f.shop)])
		food_parts.append("%s (%d of %d eaten): %s" % [nm, have, cap, ", ".join(picks)])
	out.append("FOOD: " + "; ".join(food_parts) + ".")
	var man_parts: Array = []
	for sid in b.skills:
		var st := manual_status(str(sid))
		var nm2 := str(Content.skill(str(sid)).get("name", sid))
		match str(st.state):
			"learned": man_parts.append("%s (learned)" % nm2)
			"shelf":
				if str(sid) == "shoulder" and Story._benny_lesson_due():
					man_parts.append("%s free from Coach Benny's first lesson at %s" % [nm2, shop_place(st.shop)])
				else:
					man_parts.append("%s $%d at %s" % [nm2, int(st.price), shop_place(st.shop)])
			"later": man_parts.append("%s at %s (not on the shelf yet: it arrives later in the story)" % [nm2, shop_place(st.shop)])
			_: man_parts.append("%s (not sold anywhere)" % nm2)
	out.append("MANUALS: " + "; ".join(man_parts) + ".")
	if str(b.bench) != "":
		var u: Dictionary = Content.upgrades.get(str(b.bench), {})
		out.append("WORKBENCH: %s at %s. %s" % [u.get("name", b.bench), shop_place("garage"), PreviewText.workbench(str(b.bench))])
	return out
