class_name Actor
extends Node2D
## Base fighter for the belt-scroller simulation.
## position = GROUND position (x, depth y). Jump height is `z`, applied only to the visual node,
## so sorting, shadows, lane checks and room bounds always use the ground plane.

signal defeated(actor: Actor)
signal damaged(actor: Actor, amount: int)

enum { TEAM_PLAYER, TEAM_ENEMY, TEAM_NEUTRAL }

const GRAVITY := 900.0
const DT := 1.0 / 60.0
const FLASH_SHADER := "shader_type canvas_item;\nuniform vec4 flash_color : source_color = vec4(1.0);\nuniform float flash_amount = 0.0;\nvoid fragment() {\n\tCOLOR.rgb = mix(COLOR.rgb, flash_color.rgb, flash_amount);\n}\n"
static var _shader: Shader

var room: Node                      # Room (untyped to avoid a class cycle)
var char_id := ""
var display_name := ""
var team := TEAM_ENEMY
var max_hp := 40
var hp := 40
var defense := 0.0
var height := 46.0
var half_w := 9.0
var depth_r := 4.0
var walk_speed := 80.0
var run_speed := 160.0
var depth_mult := 0.62
var liftable := true
var is_boss := false
var dizzy_threshold := 60.0
var combo_limit := 5                # hits within a short window before a forced knockdown (anti stun-lock)
var getup_invuln := 24
var lie_time := 44
var kb_scale := 1.0
var armor_light := false            # heavies: light hits do not stagger while attacking

var z := 0.0
var vz := 0.0
var vel := Vector2.ZERO
var facing := 1

var state := "idle"
var state_t := 0
var atk_id := ""
var atk: Dictionary = {}
var atk_t := 0
var atk_hit: Dictionary = {}
var atk_targets := 0
var air_attack_used := false
var hitstun := 0
var invuln := 0
var guard_t := 0
var guard_stun := 0
var dizzy_meter := 0.0
var combo_hits := 0
var combo_timer := 0
var lying := false
var dead := false
var held := ""
var held_dur := 0
var held_max := 0
var carried_actor: Actor = null
var carrier: Actor = null
var carry_t := 0
var thrower: Actor = null
var frozen := false
var scripted_anim := ""
var hurt_low := false
var projectile_spawned := false
var telegraph_t := 0
var last_attacker: Actor = null
var bounced := false

var visual: Node2D
var body: Sprite2D
var weapon_spr: Sprite2D
var shadow: Sprite2D
var sheet: Dictionary
var anim := "idle"
var anim_frame := 0
var anim_t := 0
var flash := 0.0
var flash_color := Color.WHITE
var mat: ShaderMaterial
var fx_marker: Node2D

func setup_visual(id: String) -> void:
	char_id = id
	sheet = SpriteLib.character(id)
	shadow = Sprite2D.new()
	shadow.texture = _shadow_tex()
	shadow.modulate = Color(1, 1, 1, 0.9)
	add_child(shadow)
	visual = Node2D.new()
	add_child(visual)
	body = Sprite2D.new()
	body.texture = sheet.texture
	body.centered = false
	var cell: Vector2i = sheet.cell
	body.hframes = int(sheet.columns)
	body.vframes = maxi(1, int(sheet.texture.get_height() / cell.y)) if sheet.texture else 8
	body.offset = -sheet.anchor
	visual.add_child(body)
	weapon_spr = Sprite2D.new()
	weapon_spr.centered = false
	weapon_spr.visible = false
	visual.add_child(weapon_spr)
	if _shader == null:
		_shader = Shader.new()
		_shader.code = FLASH_SHADER
	mat = ShaderMaterial.new()
	mat.shader = _shader
	body.material = mat
	weapon_spr.material = mat
	fx_marker = Node2D.new()
	fx_marker.position = Vector2(0, -height - 8)
	visual.add_child(fx_marker)

static var _shadow_cache: Texture2D
static func _shadow_tex() -> Texture2D:
	if _shadow_cache:
		return _shadow_cache
	var t := SpriteLib.tex("res://assets/fx/shadow.png")
	if t == null:
		var img := Image.create(24, 8, false, Image.FORMAT_RGBA8)
		for y in 8:
			for x in 24:
				var dx := (x - 11.5) / 12.0
				var dy := (y - 3.5) / 4.0
				var d := dx * dx + dy * dy
				img.set_pixel(x, y, Color(0, 0, 0, clampf(0.45 * (1.0 - d) * 1.6, 0.0, 0.42)))
		t = ImageTexture.create_from_image(img)
	_shadow_cache = t
	return t

