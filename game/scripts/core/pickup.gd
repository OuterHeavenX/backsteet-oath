class_name Pickup
extends Node2D
## Cash, healing buns, key items (auto-collect on touch) and weapons (Grab to pick up).

var room: Node
var kind := "cash"
var amount := 0
var weapon_id := ""
var durability := 1
var key_id := ""
var persist_key := ""
var z := 0.0
var vz := 0.0
var vx := 0.0
var life := 0
var collected := false
var spr: Sprite2D
var shadow: Sprite2D
var anim_frames := 1
var half_w := 8.0
var depth_r := 4.0

func setup(r: Node, k: String, pos: Vector2, pop: float = 0.0) -> void:
	room = r
	kind = k
	position = pos
	z = pop
	vz = pop * 10.0 if pop > 0.0 else 0.0
	shadow = Sprite2D.new()
	shadow.texture = Actor._shadow_tex()
	shadow.scale = Vector2(0.5, 0.5)
	add_child(shadow)
	spr = Sprite2D.new()
	add_child(spr)
	match kind:
		"cash":
			var pid := "coin" if amount < 8 else ("bill" if amount < 20 else "cash_stack")
			_set_pickup_art(pid)
		"heal":
			_set_pickup_art("heal_bun")
		"key":
			var art := key_id if Content.pickup_meta.has(key_id) else "parcel"
			_set_pickup_art(art)
		"weapon":
			spr.texture = SpriteLib.weapon(weapon_id)
			if not Content.weapon(weapon_id).get("carry", false):
				spr.rotation = 0.0
			spr.offset = Vector2(0, -spr.texture.get_height() / 2.0)

func _set_pickup_art(pid: String) -> void:
	var info := SpriteLib.pickup(pid)
	spr.texture = info.texture
	anim_frames = int(info.frames)
	if anim_frames > 1:
		spr.hframes = anim_frames
	spr.offset = Vector2(0, -float(info.frame.y) / 2.0)

func tick() -> void:
	if collected:
		return
	life += 1
	if z > 0.0 or vz > 0.0:
		vz -= 900.0 * Actor.DT
		z += vz * Actor.DT
		position.x += vx * Actor.DT
		if z <= 0.0:
			z = 0.0
			if vz < -80.0:
				vz = -vz * 0.35
			else:
				vz = 0.0
				vx = 0.0
	spr.position = Vector2(0, -z - (sin(life * 0.08) * 1.5 + 1.5 if kind != "weapon" else 0.0))
	if anim_frames > 1:
		spr.frame = int(life / 6) % anim_frames
	if kind in ["cash", "heal", "key"] and z < 6.0 and room.player and not room.player.dead and room.player.state != "carried":
		var p: Actor = room.player
		if absf(p.position.x - position.x) < 14 and absf(p.position.y - position.y) < 10:
			_auto_collect()
	if kind == "cash" and life > 60 * 40:
		visible = (life / 4) % 2 == 0
		if life > 60 * 45:
			collect()

func _auto_collect() -> void:
	match kind:
		"cash":
			GameState.add_cash(amount)
			Audio.sfx("cash" if amount < 20 else "cash_big", -3.0)
			room.float_text(position + Vector2(0, -20), "+$%d" % amount, Color(0.48, 0.94, 0.29))
		"heal":
			var h := GameState.heal(amount)
			room.player.hp = GameState.hp
			Audio.sfx("eat")
			room.float_text(position + Vector2(0, -20), "+%d HP" % h, Color(1, 0.6, 0.6))
		"key":
			GameState.give_key(key_id)
			Audio.sfx("quest_update")
			room.float_text(position + Vector2(0, -24), Content.item(key_id).get("name", key_id), Color(1, 0.85, 0.3))
			if persist_key != "":
				GameState.mark_collected(persist_key)
			Quests.on_key_item(key_id)
	collect()

func collect() -> void:
	collected = true
	room.remove_pickup(self)

func label() -> String:
	if kind == "weapon":
		return Content.weapon(weapon_id).get("name", weapon_id)
	return ""
