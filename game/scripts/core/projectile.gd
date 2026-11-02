class_name Projectile
extends Node2D
## Thrown weapons, bottles, bricks, fish, crates, tires (and Lou's lobbed crates).
## Ground position + z like actors. Lands as a pickup when it should be recoverable.

var room: Node
var owner_actor: Actor
var team := 0
var weapon_id := ""
var kind := "spin"
var raw := 10.0
var durability := 1
var vx := 0.0
var vy := 0.0
var z := 0.0
var vz := 0.0
var half_w := 7.0
var depth_r := 4.0
var hit: Dictionary = {}
var life := 0
var lob := false
var rolling := false
var done := false
var spr: Sprite2D
var shadow: Sprite2D
var knockdown := false

func setup(r: Node, owner_a: Actor, id: String, from: Vector2, hz: float, dir: int, dur: int, power: float) -> void:
	room = r
	owner_actor = owner_a
	team = owner_a.team if owner_a else Actor.TEAM_NEUTRAL
	weapon_id = id
	var w: Dictionary = Content.weapon(id)
	kind = w.get("throw", "spin")
	knockdown = w.get("knockdown", false)
	durability = dur
	raw = power
	position = from
	z = hz
	vx = dir * (260.0 if not w.get("carry", false) else 230.0)
	vz = 60.0
	if kind == "roll":
		vz = 0.0
		z = maxf(hz - 30.0, 0.0)
		vx = dir * 210.0
	shadow = Sprite2D.new()
	shadow.texture = Actor._shadow_tex()
	shadow.scale = Vector2(0.6, 0.6)
	add_child(shadow)
	spr = Sprite2D.new()
	spr.texture = SpriteLib.weapon(id)
	spr.flip_h = dir < 0
	add_child(spr)

func setup_lob(r: Node, owner_a: Actor, id: String, from: Vector2, hz: float, to: Vector2, power: float) -> void:
	setup(r, owner_a, id, from, hz, 1, 1, power)
	lob = true
	var t := 0.95
	vx = (to.x - from.x) / t
	vy = (to.y - from.y) / t
	vz = 0.5 * 900.0 * t - hz / t
	kind = "break"

func tick() -> void:
	if done:
		return
	life += 1
	position.x += vx * Actor.DT
	position.y += vy * Actor.DT
	if kind == "roll" and z <= 0.0:
		z = 0.0
		spr.rotation += signf(vx) * 0.25
	else:
		vz -= 900.0 * Actor.DT * (0.55 if not lob else 1.0)
		z += vz * Actor.DT
		if kind == "spin":
			spr.rotation += signf(vx) * 0.45
	position.y = clampf(position.y, room.walk_top, room.walk_bot)
	spr.position = Vector2(0, -z - 4)
	shadow.position = Vector2(0, 0)
	if not lob or z < 16.0:
		_check_hits()
	if done:
		return
	var out: bool = position.x < -20 or position.x > room.width + 20
	if kind == "roll" and (room.point_blocked(position, 6.0) or position.x < 4 or position.x > room.width - 4):
		_land()
		return
	if z <= 0.0 and kind != "roll":
		z = 0.0
		_land()
		return
	if out or life > 400:
		finish()

func _check_hits() -> void:
	for t in room.actors:
		if t.team == team or t.team == Actor.TEAM_NEUTRAL or not t.is_hittable():
			continue
		var key: int = t.get_instance_id()
		if hit.has(key):
			continue
		if absf(t.position.x - position.x) > t.half_w + half_w:
			continue
		if absf(t.position.y - position.y) > 10.0 + t.depth_r + (12.0 if lob else 0.0):
			continue
		if z > t.z + t.cur_height() + 4 or z + 8 < t.z:
			continue
		hit[key] = true
		# Quick Hands: guarding player catches incoming objects
		if t is Player and t.state == "guard" and GameState.has_skill("retrieve") and t.held == "" and signf(position.x - t.position.x) == float(t.facing) and not Content.weapon(weapon_id).get("carry", false):
			t.equip_weapon(weapon_id, durability)
			room.float_text(t.position + Vector2(0, -60), "Caught!", Color(0.5, 1, 1))
			finish()
			return
		var d := {"power": raw, "kb": 160 if knockdown else 90, "launch": 140, "hitstun": 26, "knockdown": knockdown, "depth": 10,
			"sfx": "weapon_hit_blunt", "fx": "hit_heavy" if knockdown else "hit_spark", "hitstop": 5, "shake": 1, "dizzy": 12}
		var attacker: Actor = owner_actor if owner_actor and is_instance_valid(owner_actor) else room.hazard_actor
		var res: String = t.receive_hit(attacker, d, raw, 1 if vx > 0 else -1)
		if res == "miss":
			continue
		match kind:
			"break":
				_break()
				return
			"roll":
				pass
			"bounce":
				vx = -vx * 0.25
				vz = 140.0
			_:
				vx = -vx * 0.2
				vz = 100.0
		if kind != "roll" and kind != "break":
			return
	# breakable props
	for p in room.props:
		if not p.breakable or p.broken:
			continue
		if absf(p.position.x - position.x) < p.half_w + 6 and absf(p.position.y - p.depth_r - position.y) < p.depth_r + 8 and z < 30:
			p.break_open()
			if kind == "break":
				_break()
			else:
				vx = -vx * 0.2
			return

func _land() -> void:
	match kind:
		"break":
			_break()
		_:
			if durability > 0:
				room.spawn_weapon_pickup(weapon_id, room.clamp_ground(position), durability, 0.0)
			finish()

func _break() -> void:
	var w: Dictionary = Content.weapon(weapon_id)
	Audio.sfx(w.get("break_sfx", "bottle_break"))
	room.spawn_debris(w.get("break_fx", "debris_glass"), Vector2(position.x, position.y - z))
	if lob:
		room.shake(2)
		# area damage on landing for lobbed crates
		for t in room.actors:
			if t.team != team and t.team != Actor.TEAM_NEUTRAL and t.is_hittable() and not hit.has(t.get_instance_id()):
				if absf(t.position.x - position.x) < 22 and absf(t.position.y - position.y) < 14:
					var d := {"power": raw, "kb": 150, "launch": 150, "hitstun": 26, "knockdown": true, "depth": 14, "sfx": "crate_break", "fx": "hit_heavy", "hitstop": 5}
					var attacker: Actor = owner_actor if owner_actor and is_instance_valid(owner_actor) else room.hazard_actor
					t.receive_hit(attacker, d, raw, 1 if t.position.x > position.x else -1)
	finish()

func finish() -> void:
	done = true
	room.remove_projectile(self)
