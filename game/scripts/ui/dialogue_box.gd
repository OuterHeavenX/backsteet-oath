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
var skip_btn: Button
var hbox: HBoxContainer
var portrait_spacer: Control
var portrait_left := true
var talk_t := 0.0

func _init() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	visible = false

func _ready() -> void:
	UIKit.apply(self)
	panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(600, 84)
	UIKit.place(panel, Control.PRESET_CENTER_BOTTOM, -300, -90, 600, 84)
	var ps := UIKit.panel_style(Color(0.075, 0.055, 0.1, 0.94), Color(0.95, 0.72, 0.23, 0.6), 1)
	ps.border_width_left = 0
	ps.border_width_right = 0
	ps.border_width_bottom = 0
	ps.border_width_top = 2
	ps.shadow_color = Color(0, 0, 0, 0.4)
	ps.shadow_size = 6
	ps.content_margin_left = 10
	ps.content_margin_right = 10
	ps.content_margin_top = 8
	panel.add_theme_stylebox_override("panel", ps)
	panel.grow_vertical = Control.GROW_DIRECTION_BEGIN   # extra lines/choices grow upward, never into the control deck
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.gui_input.connect(_on_panel_input)
	add_child(panel)
	hbox = UIKit.hbox(10)
	panel.add_child(hbox)
	var h := hbox
	portrait_spacer = Control.new()
	portrait_spacer.custom_minimum_size = Vector2(96, 0)
	h.add_child(portrait_spacer)
	# The bust breaks out of the top of the panel (drawn above it, positioned every frame).
	portrait_frame = PanelContainer.new()
	var pf := StyleBoxFlat.new()
	pf.bg_color = Color(0.17, 0.12, 0.2, 0.96)
	pf.border_color = Color(0.95, 0.72, 0.23, 0.85)
	pf.set_border_width_all(1)
	pf.set_corner_radius_all(6)
	pf.anti_aliasing = true
	pf.shadow_color = Color(0, 0, 0, 0.45)
	pf.shadow_size = 5
	portrait_frame.add_theme_stylebox_override("panel", pf)
	portrait_frame.size = Vector2(98, 98)
	portrait_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(portrait_frame)
	portrait = TextureRect.new()
	portrait.custom_minimum_size = Vector2(96, 96)
	portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait.pivot_offset = Vector2(48, 96)
	portrait_frame.add_child(portrait)
	var v := UIKit.vbox(2)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	h.add_child(v)
	name_label = UIKit.label("", UIKit.MUSTARD)
	if UIKit.font_big:
		name_label.add_theme_font_override("font", UIKit.font_big)
		name_label.add_theme_font_size_override("font_size", 11)
	v.add_child(name_label)
	text_label = UIKit.label("", UIKit.CREAM, UIKit.base_size() + 1)
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text_label.custom_minimum_size = Vector2(500, 40)
	text_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	v.add_child(text_label)
	choice_box = UIKit.vbox(2)
	v.add_child(choice_box)
	var foot := UIKit.hbox(8)
	v.add_child(foot)
	hint = UIKit.label("", UIKit.DIM, 0, HORIZONTAL_ALIGNMENT_RIGHT)
	hint.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foot.add_child(hint)
	skip_btn = Button.new()
	skip_btn.text = "SKIP >>"
	skip_btn.focus_mode = Control.FOCUS_NONE
	skip_btn.pressed.connect(func():
		Audio.sfx("ui_cancel", -6.0, 0.0)
		_end())
	foot.add_child(skip_btn)
	gui_input.connect(_on_panel_input)

func play(new_lines: Array) -> void:
	lines = new_lines
	idx = 0
	skip_requested = false
	active = true
	visible = true
	mouse_filter = Control.MOUSE_FILTER_STOP   # tap anywhere on the street to continue
	skip_btn.visible = true
	Audio.duck_music(true)
	_show_line()
	await finished

func ask(prompt_line: Array, options: Array) -> int:
	lines = [prompt_line]
	idx = 0
	active = true
	visible = true
	choosing = true
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	skip_btn.visible = false
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
	var pinfo := SpriteLib.portrait_info(pid) if pid != "" else {"texture": null}
	var ptex: Texture2D = pinfo.texture
	# The player speaks from the left, everyone else from the right (a simple shot/reverse-shot).
	portrait_left = speaker in ["nico", "narrator"]
	hbox.move_child(portrait_spacer, 0 if portrait_left else hbox.get_child_count() - 1)
	name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT if portrait_left else HORIZONTAL_ALIGNMENT_RIGHT
	if ptex:
		var ps := float(pinfo.size)
		var at := AtlasTexture.new()
		at.atlas = ptex
		var e := int(EMOTIONS.get(emo, 0))
		if ptex.get_width() < (e + 1) * ps:
			e = 0
		at.region = Rect2(e * ps, 0, ps, ps)
		portrait.texture = at
		portrait.flip_h = not portrait_left
		portrait_frame.visible = true
		portrait_spacer.visible = true
		if line != (lines[idx - 1] if idx > 0 else []):
			portrait.scale = Vector2(1.0, 0.94)
			var tw := portrait.create_tween()
			tw.tween_property(portrait, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	else:
		portrait.texture = null
		portrait_frame.visible = false
		portrait_spacer.visible = false
	text_label.text = full_text
	text_label.add_theme_color_override("font_color", UIKit.CREAM if speaker != "narrator" else Color(0.85, 0.85, 0.95))
	shown = 0.0
	text_label.visible_characters = 0
	advance_cd = 0.12
	match InputPrompts.kind:
		"touch": hint.text = "Tap to continue"
		"gamepad": hint.text = "(A) Next   (B) Skip"
		_: hint.text = "%s or [Enter] Next   [Esc] Skip" % InputPrompts.tag("punch")

func _process(delta: float) -> void:
	if not active:
		return
	if portrait_frame.visible:
		var px := panel.position.x + 10.0 if portrait_left else panel.position.x + panel.size.x - 108.0
		portrait_frame.position = Vector2(px, panel.position.y + panel.size.y - 104.0)
		# a gentle bob while the line types out
		talk_t += delta
		var typing := shown < full_text.length() and not choosing
		portrait.position.y = (sin(talk_t * 14.0) * 0.6 - 0.6) if typing else 0.0
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
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	Audio.duck_music(false)
	finished.emit()
