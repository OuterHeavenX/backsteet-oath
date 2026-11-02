extends Node
## Renders the title screen, its main menu and the credits to PNG (run with xvfb-run). SHOTS_DIR sets the output.
func _ready() -> void:
	var out := OS.get_environment("SHOTS_DIR")
	if out == "":
		out = "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	if OS.get_environment("SHOT_TOUCH") != "":
		InputPrompts.kind = "touch"
	if OS.get_environment("TITLE_NGPLUS") != "":
		GameState.reset_new_game()
		GameState.level = 15
		GameState.set_flag("game_complete")
		SaveService.save_game(3)
	var t = load("res://scenes/title.tscn").instantiate()
	get_tree().root.add_child.call_deferred(t)
	await get_tree().create_timer(2.5).timeout
	await _shot(out + "/title_press.png")
	var ev := InputEventKey.new()
	ev.keycode = KEY_ENTER
	ev.pressed = true
	Input.parse_input_event(ev)
	await get_tree().create_timer(1.2).timeout
	await _shot(out + "/title_menu.png")
	if OS.get_environment("TITLE_NGPLUS") != "":
		t._slots("ngplus")
		await get_tree().create_timer(0.8).timeout
		await _shot(out + "/title_ngplus.png")
		SaveService.delete_slot(3)
	t.queue_free()
	var c = load("res://scenes/credits.tscn").instantiate()
	get_tree().root.add_child(c)
	await get_tree().create_timer(3.0).timeout
	await _shot(out + "/credits.png")
	get_tree().quit()

func _shot(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
	print("shot ", path)
