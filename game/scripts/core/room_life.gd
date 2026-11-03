class_name RoomLife
extends Node
## Background life and atmosphere for v2 rooms (docs/visual/ASSET_CONTRACT_V2.md §2b): drifting clouds, lit windows
## with passing silhouettes and TV flicker, distant pedestrians and traffic, trains, pigeons that scatter, birds,
## swaying cloth and signs, animated water, light shafts, neon sign animation, atmospheric haze and a colour grade.
## Purely visual. Effects: Reduced keeps only the cheap, static-feeling parts (windows, signs, sway, water).

const HAZE_SHADER := """shader_type canvas_item;
uniform vec4 haze : source_color = vec4(0.8, 0.7, 0.7, 1.0);
uniform float amount = 0.0;
void fragment() {
	COLOR.rgb = mix(COLOR.rgb, haze.rgb, amount);
}
"""
const GRADE_SHADER := """shader_type canvas_item;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform vec3 lift = vec3(0.0);
uniform vec3 gain = vec3(1.0);
uniform float saturation = 1.0;
uniform float contrast = 1.0;
uniform float vignette = 0.2;
uniform float grain = 0.012;
uniform float bloom = 0.35;
uniform float threshold = 0.68;
uniform float t = 0.0;
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
void fragment() {
	vec3 c = texture(screen_tex, SCREEN_UV).rgb;
	// restrained bloom: only the brightest lights (neon, lamps, lit glass) bleed softly
	vec3 b = textureLod(screen_tex, SCREEN_UV, 2.5).rgb * 0.5 + textureLod(screen_tex, SCREEN_UV, 4.0).rgb * 0.5;
	c += max(b - threshold, 0.0) * bloom * 2.6;
	c = (c - 0.5) * contrast + 0.5;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	c = lift + c * (gain - lift);
	vec2 d = SCREEN_UV - 0.5;
	c *= 1.0 - vignette * smoothstep(0.25, 0.75, dot(d, d) * 1.6);
	c += (hash(SCREEN_UV * 731.0 + t) - 0.5) * grain;
	COLOR = vec4(clamp(c, 0.0, 1.0), 1.0);
}
"""
const WATER_SHADER := """shader_type canvas_item;
render_mode blend_add;
uniform sampler2D noise_tex : repeat_enable, filter_linear;
uniform vec4 tint : source_color = vec4(0.7, 0.9, 1.0, 1.0);
uniform float alpha = 0.35;
uniform float speed = 0.02;
uniform float t = 0.0;
uniform vec2 scale = vec2(4.0, 1.0);
void fragment() {
	vec2 uv = UV * scale;
	float a = texture(noise_tex, uv * vec2(1.0, 3.0) + vec2(t * speed, 0.0)).r;
	float b = texture(noise_tex, uv * vec2(0.7, 2.2) - vec2(t * speed * 0.6, t * speed * 0.15)).r;
	float glint = smoothstep(0.62, 0.8, a * b * 1.9);
	float edge = smoothstep(0.0, 0.08, UV.y) * smoothstep(1.0, 0.85, UV.y);
	COLOR = vec4(tint.rgb, glint * alpha * edge);
}
"""
const SIGN_SHADER := """shader_type canvas_item;
render_mode blend_add;
uniform sampler2D screen_tex : hint_screen_texture, filter_linear;
uniform vec4 col : source_color = vec4(1.0, 0.3, 0.7, 1.0);
uniform float t = 0.0;
uniform int pattern = 0;
uniform float energy = 0.55;
void fragment() {
	float k = 0.0;
	if (pattern == 0) {
		float band = fract(UV.x - t * 0.6);
		k = 0.25 + 0.75 * smoothstep(0.0, 0.1, band) * smoothstep(0.32, 0.12, band);
	} else if (pattern == 1) {
		k = step(0.45, fract(t * 0.9 + floor(UV.x * 5.0) * 0.17));
	} else {
		k = 0.5 + 0.5 * step(0.12, fract(sin(floor(t * 14.0)) * 43758.5));
	}
	vec3 s = texture(screen_tex, SCREEN_UV).rgb;
	float bright = max(s.r, max(s.g, s.b));
	float sat = bright - min(s.r, min(s.g, s.b));
	float tube = smoothstep(0.55, 0.85, bright) * smoothstep(0.12, 0.35, sat + (bright - 0.8) * 2.0);
	COLOR = vec4(mix(s, col.rgb, 0.35) * tube * k * energy, 1.0);
}
"""