# ---------------------------------------------------------------- main tick (called by Room)
func tick() -> void:
	if dead and state == "removed":
		return
	if frozen:
		_update_visual()
		return
	state_t += 1
	if invuln > 0: invuln -= 1
	if combo_timer > 0:
		combo_timer -= 1
		if combo_timer == 0:
			combo_hits = 0
	if dizzy_meter > 0.0 and state != "dizzy":
		dizzy_meter = maxf(0.0, dizzy_meter - 0.35)
	if telegraph_t > 0: telegraph_t -= 1
	think()
	_state_update()
	_physics_step()
	_update_visual()

## Overridden by Player (input) and Enemy (AI).
func think() -> void:
	pass

func set_state(s: String) -> void:
	if state == s:
		return
	_exit_state(state)
	state = s
	state_t = 0
	anim_t = 0
	anim_frame = 0

func _exit_state(old: String) -> void:
	if old == "guard":
		guard_t = 0
	if old == "attack":
		projectile_spawned = false

func can_act() -> bool:
	return not dead and not frozen and state in ["idle", "walk", "run", "carry"]

func is_airborne() -> bool:
	return z > 0.5 or vz > 0.0

func is_hittable() -> bool:
	return not dead and invuln <= 0 and not lying and state not in ["carried", "removed", "getup"]

func cur_height() -> float:
	if lying or state in ["knockdown", "thrown", "carried"]:
		return 14.0
	if state == "dizzy" or (state == "hurt" and hurt_low):
		return height * 0.85
	return height

# ---------------------------------------------------------------- state machine
func _state_update() -> void:
	match state:
		"idle", "walk", "run":
			_locomotion_state()
		"jump":
			_jump_state()
		"attack":
			_attack_state()
		"guard":
			_guard_state()
		"hurt":
			_hurt_state()
		"knockdown":
			_knockdown_state()
		"getup":
			_getup_state()
		"dizzy":
			_dizzy_state()
		"pickup":
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)
			if state_t >= 10:
				set_state("carry" if is_carrying_heavy() else "idle")
		"carry":
			_carry_state()
		"throw":
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)
			if state_t >= 14:
				set_state("idle")
		"carried":
			_carried_state()
		"thrown":
			_thrown_state()
		"dead":
			_dead_state()
		"cutscene", "victory", "talk", "cower":
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)

func _locomotion_state() -> void:
	# subclasses set vel in think(); decide walk/run/idle anim
	if vel.length() < 4.0:
		if state != "idle":
			set_state("idle")
	elif state == "idle":
		set_state("walk")

func _jump_state() -> void:
	if not is_airborne() and state_t > 2:
		_on_land()
		set_state("idle")

func _on_land() -> void:
	z = 0.0
	vz = 0.0
	air_attack_used = false
	if room:
		room.spawn_fx("land_dust", Vector2(position.x, position.y + 1), 0.0)
		Audio.sfx("land", -8.0)

func _attack_state() -> void:
	atk_t += 1
	var s: int = int(atk.get("startup", 4))
	var a: int = int(atk.get("active", 3))
	var r: int = _recovery_ticks()
	var air: bool = atk.get("air", false)
	if atk_t <= s:
		if not air:
			vel = vel.move_toward(Vector2.ZERO, 1200 * DT)
	elif atk_t <= s + a:
		if atk.has("move"):
			vel.x = facing * float(atk.move) * (1.0 - float(atk_t - s) / float(a + 4))
			vel.y = 0.0
		if atk.get("projectile", false):
			if not projectile_spawned:
				projectile_spawned = true
				spawn_projectile()
		else:
			_check_hits()
		if atk_t == s + 1 and atk_targets == 0 and not atk.get("projectile", false):
			Audio.sfx(atk.get("whiff", "whiff"), -6.0, 0.1)
	else:
		if not air:
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)
	if air:
		if not is_airborne() and atk_t > 2:
			_on_land()
			atk_t = maxi(atk_t, s + a)
			if atk_t >= s + a + r or atk_id in ["jump_kick", "jump_punch", "e_jump_kick", "jett_flip"]:
				on_attack_end()
				set_state("idle")
			return
		return
	if atk_t >= s + a + r:
		on_attack_end()
		set_state("carry" if is_carrying_heavy() else "idle")

