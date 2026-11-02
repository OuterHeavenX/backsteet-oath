extends Node
## Renders the end-of-game run summary card and the Show FPS readout (xvfb-run). SHOTS_DIR sets the output.
func _ready() -> void:
	var out := OS.get_environment("SHOTS_DIR") if OS.get_environment("SHOTS_DIR") != "" else "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	await get_tree().process_frame
	GameState.reset_new_game()
	for f in ["intro_done", "intro_seen", "met_mara"]:
		GameState.set_flag(f)
	GameState.room = "int_diner"
	GameState.spawn = "south"
	GameState.stats.playtime = 3725.0
	GameState.stats.defeated = 268
	GameState.stats.deaths = 4
	GameState.stats.food_eaten = 17
	GameState.stats.cash_earned = 1460
	GameState.level = 13
	Settings.show_fps = true
	var w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child(w)
	await get_tree().create_timer(2.5).timeout
	await _shot(out + "/fps_readout.png")
	w.show_run_summary()
	await get_tree().create_timer(0.8).timeout
	await _shot(out + "/run_summary.png")
	Settings.show_fps = false
	get_tree().quit()

func _shot(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
	print("shot ", path)