var vis: RoomVisuals
var room: Node2D
var meta: Dictionary
var full := true
var t := 0.0
var lanes: Array = []          # [{node, parallax, kind, entry, timer, items:[]}]
var windows: Array = []        # [{root: Control, light: ColorRect, sil: Sprite2D, kind, lit, state, timer, sil_t}]
var sways: Array = []          # [{spr, amp, speed, phase}]
var shaders_t: Array = []      # ShaderMaterials that need `t`
var pigeons: Array = []        # [{node, birds:[{spr, vel, flying, home}], x, y, timer}]
var shafts: Array = []         # [{spr, base}]
var grade_rect: ColorRect
var base_front: Node2D         # drawn above the base layer (parallax 1), still behind actors
var sign_root: Node2D
var pass_timer := 4.0
var passers: Array = []
const PASS_DISTRICTS := ["old_quarter", "canal_market", "neon_mile", "ironworks"]
const PASSERS := ["towna", "townb", "townc", "townd"]
static var _haze_shader: Shader
static var _shaders: Dictionary = {}

static func _shader(code: String) -> Shader:
	if not _shaders.has(code):
		var s := Shader.new()
		s.code = code
		_shaders[code] = s
	return _shaders[code]

func build(v: RoomVisuals, m: Dictionary, bg_root: Node2D, fg_root: Node2D) -> void:
	vis = v
	room = v.room
	meta = m
	full = Settings.effects_full()
	base_front = Node2D.new()
	bg_root.add_child(base_front)
	_apply_haze()
	if meta.has("clouds") and full:
		_make_clouds(meta.clouds, bg_root)
	for e in meta.get("life", []):
		if typeof(e) != TYPE_DICTIONARY:
			continue
		match str(e.get("type", "")):
			"window": _make_window(e)
			"sway": _make_sway(e, fg_root)
			"water": _make_water(e)
			"sign": _make_sign(e)
			"shaft":
				if full: _make_shaft(e)
			"pigeons": _make_pigeons(e)
			"pedestrians", "traffic", "train", "birds":
				if full: _make_lane(e, bg_root)
	if meta.has("grade") and full:
		_make_grade(meta.grade)

# ------------------------------------------------------------------ atmosphere
func _apply_haze() -> void:
	var h: Dictionary = meta.get("haze", {})
	if h.is_empty():
		return
	var col := Color(str(h.get("color", "#c0a090")))
	for L in vis.layers:
		var amt := 0.0
		match str(L.get("name", "")):
			"far": amt = float(h.get("far", 0.0))
			"mid": amt = float(h.get("mid", 0.0))
		if amt <= 0.0:
			continue
		var mat := ShaderMaterial.new()
		mat.shader = _shader(HAZE_SHADER)
		mat.set_shader_parameter("haze", col)
		mat.set_shader_parameter("amount", amt)
		for s in (L.node as Node2D).get_children():
			if s is Sprite2D:
				s.material = mat

func _make_grade(g: Dictionary) -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	room.add_child(layer)
	grade_rect = ColorRect.new()
	grade_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	grade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = _shader(GRADE_SHADER)
	var lift := Color(str(g.get("lift", "#000000")))
	var gain := Color(str(g.get("gain", "#ffffff")))
	mat.set_shader_parameter("lift", Vector3(lift.r, lift.g, lift.b))
	mat.set_shader_parameter("gain", Vector3(gain.r, gain.g, gain.b))
	mat.set_shader_parameter("saturation", clampf(float(g.get("saturation", 1.0)), 0.8, 1.2))
	mat.set_shader_parameter("contrast", clampf(float(g.get("contrast", 1.0)), 0.9, 1.15))
	mat.set_shader_parameter("vignette", clampf(float(g.get("vignette", 0.2)), 0.0, 0.35))
	mat.set_shader_parameter("bloom", clampf(float(g.get("bloom", 0.35)), 0.0, 0.6) * (1.0 if Settings.flash > 0.0 else 0.5))
	grade_rect.material = mat
	layer.add_child(grade_rect)
	shaders_t.append(mat)