func _recovery_ticks() -> int:
	return int(atk.get("recovery", 8))

func on_attack_end() -> void:
	pass

func _guard_state() -> void:
	guard_t += 1
	vel = vel.move_toward(Vector2.ZERO, 900 * DT)
	if guard_stun > 0:
		guard_stun -= 1

func _hurt_state() -> void:
	vel = vel.move_toward(Vector2.ZERO, 500 * DT)
	if state_t >= hitstun:
		if dizzy_meter >= dizzy_threshold and not is_boss:
			start_dizzy()
		else:
			set_state("idle")

func _knockdown_state() -> void:
	if is_airborne():
		lying = false
		return
	if not lying:
		if not bounced and absf(vz) > 0.0 and state_t > 2:
			pass
		z = 0.0
		lying = true
		state_t = 0
		vel.x *= 0.35
		Audio.sfx("fall", -2.0)
		if room:
			room.spawn_fx("dust", position + Vector2(0, 1), 0.0)
			room.shake(1)
		if held != "" and not is_boss:
			drop_weapon(true)   # bosses keep their signature weapons
	vel = vel.move_toward(Vector2.ZERO, 600 * DT)
	if hp <= 0:
		_begin_death()
		return
	if state_t >= lie_time:
		lying = false
		set_state("getup")

func _getup_state() -> void:
	vel = Vector2.ZERO
	if state_t >= 18:
		invuln = getup_invuln
		set_state("idle")

func start_dizzy() -> void:
	dizzy_meter = 0.0
	set_state("dizzy")
	if room:
		room.spawn_fx("stars", Vector2(0, -height - 4), 0.0, self, 100)

func _dizzy_state() -> void:
	vel = vel.move_toward(Vector2.ZERO, 600 * DT)
	if state_t >= 100:
		set_state("idle")

func _carry_state() -> void:
	# carrying an enemy overhead or a heavy object; movement handled by subclass think()
	if carried_actor and (not is_instance_valid(carried_actor) or carried_actor.carrier != self):
		carried_actor = null
	if carried_actor == null and not is_carrying_heavy():
		set_state("idle")
		return
	if carried_actor:
		carry_t += 1
		if carry_t > 210:
			# the carried enemy wriggles free
			var c := carried_actor
			release_carried()
			c.position = position + Vector2(-facing * 18, 0)
			c.z = 0.0
			c.set_state("idle")

func _carried_state() -> void:
	if carrier == null or not is_instance_valid(carrier) or carrier.carried_actor != self:
		carrier = null
		set_state("knockdown")
		vz = 60.0
		return
	var hp_pt := carrier.hand_point(true)
	position = Vector2(carrier.position.x + hp_pt.x * carrier.facing, carrier.position.y + 1.0)
	z = carrier.z - hp_pt.y - 6.0
	facing = -carrier.facing
	vel = Vector2.ZERO
	vz = 0.0

func _thrown_state() -> void:
	# flying body: hits the thrower's enemies (this actor's friends), then lands hard
	if room:
		for t in room.actors:
			if t == self or t == thrower or t.team != team or not t.is_hittable():
				continue
			if atk_hit.has(t.get_instance_id()):
				continue
			if absf(t.position.x - position.x) < 18 and absf(t.position.y - position.y) < 14 and z < t.height:
				atk_hit[t.get_instance_id()] = 1
				var d: Dictionary = Content.attack("thrown_body")
				var raw := 14.0
				if thrower and is_instance_valid(thrower):
					raw = thrower.calc_raw(d)
				t.receive_hit(thrower if thrower and is_instance_valid(thrower) else self, d, raw, signf(vel.x))
	if not is_airborne() and state_t > 2:
		var d2: Dictionary = Content.attack("thrown_body")
		var raw2 := 10.0
		if thrower and is_instance_valid(thrower):
			raw2 = thrower.calc_raw(d2) * 0.8
		apply_damage(int(round(raw2 * defense_factor())), thrower)
		set_state("knockdown")
		lying = false
		vz = 0.0
		z = 0.0
		room.shake(2)

