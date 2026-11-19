extends Node
## Performance harness: per scenario, room load time and a frame-time distribution (wall clock), plus where the
## frame goes (simulation script, per-frame script, everything else = engine + rendering + present), draw calls,
## texture memory and node counts.
##
## Run WITH a display and WITHOUT --fixed-fps, e.g. from game/:
##   xvfb-run -a -s "-screen 0 1280x720x24" godot --resolution 1280x720 res://tests/perf.tscn
## Environment:
##   PERF_SECONDS=8        sample duration per scenario (seconds, wall clock)
##   PERF_WARMUP=1.0       settle time after the scenario is set up, before sampling
##   PERF_ONLY=a,b         run only scenarios whose name contains one of these substrings
##   PERF_EFFECTS=full|reduced   Settings.effects for the run (default: full)
##   PERF_POSTFX=on|off    Settings.post_fx for the run (default: on)
##   PERF_DISABLE=a,b      switch systems off for profiling (names: scripts/core/perf_debug.gd)
##   PERF_SEED=1988        RNG seed applied at the start of every scenario
##   PERF_LABEL=text       free-text label stored in the output
##   PERF_OUT=/path.json   JSON output (default user://perf.json)
##   PERF_PAIRED=a,b|all   paired A/B profiling: after the normal sample, switch each named system off and on in
##                         alternating short windows inside the same run (on-off, off-on, ...) and report the mean
##                         difference. Slow drift of a shared machine cancels out, which the between-run
##                         comparison cannot do. PERF_PAIR_WINDOW=0.6 (seconds per window), PERF_PAIRS=6.
## The saved user settings are not read or written: the harness sets effects/post_fx explicitly.
##
## The output always names the renderer. A software rasteriser (llvmpipe, SwiftShader) is NOT representative of
## a GPU: use those numbers for relative comparisons on the same machine only.

const SCENARIOS := [
	{"name": "kettle_quiet", "room": "oq_kettle", "spawn": "west", "mode": "walk",
		"about": "Kettle Street, no enemies, player walks (camera scrolls)"},
	{"name": "kettle_combat8", "room": "oq_kettle", "spawn": "west", "mode": "fight",
		"enemies": ["dogs_brawler", "dogs_flanker", "dogs_heavy", "dogs_thrower", "dogs_weapon", "dogs_blocker", "dogs_brawler", "dogs_flanker"],
		"about": "Kettle Street, 8 enemies, player attacks continuously"},
	{"name": "pumpstation_rain", "room": "fr_pumpstation", "spawn": "west", "mode": "fight",
		"enemies": ["grays_brawler", "grays_heavy", "grays_flanker"],
		"about": "Pump Station Road at night in the rain, 3 enemies"},
	{"name": "marquee_neon", "room": "nm_marquee", "spawn": "west", "mode": "walk",
		"about": "Marquee Strip (neon night, 9 animated signs), player walks"},
	{"name": "vault_kowal_dark", "room": "ul_vault", "spawn": "west", "mode": "fight", "boss": "kowal", "boss_hp": 0.5,
		"about": "Kowal phase 2: darkness + lantern follow light + 2 summoned Moles"},
	{"name": "interior_diner", "room": "int_diner", "spawn": "south", "mode": "idle",
		"about": "Lucky Spoon Diner interior, idle"},
	{"name": "boss_rook", "room": "rw_floor", "spawn": "west", "mode": "fight", "boss": "rook",
		"about": "Rook's Floor, boss phase 1"},
]
const FLAGS := "intro_done,intro_seen,met_mara,duke_intro_seen,rook_intro_seen,kowal_intro_seen"
const THRESHOLDS := [[16.7, "over_16_7"], [20.0, "over_20"], [33.4, "over_33_4"]]

var seconds := 8.0
var warmup := 1.0
var paired: PackedStringArray = []
var pair_window := 0.6
var pairs := 6
var base_disabled := ""
var rng_seed := 1988
var results: Array = []
var meta: Dictionary = {}

# scripted input, driven from the physics tick so every run plays the same script
var _room: Room
var _room_name := ""
var _mode := ""
var _tick := 0
var _walk_dir := 1
var _held: Dictionary = {}
# script-time probes
var _phys_t0 := 0
var _proc_t0 := 0
var _phys_usec := 0
var _phys_ticks := 0
var _proc_usec := 0