# ------------------------------------------------------------------ clouds and parallax lanes
func _insert_at_parallax(bg_root: Node2D, node: Node2D, par: float) -> void:
	bg_root.add_child(node)
	var idx := bg_root.get_child_count() - 1
	for L in vis.layers:
		if float(L.parallax) > par:
			idx = (L.node as Node).get_index()
			break
	bg_root.move_child(node, idx)

func _make_clouds(c: Dictionary, bg_root: Node2D) -> void:
	var lane := {"node": Node2D.new(), "parallax": float(c.get("parallax", 0.08)), "kind": "clouds", "entry": c, "timer": 0.0, "items": []}
	_insert_at_parallax(bg_root, lane.node, lane.parallax)
	var files: Array = c.get("files", [])
	if files.is_empty():
		return
	var yr: Array = c.get("y", [10, 80])
	var sp: Array = c.get("speed", [3, 8])
	var tint := Color(str(c.get("tint", "#ffffff")), float(c.get("alpha", 0.85)))
	var span: float = float(room.view_width()) * 2.0 + 400.0
	for i in int(c.get("count", 5)):
		var tex := SpriteLib.tex(vis._path(str(files[i % files.size()])))
		if tex == null:
			continue
		var s := Sprite2D.new()
		s.texture = tex
		s.scale = Vector2.ONE * 0.5 * randf_range(0.8, 1.15)
		s.modulate = tint
		s.position = Vector2(randf() * span, randf_range(float(yr[0]), float(yr[1])))
		lane.node.add_child(s)
		lane.items.append({"spr": s, "v": randf_range(float(sp[0]), float(sp[1]))})
	lanes.append(lane)

func _make_lane(e: Dictionary, bg_root: Node2D) -> void:
	var lane := {"node": Node2D.new(), "parallax": float(e.get("parallax", 0.5)), "kind": str(e.type), "entry": e, "timer": randf_range(0.0, 3.0), "items": []}
	if lane.kind == "birds":
		lane.parallax = float(e.get("parallax", 0.1))
	_insert_at_parallax(bg_root, lane.node, lane.parallax)
	var hz: Dictionary = meta.get("haze", {})
	if not hz.is_empty() and lane.kind in ["pedestrians", "traffic"]:
		var mat := ShaderMaterial.new()
		mat.shader = _shader(HAZE_SHADER)
		mat.set_shader_parameter("haze", Color(str(hz.get("color", "#c0a090"))))
		mat.set_shader_parameter("amount", clampf(float(hz.get("mid", 0.12)) + 0.08, 0.0, 0.5))
		lane.node.material = mat
		lane.node.use_parent_material = false
	lanes.append(lane)

const WALKERS := ["towna", "townb", "townc", "townd", "ines", "otis", "sal", "hank", "marv", "pip", "rosa", "teddy"]

