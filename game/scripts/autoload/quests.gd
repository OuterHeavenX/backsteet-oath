extends Node
## Side jobs: start / step / complete / fail with rewards, journal text and persistence in GameState.quests.

signal quest_changed(qid: String)

var world: Node

func state(qid: String) -> String:
	return str(GameState.quests.get(qid, {}).get("state", "inactive"))

func step(qid: String) -> int:
	return int(GameState.quests.get(qid, {}).get("step", 0))

func is_active(qid: String) -> bool:
	return state(qid) == "active"

func available(qid: String) -> bool:
	var q: Dictionary = Content.quests.get(qid, {})
	if q.is_empty():
		return false
	var st := state(qid)
	if st == "active":
		return false
	if st == "done" and not q.get("repeatable", false):
		return false
	return GameState.check(q.get("requires", ""))

func step_text(qid: String) -> String:
	var q: Dictionary = Content.quests.get(qid, {})
	var st := state(qid)
	if st == "done":
		return "Completed." + (" Can be replayed." if q.get("repeatable", false) else "")
	if st == "failed":
		return "Talk to %s to try again." % Content.character_name(q.get("giver", ""))
	var steps: Array = q.get("steps", [])
	var s := step(qid)
	var t: String = steps[clampi(s, 0, steps.size() - 1)] if not steps.is_empty() else ""
	if qid == "parcels" and s == 0:
		t += " (%d/3)" % int(GameState.key_items.get("parcel", 0))
	return t

func start(qid: String) -> void:
	GameState.quests[qid] = {"state": "active", "step": 0, "data": {}}
	var q: Dictionary = Content.quests.get(qid, {})
	_toast("New side job: %s" % q.get("name", qid), UIKit.MUSTARD)
	Audio.sfx("quest_update")
	quest_changed.emit(qid)
	if world and world.hud:
		world.hud.refresh_objective()

func set_step(qid: String, n: int) -> void:
	if not GameState.quests.has(qid):
		return
	GameState.quests[qid]["step"] = n
	Audio.sfx("quest_update")
	_toast("Side job updated: " + step_text(qid), UIKit.CREAM)
	quest_changed.emit(qid)

func fail(qid: String) -> void:
	if not GameState.quests.has(qid):
		return
	GameState.quests[qid]["state"] = "failed"
	quest_changed.emit(qid)

## Grants the quest's reward (or an override for rematches / alternate outcomes).
func complete(qid: String, reward_override: Dictionary = {}) -> void:
	var q: Dictionary = Content.quests.get(qid, {})
	var r: Dictionary = reward_override if not reward_override.is_empty() else q.get("reward", {})
	if not GameState.quests.has(qid):
		GameState.quests[qid] = {"state": "active", "step": 0, "data": {}}
	var first_time := int(GameState.quests[qid].get("times", 0)) == 0
	GameState.quests[qid]["state"] = "done"
	GameState.quests[qid]["times"] = int(GameState.quests[qid].get("times", 0)) + 1
	var parts: Array = []
	if r.has("cash"):
		GameState.add_cash(int(r.cash))
		parts.append("$%d" % int(r.cash))
	for b in r.get("bag", []):
		if GameState.add_to_bag(b):
			parts.append(Content.item(b).get("name", b))
		else:
			GameState.add_cash(8)
			parts.append("$8 (bag full)")
	if r.has("gear") and (first_time or not str(r.gear) in GameState.gear):
		GameState.give_gear(r.gear)
		parts.append(Content.item(r.gear).get("name", r.gear))
	if r.has("skill"):
		GameState.learn(r.skill)
		parts.append(Content.skill(r.skill).get("name", r.skill) + " technique")
	if r.has("upgrade"):
		GameState.upgrades[r.upgrade] = maxi(1, GameState.upgrade_tier(r.upgrade))
		parts.append(Content.upgrades[r.upgrade].name)
	if r.has("xp"):
		GameState.add_xp(int(r.xp))
		parts.append("%d XP" % int(r.xp))
	Audio.sfx("quest_complete")
	_toast("Side job complete: %s!  %s" % [q.get("name", qid), ", ".join(parts)], UIKit.CASHC)
	quest_changed.emit(qid)
	if world and world.room and world.room.player:
		world.room.player.refresh_stats()
	SaveService.save_game()

func on_key_item(id: String) -> void:
	match id:
		"parcel":
			if is_active("parcels") and int(GameState.key_items.get("parcel", 0)) >= 3 and step("parcels") == 0:
				set_step("parcels", 1)
			elif is_active("parcels"):
				_toast("Parcel found! (%d/3)" % int(GameState.key_items.get("parcel", 0)), UIKit.CREAM)
		"toolbox":
			if is_active("tools") and step("tools") == 0:
				set_step("tools", 1)
		"radio":
			if is_active("radio") and step("radio") == 0:
				set_step("radio", 1)
		"conductor_punch":
			if is_active("punch") and step("punch") == 0:
				set_step("punch", 1)
		"weight_pier", "weight_iron", "weight_neon":
			if is_active("weights"):
				var n := 0
				for k in ["weight_pier", "weight_iron", "weight_neon"]:
					if GameState.has_key(k):
						n += 1
				if n >= 3 and step("weights") == 0:
					set_step("weights", 1)
				else:
					_toast("Rigged weights recovered (%d/3)" % n, UIKit.CREAM)

func _toast(msg: String, col: Color) -> void:
	if world and world.has_method("toast"):
		world.toast(msg, col)
