class_name Room
extends Node2D
## One street segment or interior. Builds itself from data/rooms.json + data/encounters.json,
## owns the fixed-tick simulation (hit-stop, shake), collision, camera, waves and transitions.

const VIEW_H := 360.0

var world: Node
var room_id := ""
var data: Dictionary = {}
var enc: Dictionary = {}
var district := ""
var tier := 1
var width := 640.0
var walk_top := 218.0
var walk_bot := 344.0
var interior := false
var blockers: Array = []          # Array[Rect2] on the ground plane

var actors: Array = []
var props: Array = []
var pickups: Array = []
var projectiles: Array = []
var npcs: Array = []
var player: Player
var hazard_actor: Actor

var bg_root: Node2D
var parallax: Sprite2D
var world_node: Node2D
var fx_root: Node2D
var overlay: Node2D
var camera: Camera2D
var cam_x := 320.0
var shake_amt := 0.0
var hitstop := 0
var tokens: Array = []
var cutscene := false
var exits_locked := false
var lock_reason := ""
var ticks := 0
var spawn_point := Vector2.ZERO
var waves_done: Dictionary = {}
var wave_alive: Dictionary = {}
var wave_queue: Array = []        # pending spawns: [time, enemy_def, wave_id, from]
var active_waves: Dictionary = {}
var boss_actors: Array = []
var boss_active := false
var boss_cfg: Dictionary = {}
var transition_cd := 30
var rain: Node2D
var edge_msg_cd := 0
var max_alive := 6

# ---------------------------------------------------------------- build
func build(id: String, spawn: String, w: Node) -> void:
	world = w
	room_id = id
	data = Content.room(id)
	enc = Content.encounters.get(id, {})
	district = data.get("district", "old_quarter")
	tier = Content.tier_for_district(district)
	width = float(data.get("width", 640))
	var wk: Array = data.get("walk", [218, 344])
	walk_top = float(wk[0])
	walk_bot = float(wk[1])
	interior = data.get("kind", "exterior") == "interior"
	max_alive = 5 if Settings.difficulty == "relaxed" else 6
	for b in data.get("blockers", []):
		blockers.append(Rect2(float(b.x), float(b.y), float(b.w), float(b.h)))
	_build_visuals()
	hazard_actor = Actor.new()
	hazard_actor.team = Actor.TEAM_NEUTRAL
	hazard_actor.position = Vector2(-999, -999)
	add_child(hazard_actor)
	hazard_actor.visible = false
	_build_props()
	_build_pickups()
	_build_npcs()
	player = Player.new()
	player.room = self
	player.setup_visual("nico")
	player.refresh_stats()
	spawn_point = spawn_position(spawn)
	player.position = spawn_point
	player.facing = _spawn_facing(spawn)
	add_actor(player)
	if not interior:
		_restore_cleared_waves()
	cam_x = _target_cam_x()
	_update_camera(true)

func _build_visuals() -> void:
	bg_root = Node2D.new()
	bg_root.z_index = -20
	add_child(bg_root)
	if not interior:
		var ptex := SpriteLib.tex("res://assets/bg/parallax_%s.png" % district)
		if ptex == null:
			ptex = _placeholder_parallax()
		parallax = Sprite2D.new()
		parallax.texture = ptex
		parallax.centered = false
		parallax.region_enabled = true
		parallax.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
		bg_root.add_child(parallax)
	var btex := SpriteLib.tex("res://assets/bg/%s.png" % room_id)
	var bg := Sprite2D.new()
	bg.texture = btex if btex else _placeholder_bg()
	bg.centered = false
	bg_root.add_child(bg)
	world_node = Node2D.new()
	world_node.y_sort_enabled = true
	add_child(world_node)
	fx_root = Node2D.new()
	fx_root.z_index = 50
	add_child(fx_root)
	overlay = Node2D.new()
	overlay.z_index = 80
	add_child(overlay)
	camera = Camera2D.new()
	camera.anchor_mode = Camera2D.ANCHOR_MODE_DRAG_CENTER
	add_child(camera)
	camera.make_current()
	if data.get("weather", "") == "rain":
		rain = RainLayer.new()
		rain.room = self
		overlay.add_child(rain)

