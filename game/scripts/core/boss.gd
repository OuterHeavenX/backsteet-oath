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
				phase = 2
				hazard_t = 9999
				if room:
					room.rook_phase_two(self)
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
	apply_sheet(SpriteLib.character(id))
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

## Weighted movesets: [attack, weight, preferred min distance, preferred max distance].
## The boss steers into range for whatever it picks, so variety comes from weights, cooldowns
## and a repeat penalty rather than from reading the player's inputs.
const MOVESETS := {
	"duke": [["duke_chain", 3.0, 36, 90], ["duke_spin", 2.0, 0, 60], ["e_charge", 1.5, 100, 400], ["e_cross", 1.5, 0, 45]],
	"rhea": [["pike_pole", 3.0, 40, 90], ["pike_sweep", 2.0, 0, 70], ["e_kick", 1.2, 0, 45], ["e_charge", 1.0, 100, 400]],
	"lou": [["e_throw", 3.0, 90, 300], ["lou_lob", 2.0, 90, 300], ["e_kick", 1.5, 0, 50], ["lou_hop", 1.2, 40, 120]],
	"otto": [["otto_haymaker", 3.0, 0, 50], ["otto_slam", 2.0, 0, 110], ["otto_charge", 1.5, 100, 400], ["e_grab", 1.2, 0, 40]],
	"jett": [["jett_flip", 2.5, 40, 120], ["jett_dash", 2.0, 90, 400], ["jett_combo", 2.5, 0, 50]],
	"sabine": [["sabine_baton", 3.0, 0, 50], ["sabine_bash", 2.0, 60, 250], ["e_hook", 1.2, 0, 40], ["e_kick", 1.0, 0, 45]],
	"heavy": [["e_heavy_punch", 3.0, 0, 45], ["e_grab", 1.5, 0, 40], ["e_charge", 1.5, 90, 400]],
	"rook1": [["rook_jab", 3.0, 0, 40], ["rook_combo", 2.0, 0, 45], ["rook_uppercut", 1.5, 0, 40], ["rook_dash", 1.5, 100, 400]],
	"rook2": [["rook_pipe", 3.0, 0, 60], ["rook_pound", 1.5, 0, 120], ["rook_dash", 1.5, 100, 400], ["rook_uppercut", 1.2, 0, 40], ["rook_combo", 1.0, 0, 45]],
}
var last_attacks: Array = []

func choose_attack() -> String:
	var key := script_id
	if script_id == "rook":
		key = "rook1" if phase == 1 else "rook2"
	if not MOVESETS.has(key):
		return super.choose_attack()
	var dist := absf(target.position.x - position.x) if target else 999.0
	if script_id == "otto" and target and target.state == "guard" and dist < 40 and not cooldowns.has("e_grab"):
		return "e_grab"
	var total := 0.0
	var opts: Array = []
	for m in MOVESETS[key]:
		var id: String = m[0]
		if cooldowns.has(id):
			continue
		var wgt: float = m[1]
		wgt *= 1.6 if dist >= float(m[2]) and dist <= float(m[3]) else 0.6
		if last_attacks.size() > 0 and last_attacks[-1] == id:
			wgt *= 0.25
		if last_attacks.size() > 1 and last_attacks[-2] == id:
			wgt *= 0.6
		opts.append([id, wgt])
		total += wgt
	if opts.is_empty():
		return MOVESETS[key][0][0]
	var r := randf() * total
	for o in opts:
		r -= float(o[1])
		if r <= 0.0:
			return o[0]
	return opts[-1][0]

func _launch_attack(id: String) -> void:
	super._launch_attack(id)
	last_attacks.append(id)
	if last_attacks.size() > 3:
		last_attacks.pop_front()
	match id:
		"otto_slam", "rook_pound":
			cooldowns[id] = 260
		"otto_charge", "rook_dash", "jett_dash", "e_charge", "sabine_bash":
			cooldowns[id] = 200
		"duke_spin":
			cooldowns[id] = 220
		"e_throw":
			cooldowns[id] = 50 if script_id == "lou" else 90
		"lou_lob":
			cooldowns[id] = 160

func _attack_state() -> void:
	super._attack_state()
	if state == "attack" and atk_id in ["otto_slam", "rook_pound"] and atk_t == int(atk.get("startup", 20)) + 1:
		room.spawn_fx("shockwave", position, 0.0)
		room.shake(4)

func spawn_projectile() -> void:
	if atk_id == "lou_lob" and target:
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
