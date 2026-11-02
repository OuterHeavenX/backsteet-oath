extends Node
var world: Node
func state(qid: String) -> String:
	return GameState.quests.get(qid, {}).get("state", "inactive")
func step_text(_qid: String) -> String:
	return ""
func on_key_item(_id: String) -> void:
	pass
