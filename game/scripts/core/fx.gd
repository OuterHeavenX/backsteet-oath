class_name FX
extends Node2D
## Sprite-strip effects, floating text and debris.

var frames := 1
var frame_ticks := 4
var life := -1
var t := 0
var spr: Sprite2D
var follow: Node2D = null
var vel := Vector2.ZERO
var grav := 0.0
var fade := false
var label: Label
var loop := false

const V2_NAME := {
	"hit_spark": "hit_light", "block_spark": "block", "perfect_flash": "perfect_block", "dust": "dust_fall",
	"land_dust": "dust_land", "stars": "stars_dizzy", "smoke": "smoke_puff", "debris_wood": "chip_wood",
	"debris_glass": "shard_glass", "debris_metal": "bit_metal"
}

static func has_v2(id: String) -> bool:
	return not SpriteLib.fx2(V2_NAME.get(id, id)).is_empty()

static func make_strip(id: String) -> FX:
	var f := FX.new()
	f.spr = Sprite2D.new()
	f.add_child(f.spr)
	var v2 := SpriteLib.fx2(V2_NAME.get(id, id))
	if not v2.is_empty():
		f.spr.texture = v2.texture
		f.frames = int(v2.count)
		f.spr.hframes = maxi(1, f.frames)
		f.spr.centered = false
		f.spr.offset = -v2.anchor
		f.spr.scale = Vector2(v2.scale, v2.scale)
		f.frame_ticks = maxi(1, int(round(60.0 / maxf(float(v2.fps), 1.0))))
		if v2.additive:
			f.spr.material = RoomVisuals.add_material()
		if v2.loop or id in ["stars", "stars_dizzy", "charge_glow"]:
			f.loop = true
		return f
	var info := SpriteLib.fx(id)
	if info.is_empty():
		f.spr.texture = _fallback_tex(id)
		f.frames = 1
		f.life = 12
	else:
		f.spr.texture = info.texture
		f.frames = int(info.frames)
		f.spr.hframes = f.frames
	f.frame_ticks = 4 if id not in ["stars", "charge_glow"] else 6
	return f

static var _fb: Dictionary = {}
static func _fallback_tex(id: String) -> Texture2D:
	if _fb.has(id):
		return _fb[id]
	var size := 12 if id != "shockwave" else 48
	var img := Image.create(size, size / (4 if id == "shockwave" else 1), false, Image.FORMAT_RGBA8)
	var col := Color(1, 0.95, 0.6) if id.begins_with("hit") else Color(0.85, 0.8, 0.7, 0.8)
	if id == "exclaim":
		col = Color(1, 0.3, 0.2)
	img.fill(Color(0, 0, 0, 0))
	var c := Vector2(img.get_width() / 2.0, img.get_height() / 2.0)
	for y in img.get_height():
		for x in img.get_width():
			if Vector2(x, y).distance_to(c) < minf(c.x, c.y):
				img.set_pixel(x, y, col)
	var tex := ImageTexture.create_from_image(img)
	_fb[id] = tex
	return tex

func _physics_process(_d: float) -> void:
	t += 1
	if spr and frames > 1:
		var f := int(t / frame_ticks)
		if life < 0 and f >= frames and not loop:
			queue_free()
			return
		spr.frame = f % frames
	elif life < 0 and t > frames * frame_ticks + 8:
		queue_free()
		return
	if vel != Vector2.ZERO or grav != 0.0:
		vel.y += grav * Actor.DT
		position += vel * Actor.DT
	if fade:
		modulate.a = clampf(1.0 - float(t) / float(maxi(life, 1)), 0.0, 1.0)
	if life >= 0 and t >= life:
		queue_free()
