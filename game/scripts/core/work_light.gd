class_name WorkLight
extends Node2D
## A switchable work light (Kowal's vault). While any light is on the vault stays readable and her Moles
## stay in their holes; she puts lights out one at a time and the player can switch them back on.
## It is only room state: no collision, nothing saved, and no light state can block the fight from ending.

var room: Node
var lit := true
var spr: Sprite2D
var glow: Sprite2D
var pool: Sprite2D
var ring: CombatMarks.Ring
var half_w := 10.0
var t := 0.0

func setup(r: Node, pos: Vector2) -> void:
	room = r
	position = pos
	var info := SpriteLib.prop_info("floodlight")
	var sc := float(info.scale)
	spr = Sprite2D.new()
	spr.texture = info.texture
	spr.centered = false
	spr.scale = Vector2(sc, sc)
	var anchor: Array = info.anchor
	spr.offset = -Vector2(float(anchor[0]), float(anchor[1])) / sc
	add_child(spr)
	var gtex := SpriteLib.tex("res://assets/fx2/glow_soft.png")
	if gtex:
		var top := float(info.texture.get_height()) * sc
		pool = Sprite2D.new()
		pool.texture = gtex
		pool.material = RoomVisuals.add_material()
		pool.scale = Vector2(240.0 / gtex.get_width(), 84.0 / gtex.get_height())
		pool.position = Vector2(0, 26)
		pool.modulate = Color(1.0, 0.86, 0.55, 0.42)
		pool.z_index = -8
		add_child(pool)
		glow = Sprite2D.new()
		glow.texture = gtex
		glow.material = RoomVisuals.add_material()
		glow.scale = Vector2.ONE * (120.0 / gtex.get_width())
		glow.position = Vector2(0, -top * 0.82)
		glow.modulate = Color(1.0, 0.9, 0.6, 0.75)
		add_child(glow)
	set_lit(true)

func set_lit(on: bool) -> void:
	lit = on
	if glow:
		glow.visible = on
	if pool:
		pool.visible = on
	spr.modulate = Color(1.05, 1.0, 0.9) if on else Color(0.42, 0.44, 0.55)

func _process(dt: float) -> void:
	t += dt
	if lit and glow:
		glow.modulate.a = 0.7 + 0.06 * sin(t * 9.0)

## Soft ring while a dark light is close enough to be worth a look; brighter when Action would switch it on.
func set_guide(near: bool, target: bool, blink: float) -> void:
	if (near or target) and not lit:
		if ring == null:
			ring = CombatMarks.Ring.new()
			add_child(ring)
			move_child(ring, 0)
			ring.position = Vector2(0, 6)
		ring.visible = true
		ring.look(Color(CombatMarks.USE_COL, 0.85 if target else 0.35 + 0.3 * blink), 13.0, 1.8 if target else 1.3)
	elif ring and ring.visible:
		ring.visible = false
