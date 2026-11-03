class_name RoomVisuals
extends Node
## v2 room presentation (docs/visual/ASSET_CONTRACT_V2.md §2): parallax layers, foreground framing with fade,
## an authored lightmap, additive glows with flicker, rim-light queries, cast-shadow and reflection data, and
## ambient emitters. Purely visual: nothing here touches collision or gameplay state.

const ADD_MAT_KEY := "add"
const AMBIENT_TYPES := ["steam", "drip", "smoke", "sparks", "paper", "leaves", "pigeons", "water_shimmer", "fan",
	"dust_motes", "embers"]

var room: Node2D
var v2 := false
var dir := ""
var layers: Array = []        # [{node: Node2D, parallax: float, repeat: bool, spr: Sprite2D, w_tx: float}]
var fg: Array = []            # [{spr: Sprite2D, x, y, parallax, fade, alpha}]
var glows: Array = []         # [{spr, x, y, r, color, energy, flicker, phase, front}]
var light_img: Image
var light_cell := 8.0
var rim_default := {"color": Color(1.0, 0.8, 0.6), "dir": Vector2(-1.0, -0.35).normalized(), "strength": 0.0}
var cast_shadow := {}
var reflects: Array = []      # [{rect: Rect2, alpha: float}]
var ambient_nodes: Array = []
var t := 0.0
var darkness := 1.0          # scene light multiplier (boss "lights out"); 1 = normal
var _dark_target := 1.0
var _dark_speed := 1.0
var bg_root_ref: Node2D
var life: RoomLife
var fg_root_ref: Node2D
static var _add_mat: CanvasItemMaterial

static func has_v2(room_id: String) -> bool:
	return FileAccess.file_exists("res://assets/bg2/%s/room.json" % room_id)

static func add_material() -> CanvasItemMaterial:
	if _add_mat == null:
		_add_mat = CanvasItemMaterial.new()
		_add_mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	return _add_mat

