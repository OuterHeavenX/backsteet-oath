class_name DialogueBox
extends Control
## Portrait dialogue with typewriter text. Advance: Punch/Confirm/Grab/tap. Skip all: Back/Cancel.
## Lines: [speaker, emotion, text]. Choices return the selected index.

signal finished
signal line_advanced

const EMOTIONS := {"neutral": 0, "happy": 1, "angry": 2, "surprised": 3, "sad": 4}

var panel: PanelContainer
var portrait: TextureRect
var portrait_frame: PanelContainer
var name_label: Label
var text_label: Label
var hint: Label
var choice_box: VBoxContainer
var lines: Array = []
var idx := 0
var shown := 0.0
var full_text := ""
var active := false
var choosing := false
var choice_result := -1
var skip_requested := false
var advance_cd := 0.0

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false

func _ready() -> void:
	panel = PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	panel.custom_minimum_size = Vector2(600, 84)
	panel.position = Vector2(-300, -92)
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.gui_input.connect(_on_panel_input)
	add_child(panel)
	var h := UIKit.hbox(8)
	panel.add_child(h)
	portrait_frame = PanelContainer.new()
	portrait_frame.add_theme_stylebox_override("panel", UIKit.panel_style(Color(0.2, 0.15, 0.22), UIKit.CREAM, 1))
	portrait_frame.custom_minimum_size = Vector2(68, 68)
	h.add_child(portrait_frame)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(64, 64)
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	portrait.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	portrait_frame.add_child(portrait)
	var v := UIKit.vbox(2)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	name_label = UIKit.label("", UIKit.MUSTARD)
	v.add_child(name_label)
	text_label = UIKit.label("", UIKit.CREAM)
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text_label.custom_minimum_size = Vector2(500, 40)
	text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(text_label)
	choice_box = UIKit.vbox(2)
	v.add_child(choice_box)
	hint = UIKit.label("", UIKit.DIM, 0, HORIZONTAL_ALIGNMENT_RIGHT)
	v.add_child(hint)

func play(new_lines: Array) -> void:
	lines = new_lines
	idx = 0
	skip_requested = false
	active = true
	visible = true
	Audio.duck_music(true)
	_show_line()
	await finished

func ask(prompt_line: Array, options: Array) -> int:
	lines = [prompt_line]
	idx = 0
	active = true
	visible = true
	choosing = true
	choice_result = -1
	_show_line()
	shown = full_text.length()
	text_label.visible_characters = -1
	for c in choice_box.get_children():
		c.queue_free()
	var btns: Array = []
	for i in options.size():
		var b := UIKit.button("> " + str(options[i]), func(): _choose(i), 480)
		choice_box.add_child(b)
		btns.append(b)
	hint.text = ""
	await get_tree().process_frame
	if not btns.is_empty():
		btns[0].grab_focus()
	await finished
	return choice_result

func _choose(i: int) -> void:
	choice_result = i
	choosing = false
	for c in choice_box.get_children():
		c.queue_free()
	_end()

func _show_line() -> void:
	if idx >= lines.size():
		_end()
		return
	var line: Array = lines[idx]
	var speaker: String = line[0]
	var emo: String = line[1] if line.size() > 1 else "neutral"
	full_text = Story.format_text(line[2] if line.size() > 2 else "")
	var ch: Dictionary = Content.characters.get(speaker, {})
	name_label.text = ch.get("name", speaker.capitalize()) if speaker != "narrator" else ""
	var pid: String = ch.get("portrait", "")
	var ptex := SpriteLib.portrait(pid) if pid != "" else null
	if ptex:
		var at := AtlasTexture.new()
		at.atlas = ptex
		var e := int(EMOTIONS.get(emo, 0))
		if ptex.get_width() < (e + 1) * 64:
			e = 0
		at.region = Rect2(e * 64, 0, 64, 64)
		portrait.texture = at
		portrait_frame.visible = true
	else:
		portrait.texture = null
		portrait_frame.visible = speaker != "narrator"
	text_label.text = full_text
	text_label.add_theme_color_override("font_color", UIKit.CREAM if speaker != "narrator" else Color(0.85, 0.85, 0.95))
	shown = 0.0
	text_label.visible_characters = 0
	advance_cd = 0.12
	hint.text = "%s Next   %s Skip" % [InputPrompts.tag("punch"), "(B)" if InputPrompts.kind == "gamepad" else ("[Esc]" if InputPrompts.kind == "keyboard" else "<tap>")]

func _process(delta: float) -> void:
	if not active:
		return
	if advance_cd > 0.0:
		advance_cd -= delta
	if not choosing and shown < full_text.length():
		var before := int(shown)
		shown += Settings.text_cps() * delta
		text_label.visible_characters = int(shown)
		if int(shown) > before and int(shown) % 3 == 0:
			Audio.sfx("dialogue_blip", -16.0, 0.08)
		if shown >= full_text.length():
			text_label.visible_characters = -1

func _unhandled_input(event: InputEvent) -> void:
	if not active or choosing:
		return
	if event.is_action_pressed("ui_cancel") or event.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		_end()
		return
	if event.is_action_pressed("ui_accept") or event.is_action_pressed("punch") or event.is_action_pressed("interact") or event.is_action_pressed("jump"):
		get_viewport().set_input_as_handled()
		_advance()

func _on_panel_input(event: InputEvent) -> void:
	if not active or choosing:
		return
	if (event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT) or (event is InputEventScreenTouch and event.pressed):
		_advance()

func _advance() -> void:
	if advance_cd > 0.0:
		return
	if shown < full_text.length():
		shown = full_text.length()
		text_label.visible_characters = -1
		advance_cd = 0.08
		return
	idx += 1
	line_advanced.emit()
	_show_line()

func _end() -> void:
	if not active:
		return
	active = false
	choosing = false
	visible = false
	Audio.duck_music(false)
	finished.emit()
