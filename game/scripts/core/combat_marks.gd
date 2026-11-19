class_name CombatMarks
extends RefCounted
## Readability aids drawn in code, so they stay crisp at any zoom and need no art pipeline:
##  - Ring: a thin ellipse on the ground (Nico's position, enemies standing in his lane, usable objects)
##  - Keyline: a one-pixel silhouette outline behind a sprite (Nico; the object the Action button will take)
##  - Tell: a badge above an attacker during the wind-up of a telegraphed attack; its SHAPE says what kind
##  - Zone: the ground area a surrounding attack will cover
## Nothing here reads or changes gameplay timing; the room decides when each one shows.

const KEY_COL := Color(0.96, 0.9, 0.78)
const USE_COL := Color(0.95, 0.72, 0.23)
const LANE_COL := Color(0.96, 0.92, 0.84)
const DANGER_COL := Color(0.9, 0.28, 0.3)
const UNBLOCK_COL := Color(0.72, 0.42, 1.0)
const BREAK_COL := Color(1.0, 0.6, 0.18)
const INK := Color(0.1, 0.07, 0.13)
const SIL_SHADER := """shader_type canvas_item;
uniform vec4 col : source_color = vec4(1.0);
void fragment() {
	COLOR = vec4(col.rgb, texture(TEXTURE, UV).a * col.a);
}
"""
static var _sil: Shader

static func tell_color(kind: String) -> Color:
	match kind:
		"unblockable": return UNBLOCK_COL
		"break": return BREAK_COL
	return DANGER_COL

## What a telegraphed attack is, from its data: "unblockable", "break" (guard-breaking) or "heavy".
static func tell_kind(d: Dictionary) -> String:
	if d.get("unblockable", false):
		return "unblockable"
	if d.get("guard_break", false):
		return "break"
	return "heavy"

class Ring extends Node2D:
	var radius := 13.0
	var col := Color.WHITE
	var width := 1.2
	func look(c: Color, r: float, w: float = 1.2) -> void:
		if c != col or r != radius or w != width:
			col = c
			radius = r
			width = w
			queue_redraw()
	func _draw() -> void:
		var pts := PackedVector2Array()
		for i in 33:
			var a := TAU * float(i) / 32.0
			pts.append(Vector2(cos(a) * radius, sin(a) * radius * 0.36))
		draw_polyline(pts, Color(INK, col.a * 0.55), width + 1.4, true)
		draw_polyline(pts, col, width, true)

class Zone extends Node2D:
	var rx := 40.0
	var ry := 12.0
	var col := Color.WHITE
	var amount := 0.0
	func look(c: Color, x: float, y: float, k: float) -> void:
		if c != col or x != rx or y != ry or absf(k - amount) > 0.02:
			col = c
			rx = x
			ry = y
			amount = k
			queue_redraw()
	func _draw() -> void:
		var pts := PackedVector2Array()
		for i in 40:
			var a := TAU * float(i) / 40.0
			pts.append(Vector2(cos(a) * rx, sin(a) * ry))
		draw_colored_polygon(pts, Color(col, 0.10 + 0.20 * amount))
		pts.append(pts[0])
		draw_polyline(pts, Color(col, 0.45 + 0.4 * amount), 1.4, true)

class Keyline extends Node2D:
	const OFFS := [Vector2(1, 0), Vector2(-1, 0), Vector2(0, 1), Vector2(0, -1)]
	var sprs: Array = []
	var mat: ShaderMaterial
	func _init() -> void:
		if CombatMarks._sil == null:
			CombatMarks._sil = Shader.new()
			CombatMarks._sil.code = CombatMarks.SIL_SHADER
		mat = ShaderMaterial.new()
		mat.shader = CombatMarks._sil
		for i in 4:
			var s := Sprite2D.new()
			s.material = mat
			add_child(s)
			sprs.append(s)
	## Copies the source sprite's frame each tick, one pixel out in four directions.
	func sync(src: Sprite2D, px: float, c: Color) -> void:
		mat.set_shader_parameter("col", c)
		for i in 4:
			var s: Sprite2D = sprs[i]
			s.texture = src.texture
			s.centered = src.centered
			s.region_enabled = src.region_enabled
			if src.region_enabled:
				s.region_rect = src.region_rect
			s.hframes = src.hframes
			s.frame = src.frame
			s.offset = src.offset
			s.scale = src.scale
			s.flip_h = src.flip_h
			s.rotation = src.rotation
			s.position = src.position + OFFS[i] * px

class Tell extends Node2D:
	var kind := "heavy"
	var age := 0
	func show_kind(k: String) -> void:
		if k != kind or not visible:
			kind = k
			age = 0
			visible = true
			queue_redraw()
	func tick() -> void:
		age += 1
		var s := 1.0 + maxf(0.0, 1.0 - age / 6.0) * 0.5
		scale = Vector2(s, s)
	func _draw() -> void:
		var c := CombatMarks.tell_color(kind)
		var cream := Color(1.0, 0.96, 0.88)
		match kind:
			"unblockable":
				# an open hand shape: a crossed-out shield. Guarding will not help.
				var sh := PackedVector2Array([Vector2(-6, -7), Vector2(6, -7), Vector2(6, 0), Vector2(0, 7), Vector2(-6, 0)])
				draw_colored_polygon(sh, c)
				sh.append(sh[0])
				draw_polyline(sh, CombatMarks.INK, 1.6, true)
				draw_line(Vector2(-3.4, -4.2), Vector2(3.4, 2.6), cream, 1.8, true)
				draw_line(Vector2(3.4, -4.2), Vector2(-3.4, 2.6), cream, 1.8, true)
			"break":
				# a cracked shield: guarding will be broken
				var sh2 := PackedVector2Array([Vector2(-6, -7), Vector2(6, -7), Vector2(6, 0), Vector2(0, 7), Vector2(-6, 0)])
				draw_colored_polygon(sh2, c)
				sh2.append(sh2[0])
				draw_polyline(sh2, CombatMarks.INK, 1.6, true)
				draw_polyline(PackedVector2Array([Vector2(1.5, -7), Vector2(-1.8, -2.5), Vector2(1.8, 0.5), Vector2(-0.5, 6.0)]), CombatMarks.INK, 1.8, true)
			_:
				# a plain warning: a heavy hit that can be guarded
				var tri := PackedVector2Array([Vector2(0, -8), Vector2(7.5, 6), Vector2(-7.5, 6)])
				draw_colored_polygon(tri, c)
				tri.append(tri[0])
				draw_polyline(tri, CombatMarks.INK, 1.6, true)
				draw_rect(Rect2(-1.0, -3.6, 2.0, 5.2), cream)
				draw_rect(Rect2(-1.0, 2.8, 2.0, 2.0), cream)