func _placeholder_bg() -> Texture2D:
	var img := Image.create(int(width), 360, false, Image.FORMAT_RGBA8)
	var wall := Color(0.55, 0.28, 0.22) if not interior else Color(0.45, 0.35, 0.3)
	var top := int(walk_top) - 4
	img.fill_rect(Rect2i(0, 0, int(width), top), wall)
	img.fill_rect(Rect2i(0, top, int(width), 360 - top), Color(0.3, 0.3, 0.36))
	img.fill_rect(Rect2i(0, top, int(width), 30), Color(0.55, 0.52, 0.48))
	for b in blockers:
		img.fill_rect(Rect2i(int(b.position.x), int(b.position.y), int(b.size.x), int(b.size.y)), Color(0.2, 0.4, 0.6))
	for d in data.get("doors", []):
		img.fill_rect(Rect2i(int(d.x) - 15, top - 50, 30, 50), Color(0.95, 0.8, 0.4))
	return ImageTexture.create_from_image(img)

func _placeholder_parallax() -> Texture2D:
	var img := Image.create(960, 220, false, Image.FORMAT_RGBA8)
	img.fill(Color(0.85, 0.55, 0.4))
	return ImageTexture.create_from_image(img)

func _build_props() -> void:
	var contents: Dictionary = enc.get("prop_contents", {})
	var list: Array = data.get("props", [])
	for i in list.size():
		var p: Dictionary = list[i]
		var c: Dictionary = {}
		var spec = contents.get(str(i), {})
		if typeof(spec) == TYPE_DICTIONARY:
			if spec.has("requires") and not GameState.check(spec.requires):
				spec = {}
			c = spec.duplicate()
			c.erase("requires")
		if c.is_empty() and p.type in ["crate", "barrel", "fish_crate"] and not interior:
			if (hash(room_id + str(i)) % 3) == 0:
				c = {"cash": 2 + (hash(room_id) % 3) * tier}
			elif (hash(room_id + str(i)) % 5) == 1:
				c = {"heal": 20}
		var prop := Prop.new()
		world_node.add_child(prop)
		prop.setup(self, p.type, Vector2(float(p.x), float(p.y)), i, c)
		props.append(prop)

func _build_pickups() -> void:
	for p in enc.get("pickups", []):
		if p.has("requires") and not GameState.check(p.requires):
			continue
		var key := "%s:pk:%s" % [room_id, p.get("id", str(p.get("x", 0)))]
		if p.has("key"):
			if GameState.is_collected(key):
				continue
			spawn_key(p.key, Vector2(p.x, p.y), key)
		elif p.has("weapon"):
			spawn_weapon_pickup(p.weapon, Vector2(p.x, p.y), -1, 0.0)

func _build_npcs() -> void:
	for n in enc.get("npcs", []):
		if n.has("requires") and not GameState.check(n.requires):
			continue
		if n.has("hide_if") and GameState.check(n.hide_if):
			continue
		spawn_npc(n.id, n.get("sprite", n.id), Vector2(float(n.x), float(n.y)), n)

# ---------------------------------------------------------------- spawn helpers
func spawn_position(spawn: String) -> Vector2:
	var mid := (walk_top + walk_bot) * 0.5
	if spawn == "west":
		return Vector2(28, mid + 10)
	if spawn == "east":
		return Vector2(width - 28, mid + 10)
	if spawn == "south":
		var ex: Dictionary = data.get("exits", {}).get("south", {})
		return Vector2((float(ex.get("x0", 40)) + float(ex.get("x1", 120))) * 0.5, walk_bot - 14)
	if spawn.begins_with("door:"):
		var did := spawn.substr(5)
		for d in data.get("doors", []):
			if d.id == did:
				return Vector2(float(d.x), walk_top + 10)
	if spawn.begins_with("x:"):
		return Vector2(float(spawn.substr(2)), mid)
	return Vector2(60, mid)

func _spawn_facing(spawn: String) -> int:
	if spawn == "east":
		return -1
	return 1

func add_actor(a: Actor) -> void:
	a.room = self
	world_node.add_child(a)
	actors.append(a)

func remove_actor(a: Actor) -> void:
	actors.erase(a)
	tokens.erase(a)
	if is_instance_valid(a):
		a.queue_free()

func spawn_enemy(id: String, pos: Vector2, opts: Dictionary = {}) -> Enemy:
	var e: Enemy
	if Content.enemies.get("bosses", {}).has(id):
		var b := Boss.new()
		b.room = self
		b.setup_boss(id)
		e = b
	else:
		e = Enemy.new()
		e.room = self
		e.setup_enemy(id, tier, opts)
	if opts.has("name"):
		e.named = opts.name
		e.display_name = opts.name
	if opts.has("drops"):
		e.drops = opts.drops
	if opts.has("ally"):
		e.ally = opts.ally
		e.team = Actor.TEAM_PLAYER if opts.ally else Actor.TEAM_ENEMY
	e.wave_id = opts.get("wave", e.wave_id)
	e.position = pos
	e.facing = -1 if pos.x > (player.position.x if player else 0.0) else 1
	add_actor(e)
	return e