class Probe extends Node:
	var h: Node
	var first := false
	func _physics_process(_d: float) -> void:
		h._probe(first, true)
	func _process(_d: float) -> void:
		h._probe(first, false)

func _probe(first: bool, physics: bool) -> void:
	var now := Time.get_ticks_usec()
	if physics:
		if first:
			_phys_t0 = now
		else:
			_phys_usec += now - _phys_t0
			_phys_ticks += 1
	elif first:
		_proc_t0 = now
	else:
		_proc_usec += now - _proc_t0

func _env(k: String, d: String) -> String:
	var v := OS.get_environment(k)
	return v if v != "" else d

func _ready() -> void:
	Audio.unlocked = true
	seconds = maxf(0.5, float(_env("PERF_SECONDS", "8")))
	warmup = maxf(0.0, float(_env("PERF_WARMUP", "1.0")))
	rng_seed = int(_env("PERF_SEED", "1988"))
	Settings.effects = "reduced" if _env("PERF_EFFECTS", "full") == "reduced" else "full"
	Settings.post_fx = _env("PERF_POSTFX", "on") != "off"
	Settings.show_fps = false
	Settings.flash = 1.0
	Settings.screen_shake = 1.0
	Settings.cinematic_bars = true
	base_disabled = OS.get_environment("PERF_DISABLE")
	PerfDebug.set_from(base_disabled)
	paired = OS.get_environment("PERF_PAIRED").split(",", false)
	pair_window = maxf(0.2, float(_env("PERF_PAIR_WINDOW", "0.6")))
	pairs = maxi(1, int(_env("PERF_PAIRS", "6")))
	# uncapped: measure the frame, not the display's refresh
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	for first in [true, false]:
		var p := Probe.new()
		p.h = self
		p.first = first
		p.process_priority = -1000000 if first else 1000000
		p.process_physics_priority = -1000000 if first else 1000000
		add_child(p)
	await get_tree().process_frame   # the root is still adding children during _ready
	meta = _collect_meta()
	print("PERF_META ", JSON.stringify(meta))
	var only := OS.get_environment("PERF_ONLY").split(",", false)
	for sc in SCENARIOS:
		var want := only.is_empty()
		for o in only:
			if str(sc.name).contains(o):
				want = true
		if want:
			await _run(sc)
	meta["loadavg_end"] = _loadavg()
	var out := _env("PERF_OUT", "user://perf.json")
	var f := FileAccess.open(out, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify({"meta": meta, "scenarios": results}, "  "))
		f.close()
	_print_table()
	print("PERF DONE ", out)
	get_tree().quit()

func _loadavg() -> String:
	var f := FileAccess.open("/proc/loadavg", FileAccess.READ)   # Linux only; empty elsewhere
	return f.get_line().strip_edges() if f else ""

## CPU accounting from /proc (Linux only): [system busy jiffies, system steal jiffies, own user, own sys].
## Lets a run on a shared machine say whether something else was competing for the CPU during the sample.
func _cpu_snapshot() -> Array:
	var f := FileAccess.open("/proc/stat", FileAccess.READ)
	var g := FileAccess.open("/proc/self/stat", FileAccess.READ)
	if f == null or g == null:
		return []
	var a := f.get_line().split(" ", false)
	var s := g.get_line()
	var b := s.substr(s.rfind(")") + 2).split(" ", false)
	if a.size() < 9 or b.size() < 13:
		return []
	var busy := int(a[1]) + int(a[2]) + int(a[3]) + int(a[6]) + int(a[7])
	return [busy, int(a[8]), int(b[11]), int(b[12])]

func _cpu_delta(a: Array, b: Array, secs: float) -> Dictionary:
	if a.is_empty() or b.is_empty() or secs <= 0.0:
		return {}
	# jiffies are 1/100 s on Linux: the values below are "% of one core", averaged over the sample
	var own := float((b[2] - a[2]) + (b[3] - a[3]))
	return {"cpu_self_pct": snappedf(own / secs, 0.1), "cpu_self_sys_pct": snappedf(float(b[3] - a[3]) / secs, 0.1),
		"cpu_other_pct": snappedf((float(b[0] - a[0]) - own) / secs, 0.1), "cpu_steal_pct": snappedf(float(b[1] - a[1]) / secs, 0.1)}

