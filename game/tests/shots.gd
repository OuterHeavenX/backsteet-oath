extends Node
## Visual check: renders key moments to PNG (run with a display, e.g. xvfb-run).
var out := ""

func _ready() -> void:
	out = OS.get_environment("SHOTS_DIR")
	if out == "":
		out = "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	Audio.unlocked = true
	var room_id := OS.get_environment("SHOT_ROOM")
	GameState.reset_new_game()
	if room_id != "":
		for f in OS.get_environment("SHOT_FLAGS").split(",", false):
			GameState.set_flag(f)
		var st := OS.get_environment("SHOT_STAGE")
		if st != "":
			GameState.stage = st
		GameState.room = room_id
		GameState.spawn = OS.get_environment("SHOT_SPAWN") if OS.get_environment("SHOT_SPAWN") != "" else "west"
	var w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.2).timeout
	await _shot("a_start")
	var steps := OS.get_environment("SHOT_STEPS").split(";", false)
	var i := 0
	for s in steps:
		var parts := s.split(":")
		match parts[0]:
			"wait": await get_tree().create_timer(float(parts[1])).timeout
			"press":
				_act(parts[1], true)
				await get_tree().create_timer(float(parts[2]) if parts.size() > 2 else 0.05).timeout
				_act(parts[1], false)
			"hold": _act(parts[1], true)
			"release": _act(parts[1], false)
			"shot":
				await _shot(parts[1])
			"spawn":
				var r = w.room
				r.spawn_enemy(parts[1], r.player.position + Vector2(float(parts[2]), float(parts[3])))
			"tp":
				w.room.player.position = Vector2(float(parts[1]), float(parts[2]))
			"menu":
				match parts[1]:
					"pause": w.open_pause()
					"status": w.push_menu(StatusMenu.new())
					"shop": w.open_shop(parts[2])
					"journal": w.push_menu(JournalMenu.new())
					"map": w.push_menu(MapMenu.new())
					"settings": w.push_menu(SettingsMenu.new())
					"close": w.close_all_menus()
		i += 1
	await _shot("z_end")
	get_tree().quit()

func _act(a: String, on: bool) -> void:
	var ev := InputEventAction.new()
	ev.action = a
	ev.pressed = on
	ev.strength = 1.0 if on else 0.0
	Input.parse_input_event(ev)

func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(out + "/" + name + ".png")
	print("shot ", name)