func spawn_npc(id: String, sprite: String, pos: Vector2, opts: Dictionary = {}) -> NPC:
	var n := NPC.new()
	n.room = self
	n.setup_npc(id, sprite, pos, opts)
	add_actor(n)
	npcs.append(n)
	return n

func find_npc(id: String) -> NPC:
	for n in npcs:
		if is_instance_valid(n) and n.npc_id == id:
			return n
	return null

func remove_npc(n: NPC) -> void:
	npcs.erase(n)
	remove_actor(n)

func spawn_weapon_pickup(id: String, pos: Vector2, dur: int, pop: float) -> Pickup:
	var p := Pickup.new()
	p.weapon_id = id
	var w := Content.weapon(id)
	p.durability = dur if dur > 0 else int(w.get("durability", 10))
	world_node.add_child(p)
	p.setup(self, "weapon", clamp_ground(pos), pop)
	pickups.append(p)
	return p

func spawn_cash(amount: int, pos: Vector2) -> void:
	if amount <= 0:
		return
	var parts := [amount]
	if amount >= 12:
		parts = [int(amount / 2), amount - int(amount / 2)]
	for a in parts:
		var p := Pickup.new()
		p.amount = a
		world_node.add_child(p)
		p.setup(self, "cash", clamp_ground(pos + Vector2(randf_range(-6, 6), randf_range(-3, 3))), 8.0)
		p.vx = randf_range(-50, 50)
		pickups.append(p)

func spawn_heal(amount: int, pos: Vector2) -> void:
	var p := Pickup.new()
	p.amount = amount
	world_node.add_child(p)
	p.setup(self, "heal", clamp_ground(pos), 8.0)
	pickups.append(p)

func spawn_key(id: String, pos: Vector2, persist: String = "") -> void:
	var p := Pickup.new()
	p.key_id = id
	p.persist_key = persist
	world_node.add_child(p)
	p.setup(self, "key", clamp_ground(pos), 10.0)
	pickups.append(p)

func remove_pickup(p: Pickup) -> void:
	pickups.erase(p)
	p.queue_free()

func remove_prop(p: Prop) -> void:
	props.erase(p)
	p.queue_free()

func spawn_projectile(owner_a: Actor, id: String, from: Vector2, hz: float, dir: int, dur: int) -> void:
	var pr := Projectile.new()
	world_node.add_child(pr)
	var power: float = owner_a.projectile_raw(id) if owner_a.has_method("projectile_raw") else 8.0
	pr.setup(self, owner_a, id, clamp_ground(from), hz, dir, dur, power)
	projectiles.append(pr)

func spawn_lob(owner_a: Actor, id: String, to: Vector2) -> void:
	var pr := Projectile.new()
	world_node.add_child(pr)
	var power: float = owner_a.projectile_raw(id) * 1.3 if owner_a.has_method("projectile_raw") else 12.0
	pr.setup_lob(self, owner_a, id, owner_a.position, 40.0, clamp_ground(to), power)
	projectiles.append(pr)
	spawn_fx("target_shadow", clamp_ground(to), 0.0, null, 57)

func remove_projectile(p: Projectile) -> void:
	projectiles.erase(p)
	p.queue_free()

func drop_hazard_crate(at: Vector2) -> void:
	var target := clamp_ground(at + Vector2(randf_range(-10, 10), randf_range(-6, 6)))
	spawn_fx("target_shadow", target, 0.0, null, 70)
	Audio.sfx("crate_fall", -4.0)
	var tw := create_tween()
	tw.tween_interval(70.0 / 60.0)
	tw.tween_callback(func():
		if not is_inside_tree():
			return
		shake(3)
		Audio.sfx("crate_break")
		spawn_debris("debris_wood", target + Vector2(0, -10))
		for t in actors.duplicate():
			if t.team == Actor.TEAM_NEUTRAL or not t.is_hittable():
				continue
			if absf(t.position.x - target.x) < 22 and absf(t.position.y - target.y) < 14:
				var d := {"power": 0.0, "kb": 140, "launch": 160, "knockdown": true, "hitstun": 30, "sfx": "crate_break", "fx": "hit_heavy", "hitstop": 6}
				var dmg := maxf(8.0, float(t.max_hp) * (0.08 if t.is_boss else 0.14))
				t.receive_hit(hazard_actor, d, dmg / t.defense_factor(), 1 if t.position.x > target.x else -1)
		# leaves a liftable crate behind (throw it at Rook!)
		var prop := Prop.new()
		world_node.add_child(prop)
		prop.setup(self, "crate", target, 900 + randi() % 1000, {})
		props.append(prop))