func _collect_meta() -> Dictionary:
	var adapter := RenderingServer.get_video_adapter_name()
	var soft := false
	for k in ["llvmpipe", "softpipe", "swiftshader", "software", "lavapipe"]:
		if adapter.to_lower().contains(k):
			soft = true
	var win := DisplayServer.window_get_size()
	var vp := get_viewport().get_visible_rect().size
	return {
		"label": OS.get_environment("PERF_LABEL"),
		"game_version": str(ProjectSettings.get_setting("application/config/version", "")),
		"engine": Engine.get_version_info().string,
		"debug_build": OS.is_debug_build(),
		"os": "%s %s" % [OS.get_name(), OS.get_version()],
		"os_distribution": OS.get_distribution_name(),
		"cpu": OS.get_processor_name(),
		"cpu_threads": OS.get_processor_count(),
		"display_server": DisplayServer.get_name(),
		"rendering_method": RenderingServer.get_current_rendering_method(),
		"rendering_driver": RenderingServer.get_current_rendering_driver_name(),
		"adapter": adapter,
		"adapter_vendor": RenderingServer.get_video_adapter_vendor(),
		"adapter_api": RenderingServer.get_video_adapter_api_version(),
		"software_renderer": soft,
		"window_px": [win.x, win.y],
		"viewport_units": [vp.x, vp.y],
		"stretch": "%s/%s" % [ProjectSettings.get_setting("display/window/stretch/mode"), ProjectSettings.get_setting("display/window/stretch/aspect")],
		"vsync": "disabled" if DisplayServer.window_get_vsync_mode() == DisplayServer.VSYNC_DISABLED else "enabled",
		"physics_tps": Engine.physics_ticks_per_second,
		"effects": Settings.effects,
		"post_fx": Settings.post_fx,
		"disabled": ",".join(PackedStringArray(PerfDebug.disabled.keys())),
		"sample_seconds": seconds,
		"warmup_seconds": warmup,
		"seed": rng_seed,
		"time_utc": Time.get_datetime_string_from_system(true),
		"loadavg_start": _loadavg(),
	}

# ---------------------------------------------------------------- scripted input
func _act(a: String, on: bool) -> void:
	if _held.get(a, false) == on:
		return
	_held[a] = on
	var ev := InputEventAction.new()
	ev.action = a
	ev.pressed = on
	ev.strength = 1.0 if on else 0.0
	Input.parse_input_event(ev)

func _release_all() -> void:
	for a in _held.keys():
		_act(a, false)

func _physics_process(_d: float) -> void:
	if _room == null or not is_instance_valid(_room) or _room.player == null:
		return
	_tick += 1
	var p: Player = _room.player
	match _mode:
		"walk":
			# ping-pong inside the room so the camera keeps scrolling and no exit is ever touched
			if p.position.x > _room.width - 260.0:
				_walk_dir = -1
			elif p.position.x < 260.0:
				_walk_dir = 1
			_act("move_right", _walk_dir > 0)
			_act("move_left", _walk_dir < 0)
		"fight":
			# jab, jab, jab, kick ... a new press every 20 ticks
			var ph := _tick % 20
			var a := "kick" if (_tick / 20) % 4 == 3 else "punch"
			if ph == 0:
				_act(a, true)
			elif ph == 3:
				_act("punch", false)
				_act("kick", false)

## Keeps the scene's load constant for the whole sample: nobody is allowed to die.
func _sustain(r: Room, boss: Node) -> void:
	var p: Player = r.player
	if p and p.hp < p.max_hp * 0.5:
		p.hp = p.max_hp
		GameState.hp = p.max_hp
	for a in r.actors:
		if a is Enemy and not a.dead:
			if a == boss:
				if a.hp < a.max_hp * 0.2:
					a.hp = int(a.max_hp * 0.4)
			elif a.hp < a.max_hp * 0.35:
				a.hp = int(a.max_hp * 0.7)
	if PerfDebug.off("actor_shader"):
		for a in r.actors:
			if a.get("body") != null and a.body and a.body.material != null:
				a.body.material = null
				a.weapon_spr.material = null

func _count_nodes(n: Node) -> int:
	var c := 1
	for ch in n.get_children():
		c += _count_nodes(ch)
	return c