func _spawn_lane_item(lane: Dictionary, cam_left: float, view_w: float) -> void:
	var e: Dictionary = lane.entry
	var p: float = lane.parallax
	var left := cam_left * p - 80.0
	var right := cam_left * p + view_w + 80.0
	var dir := 1 if randf() < 0.5 else -1
	var x := left if dir > 0 else right
	match lane.kind:
		"pedestrians":
			var who: String = WALKERS[randi() % WALKERS.size()]
			var sheet := SpriteLib.character(who)
			if not sheet.get("v2", false):
				return
			var s := Sprite2D.new()
			s.texture = sheet.texture
			s.centered = false
			s.region_enabled = true
			var k := float(e.get("scale", 0.55)) * float(sheet.scale)
			s.scale = Vector2(k * dir, k)
			s.position = Vector2(x, float(e.get("y", 212)))
			lane.node.add_child(s)
			lane.items.append({"spr": s, "v": randf_range(16.0, 28.0) * dir, "sheet": sheet, "cycle": randf(), "kind": "walker", "scale": k})
		"traffic":
			var files: Array = e.get("files", [])
			if files.is_empty():
				return
			var tex := SpriteLib.tex(vis._path(str(files[randi() % files.size()])))
			if tex == null:
				return
			var s2 := Sprite2D.new()
			s2.texture = tex
			s2.centered = false
			s2.offset = Vector2(-tex.get_width() / 2.0, -tex.get_height())
			s2.scale = Vector2(0.5 * dir, 0.5)
			s2.position = Vector2(x - dir * tex.get_width() * 0.25, float(e.get("y", 196)))
			lane.node.add_child(s2)
			if e.get("lights", false):
				var tw := float(tex.get_width())
				var th := float(tex.get_height())
				_attach_glow(s2, Vector2(tw * 0.46, -th * 0.35), 26.0, Color(1.0, 0.92, 0.7), 0.5)
				_attach_glow(s2, Vector2(-tw * 0.47, -th * 0.37), 14.0, Color(1.0, 0.2, 0.15), 0.45)
			lane.items.append({"spr": s2, "v": randf_range(60.0, 110.0) * dir, "kind": "car"})
		"train":
			var tex2 := SpriteLib.tex(vis._path(str(e.get("file", ""))))
			if tex2 == null:
				return
			var s3 := Sprite2D.new()
			s3.texture = tex2
			s3.centered = false
			s3.offset = Vector2(-tex2.get_width() / 2.0, -tex2.get_height())
			var tk := 0.5 * float(e.get("scale", 1.0))
			s3.scale = Vector2(tk * dir, tk)
			s3.position = Vector2(x - dir * tex2.get_width() * tk * 0.5, float(e.get("y", 120)))
			lane.node.add_child(s3)
			lane.items.append({"spr": s3, "v": 130.0 * dir, "kind": "train"})
		"birds":
			var bt := SpriteLib.tex("res://assets/bg2/_life/bird.png")
			if bt == null:
				return
			var yr: Array = e.get("y", [20, 80])
			var y0 := randf_range(float(yr[0]), float(yr[1]))
			for i in randi_range(2, 5):
				var b := Sprite2D.new()
				b.texture = bt
				b.hframes = 4
				b.scale = Vector2(0.5 * dir, 0.5) * randf_range(0.7, 1.0)
				b.position = Vector2(x - dir * i * randf_range(8, 16), y0 + randf_range(-8, 8))
				b.modulate = Color(0.15, 0.12, 0.18, 0.75)
				lane.node.add_child(b)
				lane.items.append({"spr": b, "v": randf_range(36.0, 48.0) * dir, "kind": "bird", "ph": randf() * 4.0})

func _attach_glow(parent: Node2D, pos: Vector2, r: float, col: Color, en: float) -> void:
	var g := Sprite2D.new()
	var tex := SpriteLib.tex("res://assets/fx2/glow_soft.png")
	if tex == null:
		return
	g.texture = tex
	g.material = RoomVisuals.add_material()
	g.position = pos   # local texel space of the parent sprite
	g.scale = Vector2.ONE * (2.0 * r / tex.get_width()) / parent.scale.abs()
	g.modulate = Color(col.r, col.g, col.b, en)
	parent.add_child(g)

# ------------------------------------------------------------------ windows
func _make_window(e: Dictionary) -> void:
	var r: Array = e.get("rect", [0, 0, 0, 0])
	var rect := Rect2(float(r[0]), float(r[1]), float(r[2]), float(r[3]))
	if rect.size.x < 4 or rect.size.y < 4:
		return
	var root := Control.new()
	root.position = rect.position
	root.size = rect.size
	root.clip_contents = true
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	base_front.add_child(root)
	var light := ColorRect.new()
	light.size = rect.size
	light.mouse_filter = Control.MOUSE_FILTER_IGNORE
	light.color = Color(0, 0, 0, 0)
	root.add_child(light)
	var sil: Sprite2D = null
	var stex := SpriteLib.tex("res://assets/bg2/_life/silhouette.png")
	if stex:
		sil = Sprite2D.new()
		sil.texture = stex
		sil.hframes = 6
		var k := rect.size.y * 0.9 / (stex.get_height())
		sil.scale = Vector2(k, k)
		sil.centered = false
		sil.offset = Vector2(-stex.get_width() / 12.0, -stex.get_height())
		sil.position = Vector2(-999, rect.size.y + 2)
		sil.modulate = Color(0.05, 0.03, 0.06, 0.55)
		root.add_child(sil)
	var kind := str(e.get("kind", "home"))
	var lit := bool(e.get("lit", true))
	windows.append({"root": root, "light": light, "sil": sil, "kind": kind, "lit": lit, "on": lit,
		"timer": randf_range(4.0, 20.0), "sil_x": -999.0, "sil_v": 0.0, "w": rect.size.x, "h": rect.size.y, "ph": randf() * 10.0})

