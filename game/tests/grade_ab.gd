extends Node
## Pixel comparison of the colour grade + bloom pass on a FROZEN frame: the room runs for a moment, the tree is
## paused, and the same frame is drawn with each variant of the pass (the 1.3.0-rc1 reference, the current one,
## and no grade at all). Because nothing else changes between the captures, the PNGs differ only by the pass.
##
## Run with a display, from game/:
##   AB_OUT=/tmp/ab AB_ROOMS=oq_kettle@640,nm_marquee@700 xvfb-run -a -s "-screen 0 1280x720x24" \
##       godot --resolution 1280x720 res://tests/grade_ab.tscn
##   python3 ../tools/perf/grade_diff.py /tmp/ab
## AB_ROOMS    room[@player_x], comma separated (default: a set that covers day, neon, rain, vault, interior)
## AB_VARIANTS ';' separated: legacy | new | nobloom | raw | new:uniform=a,b:uniform=c  (default "legacy;new;nobloom;raw")
##             legacy = the 1.3.0-rc1 pass, new = the current pass, nobloom = grade only, raw = no pass at all
## AB_SETTLE   seconds to run each room before freezing (default 2.5)

const DEFAULT_ROOMS := "oq_kettle@640,oq_kettle@1150,nm_marquee@700,nm_marquee@1300,fr_pumpstation@760,ul_vault@450,int_diner@320"

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.effects = "full"
	Settings.post_fx = true
	Settings.flash = 1.0
	var out := OS.get_environment("AB_OUT")
	if out == "":
		out = "user://grade_ab"
	DirAccess.make_dir_recursive_absolute(out)
	var rooms := OS.get_environment("AB_ROOMS")
	if rooms == "":
		rooms = DEFAULT_ROOMS
	var variants := OS.get_environment("AB_VARIANTS")
	if variants == "":
		variants = "legacy;new;nobloom;raw"
	var settle := float(OS.get_environment("AB_SETTLE")) if OS.get_environment("AB_SETTLE") != "" else 2.5
	await get_tree().process_frame
	for spec in rooms.split(",", false):
		var parts := spec.split("@")
		seed(1988)
		GameState.reset_new_game()
		for fl in "intro_done,intro_seen,met_mara,duke_intro_seen,rook_intro_seen,kowal_intro_seen".split(","):
			GameState.set_flag(fl)
		GameState.room = parts[0]
		GameState.spawn = "south" if parts[0].begins_with("int_") else "west"
		PerfDebug.set_from("")
		var w = load("res://scenes/world.tscn").instantiate()
		get_tree().root.add_child(w)
		await get_tree().create_timer(0.3).timeout
		var r: Room = w.room
		r.enc = {}
		if parts.size() > 1:
			r.player.position = Vector2(float(parts[1]), 290)
		await get_tree().create_timer(settle).timeout
		get_tree().paused = true
		var vi := 0
		for v in variants.split(";", false):
			var vp := v.split(":")
			_rebuild_grade(r, vp[0])
			for k in range(1, vp.size()):
				var kv := vp[k].split("=")
				var nums := kv[1].split(",")
				var val = Vector2(float(nums[0]), float(nums[1])) if nums.size() > 1 else float(nums[0])
				for node in [r.vis.life.grade_rect, r.vis.life.bloom_group, r.vis.life.bloom_down]:
					if node and is_instance_valid(node) and node.material:
						(node.material as ShaderMaterial).set_shader_parameter(kv[0], val)
			for i in 3:
				await RenderingServer.frame_post_draw
			var img := get_viewport().get_texture().get_image()
			var name := "%s/%s__%d_%s.png" % [out, spec.replace("@", "_"), vi, vp[0]]
			img.save_png(name)
			print("ab ", name, " ", v)
			vi += 1
		get_tree().paused = false
		w.queue_free()
		await get_tree().create_timer(0.3).timeout
	print("AB DONE")
	get_tree().quit()

func _rebuild_grade(r: Room, kind: String) -> void:
	var life: RoomLife = r.vis.life
	if life.grade_rect and is_instance_valid(life.grade_rect):
		life.shaders_t.erase(life.grade_rect.material)
		life.grade_layer.free()
		life.grade_rect = null
		life.bloom_group = null
		life.bloom_down = null
	if kind == "raw" or not life.meta.has("grade"):
		return
	PerfDebug.set_from(str({"legacy": "fast_bloom", "nobloom": "bloom"}.get(kind, "")))
	life._make_grade(life.meta.grade)
	(life.grade_rect.material as ShaderMaterial).set_shader_parameter("t", life.t)
	PerfDebug.set_from("")