func build(r: Node2D, bg_root: Node2D, glow_back: Node2D, glow_front: Node2D, fg_root: Node2D) -> bool:
	room = r
	bg_root_ref = bg_root
	fg_root_ref = fg_root
	dir = "res://assets/bg2/%s/" % room.room_id
	var meta = JSON.parse_string(FileAccess.get_file_as_string(dir + "room.json")) if has_v2(room.room_id) else null
	if typeof(meta) != TYPE_DICTIONARY:
		return false
	v2 = true
	var dens := float(meta.get("density", 2))
	var sc := 1.0 / dens
	for L in meta.get("layers", []):
		if not _visible_by_state(L):
			continue
		var node := Node2D.new()
		bg_root.add_child(node)
		var par := float(L.get("parallax", 1.0))
		var rep := bool(L.get("repeat", false))
		var entry := {"node": node, "parallax": par, "repeat": rep, "spr": null, "w_tx": 0.0, "y": float(L.get("y", 0)), "name": str(L.get("name", ""))}
		var x_tx := 0.0
		for f in L.get("files", []):
			var tex := SpriteLib.tex(_path(str(f)))
			if tex == null:
				continue
			var s := Sprite2D.new()
			s.texture = tex
			s.centered = false
			s.scale = Vector2(sc, sc)
			if rep:
				s.texture_repeat = CanvasItem.TEXTURE_REPEAT_ENABLED
				s.region_enabled = true
				entry.spr = s
				entry.w_tx = float(tex.get_width())
			s.position = Vector2(x_tx * sc, float(L.get("y", 0)))
			x_tx += tex.get_width()
			node.add_child(s)
		layers.append(entry)
	for F in meta.get("fg", []):
		if not _visible_by_state(F):
			continue
		var tex2 := SpriteLib.tex(_path(str(F.get("file", ""))))
		if tex2 == null:
			continue
		var s2 := Sprite2D.new()
		s2.texture = tex2
		s2.centered = false
		s2.scale = Vector2(sc, sc)
		s2.offset = Vector2(-tex2.get_width() / 2.0, -tex2.get_height())
		fg_root.add_child(s2)
		fg.append({"spr": s2, "x": float(F.get("x", 0)), "y": float(F.get("y", 360)), "parallax": float(F.get("parallax", 1.2)),
			"fade": bool(F.get("fade", true)), "alpha": 1.0, "w": tex2.get_width() * sc, "h": tex2.get_height() * sc})
	var lm: Dictionary = meta.get("lightmap", {})
	if lm.has("file"):
		var ltex := SpriteLib.tex(_path(str(lm.file)))
		if ltex:
			light_img = ltex.get_image()
			if light_img and light_img.is_compressed():
				light_img.decompress()
			light_cell = float(lm.get("cell", 8))
	var rim: Dictionary = meta.get("rim", {})
	if not rim.is_empty():
		var d: Array = rim.get("dir", [-1, -0.35])
		rim_default = {"color": Color(str(rim.get("color", "#ffd0a0"))), "dir": Vector2(d[0], d[1]).normalized(),
			"strength": float(rim.get("strength", 0.4))}
	var cs: Dictionary = meta.get("cast_shadow", {})
	if not cs.is_empty():
		var cd: Array = cs.get("dir", [0.55, 0.22])
		cast_shadow = {"dir": Vector2(cd[0], cd[1]), "alpha": float(cs.get("alpha", 0.22))}
	for R in meta.get("reflect", []):
		var rr: Array = R.get("rect", [0, 0, 0, 0])
		reflects.append({"rect": Rect2(rr[0], rr[1], rr[2], rr[3]), "alpha": float(R.get("alpha", 0.18))})
	var gtex := SpriteLib.tex("res://assets/fx2/glow_soft.png")
	if gtex == null:
		gtex = _fallback_glow()
	for G in meta.get("glows", []):
		var g := Sprite2D.new()
		g.texture = gtex
		g.material = add_material()
		var rad := float(G.get("r", 40))
		g.scale = Vector2.ONE * (2.0 * rad / gtex.get_width())
		g.position = Vector2(float(G.get("x", 0)), float(G.get("y", 0)))
		var col := Color(str(G.get("color", "#ffcc80")))
		var front := bool(G.get("front", false))
		var en := float(G.get("energy", 0.5))
		if front:
			en = minf(en, 0.25)
		(glow_front if front else glow_back).add_child(g)
		glows.append({"spr": g, "x": g.position.x, "y": g.position.y, "r": rad, "color": col, "energy": en,
			"flicker": str(G.get("flicker", "none")), "phase": randf() * 10.0, "front": front, "off_t": 0.0})
	if Settings.effects_full():
		for A in meta.get("ambient", []):
			_make_ambient(A, glow_back, glow_front)
	life = RoomLife.new()
	room.add_child(life)
	life.build(self, meta, bg_root, fg_root)
	return true

## Optional story-state gating for layers/fg sprites ("requires" / "unless" use GameState.check syntax).
func _visible_by_state(e: Dictionary) -> bool:
	if e.has("requires") and not GameState.check(e.requires):
		return false
	if e.has("unless") and GameState.check(e.unless):
		return false
	return true

func _path(f: String) -> String:
	if f.begins_with("res://"):
		return f
	if f.begins_with("../"):
		return "res://assets/bg2/" + f.substr(3)
	return dir + f

static var _glow_fb: Texture2D
static func _fallback_glow() -> Texture2D:
	if _glow_fb:
		return _glow_fb
	var g := Gradient.new()
	g.colors = PackedColorArray([Color(1, 1, 1, 1), Color(1, 1, 1, 0)])
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.width = 128
	gt.height = 128
	_glow_fb = gt
	return gt