func _update_windows(dt: float) -> void:
	for W in windows:
		var light: ColorRect = W.light
		if W.kind == "tv":
			var f := 0.5 + 0.5 * sin(t * 9.0 + W.ph) * sin(t * 3.3 + W.ph * 2.0)
			light.color = Color(0.45, 0.6, 1.0, 0.12 + 0.18 * f)
		W.timer -= dt
		if W.timer <= 0.0:
			W.timer = randf_range(6.0, 22.0)
			var roll := randf()
			if W.kind != "tv" and W.kind != "shop" and roll < 0.35:
				W.on = not W.on
			elif W.on and W.sil != null and W.sil_v == 0.0:
				var dir := 1.0 if randf() < 0.5 else -1.0
				W.sil_v = dir * randf_range(10.0, 18.0)
				W.sil_x = -20.0 if dir > 0 else W.w + 20.0
		if W.kind != "tv":
			var target := Color(0, 0, 0, 0)
			if W.on and not W.lit:
				target = Color(1.0, 0.8, 0.5, 0.32)
			elif not W.on and W.lit:
				target = Color(0.06, 0.05, 0.12, 0.62)
			light.color = light.color.lerp(target, clampf(dt * 3.0, 0.0, 1.0))
		if W.sil != null and W.sil_v != 0.0:
			W.sil_x += W.sil_v * dt
			var s: Sprite2D = W.sil
			s.position.x = W.sil_x
			s.scale.x = absf(s.scale.y) * signf(W.sil_v)
			s.frame = int(t * 8.0) % 6
			if W.sil_x < -40.0 or W.sil_x > W.w + 40.0:
				W.sil_v = 0.0

# ------------------------------------------------------------------ sway, water, signs, shafts
func _make_sway(e: Dictionary, fg_root: Node2D) -> void:
	var tex := SpriteLib.tex(vis._path(str(e.get("file", ""))))
	if tex == null:
		return
	var s := Sprite2D.new()
	s.texture = tex
	s.centered = false
	var pv: Array = e.get("pivot", [tex.get_width() / 2.0, 0])
	s.offset = -Vector2(float(pv[0]), float(pv[1]))
	s.scale = Vector2(0.5, 0.5)
	s.position = Vector2(float(e.get("x", 0)), float(e.get("y", 0)))
	(fg_root if e.get("front", false) else base_front).add_child(s)
	sways.append({"spr": s, "amp": deg_to_rad(float(e.get("amp", 3.0))), "speed": float(e.get("speed", 1.0)), "ph": randf() * TAU})

static var _noise_tex: NoiseTexture2D
func _make_water(e: Dictionary) -> void:
	var r: Array = e.get("rect", [0, 0, 0, 0])
	if _noise_tex == null:
		var n := FastNoiseLite.new()
		n.seed = 7
		n.frequency = 0.03
		_noise_tex = NoiseTexture2D.new()
		_noise_tex.noise = n
		_noise_tex.seamless = true
		_noise_tex.width = 256
		_noise_tex.height = 256
	var c := ColorRect.new()
	c.position = Vector2(float(r[0]), float(r[1]))
	c.size = Vector2(float(r[2]), float(r[3]))
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = _shader(WATER_SHADER)
	mat.set_shader_parameter("noise_tex", _noise_tex)
	mat.set_shader_parameter("tint", Color(str(e.get("tint", "#bfe6f0"))))
	mat.set_shader_parameter("alpha", clampf(float(e.get("alpha", 0.35)), 0.0, 0.6))
	mat.set_shader_parameter("speed", float(e.get("speed", 12)) / 600.0)
	mat.set_shader_parameter("scale", Vector2(c.size.x / 160.0, maxf(1.0, c.size.y / 40.0)))
	c.material = mat
	base_front.add_child(c)
	shaders_t.append(mat)

