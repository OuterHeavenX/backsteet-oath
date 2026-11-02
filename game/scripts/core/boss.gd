class_name Boss
extends Enemy
## Boss behaviors. Each boss has at least three attacks with distinct tells, clear recovery
## windows and an adaptation (summons, phase change or arena pressure). No input reading.

var script_id := ""
var partner: Boss = null
var summons_done: Dictionary = {}
var tired := 0
var phase := 1
var hazard_t := 0
var retreat_at := 0.0
var retreated := false
var evade_cd := 0
var phase_pending := false

func setup_boss(id: String) -> void:
	setup_enemy(id, Content.enemies.bosses[id].get("tier", 1))
	script_id = Content.enemies.bosses[id].get("script", id)
	retreat_at = float(Content.enemies.bosses[id].get("retreat_at", 0.0))
	match script_id:
		"duke":
			guard_chance = 0.1
		"rhea":
			keep = 60.0
		"lou":
			keep = 150.0
			throw_item = "fish"
		"otto":
			armor_light = true
			kb_scale = 0.4
			half_w = 13.0
			combo_limit = 7
		"jett":
			guard_chance = 0.0
			combo_limit = 5
		"sabine":
			guard_chance = 0.5
			counter_attacks = true
		"rook":
			guard_chance = 0.4
			counter_attacks = true
			combo_limit = 5
		"heavy":
			armor_light = true
			kb_scale = 0.5

func boss_update() -> void:
	if evade_cd > 0:
		evade_cd -= 1
	if tired > 0:
		tired -= 1
		vel = vel.move_toward(Vector2.ZERO, 600 * DT)
		pending_attack = ""
		if tired % 20 == 0 and room:
			room.spawn_fx("sweat", Vector2(8, -height), 0.0, self, 20)
		return
	var frac := float(hp) / float(max_hp)
	match script_id:
		"duke":
			for th in [0.6, 0.3]:
				if frac <= th and not summons_done.has(th):
					summons_done[th] = true
					_summon(["dogs_brawler", "dogs_flanker"], "duke_whistle")
		"sabine":
			for th in [0.7, 0.35]:
				if frac <= th and not summons_done.has(th):
					summons_done[th] = true
					_summon(["grays_blocker", "grays_thrower"], "sabine_whistle")
		"jett":
			if retreat_at > 0.0 and frac <= retreat_at and not retreated:
				retreated = true
				if room:
					room.boss_retreat(self)
		"rook":
			if phase == 1 and frac <= 0.5 and not phase_pending:
				phase_pending = true
			if phase == 2:
				hazard_t -= 1
				if hazard_t <= 0 and room:
					hazard_t = randi_range(220, 300)
					room.drop_hazard_crate(target.position if target else position)
		"otto":
			if frac <= 0.5 and phase == 1:
				phase = 2
				ai_speed *= 1.15
				walk_speed = ai_speed
				if room:
					room.float_text(position + Vector2(0, -70), "Otto's getting angry!", Color(1, 0.5, 0.3))

func _summon(ids: Array, line: String) -> void:
	if room == null:
		return
	Audio.sfx("whistle")
	room.boss_summon(self, ids, line)

func take_damage_and_react(attacker: Actor, d: Dictionary, raw: float, dir: int, force: bool) -> void:
	super.take_damage_and_react(attacker, d, raw, dir, force)
	if script_id == "rook" and phase_pending and phase == 1 and state == "knockdown":
		pass

func _getup_state() -> void:
	super._getup_state()
	if state == "idle" and script_id == "rook" and phase_pending and phase == 1:
		phase = 2
		phase_pending = false
		if room:
			room.rook_phase_two(self)

func become_phase_two() -> void:
	setup_visual_swap("rook_p2")
	guard_chance = 0.15
	ai_speed *= 1.12
	walk_speed = ai_speed
	aggression = 0.95
	equip_weapon("pipe", 9999)
	held_max = 9999
	hazard_t = 120
	invuln = 40

func setup_visual_swap(id: String) -> void:
	var s := SpriteLib.character(id)
	sheet = s
	body.texture = s.texture
	char_id = id

func notice_attack(attacker: Actor) -> void:
	if script_id == "jett" and can_act() and evade_cd <= 0 and absf(attacker.position.x - position.x) < 60 and absf(attacker.position.y - position.y) < 16:
		if randf() < 0.35:
			evade_cd = 90
			set_state("jump")
			vz = 250.0
			z = 0.5
			vel = Vector2(-signf(attacker.position.x - position.x) * 170.0, 0)
			facing = 1 if attacker.position.x > position.x else -1
			return
	super.notice_attack(attacker)