# ---------------------------------------------------------------- effects
func spawn_fx(id: String, pos: Vector2, zz: float, attach: Node2D = null, life: int = -1) -> void:
	var f := FX.make_strip(id)
	if life >= 0:
		f.life = life
	if attach and is_instance_valid(attach) and attach is Actor:
		attach.visual.add_child(f)
		f.position = pos
		f.scale.x = 1.0 / attach.visual.scale.x if attach.visual.scale.x != 0 else 1.0
	else:
		fx_root.add_child(f)
		f.position = pos - Vector2(0, zz)
		if id in ["shockwave", "dust", "land_dust", "target_shadow", "splash"]:
			f.z_index = -15 if id in ["target_shadow"] else 0
			if id == "target_shadow":
				f.reparent(bg_root)
				f.z_index = 5

func spawn_debris(id: String, pos: Vector2) -> void:
	for i in 5:
		var f := FX.make_strip(id)
		f.frame_ticks = 99
		if f.frames > 1:
			f.spr.frame = i % f.frames
		f.life = 34
		f.fade = true
		f.vel = Vector2(randf_range(-90, 90), randf_range(-160, -60))
		f.grav = 520.0
		f.position = pos
		fx_root.add_child(f)

func float_text(pos: Vector2, text: String, col: Color = Color.WHITE) -> void:
	var f := FX.new()
	f.life = 50
	f.fade = true
	f.vel = Vector2(0, -26)
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", col)
	l.add_theme_color_override("font_outline_color", Color(0.1, 0.07, 0.12))
	l.add_theme_constant_override("outline_size", 4)
	l.position = Vector2(-80, -8)
	l.size = Vector2(160, 12)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	f.add_child(l)
	f.position = pos
	fx_root.add_child(f)

func do_hitstop(n: int) -> void:
	hitstop = maxi(hitstop, n)

func shake(n: int) -> void:
	shake_amt = maxf(shake_amt, float(n) * Settings.screen_shake)

# ---------------------------------------------------------------- simulation
func _physics_process(_delta: float) -> void:
	ticks += 1
	if player:
		player.poll_input()
	_update_camera(false)
	if world and world.is_sim_paused():
		for a in actors:
			a._update_visual()
		return
	if transition_cd > 0:
		transition_cd -= 1
	if edge_msg_cd > 0:
		edge_msg_cd -= 1
	if hitstop > 0:
		hitstop -= 1
		return
	_clean_tokens()
	for a in actors.duplicate():
		if is_instance_valid(a) and a.get_parent():
			if cutscene and a != player and not a.get_meta("cutscene_active", false):
				a.frozen = true
			elif a.frozen and not cutscene and not a.get_meta("scripted_freeze", false):
				a.frozen = false
			a.tick()
	for p in projectiles.duplicate():
		p.tick()
	for p in pickups.duplicate():
		p.tick()
	if not cutscene:
		_update_waves()
		_check_exits()
	if parallax:
		var vw := view_width()
		parallax.position = Vector2(cam_left(), 0)
		parallax.region_rect = Rect2(cam_left() * 0.25, 0, vw, parallax.texture.get_height())

func view_width() -> float:
	return get_viewport_rect().size.x

func cam_left() -> float:
	return cam_x - view_width() * 0.5

func cam_right() -> float:
	return cam_x + view_width() * 0.5

func on_screen(a: Node2D, margin: float) -> bool:
	return a.position.x >= cam_left() + margin and a.position.x <= cam_right() - margin

func _target_cam_x() -> float:
	var vw := view_width()
	if width <= vw:
		return width * 0.5
	var tx := player.position.x + player.facing * 24.0 if player else vw * 0.5
	return clampf(tx, vw * 0.5, width - vw * 0.5)