func _dead_state() -> void:
	vel = vel.move_toward(Vector2.ZERO, 600 * DT)
	if state_t == 1:
		on_defeated()
	if state_t > 70:
		visible = (state_t / 3) % 2 == 0
	if state_t > 100 and team != TEAM_PLAYER:
		state = "removed"
		visible = false
		if room:
			room.remove_actor(self)

func _begin_death() -> void:
	dead = true
	lying = true
	set_state("dead")

func on_defeated() -> void:
	defeated.emit(self)

# ---------------------------------------------------------------- physics
func _physics_step() -> void:
	if state == "carried":
		return
	if is_airborne() or z > 0.0:
		vz -= GRAVITY * DT
		z += vz * DT
		if z <= 0.0:
			z = 0.0
			if vz < 0.0:
				if state == "knockdown" and not bounced and vz < -260.0:
					bounced = true
					vz = -vz * 0.25
					z = 0.1
				else:
					vz = 0.0
	if state != "knockdown" or not is_airborne():
		bounced = bounced if state == "knockdown" else false
	if vel != Vector2.ZERO and room:
		position = room.move_actor(self, vel * DT)

# ---------------------------------------------------------------- attacking
func start_attack(id: String, def_override: Dictionary = {}) -> bool:
	var d: Dictionary = def_override if not def_override.is_empty() else Content.attack(id)
	if d.is_empty():
		return false
	atk_id = id
	atk = d
	atk_t = 0
	atk_hit.clear()
	atk_targets = 0
	projectile_spawned = false
	if d.get("air", false):
		air_attack_used = true
	set_state("attack")
	if d.get("telegraph", false):
		telegraph_t = int(d.get("startup", 10))
	if room:
		room.notify_attack(self)
	return true

func attack_phase() -> int:
	var s: int = int(atk.get("startup", 4))
	var a: int = int(atk.get("active", 3))
	if atk_t <= s:
		return 0
	if atk_t <= s + a:
		return 1
	return 2

func in_invuln_window() -> bool:
	if state != "attack" or not atk.has("invuln"):
		return false
	var w: Array = atk.invuln
	return atk_t >= int(w[0]) and atk_t <= int(w[1])

func in_armor_window() -> bool:
	if state != "attack":
		return false
	if atk.has("armor"):
		var w: Array = atk.armor
		return atk_t >= int(w[0]) and atk_t <= int(w[1])
	return armor_light and attack_phase() < 2

func attack_x_range() -> Vector2:
	var xr: Array = atk.get("x", [0, 24])
	if facing >= 0:
		return Vector2(position.x + float(xr[0]), position.x + float(xr[1]))
	return Vector2(position.x - float(xr[1]), position.x - float(xr[0]))

func overlaps_target(t: Node2D, d: Dictionary) -> bool:
	var xr := attack_x_range()
	var thw: float = t.get("half_w") if t.get("half_w") != null else 10.0
	if t.position.x + thw < xr.x or t.position.x - thw > xr.y:
		return false
	var dr: float = t.get("depth_r") if t.get("depth_r") != null else 4.0
	if absf(t.position.y - position.y) > float(d.get("depth", 8)) + dr:
		return false
	var zr: Array = d.get("z", [0, 40])
	var a0: float = z + float(zr[0])
	var a1: float = z + float(zr[1])
	var tz: float = t.get("z") if t.get("z") != null else 0.0
	var th: float = t.cur_height() if t.has_method("cur_height") else 24.0
	return a1 >= tz and a0 <= tz + th

func _check_hits() -> void:
	if room == null:
		return
	var hits_max: int = int(atk.get("hits", 1))
	var interval: int = int(atk.get("interval", 0))
	var multi: bool = atk.get("multi", false)
	var cands: Array = room.hittables_for(self)
	cands.sort_custom(func(a, b): return absf(a.position.x - position.x) < absf(b.position.x - position.x))
	for t in cands:
		var key: int = t.get_instance_id()
		if atk_hit.has(key):
			var rec: Dictionary = atk_hit[key]
			if hits_max <= 1 or int(rec.n) >= hits_max or atk_t - int(rec.t) < interval:
				continue
		elif not multi and atk_hit.size() > 0:
			continue
		if not overlaps_target(t, atk):
			continue
		var res: String = t.receive_hit(self, atk, calc_raw(atk), facing)
		if res == "miss":
			continue
		var n := 1
		if atk_hit.has(key):
			n = int(atk_hit[key].n) + 1
		atk_hit[key] = {"t": atk_t, "n": n}
		atk_targets += 1
		on_hit_landed(t, res)

