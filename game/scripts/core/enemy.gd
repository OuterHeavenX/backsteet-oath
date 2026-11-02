class_name Enemy
extends Actor
## Data-driven street fighter AI. Enemies take an "attack token" from the room before committing,
## so only a manageable number attack at once; others hold lanes at a distance, reposition or taunt.

var enemy_id := ""
var gang := ""
var arche_id := ""
var arche: Dictionary = {}
var tier := 1
var power_mult := 1.0
var xp_reward := 10
var cash_range: Array = [2, 5]
var ai_speed := 70.0
var react := 14
var guard_chance := 0.1
var aggression := 0.5
var keep := 80.0
var attack_list: Array = []
var ranged := false
var flank := false
var counter_attacks := false
var acrobat := false
var drilled := false

var target: Actor = null
var token := false
var intent := "approach"
var decide_cd := 0
var lane_offset := 0.0
var side := 1
var pending_attack := ""
var react_t := 0
var guard_hold := 0
var taunt_t := 0
var named := ""
var drops: Array = []
var wave_id := ""
var boss_id := ""
var ally := false
var entering := false
var counted := false
var cooldowns: Dictionary = {}
var throw_item := "bottle"
var counter_pending := 0
var stuck_t := 0
var leash := false

func setup_enemy(id: String, district_tier: int, opts: Dictionary = {}) -> void:
	enemy_id = id
	tier = district_tier
	var E: Dictionary = Content.enemies
	if E.get("bosses", {}).has(id):
		_setup_boss(id, E.bosses[id])
	else:
		var parts := id.split("_")
		gang = parts[0]
		arche_id = parts[1]
		arche = E.archetypes[arche_id]
		var g: Dictionary = E.gangs.get(gang, {})
		setup_visual(id)
		max_hp = int(round(float(arche.hp) * Content.tier_mult("hp", tier)))
		defense = Content.tier_mult("def", tier)
		power_mult = Content.tier_mult("power", tier)
		xp_reward = int(round(float(arche.xp) * Content.tier_mult("xp", tier)))
		var cr: Array = arche.get("cash", [2, 5])
		var cm := Content.tier_mult("cash", tier)
		cash_range = [int(round(cr[0] * cm)), int(round(cr[1] * cm))]
		ai_speed = float(arche.speed) * (1.0 + 0.03 * (tier - 1))
		react = maxi(6, int(arche.react) - (tier - 1))
		guard_chance = float(arche.get("guard", 0.1))
		aggression = float(arche.get("aggression", 0.5))
		keep = float(arche.get("keep", 80))
		attack_list = arche.get("attacks", [])
		ranged = arche.get("ranged", false)
		flank = arche.get("flank", false)
		counter_attacks = arche.get("counter", false)
		liftable = arche.get("liftable", true)
		armor_light = int(arche.get("armor", 0)) > 0
		height = float(arche.get("height", 46))
		acrobat = g.get("acrobat", false)
		drilled = g.get("drilled", false)
		throw_item = g.get("throw", "bottle")
		display_name = g.get("name", gang.capitalize())
		if arche_id == "heavy":
			kb_scale = 0.55
			combo_limit = 7
			half_w = 12.0
		if arche_id == "flanker" and acrobat:
			attack_list = attack_list + [["e_jump_kick", 2]]
		if arche.get("weapon", false):
			var pool: Array = g.get("weapons", ["bat"])
			equip_weapon(opts.get("weapon", pool[randi() % pool.size()]))
	if opts.has("weapon") and held == "" and opts.weapon != "":
		equip_weapon(opts.weapon)
	hp = max_hp
	named = opts.get("name", "")
	if named != "":
		display_name = named
	drops = opts.get("drops", [])
	wave_id = opts.get("wave", "")
	ally = opts.get("ally", false)
	if ally:
		team = TEAM_PLAYER
	else:
		team = TEAM_ENEMY
	lane_offset = randf_range(-34, 34)
	side = 1 if randf() < 0.5 else -1
	walk_speed = ai_speed
	getup_invuln = 20
	decide_cd = randi_range(10, 30)

