extends Node
var world: Node
var credits_return := "title"
func format_text(s: String) -> String:
	return s
func objective_text() -> String:
	return "Explore."
func objective_detail() -> String:
	return ""
func new_game() -> void:
	pass
func on_room_enter(_room, _first) -> void:
	await get_tree().process_frame
func on_room_exit(_room) -> void:
	pass
func talk(_room, _npc) -> void:
	pass
func start_boss(_room, _cfg) -> void:
	pass
func boss_defeated(_room, _cfg, _ids) -> void:
	pass
func boss_retreat(_room, _b) -> void:
	pass
func rook_phase_two(_room, _b) -> void:
	pass
func escort_down(_room, _n) -> void:
	pass
func on_enemy_defeated(_room, _e) -> void:
	pass
func on_wave_clear(_room, _w) -> void:
	pass
func on_prop_event(_e, _room) -> void:
	pass
func can_retry_here(_room) -> bool:
	return true
func retry_spawn(_room) -> String:
	return "west"
func on_defeat_reset() -> void:
	pass
