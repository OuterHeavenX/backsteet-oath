class_name Player
extends Actor
## Nico. Reads InputMap actions (keyboard, gamepad, touch and the test bot all feed the same actions).

const BUFFER_TICKS := 8          # ~133 ms action buffer
const ACTIONS := ["punch", "kick", "jump", "interact", "guard"]
const SPECIAL_COLOR := Color(0.3, 0.95, 1.0)

var tickc := 0
var buf: Dictionary = {}
var input_lock := 0
var need_release: Dictionary = {}
var move_input := Vector2.ZERO
var last_tap := {"move_left": -100, "move_right": -100}
var tap_run := false
var kick_hold := 0
var charging := false
var perfect_counter_t := 0
var door_push := 0
var control_enabled := true
var context_target: Variant = null
var context_text := ""

func _init() -> void:
	team = TEAM_PLAYER
	display_name = "Nico"
	combo_limit = 3
	lie_time = 36
	dizzy_threshold = 99999.0
	liftable = false

func refresh_stats() -> void:
	max_hp = GameState.max_hp()
	hp = clampi(GameState.hp, 0, max_hp)
	defense = float(GameState.stat("def"))
	var agi := GameState.stat("agi")
	walk_speed = 92.0 * (1.0 + minf(agi * 0.015, 0.3))
	run_speed = 178.0 * (1.0 + minf(agi * 0.01, 0.2) + GameState.run_bonus())
	getup_invuln = 34 + mini(agi, 30)

## Called every physics tick by the room, even during hit-stop, so presses are never lost.
func poll_input() -> void:
	tickc += 1
	if input_lock > 0:
		input_lock -= 1
	for a in need_release.keys():
		if not Input.is_action_pressed(a):
			need_release.erase(a)
	if not control_enabled:
		move_input = Vector2.ZERO
		return
	for a in ACTIONS:
		if Input.is_action_just_pressed(a) and input_lock <= 0 and not need_release.has(a):
			buf[a] = tickc
	move_input = Input.get_vector("move_left", "move_right", "move_up", "move_down")
	for d in ["move_left", "move_right"]:
		if Input.is_action_just_pressed(d):
			if tickc - int(last_tap[d]) < 16:
				tap_run = true
			last_tap[d] = tickc
	if absf(move_input.x) < 0.2:
		tap_run = false
	if Input.is_action_pressed("kick") and not need_release.has("kick"):
		kick_hold += 1
	else:
		if charging and kick_hold >= 45 and GameState.has_skill("oath") and can_act():
			charging = false
			kick_hold = 0
			start_attack("oath_breaker")
			_special_flash()
			return
		charging = false
		kick_hold = 0

## Blocks gameplay actions until currently-held buttons are released (used after menus/doors/dialogue).
func lock_input(ticks: int = 10) -> void:
	input_lock = ticks
	buf.clear()
	for a in ACTIONS + ["run"]:
		if Input.is_action_pressed(a):
			need_release[a] = true

func consume(a: String) -> bool:
	if buf.has(a) and tickc - int(buf[a]) <= BUFFER_TICKS:
		buf.erase(a)
		return true
	return false

func peek(a: String) -> bool:
	return buf.has(a) and tickc - int(buf[a]) <= BUFFER_TICKS

func held_action(a: String) -> bool:
	return control_enabled and Input.is_action_pressed(a) and not need_release.has(a)

# ---------------------------------------------------------------- think
func think() -> void:
	if perfect_counter_t > 0:
		perfect_counter_t -= 1
	if not control_enabled or dead:
		if state in ["idle", "walk", "run"]:
			vel = vel.move_toward(Vector2.ZERO, 1200 * DT)
		return
	match state:
		"idle", "walk", "run", "carry":
			_ground_control()
		"jump":
			_air_control()
		"attack":
			_attack_control()
		"guard":
			_guard_control()

func _move_speed() -> float:
	var sp := walk_speed
	if held != "":
		var w: Dictionary = Content.weapon(held)
		sp *= 1.0 - 0.05 * float(w.get("slow", 0))
		if w.get("carry", false):
			sp *= 0.68 + 0.08 * GameState.upgrade_tier("harness")
	if carried_actor:
		sp *= 0.7
	if charging:
		sp *= 0.4
	return sp