# ---------------------------------------------------------------- one scenario
func _run(sc: Dictionary) -> void:
	seed(rng_seed)
	GameState.reset_new_game()
	for fl in FLAGS.split(","):
		GameState.set_flag(fl)
	GameState.room = sc.room
	GameState.spawn = sc.spawn
	_mode = ""
	_room = null
	_room_name = str(sc.name)
	# ---- load: room build (script + resource loading) and the first frame (texture upload, shader compile)
	var t_load := Time.get_ticks_usec()
	var w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child(w)            # World._ready builds the room synchronously
	var t_built := Time.get_ticks_usec()
	await RenderingServer.frame_post_draw   # first frame with the room on screen
	var t_first := Time.get_ticks_usec()
	var guard := 0
	while (w.room == null or w.room.player == null) and guard < 300:
		await get_tree().process_frame
		guard += 1
	var r: Room = w.room
	r.enc = {}                              # no waves, story events or boss triggers: only what this scenario spawns
	await get_tree().create_timer(0.4).timeout
	r.player.position = Vector2(clampf(r.width * 0.4, 200, r.width - 200), 290)
	var boss: Node = null
	var enemies: Array = sc.get("enemies", [])
	for i in enemies.size():
		r.spawn_enemy(enemies[i], r.player.position + Vector2(60 + (i % 4) * 30, -30 + (i / 4) * 40), {})
	if sc.has("boss"):
		boss = r.spawn_enemy(sc.boss, r.player.position + Vector2(110, 0), {})
		r.boss_actors = [boss]
		r.boss_active = true
		w.boss_bar([boss])
		if sc.has("boss_hp"):
			boss.hp = int(boss.max_hp * float(sc.boss_hp))
	if PerfDebug.off("rain") and r.rain:
		r.rain.visible = false
		r.rain.set_physics_process(false)
	if PerfDebug.off("hud"):
		w.ui_layer.visible = false
	_room = r
	_tick = 0
	_walk_dir = 1
	_mode = str(sc.get("mode", "idle"))
	# ---- settle (and for Kowal: wait until the lights are actually out)
	var t_w := Time.get_ticks_usec()
	while float(Time.get_ticks_usec() - t_w) / 1e6 < warmup:
		await get_tree().process_frame
		_sustain(r, boss)
	if sc.get("boss", "") == "kowal":
		var t_k := Time.get_ticks_usec()
		while r.vis.darkness > 0.46 and float(Time.get_ticks_usec() - t_k) / 1e6 < 8.0:
			await get_tree().process_frame
			_sustain(r, boss)
	# ---- sample
	var times := PackedFloat32Array()
	var draws := 0.0
	var draws_max := 0.0
	var objs := 0.0
	var prims := 0.0
	var enemies_start: int = r.enemies_alive()
	_phys_usec = 0
	_phys_ticks = 0
	_proc_usec = 0
	var cpu0 := _cpu_snapshot()
	var t0 := Time.get_ticks_usec()
	var last := t0
	while float(Time.get_ticks_usec() - t0) / 1e6 < seconds:
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		times.append(float(now - last) / 1000.0)
		last = now
		var dc := Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		draws += dc
		draws_max = maxf(draws_max, dc)
		objs += Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME)
		prims += Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME)
		_sustain(r, boss)
	var elapsed := float(last - t0) / 1e6
	var cpu := _cpu_delta(cpu0, _cpu_snapshot(), elapsed)
	var phys_usec := _phys_usec
	var phys_ticks := _phys_ticks
	var proc_usec := _proc_usec
	var follow := 0
	for G in r.vis.glows:
		if G.has("follow"):
			follow += 1
	var res := _stats(times)
	var n: int = res.frames
	var sim_ms := float(phys_usec) / 1000.0 / maxf(n, 1)
	var proc_ms := float(proc_usec) / 1000.0 / maxf(n, 1)
	res.merge({
		"scenario": sc.name, "room": sc.room, "about": sc.get("about", ""),
		"effects": Settings.effects, "post_fx": Settings.post_fx,
		"disabled": ",".join(PackedStringArray(PerfDebug.disabled.keys())),
		"sample_s": snappedf(elapsed, 0.01),
		"load_build_ms": snappedf(float(t_built - t_load) / 1000.0, 0.1),
		"load_first_frame_ms": snappedf(float(t_first - t_built) / 1000.0, 0.1),
		"load_total_ms": snappedf(float(t_first - t_load) / 1000.0, 0.1),
		"sim_ms_per_frame": snappedf(sim_ms, 0.01),
		"sim_ms_per_tick": snappedf(float(phys_usec) / 1000.0 / maxf(phys_ticks, 1), 0.001),
		"ticks_per_frame": snappedf(float(phys_ticks) / maxf(n, 1), 0.01),
		"process_ms_per_frame": snappedf(proc_ms, 0.01),
		"other_ms_per_frame": snappedf(float(res.avg_ms) - sim_ms - proc_ms, 0.01),
		"draw_calls_avg": snappedf(draws / maxf(n, 1), 0.1),
		"draw_calls_max": draws_max,
		"objects_avg": snappedf(objs / maxf(n, 1), 0.1),
		"primitives_avg": snappedf(prims / maxf(n, 1), 0.1),
		"nodes_total": Performance.get_monitor(Performance.OBJECT_NODE_COUNT),
		"nodes_room": _count_nodes(r),
		"actors": r.actors.size(),
		"enemies_start": enemies_start,
		"enemies_end": r.enemies_alive(),
		"darkness": snappedf(r.vis.darkness, 0.01),
		"follow_lights": follow,
		"texture_mem_mb": snappedf(Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED) / 1048576.0, 0.1),
		"video_mem_mb": snappedf(Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED) / 1048576.0, 0.1),
	})
	res.merge(cpu)
	if not paired.is_empty():
		res["paired"] = await _run_paired(w, r, boss)
	_mode = ""
	_release_all()
	# ---- transition: reload the same room inside the running world (a door/edge transition without the fade)
	var t_r := Time.get_ticks_usec()
	_room = null
	w._load_room(sc.room, sc.spawn)
	await RenderingServer.frame_post_draw
	res["reload_ms"] = snappedf(float(Time.get_ticks_usec() - t_r) / 1000.0, 0.1)
	print("PERF ", JSON.stringify(res))
	results.append(res)
	w.queue_free()
	await get_tree().create_timer(0.3).timeout

