extends Node
## Visual check: renders key moments to PNG (run with a display, e.g. xvfb-run).
var out := ""

func _ready() -> void:
	out = OS.get_environment("SHOTS_DIR")
	if out == "":
		out = "user://shots"
	DirAccess.make_dir_recursive_absolute(out)
	Audio.unlocked = true
	if OS.get_environment("SHOT_EFFECTS") != "":
		Settings.effects = OS.get_environment("SHOT_EFFECTS")
	if OS.get_environment("SHOT_LARGE") != "":
		Settings.large_text = true
	if OS.get_environment("SHOT_TOUCH") != "":
		Settings.touch_controls = "on"
		InputPrompts.kind = "touch"
	if OS.get_environment("SHOT_LARGE") != "":
		Settings.large_text = true
		UIKit.build_theme()
	var room_id := OS.get_environment("SHOT_ROOM")
	GameState.reset_new_game()
	if room_id != "":
		for f in OS.get_environment("SHOT_FLAGS").split(",", false):
			GameState.set_flag(f)
		var st := OS.get_environment("SHOT_STAGE")
		if st != "":
			GameState.stage = st
		# SHOT_QUESTS=mural,radio:active  -> side jobs to start in a given state (default: done)
		for q in OS.get_environment("SHOT_QUESTS").split(",", false):
			var qp := q.split(":")
			GameState.quests[qp[0]] = {"state": qp[1] if qp.size() > 1 else "done", "step": 0, "data": {}}
		GameState.room = room_id
		GameState.spawn = OS.get_environment("SHOT_SPAWN") if OS.get_environment("SHOT_SPAWN") != "" else "west"
	if OS.get_environment("SHOT_NG") != "":
		GameState.ng_cycle = int(OS.get_environment("SHOT_NG"))
		GameState.new_game_plus = true
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
			"room":
				w._load_room(parts[1], parts[2] if parts.size() > 2 else "west")
				await get_tree().create_timer(0.8).timeout
			"boss":
				var r2 = w.room
				var b = r2.spawn_enemy(parts[1], r2.player.position + Vector2(float(parts[2]), 0), {})
				r2.boss_actors = [b]
				r2.boss_active = true
				w.boss_bar([b])
				Audio.play_music("boss")
			"xp":
				GameState.add_xp(int(parts[1]))
				GameState.add_cash(int(parts[2]) if parts.size() > 2 else 0)
				w.room.player.refresh_stats()
				w.hud.levelup.visible = false
			"weapon":
				w.room.player.equip_weapon(parts[1])
			"hp":
				# set current HP (for shop / status previews at less than full health)
				GameState.hp = clampi(int(parts[1]), 1, GameState.max_hp())
				w.room.player.hp = GameState.hp
			"learn":
				GameState.learn(parts[1])
			"points":
				GameState.points = int(parts[1])
			"life":
				# test harness: rebuild the room's background life from a fixture JSON (tests/fixtures/life/)
				var lm = JSON.parse_string(FileAccess.get_file_as_string(parts[1] if parts[1].begins_with("res://") else "res://tests/fixtures/life/" + parts[1]))
				var v = w.room.vis
				if v.life:
					v.life.queue_free()
				v.life = RoomLife.new()
				w.room.add_child(v.life)
				v.life.build(v, lm, w.room.bg_root, w.room.fg_root)
			"bosshp":
				for b in w.room.boss_actors:
					if is_instance_valid(b):
						b.hp = int(b.max_hp * float(parts[1]))
			"tp":
				w.room.player.position = Vector2(float(parts[1]), float(parts[2]))
			"attack":
				# force the n-th enemy to start an attack now (for capturing tells): attack:<index>:<attack id>
				var foes: Array = []
				for a in w.room.actors:
					if a is Enemy and not a.dead:
						foes.append(a)
				if int(parts[1]) < foes.size():
					var foe: Enemy = foes[int(parts[1])]
					foe.facing = 1 if w.room.player.position.x > foe.position.x else -1
					foe.set_state("idle")
					foe._launch_attack(parts[2])
			"freeze":
				for a in w.room.actors:
					if a is Enemy:
						a.hold = parts.size() < 2 or parts[1] != "off"
			"flag":
				GameState.set_flag(parts[1])
			"quest":
				# quest:<id>[:<state>[:<step>]]  set a side job's state mid-run (default: done)
				GameState.quests[parts[1]] = {"state": parts[2] if parts.size() > 2 else "done", "step": int(parts[3]) if parts.size() > 3 else 0, "data": {}}
			"story":
				# story:<method>  call a Story method that takes the current room (e.g. story:_seat_ending_guests)
				Story.call(parts[1], w.room)
			"talk":
				# talk:<npc id>  start a conversation with an NPC in the room (as if the player walked up and pressed Action)
				var who = w.room.find_npc(parts[1])
				if who != null:
					w.room.player.position = who.position + Vector2(-26, 2)
					w.room.talk_to(who)
			"wavedone":
				w.room.waves_done[parts[1]] = true
			"killboss":
				for b in w.room.boss_actors.duplicate():
					if is_instance_valid(b):
						b.hp = 1
						b.take_damage_and_react(w.room.player, {"knockdown": true, "kb": 120, "launch": 140, "power": 99}, 99.0, 1, false)
			"killall":
				for a in w.room.actors.duplicate():
					if a is Enemy and not a.dead and a.team == Actor.TEAM_ENEMY:
						a.hp = 0
						a.take_damage_and_react(w.room.hazard_actor, {"knockdown": true, "kb": 100, "launch": 120}, 0.0, 1, false)
			"dlg":
				# advance dialogue for N seconds
				var t_end := Time.get_ticks_msec() + int(float(parts[1]) * 1000.0)
				while Time.get_ticks_msec() < t_end:
					if w.dialogue.active:
						_act("ui_accept", true)
						await get_tree().create_timer(0.05).timeout
						_act("ui_accept", false)
					await get_tree().create_timer(0.12).timeout
			"menu":
				match parts[1]:
					"pause": w.open_pause()
					"status": w.push_menu(StatusMenu.new())
					"status_tab":
						var sm := StatusMenu.new()
						sm.tab = int(parts[2])
						w.push_menu(sm)
					"shop": w.open_shop(parts[2])
					"journal": w.push_menu(JournalMenu.new())
					"builds": w.push_menu(BuildGuideMenu.new())
					"manual": ManualPreviewMenu.ask(w, parts[2], parts[3] if parts.size() > 3 else "")
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