var cam_focus := -1.0
func _update_camera(snap: bool) -> void:
	var target := _target_cam_x() if cam_focus < 0.0 else clampf(cam_focus, view_width() * 0.5, maxf(width - view_width() * 0.5, view_width() * 0.5))
	if width <= view_width():
		target = width * 0.5
	if snap:
		cam_x = target
	else:
		cam_x = lerpf(cam_x, target, 0.12)
		if absf(cam_x - target) < 0.3:
			cam_x = target
	var off := Vector2.ZERO
	if shake_amt > 0.05:
		off = Vector2(randf_range(-shake_amt, shake_amt), randf_range(-shake_amt, shake_amt) * 0.6)
		shake_amt *= 0.82
	else:
		shake_amt = 0.0
	camera.position = Vector2(round(cam_x + off.x), round(VIEW_H * 0.5 + off.y))

# ---------------------------------------------------------------- collision
func move_actor(a: Actor, d: Vector2) -> Vector2:
	var p := a.position
	var hw := a.half_w * 0.7
	var left := 6.0 + hw
	var right := width - 6.0 - hw
	var nx := p.x + d.x
	if a == player and not exits_locked:
		left = -12.0
		right = width + 12.0
	if a is Enemy and (a as Enemy).entering:
		left = -80.0
		right = width + 80.0
	nx = clampf(nx, left, right)
	if a.state != "thrown" and _blocked_box(nx, p.y, hw, a):
		nx = p.x
	var ny := clampf(p.y + d.y, walk_top, walk_bot)
	if a.state != "thrown" and _blocked_box(nx, ny, hw, a):
		ny = p.y
	return Vector2(nx, ny)

func _blocked_box(x: float, y: float, hw: float, _a: Actor) -> bool:
	var box := Rect2(x - hw, y - 2.0, hw * 2.0, 4.0)
	for b in blockers:
		if box.intersects(b):
			return true
	for pr in props:
		if pr.is_solid() and box.intersects(pr.ground_rect()):
			return true
	return false

func point_blocked(p: Vector2, hw: float) -> bool:
	return _blocked_box(p.x, p.y, hw, null)

func clamp_ground(p: Vector2) -> Vector2:
	var q := Vector2(clampf(p.x, 12.0, width - 12.0), clampf(p.y, walk_top + 2.0, walk_bot - 2.0))
	if _blocked_box(q.x, q.y, 6.0, null):
		# nudge to the nearest free spot so dropped items never land inside geometry
		for r in [8, 16, 24, 36, 48, 64]:
			for dir in [Vector2(0, 1), Vector2(0, -1), Vector2(1, 0), Vector2(-1, 0), Vector2(1, 1), Vector2(-1, 1)]:
				var c: Vector2 = q + dir * r
				c.x = clampf(c.x, 12.0, width - 12.0)
				c.y = clampf(c.y, walk_top + 2.0, walk_bot - 2.0)
				if not _blocked_box(c.x, c.y, 6.0, null):
					return c
	return q

# ---------------------------------------------------------------- combat queries
func hittables_for(a: Actor) -> Array:
	var out: Array = []
	for t in actors:
		if t == a or t.team == a.team or t.team == Actor.TEAM_NEUTRAL:
			continue
		if t.is_hittable():
			out.append(t)
	if a.team == Actor.TEAM_PLAYER:
		for p in props:
			if p.breakable and not p.broken:
				out.append(p)
	return out

func pick_target(e: Actor) -> Actor:
	var best: Actor = null
	var best_d := INF
	for t in actors:
		if t.team == e.team or t.team == Actor.TEAM_NEUTRAL or t.dead or t.state == "carried":
			continue
		var d := absf(t.position.x - e.position.x) + absf(t.position.y - e.position.y) * 1.5
		if t is NPC and (t as NPC).escort:
			d *= 1.4
		if t != player and e.team == Actor.TEAM_ENEMY and not (t is NPC):
			d *= 1.2
		if d < best_d:
			best_d = d
			best = t
	return best

func notify_attack(attacker: Actor) -> void:
	for t in actors:
		if t is Enemy and t.team != attacker.team and not t.dead:
			t.notice_attack(attacker)

func request_token(e: Enemy) -> bool:
	var cap := 1 if Settings.difficulty == "relaxed" else 2
	if boss_active:
		cap = 1
	if tokens.size() < cap:
		tokens.append(e)
		return true
	return false

func release_token(e: Enemy) -> void:
	tokens.erase(e)

func _clean_tokens() -> void:
	for t in tokens.duplicate():
		if not is_instance_valid(t) or t.dead or not actors.has(t):
			tokens.erase(t)

func count_team_near(a: Actor, r: float) -> int:
	var n := 0
	for t in actors:
		if t != a and t.team == a.team and not t.dead and absf(t.position.x - a.position.x) < r:
			n += 1
	return n