func _setup_boss(id: String, b: Dictionary) -> void:
	boss_id = id
	is_boss = true
	setup_visual(b.get("sprite", id))
	tier = int(b.get("tier", tier))
	max_hp = int(b.hp)
	if Settings.difficulty == "relaxed":
		max_hp = int(max_hp * 0.85)
	defense = float(b.get("def", 0))
	power_mult = float(b.get("power", 1.0))
	xp_reward = int(b.get("xp", 100))
	cash_range = [int(b.get("cash", 0)), int(b.get("cash", 0))]
	ai_speed = float(b.get("speed", 80))
	react = 8
	aggression = 0.8
	keep = 70.0
	height = float(b.get("height", 48))
	display_name = b.get("name", id)
	liftable = false
	combo_limit = 6
	dizzy_threshold = 99999.0
	kb_scale = 0.7
	lie_time = 34
	getup_invuln = 30
	if b.has("weapon"):
		equip_weapon(b.weapon)

# ---------------------------------------------------------------- AI
func think() -> void:
	for k in cooldowns.keys():
		cooldowns[k] = int(cooldowns[k]) - 1
		if cooldowns[k] <= 0:
			cooldowns.erase(k)
	if state == "guard":
		guard_hold -= 1
		if counter_pending > 0:
			counter_pending -= 1
			if counter_pending == 0:
				_face_target()
				start_attack(_counter_attack())
				return
		if guard_hold <= 0:
			set_state("idle")
		return
	if not can_act():
		if token and state in ["hurt", "knockdown", "dizzy", "carried", "thrown", "dead"]:
			_release_token()
		return
	if room == null:
		return
	target = room.pick_target(self)
	if target == null:
		vel = vel.move_toward(Vector2.ZERO, 600 * DT)
		return
	if entering:
		_enter_screen()
		return
	if leash and not room.on_screen(self, -10):
		_move_toward(Vector2(clampf(position.x, room.cam_left() + 30, room.cam_right() - 30), position.y), ai_speed)
		return
	boss_update()
	if state != "idle" and state != "walk" and state != "run":
		return
	decide_cd -= 1
	if decide_cd <= 0:
		_decide()
	_steer()

## Hook for bosses (phase changes, summons, arena hazards).
func boss_update() -> void:
	pass

func _decide() -> void:
	decide_cd = randi_range(12, 28)
	if is_boss or ally:
		intent = "attack" if randf() < aggression + 0.15 else "wait"
		if intent == "attack" and pending_attack == "":
			pending_attack = choose_attack()
			react_t = react
		return
	if token:
		intent = "attack"
		return
	if randf() < aggression and room.request_token(self):
		token = true
		intent = "attack"
		pending_attack = choose_attack()
		react_t = react
		return
	intent = "wait"
	pending_attack = ""
	if randf() < 0.18:
		lane_offset = randf_range(-40, 40)
	if randf() < 0.08 and taunt_t <= 0:
		taunt_t = 50

func choose_attack() -> String:
	if attack_list.is_empty():
		return "e_jab"
	var dist := absf(target.position.x - position.x) if target else 999.0
	var total := 0.0
	var opts: Array = []
	for pair in attack_list:
		var id: String = pair[0]
		var w := float(pair[1])
		if cooldowns.has(id):
			continue
		if id == "e_throw" and dist < 70:
			w *= 0.2
		if id == "e_jump_kick" and dist < 50:
			w *= 0.3
		if id == "e_charge" and dist < 90:
			w *= 0.2
		if id == "e_swing" and held == "":
			continue
		opts.append([id, w])
		total += w
	if opts.is_empty():
		return "e_jab"
	var r := randf() * total
	for o in opts:
		r -= float(o[1])
		if r <= 0.0:
			return o[0]
	return opts[0][0]