# ---------------------------------------------------------------- paired A/B profiling
## Rebuilds the grade/bloom pass with the baseline switches plus `extra` (or without `minus`).
func _regrade(r: Room, extra: String, minus: String = "") -> void:
	var life: RoomLife = r.vis.life
	if life.grade_layer and is_instance_valid(life.grade_layer):
		life.shaders_t.erase(life.grade_rect.material)
		life.grade_layer.free()
		life.grade_rect = null
		life.bloom_group = null
		life.bloom_down = null
	var keep := PerfDebug.disabled.duplicate()
	PerfDebug.set_from(base_disabled + "," + extra)
	if minus != "":
		PerfDebug.disabled.erase(minus)
	if not PerfDebug.off("grade"):
		life._make_grade(life.meta.grade)
		(life.grade_rect.material as ShaderMaterial).set_shader_parameter("t", life.t)
	PerfDebug.disabled = keep

func _show(nodes: Array, on: bool) -> void:
	for n in nodes:
		if is_instance_valid(n):
			n.visible = on

## system name -> Callable(on: bool), only for systems this room actually has.
func _toggles(w: Node, r: Room) -> Dictionary:
	var t := {}
	var vis: RoomVisuals = r.vis
	var life: RoomLife = vis.life
	if life.meta.has("grade") and Settings.post_fx and Settings.effects_full():
		t["grade"] = func(on: bool): _regrade(r, "" if on else "grade")
		t["bloom"] = func(on: bool): _regrade(r, "" if on else "bloom")
		# "on" = the current bloom, "off" = the 1.3.0-rc1 reference pass, whatever the baseline is
		t["fast_bloom"] = func(on: bool): _regrade(r, "" if on else "fast_bloom", "fast_bloom" if on else "")
	var hazed := []
	var par := []
	var base := []
	for L in vis.layers:
		(base if str(L.name) == "base" else par).append(L.node)
		for s in (L.node as Node).get_children():
			if s is Sprite2D and s.material is ShaderMaterial:
				hazed.append([s, s.material])
	if not hazed.is_empty():
		t["haze"] = func(on: bool):
			for h in hazed:
				h[0].material = h[1] if on else null
	if not par.is_empty():
		t["parallax"] = func(on: bool): _show(par, on)
	if not base.is_empty():
		t["base_layer"] = func(on: bool): _show(base, on)
	if not vis.fg.is_empty():
		t["fg"] = func(on: bool): r.fg_root.visible = on
	if not vis.glows.is_empty():
		var gl := vis.glows.map(func(G): return G.spr)
		t["glows"] = func(on: bool): _show(gl, on)
	if not vis.ambient_nodes.is_empty():
		t["ambient"] = func(on: bool): _show(vis.ambient_nodes, on)
	if vis.light_img != null:
		var img := vis.light_img
		t["lightmap"] = func(on: bool): vis.light_img = img if on else null
	t["rim"] = func(on: bool): vis._rim_off = not on
	if not vis.cast_shadow.is_empty():
		var cs := vis.cast_shadow
		t["cast"] = func(on: bool): vis.cast_shadow = cs if on else {}
	if not vis.reflects.is_empty():
		var rf := vis.reflects
		t["reflect"] = func(on: bool): vis.reflects = rf if on else []
	var life_all := []
	var clouds := []
	var lanes := []
	for L in life.lanes:
		(clouds if L.kind == "clouds" else lanes).append(L.node)
	var groups := {"clouds": clouds, "lanes": lanes, "windows": life.windows.map(func(W): return W.root),
		"sway": life.sways.map(func(S): return S.spr), "shafts": life.shafts.map(func(S): return S.spr),
		"signs": [life.sign_root] if life.sign_root else [], "pigeons": [], "water": []}
	for F in life.pigeons:
		for B in F.birds:
			groups.pigeons.append(B.spr)
	var water_shader := RoomLife._shader(RoomLife.WATER_SHADER)
	for c in life.base_front.get_children():
		if c is ColorRect and c.material is ShaderMaterial and (c.material as ShaderMaterial).shader == water_shader:
			groups.water.append(c)
	for k in groups:
		var nodes: Array = groups[k]
		if nodes.is_empty():
			continue
		life_all.append_array(nodes)
		t[k] = func(on: bool): _show(nodes, on)
	if not life_all.is_empty():
		t["life"] = func(on: bool): _show(life_all, on)
	if r.rain:
		t["rain"] = func(on: bool):
			r.rain.visible = on
			r.rain.set_physics_process(on)
	t["actor_shader"] = func(on: bool):
		for a in r.actors:
			if a.get("body") != null and a.body:
				a.body.material = a.mat if on else null
				a.weapon_spr.material = a.mat if on else null
	t["actors_props"] = func(on: bool): r.world_node.visible = on
	if _mode == "fight":
		t["combat_fx"] = func(on: bool):
			if on:
				PerfDebug.disabled.erase("combat_fx")
			else:
				PerfDebug.disabled["combat_fx"] = true
	t["hud"] = func(on: bool): w.ui_layer.visible = on
	return t