func _make_sign(e: Dictionary) -> void:
	if not full:
		return
	if sign_root == null:
		sign_root = Node2D.new()
		base_front.add_child(sign_root)
		var bb := BackBufferCopy.new()
		bb.copy_mode = BackBufferCopy.COPY_MODE_VIEWPORT
		sign_root.add_child(bb)
	var r: Array = e.get("rect", [0, 0, 0, 0])
	var c := ColorRect.new()
	c.position = Vector2(float(r[0]), float(r[1]))
	c.size = Vector2(float(r[2]), float(r[3]))
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := ShaderMaterial.new()
	mat.shader = _shader(SIGN_SHADER)
	mat.set_shader_parameter("col", Color(str(e.get("color", "#ff4fa8"))))
	mat.set_shader_parameter("pattern", {"chase": 0, "blink": 1, "buzz": 2}.get(str(e.get("pattern", "chase")), 0))
	mat.set_shader_parameter("energy", 0.55 if Settings.flash > 0.0 else 0.3)
	c.material = mat
	sign_root.add_child(c)
	shaders_t.append(mat)

func _make_shaft(e: Dictionary) -> void:
	var tex := SpriteLib.tex("res://assets/fx2/light_cone.png")
	if tex == null:
		return
	var s := Sprite2D.new()
	s.texture = tex
	s.material = RoomVisuals.add_material()
	s.centered = false
	s.offset = Vector2(-tex.get_width() / 2.0, 0)
	s.position = Vector2(float(e.get("x", 0)), float(e.get("y", 0)))
	s.scale = Vector2(float(e.get("w", 90)) / tex.get_width(), float(e.get("h", 240)) / tex.get_height())
	s.rotation = deg_to_rad(float(e.get("angle", 0)))
	var col := Color(str(e.get("color", "#ffe0b0")))
	var en := clampf(float(e.get("energy", 0.18)), 0.0, 0.3)
	s.modulate = Color(col.r, col.g, col.b, en)
	if vis.room.get("glow_front"):
		vis.room.glow_front.add_child(s)
	else:
		base_front.add_child(s)
	shafts.append({"spr": s, "base": en, "ph": randf() * 10.0})
	vis._make_ambient({"type": "dust_motes", "x": float(e.get("x", 0)), "y": float(e.get("y", 0)) + float(e.get("h", 240)) * 0.5,
		"w": float(e.get("w", 90)) * 0.8, "h": float(e.get("h", 240)) * 0.8, "rate": 0.6}, base_front, base_front)

# ------------------------------------------------------------------ pigeons
func _make_pigeons(e: Dictionary) -> void:
	var tex := SpriteLib.tex("res://assets/bg2/_life/pigeon.png")
	if tex == null:
		return
	var flock := {"x": float(e.get("x", 0)), "y": float(e.get("y", 300)), "birds": [], "away": 0.0}
	for i in int(e.get("count", 4)):
		var s := Sprite2D.new()
		s.texture = tex
		s.hframes = 8
		s.centered = false
		s.offset = Vector2(-tex.get_width() / 16.0, -tex.get_height())
		s.scale = Vector2(0.5 * (1 if randf() < 0.5 else -1), 0.5)
		var home := Vector2(flock.x + randf_range(-22, 22), flock.y + randf_range(-6, 6))
		s.position = home
		base_front.add_child(s)
		flock.birds.append({"spr": s, "home": home, "vel": Vector2.ZERO, "flying": false, "t": randf() * 3.0})
	pigeons.append(flock)

func _update_pigeons(dt: float) -> void:
	var p: Node2D = room.player if room.get("player") else null
	for F in pigeons:
		var near := p != null and p.position.distance_to(Vector2(F.x, F.y)) < 60.0
		if not F.get("scattered", false) and near:
			F.scattered = true
			F.away = randf_range(18.0, 35.0)
			for B in F.birds:
				var s0: Sprite2D = B.spr
				B.flying = true
				var away_dir := signf(s0.position.x - p.position.x)
				if away_dir == 0.0:
					away_dir = 1.0
				B.vel = Vector2(away_dir * randf_range(50, 90), randf_range(-90, -60))
				s0.scale.x = absf(s0.scale.x) * away_dir
		elif F.get("scattered", false):
			F.away -= dt
			if F.away <= 0.0 and not near:
				F.scattered = false
				for B in F.birds:
					B.flying = false
					(B.spr as Sprite2D).position = B.home
					(B.spr as Sprite2D).modulate.a = 1.0
		for B in F.birds:
			var s: Sprite2D = B.spr
			if B.flying:
				s.position += B.vel * dt
				B.vel.y -= 10.0 * dt
				s.frame = 4 + int(t * 14.0 + B.t) % 4
				s.modulate.a = maxf(0.0, s.modulate.a - dt * 0.4)
			else:
				B.t += dt
				s.frame = (2 + int(B.t * 3.0) % 2) if fmod(B.t, 5.0) > 3.6 else int(B.t * 1.5) % 2