func _ground_control() -> void:
	var mv := move_input
	var want_run := (held_action("run") or tap_run) and absf(mv.x) > 0.3 and carried_actor == null and not is_carrying_heavy() and not charging
	var sp := run_speed if want_run else _move_speed()
	var target := Vector2(mv.x * sp, mv.y * sp * depth_mult)
	var accel := 1600.0 if mv.length() > 0.1 else 2000.0
	vel = vel.move_toward(target, accel * DT)
	if absf(mv.x) > 0.2:
		facing = 1 if mv.x > 0 else -1
	if state in ["idle", "walk", "run"]:
		if want_run and vel.length() > 20:
			if state != "run":
				set_state("run")
		elif state == "run":
			set_state("walk")
	if kick_hold >= 45 and GameState.has_skill("oath") and not charging and (state in ["idle", "walk"]) and carried_actor == null:
		charging = true
		room.spawn_fx("charge_glow", Vector2(0, -height * 0.5), 0.0, self, 30)
	# door entry by pushing up against a door
	if mv.y < -0.6 and room and room.door_at(self) != {}:
		door_push += 1
		if door_push > 6:
			door_push = 0
			room.try_door(room.door_at(self))
			return
	else:
		door_push = 0
	# actions, in priority order
	if consume("interact"):
		if held_action("guard") and held != "":
			drop_weapon()
			return
		_interact()
		return
	if held_action("guard") and carried_actor == null and not is_carrying_heavy():
		if consume("kick") and GameState.has_skill("rising"):
			start_attack("rising_kick"); _special_flash(); return
		if consume("punch") and GameState.has_skill("sweep"):
			start_attack("spin_sweep"); _special_flash(); return
		set_state("guard")
		vel *= 0.3
		return
	if consume("jump") and carried_actor == null and not is_carrying_heavy():
		set_state("jump")
		vz = 300.0
		z = 0.5
		var air_sp := run_speed if state == "run" or want_run else walk_speed
		vel = Vector2(mv.x * air_sp, mv.y * walk_speed * depth_mult)
		Audio.sfx("jump", -6.0)
		return
	if consume("punch"):
		_punch_action(want_run or state == "run")
		return
	if consume("kick"):
		_kick_action(want_run or state == "run")
		return

func _punch_action(running: bool) -> void:
	if carried_actor:
		if GameState.has_skill("giant"):
			start_attack("giant_spin")
			_special_flash()
		else:
			throw_carried()
		return
	if held != "":
		var w: Dictionary = Content.weapon(held)
		if w.get("carry", false) or w.get("attack", "") == "":
			throw_held()
			return
		start_attack(w.attack)
		return
	if running:
		if GameState.has_skill("shoulder"):
			start_attack("shoulder"); _special_flash()
		else:
			start_attack("run_punch")
		return
	start_attack("punch_a")

func _kick_action(running: bool) -> void:
	if carried_actor:
		throw_carried()
		return
	if is_carrying_heavy():
		throw_held()
		return
	if running:
		start_attack("dropkick")
		return
	start_attack("kick")

func _air_control() -> void:
	# light air steering
	var mv := move_input
	vel.x = move_toward(vel.x, mv.x * maxf(absf(vel.x), walk_speed), 300 * DT)
	if absf(mv.x) > 0.3:
		facing = 1 if mv.x > 0 else -1
	if air_attack_used:
		return
	if consume("guard") and GameState.has_skill("slam"):
		_start_slam()
		return
	if consume("punch"):
		if held != "" and Content.weapon(held).get("attack", "") == "":
			throw_held()
		elif GameState.has_skill("heel"):
			start_attack("heel_drop"); _special_flash()
		else:
			start_attack("jump_punch")
		return
	if consume("kick"):
		start_attack("jump_kick")

func _start_slam() -> void:
	air_attack_used = true
	start_attack("slam_land")
	atk_t = -999  # wait in the air until landing
	vz = minf(vz, -380.0)
	vel.x *= 0.3
	_special_flash()

func _attack_state() -> void:
	if atk_id == "slam_land" and atk_t < 0:
		if is_airborne():
			vz = minf(vz, -380.0)
			return
		atk_t = 0
		z = 0.0
		room.spawn_fx("shockwave", position, 0.0)
		room.shake(4)
		Audio.sfx("slam")
	if atk_id == "giant_spin":
		_giant_spin_update()
	super._attack_state()

