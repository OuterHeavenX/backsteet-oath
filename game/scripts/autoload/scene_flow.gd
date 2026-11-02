extends Node
## Screen fades and top-level scene changes (title <-> world <-> credits).

var _layer: CanvasLayer
var _rect: ColorRect
var busy := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_layer = CanvasLayer.new()
	_layer.layer = 120
	add_child(_layer)
	_rect = ColorRect.new()
	_rect.color = Color(0.06, 0.04, 0.08, 0.0)
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	_layer.add_child(_rect)

func fade_out(t: float = 0.3) -> void:
	_rect.mouse_filter = Control.MOUSE_FILTER_STOP
	var tw := create_tween()
	tw.tween_property(_rect, "color:a", 1.0, t)
	await tw.finished

func fade_in(t: float = 0.3) -> void:
	var tw := create_tween()
	tw.tween_property(_rect, "color:a", 0.0, t)
	await tw.finished
	_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE

func is_black() -> bool:
	return _rect.color.a > 0.99

func goto(scene_path: String, t: float = 0.35) -> void:
	if busy:
		return
	busy = true
	await fade_out(t)
	get_tree().paused = false
	get_tree().change_scene_to_file(scene_path)
	await get_tree().process_frame
	await get_tree().process_frame
	busy = false
	await fade_in(t)