# ------------------------------------------------------------------ per-frame
func update(cam_left: float, view_w: float, actors: Array, dt: float) -> void:
	if not v2:
		return
	t += dt
	if life:
		life.update(cam_left, view_w, dt)
	if darkness != _dark_target:
		darkness = move_toward(darkness, _dark_target, dt / maxf(_dark_speed, 0.01))
		var m := Color(darkness, darkness, darkness * 1.05)
		if bg_root_ref:
			bg_root_ref.modulate = m
		if fg_root_ref:
			fg_root_ref.modulate = m
		for pr in room.props:
			if is_instance_valid(pr):
				pr.modulate = light_at(pr.position)
	for G in glows:
		if G.has("follow"):
			var f = G.follow
			if is_instance_valid(f) and not f.dead:
				G.x = f.position.x + float(G.off.x) * float(f.facing)
				G.y = f.position.y + float(G.off.y) - f.z
				(G.spr as Sprite2D).position = Vector2(G.x, G.y)
			else:
				(G.spr as Sprite2D).visible = false
	var cam_c := cam_left + view_w * 0.5
	for L in layers:
		var par: float = L.parallax
		var node: Node2D = L.node
		if L.repeat and L.spr:
			var s: Sprite2D = L.spr
			var dens := 1.0 / s.scale.x
			node.position = Vector2(cam_left, 0)
			s.position = Vector2(0, float(L.y))
			s.region_rect = Rect2(cam_left * par * dens, 0, (view_w + 4.0) * dens, s.texture.get_height())
		else:
			node.position = Vector2(cam_left * (1.0 - par), 0)
	for F in fg:
		var s2: Sprite2D = F.spr
		var x: float = cam_c + (float(F.x) - cam_c) * float(F.parallax)
		s2.position = Vector2(x, float(F.y))
		var target := 1.0
		if F.fade:
			var rect := Rect2(x - float(F.w) / 2.0, float(F.y) - float(F.h), float(F.w), float(F.h))
			for a in actors:
				if not is_instance_valid(a) or a.state == "removed":
					continue
				var ar := Rect2(a.position.x - 14.0, a.position.y - a.height - a.z - 4.0, 28.0, a.height + 6.0)
				if rect.intersects(ar):
					target = 0.3
					break
		F.alpha = move_toward(float(F.alpha), target, dt * 4.0)
		s2.modulate.a = F.alpha
	for G in glows:
		var k := 1.0
		match str(G.flicker):
			"neon":
				k = 0.94 + 0.06 * sin(t * 47.0 + G.phase)
				if G.off_t > 0.0:
					G.off_t -= dt
					k = 0.25
				elif randf() < dt * 0.12:
					G.off_t = randf_range(0.04, 0.14)
			"flame":
				k = 0.86 + 0.1 * sin(t * 7.3 + G.phase) + 0.06 * sin(t * 13.1 + G.phase * 2.0)
			"fluor":
				k = 1.0
				if G.off_t > 0.0:
					G.off_t -= dt
					k = 0.55 if fmod(t * 30.0, 2.0) < 1.0 else 1.0
				elif randf() < dt * 0.05:
					G.off_t = randf_range(0.15, 0.4)
		var c: Color = G.color
		(G.spr as Sprite2D).modulate = Color(c.r, c.g, c.b, float(G.energy) * k)

## Dims the whole room (backgrounds, props and actors through light_at) over `secs` seconds.
func set_darkness(level: float, secs: float = 0.6) -> void:
	_dark_target = clampf(level, 0.2, 1.0)
	_dark_speed = secs

