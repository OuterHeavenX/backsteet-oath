class_name SpriteLib
extends RefCounted
## Loads character sheets, icons, props, weapons and FX textures with caching.
## Missing art falls back to generated placeholders so the game never crashes on a missing file.

const CHAR_DIR := "res://assets/sprites/characters/"
const CHAR2_DIR := "res://assets/sprites/chars/"
const ANIMS := {
	"idle": [0, 2], "walk": [2, 4], "run": [6, 4], "punch_a": [10, 2], "punch_b": [12, 2], "punch_c": [14, 3],
	"kick": [17, 3], "kick_c": [20, 3], "jump": [23, 2], "jump_kick": [25, 1], "jump_punch": [26, 1],
	"run_punch": [27, 1], "dropkick": [28, 1], "guard": [29, 1], "hurt": [30, 2], "knockdown": [32, 3],
	"getup": [35, 2], "dizzy": [37, 2], "pickup": [39, 1], "carry": [40, 2], "throw": [42, 2], "swing": [44, 3],
	"sweep": [47, 2], "rising_kick": [49, 2], "slam": [51, 1], "victory": [52, 2], "talk": [54, 2], "cower": [56, 2]
}

static var _chars: Dictionary = {}
static var _tex: Dictionary = {}
static var _json: Dictionary = {}

const LOOPS := ["idle", "walk", "run", "dizzy", "talk", "victory", "cower", "carry", "carry_walk"]
const V1_TICKS := {"idle": 30, "walk": 8, "run": 5, "dizzy": 12, "talk": 14, "victory": 16, "cower": 6, "carry": 9}
const ALIASES := {
	"hurt": ["hurt_high"], "hurt_high": ["hurt"], "hurt_low": ["hurt"], "hurt_back": ["hurt_high", "hurt"],
	"carry_walk": ["carry"], "land": [], "jump": ["idle"]
}

static func _read_json(path: String) -> Variant:
	if _json.has(path):
		return _json[path]
	var v: Variant = null
	if FileAccess.file_exists(path):
		v = JSON.parse_string(FileAccess.get_file_as_string(path))
	_json[path] = v
	return v

## Frees per-room caches (character atlases, backgrounds) so texture memory stays bounded on the web.
static func clear_room_cache() -> void:
	_chars.clear()
	for k in _tex.keys():
		if str(k).contains("/bg2/") or str(k).contains("/sprites/chars/"):
			_tex.erase(k)

## Normalised character sheet (v2 packed atlas or v1 grid):
## {v2, texture, scale, rects[Rect2 tx], offs[Vector2 tx], hand[[Vector2 u, deg, front]], head[Vector2 u],
##  anims{name: {frames, fps, loop, stride, contact}}, height}
static func character(id: String) -> Dictionary:
	if _chars.has(id):
		return _chars[id]
	var data: Dictionary
	var meta2 = _read_json(CHAR2_DIR + id + ".json")
	if typeof(meta2) == TYPE_DICTIONARY and ResourceLoader.exists(CHAR2_DIR + id + ".png"):
		data = _char_v2(id, meta2)
	else:
		data = _char_v1(id)
	_chars[id] = data
	return data

static func _char_v2(id: String, meta: Dictionary) -> Dictionary:
	var dens := float(meta.get("density", 2))
	var sc := 1.0 / dens
	var rects: Array = []
	var offs: Array = []
	for f in meta.get("frames", []):
		rects.append(Rect2(float(f[0]), float(f[1]), float(f[2]), float(f[3])))
		offs.append(Vector2(float(f[4]), float(f[5])))
	var hand: Array = []
	for h in meta.get("hand", []):
		hand.append([Vector2(float(h[0]), float(h[1])) * sc, float(h[2]) if h.size() > 2 else 0.0, int(h[3]) if h.size() > 3 else 1])
	var head: Array = []
	for h in meta.get("head", []):
		head.append(Vector2(float(h[0]), float(h[1])) * sc)
	var anims := {}
	var src: Dictionary = meta.get("anims", {})
	for k in src:
		var a: Dictionary = src[k]
		var fr := PackedInt32Array()
		for i in a.get("frames", []):
			fr.append(int(i))
		anims[k] = {"frames": fr, "fps": float(a.get("fps", 10)), "loop": bool(a.get("loop", k in LOOPS)),
			"stride": float(a.get("stride", 0.0)), "contact": int(a.get("contact", mini(1, fr.size() - 1)))}
	return {"v2": true, "texture": load(CHAR2_DIR + id + ".png"), "scale": sc, "rects": rects, "offs": offs,
		"hand": hand, "head": head, "anims": anims, "height": float(meta.get("height", 96)) * sc}