func _attack_range(id: String) -> Vector2:
	var d: Dictionary = Content.attack(id)
	if d.get("projectile", false):
		return Vector2(80, 230)
	if id in ["e_charge", "otto_charge", "rook_dash", "jett_dash", "sabine_bash"]:
		return Vector2(60, 200)
	if id in ["e_jump_kick", "jett_flip"]:
		return Vector2(46, 110)
	var xr: Array = d.get("x", [4, 28])
	return Vector2(maxf(float(xr[0]), 6.0), float(xr[1]) - 3.0)

func _steer() -> void:
	var tp := target.position
	var dx := position.x - tp.x
	if absf(dx) > 2.0:
		side = 1 if dx > 0 else -1
	if taunt_t > 0:
		taunt_t -= 1
		vel = vel.move_toward(Vector2.ZERO, 600 * DT)
		_face_target()
		scripted_anim = "victory" if taunt_t > 10 else ""
		if taunt_t <= 0:
			scripted_anim = ""
		return
	scripted_anim = ""
	if ranged and intent == "attack":
		_ranged_behavior()
		return
	if intent == "attack" and pending_attack != "":
		var rng := _attack_range(pending_attack)
		var want_side := side
		if flank and target.facing == -side and absf(dx) < 140:
			want_side = -target.facing  # slip behind the target
		var desired := Vector2(tp.x + want_side * (rng.x + rng.y) * 0.5, tp.y)
		var d: Dictionary = Content.attack(pending_attack)
		var depth_ok := absf(position.y - tp.y) <= float(d.get("depth", 8)) - 1.0
		var adx := absf(dx)
		var in_range := adx >= rng.x - 2 and adx <= rng.y + 2
		if pending_attack in ["e_charge", "otto_charge", "rook_dash", "jett_dash", "sabine_bash"]:
			depth_ok = absf(position.y - tp.y) <= 6.0
		if depth_ok and in_range and (room.on_screen(self, 6) or ally):
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)
			_face_target()
			react_t -= 1
			if react_t <= 0:
				var a := pending_attack
				pending_attack = ""
				_launch_attack(a)
			return
		_move_toward(desired, ai_speed * (1.15 if flank else 1.0))
		stuck_t += 1
		if stuck_t > 240:
			stuck_t = 0
			_release_token()
			intent = "wait"
		return
	# waiting: hold a lane at a distance, on our current side, spread out from friends
	var hold := keep + (20.0 if drilled else 0.0)
	var desired_w := Vector2(tp.x + side * hold, tp.y + lane_offset)
	if drilled and room.count_team_near(self, 160) >= 2:
		desired_w.x = tp.x + side * hold * 0.8
	_move_toward(desired_w, ai_speed * 0.7)
	if guard_chance > 0.4 and absf(dx) < 90 and randf() < 0.02:
		set_state("guard")
		guard_hold = 40
	_face_target()

func _ranged_behavior() -> void:
	var tp := target.position
	var dx := position.x - tp.x
	var adx := absf(dx)
	var desired := Vector2(tp.x + side * 160.0, tp.y)
	if adx < 70:
		desired.x = tp.x + side * 200.0
	if pending_attack == "" or pending_attack == "e_throw":
		var aligned := absf(position.y - tp.y) < 10
		if aligned and adx > 80 and adx < 240 and room.on_screen(self, 10):
			_face_target()
			vel = vel.move_toward(Vector2.ZERO, 900 * DT)
			react_t -= 1
			if react_t <= 0:
				pending_attack = ""
				_launch_attack("e_throw")
			return
	elif adx < 40:
		_face_target()
		var a := pending_attack
		pending_attack = ""
		_launch_attack(a)
		return
	_move_toward(desired, ai_speed)

func _launch_attack(id: String) -> void:
	if id == "":
		return
	var d: Dictionary = Content.attack(id)
	if d.is_empty():
		return
	start_attack(id)
	cooldowns[id] = 40 + int(d.get("recovery", 20))
	if int(d.get("startup", 0)) >= 18 and room:
		room.spawn_fx("exclaim", Vector2(0, -height - 10), 0.0, self, int(d.startup))
	if d.get("air", false):
		vz = 260.0
		z = 0.5
		vel.x = facing * 150.0