## Raw damage before the target's defense. Overridden by Player/Enemy.
func calc_raw(d: Dictionary) -> float:
	return float(d.get("power", 5))

func on_hit_landed(_target: Node, _res: String) -> void:
	pass

func defense_factor() -> float:
	return 60.0 / (60.0 + defense * 2.5)

func spawn_projectile() -> void:
	pass

# ---------------------------------------------------------------- receiving hits
## Returns "hit", "block", "perfect", "armor" or "miss".
func receive_hit(attacker: Actor, d: Dictionary, raw: float, dir: int) -> String:
	if not is_hittable() or in_invuln_window():
		return "miss"
	last_attacker = attacker
	var from_front := signf(attacker.position.x - position.x) == float(facing) or absf(attacker.position.x - position.x) < 2.0
	var unblockable: bool = d.get("unblockable", false)
	if state == "guard" and from_front and not unblockable and not (d.get("low", false) and team == TEAM_ENEMY and not is_boss):
		if guard_t <= perfect_window():
			on_perfect_guard(attacker)
			return "perfect"
		if d.get("guard_break", false):
			guard_t = 0
			Audio.sfx("guard_break")
			room.spawn_fx("block_spark", hit_point(), 0.0)
			take_damage_and_react(attacker, d, raw * 0.5, dir, true)
			return "hit"
		guard_stun = 10
		vel.x = dir * float(d.get("kb", 60)) * 0.6 * kb_scale
		Audio.sfx("block")
		room.spawn_fx("block_spark", hit_point(), 0.0)
		room.do_hitstop(2)
		on_blocked(attacker)
		return "block"
	if in_armor_window() and not d.get("knockdown", false) and not d.get("guard_break", false):
		var dmg_a := apply_damage(int(round(raw * defense_factor())), attacker)
		flash = 0.8
		flash_color = Color(1, 0.6, 0.4)
		Audio.sfx(d.get("sfx", "punch_light"), -2.0)
		room.spawn_fx("hit_spark", hit_point(), 0.0)
		room.do_hitstop(2)
		damaged.emit(self, dmg_a)
		if hp <= 0:
			take_damage_and_react(attacker, d, 0.0, dir, true)
		return "armor"
	take_damage_and_react(attacker, d, raw, dir, false)
	return "hit"

func perfect_window() -> int:
	return 8

func on_perfect_guard(attacker: Actor) -> void:
	Audio.sfx("perfect_guard")
	room.spawn_fx("perfect_flash", hit_point(), 0.0)
	room.do_hitstop(6)
	if attacker and attacker.state == "attack":
		attacker.set_state("hurt")
		attacker.hitstun = 34
		attacker.vel.x = -attacker.facing * 60.0

func on_blocked(_attacker: Actor) -> void:
	pass

func hit_point() -> Vector2:
	return Vector2(position.x, position.y - z - cur_height() * 0.6)