func _giant_spin_update() -> void:
	if carried_actor == null:
		atk_t = int(atk.startup) + int(atk.active)
		return
	if atk_t % 6 == 0:
		facing = -facing
	if atk_t >= int(atk.startup) + int(atk.active) - 1:
		throw_carried(1.4)

func _attack_control() -> void:
	var c: Dictionary = atk.get("cancel", {})
	if c.is_empty():
		return
	if atk_t < int(atk.get("cancel_from", 99)):
		return
	if atk_targets == 0 and atk_id.begins_with("swing") == false and atk_id != "punch_rapid":
		# combos only continue on contact (whiffed jabs recover normally), but buffered presses keep their window
		if atk_t < int(atk.startup) + int(atk.active) + int(atk.recovery) - 2:
			return
	if peek("punch") and c.has("punch"):
		var nxt: String = c.punch
		if atk_id == "punch_b" and GameState.has_skill("rapid"):
			nxt = "punch_rapid"
		if nxt.begins_with("swing") and held == "":
			return
		consume("punch")
		start_attack(nxt)
		if nxt == "punch_rapid":
			_special_flash()
		return
	if peek("kick") and c.has("kick"):
		consume("kick")
		start_attack(c.kick)

func _guard_control() -> void:
	if guard_stun > 0:
		return
	if perfect_counter_t > 0 and GameState.has_skill("counter") and consume("punch"):
		perfect_counter_t = 0
		start_attack("guard_counter")
		_special_flash()
		return
	if not held_action("guard"):
		set_state("idle")
		return
	if consume("kick") and GameState.has_skill("rising"):
		start_attack("rising_kick"); _special_flash(); return
	if consume("punch") and GameState.has_skill("sweep"):
		start_attack("spin_sweep"); _special_flash(); return
	if consume("interact") and held != "":
		drop_weapon()
	if absf(move_input.x) > 0.6:
		var nf := 1 if move_input.x > 0 else -1
		if nf != facing and guard_t > 6:
			facing = nf

func _special_flash() -> void:
	flash = 0.7
	flash_color = SPECIAL_COLOR

# ---------------------------------------------------------------- context actions
func _interact() -> void:
	if carried_actor:
		throw_carried()
		return
	if is_carrying_heavy():
		throw_held()
		return
	var ctx: Dictionary = room.find_context(self)
	match ctx.get("type", ""):
		"npc":
			room.talk_to(ctx.node)
			return
		"door":
			room.try_door(ctx.door)
			return
		"pickup":
			_pick_up(ctx.node)
			return
		"prop":
			_lift_prop(ctx.node)
			return
		"enemy":
			_grab_enemy(ctx.node)
			return
	if held != "":
		throw_held()

func _pick_up(p: Node) -> void:
	if not is_instance_valid(p):
		return
	if held != "":
		drop_weapon()
	equip_weapon(p.weapon_id, p.durability)
	p.collect()
	if not GameState.has_skill("retrieve"):
		set_state("pickup")
		vel = Vector2.ZERO

func _lift_prop(p: Node) -> void:
	if not is_instance_valid(p) or not p.liftable:
		return
	if held != "":
		drop_weapon()
	var wid: String = p.lift_weapon
	p.lifted()
	equip_weapon(wid, 1)
	if not GameState.has_skill("retrieve"):
		set_state("pickup")
		vel = Vector2.ZERO

func _grab_enemy(e: Actor) -> void:
	if not is_instance_valid(e) or e.dead:
		return
	if held != "":
		drop_weapon()
	carried_actor = e
	carry_t = 0
	e.carrier = self
	e.lying = false
	e.set_state("carried")
	Audio.sfx("grab")
	set_state("pickup")
	vel = Vector2.ZERO

func throw_carried(mult: float = 1.0) -> void:
	var e := carried_actor
	if e == null:
		return
	release_carried()
	e.thrower = self
	e.atk_hit.clear()
	e.set_state("thrown")
	e.facing = -facing
	e.vel = Vector2(facing * 300.0 * mult, 0)
	e.vz = 170.0
	e.z = maxf(e.z, 20.0)
	e.lying = false
	Audio.sfx("throw")
	set_state("throw")

func throw_held() -> void:
	if held == "":
		return
	var id := held
	var dur := held_dur
	held = ""
	weapon_spr.visible = false
	var from := Vector2(position.x + facing * 10, position.y)
	var hz := z + (40.0 if Content.weapon(id).get("carry", false) else 28.0)
	room.spawn_projectile(self, id, from, hz, facing, dur)
	Audio.sfx("throw")
	set_state("throw")