func on_attack_end() -> void:
	_release_token()
	if acrobat and randf() < 0.3 and not is_boss:
		vel.x = -facing * 140.0

func _release_token() -> void:
	if token and room:
		room.release_token(self)
	token = false
	intent = "wait"

func _enter_screen() -> void:
	var cam_l: float = room.cam_left()
	var cam_r: float = room.cam_right()
	if position.x < cam_l + 24:
		_move_toward(Vector2(cam_l + 40, position.y), ai_speed)
		facing = 1
	elif position.x > cam_r - 24:
		_move_toward(Vector2(cam_r - 40, position.y), ai_speed)
		facing = -1
	else:
		entering = false

func _move_toward(p: Vector2, sp: float) -> void:
	var to := p - position
	to.y = clampf(to.y, -200, 200)
	var sep := Vector2.ZERO
	for o in room.actors:
		if o == self or o.team != team or o.dead:
			continue
		var d: Vector2 = position - o.position
		if absf(d.x) < 22 and absf(d.y) < 10:
			sep += Vector2(signf(d.x) if d.x != 0 else randf_range(-1, 1), signf(d.y) if d.y != 0 else randf_range(-1, 1)) * 40.0
	var dir := to
	if dir.length() < 3.0:
		vel = vel.move_toward(sep, 800 * DT)
		return
	dir = dir.normalized()
	var target_v := Vector2(dir.x * sp, dir.y * sp * depth_mult) + sep
	vel = vel.move_toward(target_v, 900 * DT)
	if absf(vel.x) > 10 and intent != "wait":
		facing = 1 if vel.x > 0 else -1
	if state == "idle" and vel.length() > 4:
		set_state("walk")

func _face_target() -> void:
	if target:
		var dx := target.position.x - position.x
		if absf(dx) > 2:
			facing = 1 if dx > 0 else -1

## Called by the room when a hostile starts an attack nearby: blockers raise their guard.
func notice_attack(attacker: Actor) -> void:
	if dead or not can_act() or ally:
		return
	if absf(attacker.position.x - position.x) > 70 or absf(attacker.position.y - position.y) > 16:
		return
	var front := signf(attacker.position.x - position.x) == float(facing)
	if not front:
		return
	if randf() < guard_chance * (1.0 if not is_boss else 1.0):
		set_state("guard")
		guard_t = 99  # enemies never get perfect guards
		guard_hold = randi_range(24, 44)

func on_blocked(attacker: Actor) -> void:
	if counter_attacks or is_boss:
		if randf() < (0.45 if not is_boss else 0.6) and counter_pending <= 0:
			counter_pending = 6
			guard_hold = maxi(guard_hold, 10)

func _counter_attack() -> String:
	return "e_counter"

func perfect_window() -> int:
	return -1

func calc_raw(d: Dictionary) -> float:
	var p := float(d.get("power", 5)) * power_mult
	if atk_id == "e_swing" and held != "":
		p += float(Content.weapon(held).get("power", 6)) * 0.6 * power_mult
	return p

func projectile_raw(id: String) -> float:
	return float(Content.weapon(id).get("throw_power", 8)) * 0.75 * power_mult

func spawn_projectile() -> void:
	if room == null:
		return
	var item := throw_item
	if held != "" and Content.weapon(held).get("family", "") == "throwable":
		item = held
		held = ""
		weapon_spr.visible = false
	room.spawn_projectile(self, item, Vector2(position.x + facing * 10, position.y), z + 30.0, facing, 1)

func take_damage_and_react(attacker: Actor, d: Dictionary, raw: float, dir: int, force: bool) -> void:
	super.take_damage_and_react(attacker, d, raw, dir, force)
	pending_attack = ""
	if token and state in ["knockdown"]:
		_release_token()
	if held != "" and state == "knockdown" and not is_boss:
		drop_weapon(true)

func on_defeated() -> void:
	_release_token()
	super.on_defeated()
	if room:
		room.on_enemy_defeated(self)
