class_name RotateOverlay
extends Control
## Portrait orientation notice for phones. Pauses the game without destroying any state.

var paused_by_me := false

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	process_mode = Node.PROCESS_MODE_ALWAYS
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false

func _ready() -> void:
	UIKit.apply(self)
	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.04, 0.08, 0.97)
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var c := CenterContainer.new()
	c.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(c)
	var v := UIKit.vbox(6)
	c.add_child(v)
	var tex := SpriteLib.ui("rotate_device")
	if tex:
		var r := UIKit.icon_rect(tex, 64)
		v.add_child(r)
	var l := UIKit.label("Please rotate your device\nto landscape.", UIKit.CREAM, 0, HORIZONTAL_ALIGNMENT_CENTER)
	v.add_child(l)
	get_tree().root.size_changed.connect(_check)
	_check()

func _check() -> void:
	var s := DisplayServer.window_get_size()
	var portrait := s.y > s.x * 1.05 and (OS.has_feature("web") or OS.has_feature("mobile"))
	if portrait and not visible:
		visible = true
		mouse_filter = Control.MOUSE_FILTER_STOP
		if not get_tree().paused:
			get_tree().paused = true
			paused_by_me = true
	elif not portrait and visible:
		visible = false
		mouse_filter = Control.MOUSE_FILTER_IGNORE
		if paused_by_me:
			paused_by_me = false
			var w := get_tree().current_scene
			if w and w.has_method("top_menu") and w.top_menu() != null:
				return
			get_tree().paused = false
