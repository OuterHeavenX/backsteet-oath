class_name Playtest
extends RefCounted
## Opt-in, local playtest notes (Settings > Playtest log). When it is on, a handful of timestamps and counts
## are kept inside the save's own stats ("pt") so a facilitator can read them from the pause menu or the
## end-of-run card. Nothing is sent anywhere and nothing is recorded while the setting is off.

static func on() -> bool:
	return Settings.playtest_log

static func _pt() -> Dictionary:
	if typeof(GameState.stats.get("pt")) != TYPE_DICTIONARY:
		GameState.stats["pt"] = {}
	return GameState.stats["pt"]

static func now() -> float:
	return snappedf(float(GameState.stats.get("playtime", 0.0)), 0.1)

## Records the play time of the first time something happened (later calls are ignored).
static func once(key: String) -> void:
	if not on():
		return
	var pt := _pt()
	if not pt.has(key):
		pt[key] = now()

## Adds to a counter, optionally under a sub-key (e.g. knockouts per room).
static func count(key: String, sub: String = "", amount: int = 1) -> void:
	if not on():
		return
	var pt := _pt()
	if sub == "":
		pt[key] = int(pt.get(key, 0)) + amount
		return
	if typeof(pt.get(key)) != TYPE_DICTIONARY:
		pt[key] = {}
	pt[key][sub] = int(pt[key].get(sub, 0)) + amount

static func _t(v) -> String:
	return UIKit.fmt_time(float(v))

## Readable lines for the playtest page and the run summary. Empty when nothing has been recorded.
static func lines() -> Array:
	var pt = GameState.stats.get("pt", {})
	if typeof(pt) != TYPE_DICTIONARY or pt.is_empty():
		return []
	var out: Array = []
	for pair in [["first_move", "First movement"], ["first_hit", "First hit landed"], ["first_block", "First block"],
			["first_throw", "First throw"], ["first_door", "First door entered"], ["first_meal", "First meal"],
			["first_technique", "First technique used"], ["first_purchase", "First purchase"], ["first_ko", "First knockout"]]:
		if pt.has(pair[0]):
			out.append("%s: %s" % [pair[1], _t(pt[pair[0]])])
	var tips: Array = []
	var skipped: Array = []
	for k in pt.keys():
		var key := str(k)
		if key.begins_with("tip:"):
			tips.append("%s %s" % [key.substr(4), _t(pt[k])])
		elif key.begins_with("skip:"):
			skipped.append(key.substr(5))
	if not tips.is_empty():
		out.append("Tips done by doing: " + ", ".join(tips))
	if not skipped.is_empty():
		out.append("Tips skipped: " + ", ".join(skipped))
	var stages: Array = []
	for k in pt.keys():
		if str(k).begins_with("stage:"):
			stages.append([float(pt[k]), str(k).substr(6)])
	stages.sort_custom(func(a, b): return a[0] < b[0])
	if not stages.is_empty():
		var parts: Array = []
		for s in stages:
			parts.append("%s %s" % [s[1], _t(s[0])])
		out.append("Story stages reached: " + ", ".join(parts))
	if typeof(pt.get("ko")) == TYPE_DICTIONARY:
		var kos: Array = []
		for r in pt.ko:
			kos.append("%s x%d" % [Content.room(str(r)).get("name", str(r)), int(pt.ko[r])])
		out.append("Knockouts: " + ", ".join(kos))
	if pt.has("purchases"):
		out.append("Purchases: %d  ($%d spent in shops)" % [int(pt.purchases), int(pt.get("spent", 0))])
	if pt.has("sparring"):
		out.append("Sparring sessions: %d" % int(pt.sparring))
	if pt.has("lights_on"):
		out.append("Work lights switched on: %d" % int(pt.lights_on))
	return out