func enemies_alive() -> int:
	var n := 0
	for t in actors:
		if t is Enemy and t.team == Actor.TEAM_ENEMY and not t.dead:
			n += 1
	return n

func combat_active() -> bool:
	return enemies_alive() > 0

# ---------------------------------------------------------------- waves & bosses
func _restore_cleared_waves() -> void:
	for wv in enc.get("waves", []):
		if not GameState.wave_available(room_id, wv.id, wv.get("respawn", false)):
			waves_done[wv.id] = true

func _update_waves() -> void:
	# pending spawns (staggered so reinforcements are readable)
	if not wave_queue.is_empty():
		var alive := enemies_alive()
		var next: Array = wave_queue[0]
		if ticks >= int(next[0]) and alive < max_alive:
			wave_queue.pop_front()
			_spawn_wave_enemy(next[1], next[2], next[3])
	if ticks < 70 or player == null:
		return
	if player.position.distance_to(spawn_point) < 50 and ticks < 300:
		return
	for wv in enc.get("waves", []):
		var wid: String = wv.id
		if waves_done.has(wid) or active_waves.has(wid):
			continue
		if wv.has("requires") and not GameState.check(wv.requires):
			continue
		if wv.has("hide_if") and GameState.check(wv.hide_if):
			continue
		var at := float(wv.get("at", 0))
		var trig := player.position.x >= at if not wv.get("from_east", false) else player.position.x <= at
		if not trig:
			continue
		_start_wave(wv)
	var bcfg: Dictionary = enc.get("boss", {})
	if not bcfg.is_empty() and not boss_active and not GameState.has_flag("boss_" + bcfg.id):
		if (not bcfg.has("requires") or GameState.check(bcfg.requires)) and player.position.x >= float(bcfg.get("at", 0)) and enemies_alive() == 0:
			boss_active = true
			Story.start_boss(self, bcfg)

func _start_wave(wv: Dictionary) -> void:
	active_waves[wv.id] = true
	wave_alive[wv.id] = 0
	if wv.get("lock", false):
		lock_exits(true, wv.get("lock_text", "Not until this fight is over!"))
	var from: String = wv.get("from", "auto")
	var delay := 0
	var list: Array = []
	for e in wv.get("enemies", []):
		if typeof(e) == TYPE_ARRAY:
			for i in int(e[1]):
				list.append({"id": e[0]})
		else:
			list.append(e)
	for i in list.size():
		var f := from
		if from == "auto":
			f = "right" if player.position.x < width - 200 else "left"
			if i % 3 == 2 and player.position.x > 220:
				f = "left"
		elif from == "both":
			f = "right" if i % 2 == 0 else "left"
		wave_queue.append([ticks + delay, list[i], wv.id, f])
		wave_alive[wv.id] = int(wave_alive[wv.id]) + 1
		delay += 28
	if wv.has("say"):
		world.toast(wv.say)

func _spawn_wave_enemy(def: Dictionary, wid: String, from: String) -> void:
	var y := randf_range(walk_top + 6, walk_bot - 6)
	var x: float
	var entering := true
	if from == "left":
		x = cam_left() - 24.0
		if x < 10.0:
			x = 10.0
	else:
		x = cam_right() + 24.0
		if x > width - 10.0:
			x = width - 10.0
	if from == "back":
		x = clampf(player.position.x + randf_range(-140, 140), 20, width - 20)
		y = walk_top + 2
		entering = false
	var opts := def.duplicate()
	opts["wave"] = wid
	var e := spawn_enemy(def.id, clamp_ground(Vector2(x, y)) if not entering else Vector2(x, y), opts)
	e.entering = entering and not on_screen(e, 20)
	e.leash = true
	if def.has("hp_mult"):
		e.max_hp = int(e.max_hp * float(def.hp_mult))
		e.hp = e.max_hp

func lock_exits(on: bool, reason: String = "") -> void:
	exits_locked = on
	lock_reason = reason