## A glow that follows an actor (e.g. Kowal's lantern). It also feeds rim light like any other glow.
func add_follow_light(node: Node2D, radius: float, col: Color, energy: float, offset: Vector2) -> void:
	var gtex := SpriteLib.tex("res://assets/fx2/glow_soft.png")
	if gtex == null:
		gtex = _fallback_glow()
	var g := Sprite2D.new()
	g.texture = gtex
	g.material = add_material()
	g.scale = Vector2.ONE * (2.0 * radius / gtex.get_width())
	g.modulate = Color(col.r, col.g, col.b, energy)
	var holder: Node = room.glow_front if room.get("glow_front") else room
	holder.add_child(g)
	glows.append({"spr": g, "x": node.position.x, "y": node.position.y, "r": radius, "color": col, "energy": energy,
		"flicker": "flame", "phase": randf() * 10.0, "front": false, "off_t": 0.0, "follow": node, "off": offset})

# ------------------------------------------------------------------ queries used by actors and props
func light_at(p: Vector2) -> Color:
	if light_img == null:
		return Color(darkness, darkness, darkness)
	var w := light_img.get_width()
	var h := light_img.get_height()
	var fx := clampf(p.x / light_cell - 0.5, 0.0, w - 1.0)
	var fy := clampf(p.y / light_cell - 0.5, 0.0, h - 1.0)
	var x0 := int(fx)
	var y0 := int(fy)
	var x1 := mini(x0 + 1, w - 1)
	var y1 := mini(y0 + 1, h - 1)
	var tx := fx - x0
	var ty := fy - y0
	var c := light_img.get_pixel(x0, y0).lerp(light_img.get_pixel(x1, y0), tx).lerp(
		light_img.get_pixel(x0, y1).lerp(light_img.get_pixel(x1, y1), tx), ty)
	var k := 255.0 / 204.0 * darkness
	return Color(c.r * k, c.g * k, c.b * k)

func rim_at(p: Vector2) -> Dictionary:
	var best := 0.0
	var res := rim_default
	for G in glows:
		if G.front:
			continue
		var gp := Vector2(G.x, G.y)
		var d := gp.distance_to(p)
		var reach := float(G.r) * 1.5
		if d >= reach:
			continue
		var score := float(G.energy) * (1.0 - d / reach)
		if score > best:
			best = score
			var dv := (p - gp)
			res = {"color": G.color, "dir": dv.normalized() if dv.length() > 0.5 else Vector2(0, 1),
				"strength": clampf(score * 1.3, 0.0, 0.8)}
	if best > 0.0 and float(rim_default.strength) > float(res.strength):
		return rim_default
	return res

func reflect_at(p: Vector2) -> float:
	if not Settings.effects_full():
		return 0.0
	for R in reflects:
		if (R.rect as Rect2).has_point(p):
			return float(R.alpha)
	return 0.0