func take_damage_and_react(attacker: Actor, d: Dictionary, raw: float, dir: int, force_stagger: bool) -> void:
	if carried_actor:
		var c := carried_actor
		release_carried()
		c.set_state("knockdown")
		c.vz = 80.0
	if is_carrying_heavy():
		drop_weapon(true)
	var dmg := int(round(raw * defense_factor() * incoming_mult()))
	if raw > 0.0:
		dmg = maxi(1, dmg)
	dmg = apply_damage(dmg, attacker)
	damaged.emit(self, dmg)
	flash = 1.0
	flash_color = Color.WHITE
	var fx_name: String = d.get("fx", "hit_spark")
	room.spawn_fx(fx_name, hit_point() + Vector2(-dir * 4, 0), 0.0)
	Audio.sfx(d.get("sfx", "punch_light"))
	room.do_hitstop(int(d.get("hitstop", 3)))
	if int(d.get("shake", 0)) > 0:
		room.shake(int(d.shake))
	combo_hits += 1
	combo_timer = 70
	dizzy_meter += float(d.get("dizzy", 8)) * attacker.dizzy_mult()
	var knock: bool = d.get("knockdown", false) or hp <= 0 or combo_hits >= combo_limit or state == "dizzy" or is_airborne()
	if is_boss and not hp <= 0 and not d.get("knockdown", false):
		knock = combo_hits >= combo_limit
	facing = -dir if dir != 0 else facing
	if knock:
		combo_hits = 0
		dizzy_meter *= 0.5 if state != "dizzy" else 0.0
		set_state("knockdown")
		lying = false
		bounced = false
		vel = Vector2(dir * maxf(float(d.get("kb", 120)), 120.0) * kb_scale, 0)
		vz = maxf(float(d.get("launch", 130)), 110.0) * (0.8 if is_boss else 1.0)
		z = maxf(z, 0.5)
	else:
		set_state("hurt")
		hurt_low = randf() < 0.4
		hitstun = int(d.get("hitstun", 18))
		if force_stagger:
			hitstun = maxi(hitstun, 28)
		vel = Vector2(dir * float(d.get("kb", 60)) * kb_scale, 0)

func incoming_mult() -> float:
	return 1.0

func dizzy_mult() -> float:
	return 1.0

func apply_damage(dmg: int, _attacker: Actor) -> int:
	var before := hp
	hp = maxi(0, hp - maxi(dmg, 0))
	return before - hp

# ---------------------------------------------------------------- carrying / weapons
func is_carrying_heavy() -> bool:
	return held != "" and Content.weapon(held).get("carry", false)

func hand_point(carry: bool = false) -> Vector2:
	var hand: Array = sheet.get("hand", [])
	var frame := body.frame if body else 0
	if carry:
		var c: Array = sheet.anims.get("carry", [40, 2])
		frame = int(c[0])
	if frame < hand.size():
		var h: Array = hand[frame]
		return Vector2(float(h[0]) - sheet.anchor.x, float(h[1]) - sheet.anchor.y)
	return Vector2(10, -30) if not carry else Vector2(0, -48)

func hand_angle() -> float:
	var hand: Array = sheet.get("hand", [])
	if body and body.frame < hand.size():
		return float(hand[body.frame][2])
	return 0.0

func equip_weapon(id: String, durability: int = -1) -> void:
	held = id
	var w: Dictionary = Content.weapon(id)
	var up := {"power": 0, "dur": 0.0}
	if team == TEAM_PLAYER:
		up = GameState.weapon_upgrade_for_family(w.get("family", ""))
	held_max = int(round(float(w.get("durability", 10)) * (1.0 + float(up.dur))))
	held_dur = durability if durability > 0 else held_max
	weapon_spr.texture = SpriteLib.weapon(id)
	weapon_spr.visible = true
	Audio.sfx("pickup", -4.0)

func drop_weapon(knocked: bool = false) -> void:
	if held == "":
		return
	var id := held
	var dur := held_dur
	held = ""
	weapon_spr.visible = false
	if room:
		var off := Vector2(randf_range(-14, 14), randf_range(-6, 6)) if knocked else Vector2(facing * 12, 2)
		room.spawn_weapon_pickup(id, room.clamp_ground(position + off), dur, 12.0 if knocked else 2.0)

func use_weapon_durability() -> void:
	if held == "":
		return
	held_dur -= 1
	if held_dur <= 0:
		var w: Dictionary = Content.weapon(held)
		Audio.sfx(w.get("break_sfx", "crate_break"))
		room.spawn_debris(w.get("break_fx", "debris_wood"), hit_point())
		held = ""
		weapon_spr.visible = false

func release_carried() -> void:
	if carried_actor:
		carried_actor.carrier = null
		carried_actor = null
	carry_t = 0

# ---------------------------------------------------------------- visuals
func play_anim(name: String) -> void:
	if anim != name:
		anim = name
		anim_frame = 0
		anim_t = 0