func spawn_projectile() -> void:
	pass

# ---------------------------------------------------------------- combat math
func calc_raw(d: Dictionary) -> float:
	var atk_s := float(GameState.stat("atk"))
	var tec := float(GameState.stat("tec"))
	var p := float(d.get("power", 5))
	if atk_id.begins_with("swing") and held != "":
		var w: Dictionary = Content.weapon(held)
		var fam: String = w.get("family", "")
		var up := GameState.weapon_upgrade_for_family(fam)
		var m := GameState.mastery_level(fam)
		return (float(w.get("power", 0)) + float(up.power) + p) * (1.0 + atk_s * 0.04 + tec * 0.03) * (1.0 + 0.06 * m)
	if d.get("stat", "atk") == "tec":
		return p * (1.0 + atk_s * 0.03 + tec * 0.05)
	return p * (1.0 + atk_s * 0.06)

func projectile_raw(id: String) -> float:
	var w: Dictionary = Content.weapon(id)
	var fam: String = w.get("family", "")
	var up := GameState.weapon_upgrade_for_family(fam)
	var m := GameState.mastery_level(fam)
	var atk_s := float(GameState.stat("atk"))
	var tec := float(GameState.stat("tec"))
	return (float(w.get("throw_power", 8)) + float(up.power)) * (1.0 + atk_s * 0.04 + tec * 0.04) * (1.0 + 0.05 * m)

func dizzy_mult() -> float:
	return 1.0 + float(GameState.stat("tec")) * 0.03

func incoming_mult() -> float:
	return Settings.incoming_damage_mult()

func perfect_window() -> int:
	var w := 8 + mini(GameState.stat("tec") / 4, 6)
	if Settings.difficulty == "relaxed":
		w += 4
	return w

func _recovery_ticks() -> int:
	var r := int(atk.get("recovery", 8))
	var cut := mini(GameState.stat("agi") / 6, 4)
	return maxi(4, r - cut)

func on_hit_landed(target: Node, res: String) -> void:
	if res == "miss":
		return
	if atk_id.begins_with("swing") and held != "":
		var fam: String = Content.weapon(held).get("family", "")
		if GameState.add_mastery(fam, 1):
			room.float_text(position + Vector2(0, -height - 14), "%s mastery %d!" % [Content.weapon_families[fam].name, GameState.mastery_level(fam)], Color(1, 0.85, 0.3))
		use_weapon_durability()

func on_perfect_guard(attacker: Actor) -> void:
	super.on_perfect_guard(attacker)
	perfect_counter_t = 26
	room.float_text(position + Vector2(0, -height - 10), "PERFECT!", Color(0.4, 1.0, 1.0))

func apply_damage(dmg: int, attacker: Actor) -> int:
	var d := super.apply_damage(dmg, attacker)
	GameState.hp = hp
	GameState.stats_changed.emit()
	if room and d > 0:
		room.on_player_damaged(d)
	return d

func on_defeated() -> void:
	var idx := GameState.bag.find("smelling_salts")
	if idx >= 0:
		GameState.remove_from_bag(idx)
		dead = false
		lying = false
		hp = int(max_hp / 2)
		GameState.hp = hp
		GameState.stats_changed.emit()
		set_state("getup")
		invuln = 90
		room.float_text(position + Vector2(0, -60), "Smelling salts!", Color(0.5, 1, 0.5))
		Audio.sfx("heal")
		return
	super.on_defeated()
	if room:
		room.on_player_defeated()

func current_context_text() -> String:
	if room == null or not control_enabled:
		return ""
	if carried_actor:
		return "%s Throw" % InputPrompts.tag("interact")
	if is_carrying_heavy():
		return "%s Throw" % InputPrompts.tag("interact")
	var ctx: Dictionary = room.find_context(self)
	match ctx.get("type", ""):
		"npc":
			return "%s %s" % [InputPrompts.tag("interact"), ctx.get("label", "Talk")]
		"door":
			return "%s %s" % [InputPrompts.tag("interact"), ctx.get("label", "Enter")]
		"pickup":
			return "%s Pick up %s" % [InputPrompts.tag("interact"), ctx.get("label", "")]
		"prop":
			return "%s Lift %s" % [InputPrompts.tag("interact"), ctx.get("label", "")]
		"enemy":
			return "%s Grab" % InputPrompts.tag("interact")
	return ""