func _jump_state() -> void:
	if not is_airborne() and state_t > 2:
		_on_land()
		set_state("idle")
		if script_id == "jett":
			tired = 0

func _counter_attack() -> String:
	match script_id:
		"sabine": return "sabine_counter"
		"rook": return "rook_counter"
	return "e_counter"

func on_attack_end() -> void:
	super.on_attack_end()
	# recovery windows after big moves
	match atk_id:
		"duke_spin": tired = 40
		"otto_charge": tired = 80 if atk_targets == 0 else 30
		"otto_slam": tired = 36
		"jett_dash": tired = 26
		"jett_flip": tired = 18
		"sabine_bash": tired = 34 if atk_targets == 0 else 10
		"rook_pound": tired = 40
		"rook_dash": tired = 22 if atk_targets == 0 else 0
		"e_throw":
			if script_id == "lou":
				tired = 10

func choose_attack() -> String:
	var dist := absf(target.position.x - position.x) if target else 999.0
	var r := randf()
	match script_id:
		"duke":
			if dist < 46:
				return "duke_spin" if r < 0.45 and not cooldowns.has("duke_spin") else "e_cross"
			if dist > 120 and not cooldowns.has("e_charge"):
				return "e_charge"
			return "duke_chain"
		"rhea":
			if dist < 40:
				return "pike_sweep" if r < 0.5 else "e_kick"
			return "pike_pole" if r < 0.7 else "pike_sweep"
		"lou":
			if dist < 50:
				return "e_kick"
			return "e_throw"
		"otto":
			if target and target.state == "guard" and dist < 40:
				return "e_grab"
			if dist < 44:
				return "otto_haymaker" if r < 0.6 else ("otto_slam" if not cooldowns.has("otto_slam") else "e_grab")
			if dist > 110 and not cooldowns.has("otto_charge"):
				return "otto_charge"
			return "otto_slam" if not cooldowns.has("otto_slam") else "otto_haymaker"
		"jett":
			if dist < 44:
				return "jett_combo"
			if dist > 120 and not cooldowns.has("jett_dash"):
				return "jett_dash"
			return "jett_flip"
		"sabine":
			if dist < 46:
				return "sabine_baton"
			return "sabine_bash" if not cooldowns.has("sabine_bash") else "sabine_baton"
		"rook":
			if phase == 1:
				if dist < 40:
					return ["rook_jab", "rook_combo", "rook_uppercut"][int(r * 3.0) % 3]
				if dist > 110 and not cooldowns.has("rook_dash"):
					return "rook_dash"
				return "rook_jab" if r < 0.5 else "rook_combo"
			if dist < 50:
				return "rook_pipe" if r < 0.55 else ("rook_pound" if not cooldowns.has("rook_pound") else "rook_uppercut")
			if dist > 110 and not cooldowns.has("rook_dash"):
				return "rook_dash"
			return "rook_pound" if not cooldowns.has("rook_pound") and r < 0.4 else "rook_pipe"
		"heavy":
			if dist < 40:
				return "e_heavy_punch" if r < 0.6 else "e_grab"
			return "e_charge" if dist > 100 else "e_heavy_punch"
	return super.choose_attack()

func _launch_attack(id: String) -> void:
	super._launch_attack(id)
	match id:
		"otto_slam", "rook_pound":
			cooldowns[id] = 260
		"otto_charge", "rook_dash", "jett_dash", "e_charge", "sabine_bash":
			cooldowns[id] = 200
		"duke_spin":
			cooldowns[id] = 220
		"e_throw":
			cooldowns[id] = 50 if script_id == "lou" else 90
			if script_id == "lou" and randf() < 0.35:
				throw_item = "crate"
			elif script_id == "lou":
				throw_item = "fish"

func _attack_state() -> void:
	super._attack_state()
	if state == "attack" and atk_id in ["otto_slam", "rook_pound"] and atk_t == int(atk.get("startup", 20)) + 1:
		room.spawn_fx("shockwave", position, 0.0)
		room.shake(4)

func spawn_projectile() -> void:
	if script_id == "lou" and throw_item == "crate" and target:
		room.spawn_lob(self, "crate", target.position)
		return
	super.spawn_projectile()

func on_defeated() -> void:
	super.on_defeated()
	if partner and is_instance_valid(partner) and not partner.dead:
		partner.aggression = 1.0
		partner.ai_speed *= 1.2
		partner.walk_speed = partner.ai_speed
		partner.react = 5
