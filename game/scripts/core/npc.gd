class_name NPC
extends Actor
## Neighbors, shopkeepers, followers (Biscuit the dog, escorted Mr. Hollis) and the ally Jett.

var npc_id := ""
var mode := "idle"           # idle, wander, follow, cower, behind_counter
var talkable := true
var shop := ""
var home := Vector2.ZERO
var wander_dir := 1
var wander_t := 0
var follow_target: Actor = null
var follow_gap := 34.0
var escort := false
var bark_t := 0
var label_override := ""

func setup_npc(id: String, sprite_id: String, pos: Vector2, opts: Dictionary) -> void:
	npc_id = id
	setup_visual(sprite_id)
	position = pos
	home = pos
	display_name = Content.character_name(id)
	mode = opts.get("mode", "idle")
	shop = opts.get("shop", "")
	facing = int(opts.get("facing", -1))
	talkable = opts.get("talk", true)
	label_override = opts.get("label", "")
	team = TEAM_NEUTRAL
	walk_speed = 40.0
	if id == "biscuit":
		height = 20.0
		half_w = 8.0
		walk_speed = 110.0
	if mode == "follow":
		walk_speed = 95.0 if id != "biscuit" else 120.0
	if opts.get("escort", false):
		escort = true
		team = TEAM_PLAYER
		max_hp = int(opts.get("hp", 60))
		hp = max_hp
		walk_speed = 70.0
		combo_limit = 2

func is_hittable() -> bool:
	if not escort:
		return false
	return super.is_hittable()

func think() -> void:
	if frozen:
		return
	match mode:
		"idle", "behind_counter":
			vel = vel.move_toward(Vector2.ZERO, 400 * DT)
			if room and room.player and absf(room.player.position.x - position.x) < 70 and mode == "idle":
				facing = 1 if room.player.position.x > position.x else -1
		"wander":
			wander_t -= 1
			if wander_t <= 0:
				wander_t = randi_range(90, 260)
				wander_dir = [-1, 0, 1][randi() % 3]
				if absf(position.x - home.x) > 120:
					wander_dir = -1 if position.x > home.x else 1
			vel = vel.move_toward(Vector2(wander_dir * walk_speed * 0.6, 0), 300 * DT)
			if wander_dir != 0:
				facing = wander_dir
			if room and room.combat_active():
				mode = "cower"
		"follow":
			if follow_target and is_instance_valid(follow_target) and state in ["idle", "walk"]:
				var to := follow_target.position + Vector2(-follow_target.facing * follow_gap, 4) - position
				if escort and room and room.combat_active():
					to = follow_target.position + Vector2(-follow_target.facing * 50, 0) - position
				if to.length() > 10:
					var d := to.normalized()
					var sp := walk_speed * (1.6 if to.length() > 120 else 1.0)
					vel = vel.move_toward(Vector2(d.x * sp, d.y * sp * 0.7), 500 * DT)
					if absf(vel.x) > 5:
						facing = 1 if vel.x > 0 else -1
				else:
					vel = vel.move_toward(Vector2.ZERO, 500 * DT)
			if npc_id == "biscuit":
				bark_t -= 1
				if bark_t <= 0:
					bark_t = randi_range(240, 600)
					Audio.sfx("dog_bark", -8.0)
		"cower":
			vel = vel.move_toward(Vector2.ZERO, 400 * DT)
			if room and not room.combat_active() and state_t > 120:
				mode = "wander" if home != Vector2.ZERO else "idle"

func _anim_for_state() -> Array:
	if mode == "cower" and state in ["idle", "walk"]:
		return ["cower", "loop", 0]
	if npc_id == "biscuit":
		if state == "walk":
			return ["walk", "stride", 0]
		if bark_t > 0 and bark_t < 20:
			return ["bark", "fixed", 0]
		return ["idle", "loop", 0]
	return super._anim_for_state()

func on_defeated() -> void:
	defeated.emit(self)
	if escort and room:
		room.escort_down(self)

func _dead_state() -> void:
	vel = Vector2.ZERO
	if state_t == 1:
		on_defeated()

func context_label() -> String:
	if label_override != "":
		return label_override
	if shop != "":
		return "Talk to %s" % display_name
	return "Talk to %s" % display_name