func on_enemy_defeated(e: Enemy) -> void:
	if e.counted or e.ally:
		return
	e.counted = true
	GameState.stats.defeated = int(GameState.stats.get("defeated", 0)) + 1
	var gained := GameState.add_xp(e.xp_reward)
	float_text(e.position + Vector2(0, -50), "+%d XP" % e.xp_reward, Color(0.29, 0.94, 0.94))
	if gained > 0 and world:
		world.on_level_up()
	var cash := randi_range(int(e.cash_range[0]), int(e.cash_range[1]))
	if cash > 0:
		spawn_cash(cash, e.position)
	for d in e.drops:
		if d.has("key"):
			spawn_key(d.key, e.position, d.get("persist", ""))
		elif d.has("weapon"):
			spawn_weapon_pickup(d.weapon, e.position, -1, 10.0)
		elif d.has("heal"):
			spawn_heal(int(d.heal), e.position)
	if e.wave_id != "" and wave_alive.has(e.wave_id):
		wave_alive[e.wave_id] = int(wave_alive[e.wave_id]) - 1
		if int(wave_alive[e.wave_id]) <= 0:
			_wave_complete(e.wave_id)
	if e.is_boss:
		_check_boss_done()
	Story.on_enemy_defeated(self, e)

func _wave_complete(wid: String) -> void:
	waves_done[wid] = true
	active_waves.erase(wid)
	var wv := _wave_def(wid)
	GameState.wave_cleared(room_id, wid)
	if wv.get("lock", false):
		lock_exits(false)
		world.toast("The way is clear.")
	if wv.has("on_clear"):
		Story.on_wave_clear(self, wid)

func _wave_def(wid: String) -> Dictionary:
	for wv in enc.get("waves", []):
		if wv.id == wid:
			return wv
	return {}

func _check_boss_done() -> void:
	for b in boss_actors:
		if is_instance_valid(b) and not b.dead and actors.has(b):
			return
	if boss_active and not boss_actors.is_empty():
		boss_active = false
		var ids: Array = []
		for b in boss_actors:
			if is_instance_valid(b):
				ids.append(b.boss_id)
		boss_actors.clear()
		for t in actors.duplicate():
			if t is Enemy and not t.is_boss and not t.ally and not t.dead and t.team == Actor.TEAM_ENEMY:
				t.hp = 0
				t.take_damage_and_react(hazard_actor, {"knockdown": true, "kb": 100, "launch": 120}, 0.0, 1 if t.position.x > player.position.x else -1)
		lock_exits(false)
		world.boss_bar(null)
		Story.boss_defeated(self, boss_cfg, ids)

func begin_boss_fight(cfg: Dictionary, bosses: Array) -> void:
	boss_cfg = cfg
	boss_actors = bosses
	boss_active = true
	lock_exits(true, cfg.get("lock_text", "No running now!"))
	world.boss_bar(bosses)

func boss_summon(b: Boss, ids: Array, line: String) -> void:
	world.bark(b, line)
	var side := 1
	for id in ids:
		var x := cam_right() + 20 if side > 0 else cam_left() - 20
		var e := spawn_enemy(id, Vector2(clampf(x, 10, width - 10), randf_range(walk_top + 10, walk_bot - 10)), {})
		e.entering = true
		e.leash = true
		side = -side

func boss_retreat(b: Boss) -> void:
	Story.boss_retreat(self, b)

func rook_phase_two(b: Boss) -> void:
	Story.rook_phase_two(self, b)

func escort_down(n: NPC) -> void:
	Story.escort_down(self, n)

func on_player_damaged(_d: int) -> void:
	pass

func on_player_defeated() -> void:
	if world:
		world.on_player_defeated()

# ---------------------------------------------------------------- exits, doors, context
func _check_exits() -> void:
	if transition_cd > 0 or player == null or player.dead or not player.control_enabled:
		return
	var ex: Dictionary = data.get("exits", {})
	var p := player.position
	var side := ""
	if p.x < 2.0 and player.vel.x < -1.0:
		side = "west"
	elif p.x > width - 2.0 and player.vel.x > 1.0:
		side = "east"
	elif p.y >= walk_bot - 0.5 and player.move_input.y > 0.5 and ex.has("south"):
		var s: Dictionary = ex.south
		if p.x >= float(s.x0) and p.x <= float(s.x1):
			side = "south"
	if side == "":
		return
	if not ex.has(side):
		player.position.x = clampf(p.x, 8, width - 8)
		return
	var e: Dictionary = ex[side]
	if exits_locked:
		_bounce_back(lock_reason if lock_reason != "" else "You can't leave yet!")
		return
	if e.has("requires") and not GameState.check(e.requires):
		_bounce_back(e.get("locked_text", "The way is blocked."))
		return
	transition_cd = 60
	world.change_room(e.to, e.spawn)