# ------------------------------------------------------------------ ambient life
func _make_ambient(A: Dictionary, back: Node2D, front: Node2D) -> void:
	var typ := str(A.get("type", ""))
	if typ not in AMBIENT_TYPES:
		return
	var p := CPUParticles2D.new()
	p.position = Vector2(float(A.get("x", 0)), float(A.get("y", 0)))
	var w := float(A.get("w", 8))
	var h := float(A.get("h", 4))
	var rate := float(A.get("rate", 1.0))
	p.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	p.emission_rect_extents = Vector2(w * 0.5, h * 0.5)
	p.local_coords = false
	var tex := SpriteLib.tex("res://assets/fx2/glow_soft.png")
	if tex == null:
		tex = _fallback_glow()
	p.texture = tex
	var base_scale := 6.0 / tex.get_width()
	match typ:
		"steam", "smoke":
			p.amount = maxi(1, int(10 * rate))
			p.lifetime = 2.6
			p.direction = Vector2(0.15, -1)
			p.spread = 12
			p.initial_velocity_min = 10
			p.initial_velocity_max = 20
			p.gravity = Vector2(4, -6)
			p.scale_amount_min = base_scale * 1.6
			p.scale_amount_max = base_scale * 3.2
			var sc := Curve.new()
			sc.add_point(Vector2(0, 0.4))
			sc.add_point(Vector2(1, 1.6))
			p.scale_amount_curve = sc
			p.color_ramp = _ramp(Color(0.92, 0.92, 0.95, 0.0), Color(0.9, 0.9, 0.95, 0.22) if typ == "steam" else Color(0.3, 0.3, 0.34, 0.25), Color(0.9, 0.9, 0.95, 0.0))
			back.add_child(p)
		"drip":
			p.amount = maxi(1, int(3 * rate))
			p.lifetime = 1.2
			p.direction = Vector2(0, 1)
			p.spread = 0
			p.initial_velocity_min = 5
			p.initial_velocity_max = 5
			p.gravity = Vector2(0, 260)
			p.scale_amount_min = base_scale * 0.25
			p.scale_amount_max = base_scale * 0.3
			p.color = Color(0.7, 0.85, 1.0, 0.6)
			p.material = add_material()
			back.add_child(p)
		"sparks", "embers":
			p.amount = maxi(1, int((14 if typ == "sparks" else 8)) * rate)
			p.lifetime = 1.0 if typ == "sparks" else 3.0
			p.direction = Vector2(0, -1)
			p.spread = 50 if typ == "sparks" else 20
			p.initial_velocity_min = 30 if typ == "sparks" else 6
			p.initial_velocity_max = 70 if typ == "sparks" else 14
			p.gravity = Vector2(0, 120 if typ == "sparks" else -4)
			p.scale_amount_min = base_scale * 0.2
			p.scale_amount_max = base_scale * 0.4
			p.color_ramp = _ramp(Color(1, 0.9, 0.5, 1), Color(1, 0.55, 0.15, 0.9), Color(0.8, 0.2, 0.05, 0))
			p.material = add_material()
			(front if typ == "sparks" else back).add_child(p)
		"paper", "leaves":
			p.amount = maxi(1, int(3 * rate))
			p.lifetime = 6.0
			p.direction = Vector2(1, -0.2)
			p.spread = 30
			p.initial_velocity_min = 8
			p.initial_velocity_max = 18
			p.gravity = Vector2(2, 3)
			p.angular_velocity_min = -90
			p.angular_velocity_max = 90
			p.scale_amount_min = base_scale * 0.35
			p.scale_amount_max = base_scale * 0.5
			p.color = Color(0.85, 0.8, 0.7, 0.7) if typ == "paper" else Color(0.75, 0.5, 0.2, 0.7)
			back.add_child(p)
		"water_shimmer":
			p.amount = maxi(1, int(10 * rate))
			p.lifetime = 1.4
			p.direction = Vector2(1, 0)
			p.spread = 180
			p.initial_velocity_min = 1
			p.initial_velocity_max = 3
			p.gravity = Vector2.ZERO
			p.scale_amount_min = base_scale * 0.4
			p.scale_amount_max = base_scale * 0.9
			p.color_ramp = _ramp(Color(0.8, 0.95, 1.0, 0.0), Color(0.85, 0.95, 1.0, 0.35), Color(0.8, 0.95, 1.0, 0.0))
			p.material = add_material()
			back.add_child(p)
		_:
			p.amount = maxi(1, int(10 * rate))
			p.lifetime = 5.0
			p.direction = Vector2(1, -0.3)
			p.spread = 180
			p.initial_velocity_min = 2
			p.initial_velocity_max = 5
			p.gravity = Vector2(0, -1)
			p.scale_amount_min = base_scale * 0.15
			p.scale_amount_max = base_scale * 0.3
			p.color_ramp = _ramp(Color(1, 0.95, 0.8, 0.0), Color(1, 0.95, 0.8, 0.3), Color(1, 0.95, 0.8, 0.0))
			p.material = add_material()
			back.add_child(p)
	p.preprocess = p.lifetime
	ambient_nodes.append(p)

func _ramp(a: Color, b: Color, c: Color) -> Gradient:
	var g := Gradient.new()
	g.offsets = PackedFloat32Array([0.0, 0.3, 1.0])
	g.colors = PackedColorArray([a, b, c])
	return g