## [avg frame ms, frames, avg draw calls] over one window, after letting the switch take effect.
func _window(r: Room, boss: Node) -> Array:
	for i in 3:
		await get_tree().process_frame
		_sustain(r, boss)
	var t0 := Time.get_ticks_usec()
	var n := 0
	var dc := 0.0
	while float(Time.get_ticks_usec() - t0) / 1e6 < pair_window:
		await get_tree().process_frame
		n += 1
		dc += Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME)
		_sustain(r, boss)
	return [float(Time.get_ticks_usec() - t0) / 1000.0 / maxi(n, 1), n, dc / maxi(n, 1)]

func _run_paired(w: Node, r: Room, boss: Node) -> Dictionary:
	var out := {}
	var tog := _toggles(w, r)
	var names: Array = tog.keys() if "all" in paired else Array(paired)
	for sys in names:
		if not tog.has(sys):
			continue
		var f: Callable = tog[sys]
		var diffs: Array = []
		var on_ms := 0.0
		var off_ms := 0.0
		var on_dc := 0.0
		var off_dc := 0.0
		for k in pairs:
			var a := [0.0, 0, 0.0]
			var b := [0.0, 0, 0.0]
			for on in ([true, false] if k % 2 == 0 else [false, true]):
				f.call(on)
				var m: Array = await _window(r, boss)
				if on:
					a = m
				else:
					b = m
			diffs.append(float(a[0]) - float(b[0]))
			on_ms += float(a[0])
			off_ms += float(b[0])
			on_dc += float(a[2])
			off_dc += float(b[2])
		f.call(true)
		diffs.sort()
		var mean := 0.0
		for d in diffs:
			mean += d
		mean /= diffs.size()
		var sd := 0.0
		for d in diffs:
			sd += (d - mean) * (d - mean)
		sd = sqrt(sd / maxi(diffs.size() - 1, 1))
		out[sys] = {"saved_ms": snappedf(mean, 0.01), "median_ms": snappedf(diffs[diffs.size() / 2], 0.01),
			"sem_ms": snappedf(sd / sqrt(diffs.size()), 0.01), "pairs": diffs.size(),
			"on_ms": snappedf(on_ms / pairs, 0.01), "off_ms": snappedf(off_ms / pairs, 0.01),
			"on_draw_calls": snappedf(on_dc / pairs, 0.1), "off_draw_calls": snappedf(off_dc / pairs, 0.1)}
		print("PAIRED %-18s %-14s on %6.2f  off %6.2f  saved %6.2f +/- %.2f ms  (draw calls %.0f -> %.0f)" % [_room_name, sys,
			out[sys].on_ms, out[sys].off_ms, out[sys].saved_ms, out[sys].sem_ms, out[sys].on_draw_calls, out[sys].off_draw_calls])
	return out