static func _char_v1(id: String) -> Dictionary:
	var png := CHAR_DIR + id + ".png"
	var tex_: Texture2D = null
	var anims_src: Dictionary = ANIMS
	var hand_src: Array = []
	var cell := Vector2i(64, 64)
	var anchor := Vector2(32, 60)
	var columns := 8
	if ResourceLoader.exists(png):
		tex_ = load(png)
		var meta = _read_json(CHAR_DIR + id + ".json")
		if typeof(meta) == TYPE_DICTIONARY:
			anims_src = meta.get("anims", ANIMS)
			hand_src = meta.get("hand", [])
			var c: Array = meta.get("cell", [64, 64])
			cell = Vector2i(int(c[0]), int(c[1]))
			var an: Array = meta.get("anchor", [32, 60])
			anchor = Vector2(an[0], an[1])
			columns = int(meta.get("columns", 8))
	else:
		tex_ = _placeholder_sheet(id)
	var rows := maxi(1, int(tex_.get_height() / cell.y)) if tex_ else 8
	var rects: Array = []
	var offs: Array = []
	for i in columns * rows:
		rects.append(Rect2((i % columns) * cell.x, (i / columns) * cell.y, cell.x, cell.y))
		offs.append(-anchor)
	var hand: Array = []
	for h in hand_src:
		hand.append([Vector2(float(h[0]) - anchor.x, float(h[1]) - anchor.y), float(h[2]), 1])
	var anims := {}
	for k in anims_src:
		var a: Array = anims_src[k]
		var fr := PackedInt32Array()
		for i in int(a[1]):
			fr.append(int(a[0]) + i)
		anims[k] = {"frames": fr, "fps": 60.0 / float(V1_TICKS.get(k, 8)), "loop": k in LOOPS, "stride": 0.0,
			"contact": mini(1, fr.size() - 1)}
	return {"v2": false, "texture": tex_, "scale": 1.0, "rects": rects, "offs": offs, "hand": hand, "head": [],
		"anims": anims, "height": 46.0}

## Anim lookup with fallbacks (v1 sheets lack the v2-only anims).
static func anim_def(sheet: Dictionary, name: String) -> Dictionary:
	var anims: Dictionary = sheet.get("anims", {})
	if anims.has(name):
		return anims[name]
	for alt in ALIASES.get(name, []):
		if anims.has(alt):
			return anims[alt]
	return anims.get("idle", {"frames": PackedInt32Array([0]), "fps": 4.0, "loop": true, "stride": 0.0, "contact": 0})

static func tex(path: String) -> Texture2D:
	if _tex.has(path):
		return _tex[path]
	var t: Texture2D = null
	if ResourceLoader.exists(path):
		t = load(path)
	_tex[path] = t
	return t

static func icon(id: String) -> Texture2D:
	var t := tex("res://assets/icons2/%s.png" % id)
	if t == null:
		t = tex("res://assets/icons/%s.png" % id)
	if t == null:
		t = _placeholder_box("icon_" + id, Vector2i(16, 16), Color(0.94, 0.75, 0.25))
	return t

static func ui(id: String) -> Texture2D:
	return tex("res://assets/ui/%s.png" % id)

static func ui2(id: String) -> Texture2D:
	var t := tex("res://assets/ui2/%s.png" % id)
	return t if t else tex("res://assets/ui/%s.png" % id)

static func ui2_meta() -> Dictionary:
	var m = _read_json("res://assets/ui2/ui.json")
	return m if typeof(m) == TYPE_DICTIONARY else {}

static func props2_meta() -> Dictionary:
	var m = _read_json("res://assets/props2/props.json")
	return m if typeof(m) == TYPE_DICTIONARY else {}

## {texture, scale, anchor (u), footprint (u)} for a prop type, preferring v2 art.
static func prop_info(type: String) -> Dictionary:
	var m2: Dictionary = props2_meta()
	var t2 := tex("res://assets/props2/%s.png" % type)
	if t2 and m2.has(type):
		var e: Dictionary = m2[type]
		var d := float(e.get("density", 2))
		return {"texture": t2, "scale": 1.0 / d, "anchor": e.get("anchor", [t2.get_width() / (2.0 * d), t2.get_height() / d]),
			"footprint": e.get("footprint", [t2.get_width() / d - 4, 8])}
	var t := prop(type)
	var meta: Dictionary = Content.props_meta.get(type, {})
	return {"texture": t, "scale": 1.0, "anchor": meta.get("anchor", [t.get_width() / 2.0, t.get_height()]),
		"footprint": meta.get("footprint", [t.get_width() - 4, 8])}