# ------------------------------------------------------------------ per frame
func update(cam_left: float, view_w: float, dt: float) -> void:
	t += dt
	for m in shaders_t:
		(m as ShaderMaterial).set_shader_parameter("t", t)
	for L in lanes:
		var node: Node2D = L.node
		node.position.x = cam_left * (1.0 - float(L.parallax))
		var lo := cam_left * float(L.parallax) - 160.0
		var hi := cam_left * float(L.parallax) + view_w + 160.0
		if L.kind == "clouds":
			var span := view_w * 2.0 + 400.0
			for it in L.items:
				var s: Sprite2D = it.spr
				s.position.x += float(it.v) * dt
				if s.position.x > hi + 200.0:
					s.position.x -= span
				elif s.position.x < lo - 200.0:
					s.position.x += span
			continue
		var e: Dictionary = L.entry
		L.timer -= dt
		if L.timer <= 0.0:
			if L.kind == "train":
				var iv: Array = e.get("interval", [25, 45])
				L.timer = randf_range(float(iv[0]), float(iv[1]))
			else:
				L.timer = -log(maxf(randf(), 0.001)) / maxf(float(e.get("rate", 0.1)), 0.01)
			_spawn_lane_item(L, cam_left, view_w)
		for it in L.items.duplicate():
			var s2: Sprite2D = it.spr
			if not is_instance_valid(s2):
				L.items.erase(it)
				continue
			s2.position.x += float(it.v) * dt
			match it.kind:
				"walker":
					var sheet: Dictionary = it.sheet
					var ad := SpriteLib.anim_def(sheet, "walk")
					var fr: PackedInt32Array = ad.frames
					if fr.size() > 0:
						var stride := maxf(float(ad.get("stride", 36.0)) * float(it.scale) / float(sheet.scale), 6.0)
						it.cycle = fposmod(float(it.cycle) + absf(float(it.v)) * dt / stride, 1.0)
						var f := int(fr[int(float(it.cycle) * fr.size()) % fr.size()])
						s2.region_rect = sheet.rects[f]
						s2.offset = sheet.offs[f]
				"bird":
					it.ph = float(it.ph) + dt
					s2.frame = int(float(it.ph) * 10.0) % 4
			if s2.position.x < lo - 300.0 or s2.position.x > hi + 300.0:
				s2.queue_free()
				L.items.erase(it)
	_update_windows(dt)
	for S in sways:
		(S.spr as Sprite2D).rotation = S.amp * sin(t * S.speed + S.ph) + S.amp * 0.3 * sin(t * S.speed * 2.3 + S.ph)
	for SH in shafts:
		var s3: Sprite2D = SH.spr
		s3.modulate.a = float(SH.base) * (0.85 + 0.15 * sin(t * 0.5 + SH.ph))
	_update_pigeons(dt)
	_update_passersby(dt)

## Townsfolk strolling along the back of the sidewalk when the street is quiet (neighbourhood districts only).
func _update_passersby(dt: float) -> void:
	passers = passers.filter(func(n): return is_instance_valid(n) and not n.is_queued_for_deletion())
	if room.interior or not (str(room.district) in PASS_DISTRICTS) or room.cutscene or room.boss_active or room.combat_active():
		return
	if room.player == null or Story.busy:
		return
	pass_timer -= dt
	if pass_timer > 0.0 or passers.size() >= (3 if full else 1):
		return
	pass_timer = randf_range(5.0, 12.0)
	var dir := 1 if randf() < 0.5 else -1
	var x: float = room.cam_left() - 30.0 if dir > 0 else room.cam_right() + 30.0
	x = clampf(x, 16.0, room.width - 16.0)
	var y: float = room.walk_top + randf_range(3.0, 16.0)
	var who: String = PASSERS[randi() % PASSERS.size()]
	var n: NPC = room.spawn_npc("passerby", who, Vector2(x, y), {"mode": "pass", "talk": false, "facing": dir})
	n.pass_dir = dir
	n.walk_speed = randf_range(34.0, 46.0)
	passers.append(n)
