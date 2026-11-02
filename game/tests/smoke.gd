extends Node
## Headless smoke: loads every script, starts a new game, simulates input for a few seconds.

func _ready() -> void:
	var errs := 0
	for f in _scripts("res://scripts"):
		var s = load(f)
		if s == null:
			print("LOAD FAIL ", f)
			errs += 1
	print("scripts checked, failures=", errs)
	GameState.reset_new_game()
	var w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(0.5).timeout
	print("world=", w, " room=", w.room.room_id if w and w.room else "none")
	Input.action_press("move_right")
	await get_tree().create_timer(1.0).timeout
	Input.action_release("move_right")
	for i in 6:
		Input.action_press("punch")
		await get_tree().physics_frame
		await get_tree().physics_frame
		Input.action_release("punch")
		await get_tree().create_timer(0.15).timeout
	Input.action_press("jump"); await get_tree().physics_frame; Input.action_release("jump")
	await get_tree().create_timer(0.3).timeout
	Input.action_press("kick"); await get_tree().physics_frame; Input.action_release("kick")
	await get_tree().create_timer(0.8).timeout
	var p = w.room.player
	print("player pos=", p.position, " state=", p.state, " hp=", p.hp, " z=", p.z)
	var e = w.room.spawn_enemy("dogs_brawler", p.position + Vector2(40, 0))
	for i in 240:
		await get_tree().physics_frame
	print("enemy state=", e.state, " hp=", e.hp, " player hp=", p.hp)
	print("SMOKE DONE")
	get_tree().quit(errs)

func _scripts(dir: String) -> Array:
	var out := []
	var d := DirAccess.open(dir)
	for f in d.get_files():
		if f.ends_with(".gd"):
			out.append(dir + "/" + f)
	for sub in d.get_directories():
		out.append_array(_scripts(dir + "/" + sub))
	return out