func _stats(times: PackedFloat32Array) -> Dictionary:
	var s := times.duplicate()
	s.sort()
	var n := s.size()
	if n == 0:
		return {"frames": 0, "avg_ms": 0.0}
	var sum := 0.0
	for t in s:
		sum += t
	var avg := sum / n
	var p50: float = s[mini(n - 1, int(n * 0.50))]
	var res := {"frames": n, "avg_ms": snappedf(avg, 0.01), "fps_avg": snappedf(1000.0 / maxf(avg, 0.001), 0.1),
		"min_ms": snappedf(s[0], 0.01), "p50_ms": snappedf(p50, 0.01),
		"p90_ms": snappedf(s[mini(n - 1, int(n * 0.90))], 0.01), "p95_ms": snappedf(s[mini(n - 1, int(n * 0.95))], 0.01),
		"p99_ms": snappedf(s[mini(n - 1, int(n * 0.99))], 0.01), "max_ms": snappedf(s[n - 1], 0.01)}
	for th in THRESHOLDS:
		var c := 0
		for t in s:
			if t > float(th[0]):
				c += 1
		var key: String = th[1]
		res[key] = c
		res[key + "_pct"] = snappedf(100.0 * c / n, 0.1)
	# a spike is a hitch relative to this scenario's own typical frame: more than twice its median
	var spikes := 0
	for t in s:
		if t > p50 * 2.0:
			spikes += 1
	res["spikes"] = spikes
	res["spike_threshold_ms"] = snappedf(p50 * 2.0, 0.01)
	return res

func _print_table() -> void:
	print("")
	print("Renderer: %s | %s %s | %s | window %dx%d | effects=%s post_fx=%s disabled=[%s]%s" % [meta.adapter, meta.rendering_method,
		meta.adapter_api, meta.os, meta.window_px[0], meta.window_px[1], meta.effects, str(meta.post_fx), meta.disabled,
		"  ** SOFTWARE RENDERER: not GPU numbers **" if meta.software_renderer else ""])
	print("%-18s %6s %6s %6s %6s %6s %6s %6s %7s %7s %7s %6s %6s %6s %6s %6s %7s %7s" % ["scenario", "frames", "avg", "p50", "p90", "p95", "p99",
		"max", ">16.7%", ">20%", ">33.4%", "spikes", "sim", "proc", "other", "draws", "load", "reload"])
	for r in results:
		print("%-18s %6d %6.1f %6.1f %6.1f %6.1f %6.1f %6.1f %7.1f %7.1f %7.1f %6d %6.2f %6.2f %6.1f %6.1f %7.0f %7.0f" % [r.scenario, r.frames,
			r.avg_ms, r.p50_ms, r.p90_ms, r.p95_ms, r.p99_ms, r.max_ms, r.over_16_7_pct, r.over_20_pct, r.over_33_4_pct, r.spikes,
			r.sim_ms_per_frame, r.process_ms_per_frame, r.other_ms_per_frame, r.draw_calls_avg, r.load_total_ms, r.reload_ms])
	print("(ms; sim = _physics_process script per rendered frame, proc = _process script, other = engine + rendering + present)")