func _bounce_back(msg: String) -> void:
	player.position.x = clampf(player.position.x, 10, width - 10)
	if player.position.y >= walk_bot - 0.5:
		player.position.y = walk_bot - 3
	player.vel = Vector2.ZERO
	if edge_msg_cd <= 0:
		edge_msg_cd = 90
		world.toast(msg)

func door_at(a: Actor) -> Dictionary:
	if a.position.y > walk_top + 16:
		return {}
	for d in data.get("doors", []):
		if absf(a.position.x - float(d.x)) <= 16:
			return d
	return {}

func try_door(d: Dictionary) -> void:
	if transition_cd > 0 or d.is_empty():
		return
	if exits_locked:
		_bounce_back(lock_reason)
		return
	if d.has("requires") and not GameState.check(d.requires):
		if edge_msg_cd <= 0:
			edge_msg_cd = 90
			world.toast(d.get("locked_text", "It's locked."))
		return
	transition_cd = 60
	Audio.sfx("door")
	world.change_room(d.to, d.get("spawn", "south"))

func find_context(p: Player) -> Dictionary:
	var best: Dictionary = {}
	var best_d := INF
	for n in npcs:
		if not is_instance_valid(n) or not n.talkable or n.dead:
			continue
		var dx := absf(n.position.x - p.position.x)
		var dy := absf(n.position.y - p.position.y)
		var reach_y := 30.0 if n.mode == "behind_counter" else 16.0
		if dx < 36 and dy < reach_y and dx + dy < best_d:
			best_d = dx + dy
			best = {"type": "npc", "node": n, "label": n.context_label()}
	if not best.is_empty():
		return best
	var d := door_at(p)
	if not d.is_empty():
		return {"type": "door", "door": d, "label": "Enter " + d.get("label", "")}
	for pr in props:
		if pr.type == "bus_stop" and absf(pr.position.x - p.position.x) < 26 and absf(pr.position.y - p.position.y) < 20:
			return {"type": "npc", "node": pr, "label": "Bus Stop"}
	for pk in pickups:
		if pk.kind != "weapon" or pk.collected or pk.z > 6:
			continue
		var dd: float = absf(pk.position.x - p.position.x) + absf(pk.position.y - p.position.y) * 1.5
		if absf(pk.position.x - p.position.x) < 22 and absf(pk.position.y - p.position.y) < 12 and dd < best_d:
			best_d = dd
			best = {"type": "pickup", "node": pk, "label": pk.label()}
	if not best.is_empty():
		return best
	for pr in props:
		if not pr.liftable or pr.broken:
			continue
		if absf(pr.position.x - p.position.x) < pr.half_w + 14 and p.position.y - pr.position.y > -6 and p.position.y - pr.position.y < 16:
			return {"type": "prop", "node": pr, "label": pr.label()}
	for e in actors:
		if e is Enemy and e.liftable and not e.dead and (e.state == "dizzy" or e.lying) and not e.is_boss:
			if absf(e.position.x - p.position.x) < 26 and absf(e.position.y - p.position.y) < 12:
				return {"type": "enemy", "node": e}
	return {}

func talk_to(n: Node) -> void:
	if n is Prop and n.type == "bus_stop":
		world.open_bus()
		return
	if n is NPC:
		n.facing = 1 if player.position.x > n.position.x else -1
		player.facing = -n.facing
		Story.talk(self, n)

# ---------------------------------------------------------------- cutscene helpers
func set_cutscene(on: bool) -> void:
	cutscene = on
	if player:
		player.control_enabled = not on
		if on:
			player.vel = Vector2.ZERO
			if player.state in ["walk", "run", "guard"]:
				player.set_state("idle")
		else:
			player.lock_input(8)

func walk_to(a: Actor, target: Vector2, speed: float = 70.0) -> void:
	a.set_meta("cutscene_active", true)
	a.frozen = false
	var guard := 0
	while is_instance_valid(a) and a.position.distance_to(target) > 3.0 and guard < 600:
		var d := (target - a.position).normalized()
		a.vel = Vector2(d.x * speed, d.y * speed * 0.7)
		if absf(d.x) > 0.1:
			a.facing = 1 if d.x > 0 else -1
		if a.state == "idle":
			a.set_state("walk")
		guard += 1
		await get_tree().physics_frame
	if is_instance_valid(a):
		a.vel = Vector2.ZERO
		a.set_state("idle")
		a.set_meta("cutscene_active", false)
		if a != player and cutscene:
			a.frozen = true

func focus_camera(x: float) -> void:
	cam_focus = x

func release_camera() -> void:
	cam_focus = -1.0
