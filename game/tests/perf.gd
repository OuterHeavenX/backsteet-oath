extends Node
## Performance sampling: per scenario, frame-time stats (wall clock), draw calls, texture memory, node count.
## Run with a display (xvfb-run) and NO --fixed-fps. Results go to stdout and user://perf.json.
## Software-rendered containers are not representative of GPUs; use this for relative comparisons.

const SCENARIOS := [
	{"name": "explore_kettle", "room": "oq_kettle", "spawn": "west", "enemies": [], "walk": true},
	{"name": "crowd_kettle", "room": "oq_kettle", "spawn": "west", "enemies": ["dogs_brawler", "dogs_flanker", "dogs_heavy", "dogs_thrower", "dogs_weapon", "dogs_blocker", "dogs_brawler", "dogs_flanker"]},
	{"name": "rain_pumpstation", "room": "fr_pumpstation", "spawn": "west", "enemies": ["grays_brawler", "grays_heavy", "grays_flanker"]},
	{"name": "interior_diner", "room": "int_diner", "spawn": "south", "enemies": []},
	{"name": "boss_rook", "room": "rw_floor", "spawn": "west", "enemies": [], "boss": "rook"},
]
const SECONDS := 6.0

var results: Array = []

func _ready() -> void:
	Audio.unlocked = true
	if OS.get_environment("PERF_EFFECTS") != "":
		Settings.effects = OS.get_environment("PERF_EFFECTS")
	await get_tree().process_frame   # the root is still adding children during _ready
	var only := OS.get_environment("PERF_ONLY")
	for sc in SCENARIOS:
		if only != "" and not str(sc.name).contains(only):
			continue
		await _run(sc)
	var f := FileAccess.open("user://perf.json", FileAccess.WRITE)
	f.store_string(JSON.stringify(results, "  "))
	print("PERF DONE")
	get_tree().quit()

func _run(sc: Dictionary) -> void:
	GameState.reset_new_game()
	for fl in "intro_done,intro_seen,met_mara,duke_intro_seen,rook_intro_seen".split(","):
		GameState.set_flag(fl)
	GameState.room = sc.room
	GameState.spawn = sc.spawn
	var w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child(w)
	await get_tree().create_timer(1.0).timeout
	var guard := 0
	while (w.room == null or w.room.player == null) and guard < 300:
		await get_tree().process_frame
		guard += 1
	var r = w.room
	r.player.position = Vector2(clampf(r.width * 0.4, 200, r.width - 200), 290)
	for i in sc.enemies.size():
		r.spawn_enemy(sc.enemies[i], r.player.position + Vector2(60 + (i % 4) * 30, -30 + (i / 4) * 40), {})
	if sc.has("boss"):
		var b = r.spawn_enemy(sc.boss, r.player.position + Vector2(110, 0), {})
		r.boss_actors = [b]
		r.boss_active = true
		w.boss_bar([b])
	if sc.get("walk", false):
		var ev := InputEventAction.new()
		ev.action = "right"
		ev.pressed = true
		Input.parse_input_event(ev)
	await get_tree().create_timer(0.5).timeout
	var times: Array = []
	var draws: Array = []
	var t0 := Time.get_ticks_usec()
	var last := t0
	while float(Time.get_ticks_usec() - t0) / 1e6 < SECONDS:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		times.append(float(now - last) / 1000.0)
		last = now
		draws.append(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		if r.player and r.player.hp < 20:
			r.player.hp = 60
			GameState.hp = 60
	if sc.get("walk", false):
		var ev2 := InputEventAction.new()
		ev2.action = "right"
		ev2.pressed = false
		Input.parse_input_event(ev2)
	times.sort()
	var n := times.size()
	var avg := 0.0
	for t in times:
		avg += t
	avg /= maxf(n, 1)
	var dsum := 0.0
	for d in draws:
		dsum += d
	var res := {"scenario": sc.name, "frames": n, "avg_ms": snappedf(avg, 0.01), "fps_avg": snappedf(1000.0 / maxf(avg, 0.001), 0.1),
		"p95_ms": snappedf(times[int(n * 0.95)], 0.01), "max_ms": snappedf(times[n - 1], 0.01),
		"draw_calls_avg": snappedf(dsum / maxf(draws.size(), 1), 0.1),
		"texture_mem_mb": snappedf(Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED) / 1048576.0, 0.1),
		"nodes": Performance.get_monitor(Performance.OBJECT_NODE_COUNT)}
	print("PERF ", JSON.stringify(res))
	results.append(res)
	w.queue_free()
	await get_tree().create_timer(0.3).timeout
