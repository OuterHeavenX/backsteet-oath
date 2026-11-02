class_name RainLayer
extends Node2D
## Restrained rain: thin slanted streaks + small ground splashes. Low alpha keeps tells readable.

var room: Node
var drops: Array = []
var splashes: Array = []

func _ready() -> void:
	for i in 70:
		drops.append(Vector3(randf() * 800.0, randf() * 360.0, randf_range(0.6, 1.0)))

func _physics_process(_d: float) -> void:
	if room == null:
		return
	var left: float = room.cam_left()
	var vw: float = room.view_width()
	for i in drops.size():
		var d: Vector3 = drops[i]
		d.y += 7.0 * d.z
		d.x -= 1.6 * d.z
		if d.y > 350.0:
			if randf() < 0.35:
				splashes.append(Vector3(left + fposmod(d.x, vw), randf_range(room.walk_top, room.walk_bot), 0))
			d.y = randf_range(-40.0, 0.0)
			d.x = randf() * (vw + 60.0)
		drops[i] = d
	for i in range(splashes.size() - 1, -1, -1):
		var s: Vector3 = splashes[i]
		s.z += 1
		if s.z > 8:
			splashes.remove_at(i)
		else:
			splashes[i] = s
	queue_redraw()

func _draw() -> void:
	if room == null:
		return
	var left: float = room.cam_left()
	var vw: float = room.view_width()
	var col := Color(0.75, 0.82, 0.95, 0.32)
	for d in drops:
		var x: float = left + fposmod(d.x, vw + 60.0) - 30.0
		draw_line(Vector2(x, d.y), Vector2(x - 2.0, d.y + 8.0 * d.z), col, 1.0)
	for s in splashes:
		var r: float = 1.0 + s.z * 0.5
		draw_line(Vector2(s.x - r, s.y), Vector2(s.x + r, s.y), Color(0.8, 0.85, 1.0, 0.4 - s.z * 0.04), 1.0)
