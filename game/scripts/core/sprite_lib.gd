class_name SpriteLib
extends RefCounted
## Loads character sheets, icons, props, weapons and FX textures with caching.
## Missing art falls back to generated placeholders so the game never crashes on a missing file.

const CHAR_DIR := "res://assets/sprites/characters/"
const ANIMS := {
	"idle": [0, 2], "walk": [2, 4], "run": [6, 4], "punch_a": [10, 2], "punch_b": [12, 2], "punch_c": [14, 3],
	"kick": [17, 3], "kick_c": [20, 3], "jump": [23, 2], "jump_kick": [25, 1], "jump_punch": [26, 1],
	"run_punch": [27, 1], "dropkick": [28, 1], "guard": [29, 1], "hurt": [30, 2], "knockdown": [32, 3],
	"getup": [35, 2], "dizzy": [37, 2], "pickup": [39, 1], "carry": [40, 2], "throw": [42, 2], "swing": [44, 3],
	"sweep": [47, 2], "rising_kick": [49, 2], "slam": [51, 1], "victory": [52, 2], "talk": [54, 2], "cower": [56, 2]
}

static var _chars: Dictionary = {}
static var _tex: Dictionary = {}

## Returns {texture, anims, hand, cell, anchor}
static func character(id: String) -> Dictionary:
	if _chars.has(id):
		return _chars[id]
	var png := CHAR_DIR + id + ".png"
	var js := CHAR_DIR + id + ".json"
	var data := {"texture": null, "anims": ANIMS, "hand": [], "cell": Vector2i(64, 64), "anchor": Vector2(32, 60), "columns": 8}
	if ResourceLoader.exists(png):
		data.texture = load(png)
		if FileAccess.file_exists(js):
			var meta = JSON.parse_string(FileAccess.get_file_as_string(js))
			if typeof(meta) == TYPE_DICTIONARY:
				if meta.has("anims"):
					data.anims = meta.anims
				data.hand = meta.get("hand", [])
				var c: Array = meta.get("cell", [64, 64])
				data.cell = Vector2i(int(c[0]), int(c[1]))
				var a: Array = meta.get("anchor", [32, 60])
				data.anchor = Vector2(a[0], a[1])
				data.columns = int(meta.get("columns", 8))
	else:
		data.texture = _placeholder_sheet(id)
	_chars[id] = data
	return data

static func tex(path: String) -> Texture2D:
	if _tex.has(path):
		return _tex[path]
	var t: Texture2D = null
	if ResourceLoader.exists(path):
		t = load(path)
	_tex[path] = t
	return t

static func icon(id: String) -> Texture2D:
	var t := tex("res://assets/icons/%s.png" % id)
	if t == null:
		t = _placeholder_box("icon_" + id, Vector2i(16, 16), Color(0.94, 0.75, 0.25))
	return t

static func ui(id: String) -> Texture2D:
	return tex("res://assets/ui/%s.png" % id)

static func prop(type: String) -> Texture2D:
	var t := tex("res://assets/props/%s.png" % type)
	if t == null:
		var meta: Dictionary = Content.props_meta.get(type, {})
		var fp: Array = meta.get("footprint", [24, 10])
		var size := Vector2i(maxi(int(fp[0]), 10), 28 if int(fp[1]) > 0 else 40)
		t = _placeholder_box("prop_" + type, size, Color(0.55, 0.4, 0.3))
	return t

static func weapon(id: String) -> Texture2D:
	var w: Dictionary = Content.weapon(id)
	var spr: String = w.get("sprite", id)
	if spr.begins_with("prop:"):
		return prop(spr.substr(5))
	var t := tex("res://assets/weapons/%s.png" % spr)
	if t == null:
		t = _placeholder_box("w_" + id, Vector2i(24, 6), Color(0.7, 0.7, 0.75))
	return t

static func weapon_grip(id: String) -> Vector2:
	var w: Dictionary = Content.weapon(id)
	var spr: String = w.get("sprite", id)
	if spr.begins_with("prop:"):
		var t := prop(spr.substr(5))
		return Vector2(t.get_width() / 2.0, t.get_height())
	var meta: Dictionary = Content.weapon_sprites.get(spr, {})
	if meta.has("grip"):
		return Vector2(meta.grip[0], meta.grip[1])
	var t2 := weapon(id)
	return Vector2(3, t2.get_height() / 2.0)

static func fx(id: String) -> Dictionary:
	var meta: Dictionary = Content.fx_meta.get(id, {})
	var t := tex("res://assets/fx/%s.png" % id)
	if t == null:
		return {}
	var fr: Array = meta.get("frame", [t.get_height(), t.get_height()])
	return {"texture": t, "frame": Vector2i(int(fr[0]), int(fr[1])), "frames": int(meta.get("frames", 1))}

static func pickup(id: String) -> Dictionary:
	var meta: Dictionary = Content.pickup_meta.get(id, {})
	var t := tex("res://assets/pickups/%s.png" % id)
	if t == null:
		t = _placeholder_box("pk_" + id, Vector2i(10, 8), Color(0.48, 0.94, 0.29))
		return {"texture": t, "frame": Vector2i(10, 8), "frames": 1}
	var fr: Array = meta.get("frame", [t.get_width(), t.get_height()])
	return {"texture": t, "frame": Vector2i(int(fr[0]), int(fr[1])), "frames": int(meta.get("frames", 1))}

static func portrait(id: String) -> Texture2D:
	return tex("res://assets/portraits/%s.png" % id)

# ---------------------------------------------------------------- placeholders
static func _placeholder_box(key: String, size: Vector2i, col: Color) -> Texture2D:
	if _tex.has("ph:" + key):
		return _tex["ph:" + key]
	var img := Image.create(size.x, size.y, false, Image.FORMAT_RGBA8)
	img.fill(col)
	for x in size.x:
		img.set_pixel(x, 0, Color(0.1, 0.07, 0.12))
		img.set_pixel(x, size.y - 1, Color(0.1, 0.07, 0.12))
	for y in size.y:
		img.set_pixel(0, y, Color(0.1, 0.07, 0.12))
		img.set_pixel(size.x - 1, y, Color(0.1, 0.07, 0.12))
	var t := ImageTexture.create_from_image(img)
	_tex["ph:" + key] = t
	return t

static func _placeholder_sheet(id: String) -> Texture2D:
	var h := hash(id)
	var body := Color.from_hsv(float(h % 360) / 360.0, 0.55, 0.85)
	var img := Image.create(512, 512, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for f in 58:
		var cx := (f % 8) * 64
		var cy := (f / 8) * 64
		var lying := f >= 33 and f <= 34
		if lying:
			img.fill_rect(Rect2i(cx + 10, cy + 50, 44, 10), body)
			img.fill_rect(Rect2i(cx + 44, cy + 46, 14, 14), Color(0.96, 0.79, 0.63))
		else:
			img.fill_rect(Rect2i(cx + 24, cy + 30, 16, 30), body)
			img.fill_rect(Rect2i(cx + 21, cy + 12, 22, 20), Color(0.96, 0.79, 0.63))
			img.fill_rect(Rect2i(cx + 21, cy + 10, 22, 6), Color(0.16, 0.12, 0.14))
			img.fill_rect(Rect2i(cx + 36, cy + 20, 3, 3), Color(0.1, 0.07, 0.12))
			if f in [11, 13, 15, 27]:
				img.fill_rect(Rect2i(cx + 38, cy + 34, 14, 5), body)
			if f in [18, 21, 25, 28]:
				img.fill_rect(Rect2i(cx + 38, cy + 44, 16, 5), body.darkened(0.3))
	return ImageTexture.create_from_image(img)