func _anim_for_state() -> Array:
	# returns [anim_name, frame_index_within_anim]
	if scripted_anim != "":
		return [scripted_anim, -1]
	match state:
		"idle":
			if carried_actor or is_carrying_heavy():
				return ["carry", 0]
			return ["idle", -1]
		"walk":
			if carried_actor or is_carrying_heavy():
				return ["carry", -1]
			return ["walk", -1]
		"run":
			return ["run", -1]
		"carry":
			return ["carry", 0 if vel.length() < 4 else -1]
		"jump":
			return ["jump", 0 if vz > 0 else 1]
		"attack":
			return [atk.get("anim", "punch_a"), _attack_frame()]
		"guard":
			return ["guard", 0]
		"hurt":
			return ["hurt", 1 if hurt_low else 0]
		"knockdown":
			if lying:
				return ["knockdown", 2]
			return ["knockdown", 0 if vz > 0 else 1]
		"getup":
			return ["getup", 0 if state_t < 9 else 1]
		"dizzy":
			return ["dizzy", -1]
		"pickup":
			return ["pickup", 0]
		"throw":
			return ["throw", 0 if state_t < 5 else 1]
		"carried", "thrown":
			return ["knockdown", 0]
		"dead":
			return ["knockdown", 2]
		"victory":
			return ["victory", -1]
		"talk":
			return ["talk", -1]
		"cower":
			return ["cower", -1]
	return ["idle", -1]

func _attack_frame() -> int:
	var a: Array = sheet.anims.get(atk.get("anim", "punch_a"), [0, 1])
	var count := int(a[1])
	var ph := attack_phase()
	if atk.get("hits", 1) > 1 and ph == 1:
		return int(atk_t / 3) % maxi(count, 1)
	if count <= 1:
		return 0
	if count == 2:
		return 0 if ph == 0 else 1
	return clampi(ph, 0, count - 1)

func _anim_speed(name: String) -> int:
	match name:
		"idle": return 30
		"walk": return 8
		"run": return 5
		"dizzy": return 12
		"talk": return 14
		"victory": return 16
		"cower": return 6
		"carry": return 9
	return 8

func _update_visual() -> void:
	if body == null:
		return
	var pair := _anim_for_state()
	var name: String = pair[0]
	var fixed: int = pair[1]
	var a: Array = sheet.anims.get(name, sheet.anims.get("idle", [0, 1]))
	if name != anim:
		anim = name
		anim_t = 0
		anim_frame = 0
	var count := maxi(1, int(a[1]))
	if fixed >= 0:
		anim_frame = mini(fixed, count - 1)
	else:
		anim_t += 1
		if anim_t >= _anim_speed(name):
			anim_t = 0
			anim_frame = (anim_frame + 1) % count
	body.frame = clampi(int(a[0]) + anim_frame, 0, body.hframes * body.vframes - 1)
	visual.position = Vector2(0, -round(z))
	visual.scale.x = float(facing)
	# shadow shrinks with height
	var s := clampf(1.0 - z / 140.0, 0.45, 1.0)
	shadow.scale = Vector2(s, s) * (1.25 if height > 50 else 1.0)
	shadow.visible = state != "removed"
	# weapon attachment
	if held != "" and weapon_spr.visible:
		var hp_pt := hand_point()
		if is_carrying_heavy():
			hp_pt = hand_point(true)
			var tex := weapon_spr.texture
			weapon_spr.position = hp_pt
			weapon_spr.offset = Vector2(-tex.get_width() / 2.0, -tex.get_height())
			weapon_spr.rotation = 0.0
			weapon_spr.z_index = 1
		else:
			weapon_spr.position = hp_pt
			weapon_spr.offset = -SpriteLib.weapon_grip(held)
			weapon_spr.rotation = deg_to_rad(hand_angle())
			weapon_spr.z_index = 0 if state == "attack" else -1
	# flash / telegraph tint
	if flash > 0.0:
		flash = maxf(0.0, flash - 0.12)
	var f := flash * Settings.flash
	if telegraph_t > 0 and (telegraph_t / 4) % 2 == 0:
		f = maxf(f, 0.45 * maxf(Settings.flash, 0.35))
		mat.set_shader_parameter("flash_color", Color(1.0, 0.35, 0.25))
	else:
		mat.set_shader_parameter("flash_color", flash_color)
	mat.set_shader_parameter("flash_amount", f)
	if invuln > 0 and state in ["idle", "walk", "run", "guard"] and team == TEAM_PLAYER:
		body.modulate.a = 0.55 if (invuln / 3) % 2 == 0 else 1.0
	else:
		body.modulate.a = 1.0