static func prop(type: String) -> Texture2D:
	var t := tex("res://assets/props/%s.png" % type)
	if t == null:
		var meta: Dictionary = Content.props_meta.get(type, {})
		var fp: Array = meta.get("footprint", [24, 10])
		var size := Vector2i(maxi(int(fp[0]), 10), 28 if int(fp[1]) > 0 else 40)
		t = _placeholder_box("prop_" + type, size, Color(0.55, 0.4, 0.3))
	return t

static func weapons2_meta() -> Dictionary:
	var m = _read_json("res://assets/weapons2/weapons.json")
	if typeof(m) == TYPE_DICTIONARY:
		return m.get("weapons", m)
	return {}

## {texture, scale, grip (tx), prop (bool)} for a held weapon, preferring v2 art.
static func weapon_info(id: String) -> Dictionary:
	var w: Dictionary = Content.weapon(id)
	var spr: String = w.get("sprite", id)
	if spr.begins_with("prop:"):
		var p := prop_info(spr.substr(5))
		var t: Texture2D = p.texture
		return {"texture": t, "scale": p.scale, "grip": Vector2(t.get_width() / 2.0, t.get_height()), "prop": true}
	var m2: Dictionary = weapons2_meta()
	var t2 := tex("res://assets/weapons2/%s.png" % spr)
	if t2 and m2.has(spr):
		var e: Dictionary = m2[spr]
		var g: Array = e.get("grip", [6, t2.get_height() / 2.0])
		return {"texture": t2, "scale": 1.0 / float(e.get("density", 2)), "grip": Vector2(g[0], g[1]), "prop": false}
	return {"texture": weapon(id), "scale": 1.0, "grip": weapon_grip(id), "prop": false}

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

## v2 effect strip: {texture, cell, count, anchor (tx), fps, additive, scale}; empty if missing.
static func fx2(id: String) -> Dictionary:
	var all = _read_json("res://assets/fx2/fx.json")
	if typeof(all) != TYPE_DICTIONARY or not all.has(id):
		return {}
	var e: Dictionary = all[id]
	var t := tex("res://assets/fx2/%s" % str(e.get("file", id + ".png")))
	if t == null:
		return {}
	var c: Array = e.get("cell", [t.get_width(), t.get_height()])
	var an: Array = e.get("anchor", [float(c[0]) / 2.0, float(c[1]) / 2.0])
	return {"texture": t, "cell": Vector2(c[0], c[1]), "count": int(e.get("count", 1)), "anchor": Vector2(an[0], an[1]),
		"fps": float(e.get("fps", 24)), "additive": bool(e.get("additive", false)), "scale": 1.0 / float(e.get("density", 2))}

static func pickup(id: String) -> Dictionary:
	var m2 = _read_json("res://assets/pickups2/pickups.json")
	var t2 := tex("res://assets/pickups2/%s.png" % id)
	if t2 and typeof(m2) == TYPE_DICTIONARY:
		var src: Dictionary = m2.get("pickups", m2)
		var e: Dictionary = src.get(id, {})
		var d := float(e.get("density", 2))
		var fr2: Array = e.get("frame", [t2.get_width(), t2.get_height()])
		return {"texture": t2, "frame": Vector2i(int(fr2[0]), int(fr2[1])), "frames": int(e.get("frames", 1)), "scale": 1.0 / d}
	var meta: Dictionary = Content.pickup_meta.get(id, {})
	var t := tex("res://assets/pickups/%s.png" % id)
	if t == null:
		t = _placeholder_box("pk_" + id, Vector2i(10, 8), Color(0.48, 0.94, 0.29))
		return {"texture": t, "frame": Vector2i(10, 8), "frames": 1, "scale": 1.0}
	var fr: Array = meta.get("frame", [t.get_width(), t.get_height()])
	return {"texture": t, "frame": Vector2i(int(fr[0]), int(fr[1])), "frames": int(meta.get("frames", 1)), "scale": 1.0}

## {texture, size (tx per expression), v2}
static func portrait_info(id: String) -> Dictionary:
	var t2 := tex("res://assets/portraits2/%s.png" % id)
	if t2:
		return {"texture": t2, "size": t2.get_height(), "v2": true}
	var t := tex("res://assets/portraits/%s.png" % id)
	return {"texture": t, "size": t.get_height() if t else 64, "v2": false}

static func portrait(id: String) -> Texture2D:
	return portrait_info(id).texture

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
