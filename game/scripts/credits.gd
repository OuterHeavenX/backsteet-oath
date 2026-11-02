extends Control
## Scrolling credits. Returns to the title or into postgame free roam.

var scroll: VBoxContainer
var speed := 18.0
var done := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().root.theme = UIKit.build_theme()
	UIKit.apply(self)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.07, 0.05, 0.09)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	scroll = UIKit.vbox(4)
	scroll.position = Vector2(get_viewport_rect().size.x / 2.0 - 200, get_viewport_rect().size.y + 10)
	scroll.size = Vector2(400, 0)
	add_child(scroll)
	var logo := SpriteLib.ui("logo")
	if logo:
		var c := CenterContainer.new()
		c.custom_minimum_size = Vector2(400, logo.get_height())
		var tr := TextureRect.new()
		tr.texture = logo
		c.add_child(tr)
		scroll.add_child(c)
	for entry in Content.story.get("credits", []):
		var l: Label
		if entry.begins_with("#"):
			l = UIKit.heading(entry.substr(1))
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
			scroll.add_child(UIKit.spacer(8))
		else:
			l = UIKit.label(entry, UIKit.CREAM, 0, HORIZONTAL_ALIGNMENT_CENTER)
		l.custom_minimum_size = Vector2(400, 0)
		l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		scroll.add_child(l)
	var hint := UIKit.label("Hold %s to speed up   -   %s to skip" % [InputPrompts.tag("punch"), InputPrompts.tag("pause")], UIKit.DIM)
	UIKit.place(hint, Control.PRESET_BOTTOM_LEFT, 6, -14, 400, 10)
	add_child(hint)
	Audio.play_music("ending", 1.0)

func _process(delta: float) -> void:
	if done:
		return
	var sp := speed * (4.0 if Input.is_action_pressed("punch") or Input.is_action_pressed("ui_accept") else 1.0)
	scroll.position.y -= sp * delta
	if scroll.position.y + scroll.size.y < -20:
		_finish()

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("pause") or event.is_action_pressed("ui_cancel"):
		_finish()

func _finish() -> void:
	if done:
		return
	done = true
	if Story.credits_return == "world":
		SceneFlow.goto("res://scenes/world.tscn")
	else:
		SceneFlow.goto("res://scenes/title.tscn")
