extends Control
## Title screen. Waits for a first press (browser audio policy), then shows the main menu.

var menus: Array = []
var menu_layer: CanvasLayer
var press_label: Label
var main_box: VBoxContainer
var started := false
var blink := 0.0
var logo: TextureRect
var layers: Array = []   # [{node: TextureRect, depth: float}]
var drift_t := 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().paused = false
	get_tree().root.theme = UIKit.build_theme()
	UIKit.apply(self)
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var layered := _build_layers()
	var bg_tex := SpriteLib.tex("res://assets/bg/title_bg.png")
	if layered:
		pass
	elif bg_tex:
		var bg := TextureRect.new()
		bg.texture = bg_tex
		bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		add_child(bg)
	else:
		var cr := ColorRect.new()
		cr.color = Color(0.16, 0.1, 0.16)
		cr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		add_child(cr)
	var logo_tex := SpriteLib.ui2("logo")
	var top := CenterContainer.new()
	UIKit.place(top, Control.PRESET_CENTER_TOP, -240, 10, 480, 134)
	add_child(top)
	if logo_tex:
		logo = TextureRect.new()
		logo.texture = logo_tex
		logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		logo.custom_minimum_size = Vector2(440, 132)
		logo.pivot_offset = Vector2(220, 66)
		top.add_child(logo)
		logo.modulate.a = 0.0
		logo.scale = Vector2(1.12, 1.12)
		var tw := logo.create_tween()
		tw.tween_property(logo, "modulate:a", 1.0, 0.6)
		tw.parallel().tween_property(logo, "scale", Vector2.ONE, 0.7).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	else:
		var l := UIKit.heading("BACKSTREET OATH")
		l.add_theme_font_size_override("font_size", 28)
		top.add_child(l)
	var sub := UIKit.label("BELLWETHER  ·  1988", UIKit.CREAM, 0, HORIZONTAL_ALIGNMENT_CENTER)
	UIKit.place(sub, Control.PRESET_CENTER_TOP, -100, 146, 200, 10)
	sub.add_theme_color_override("font_outline_color", UIKit.INK)
	sub.add_theme_constant_override("outline_size", 4)
	add_child(sub)
	press_label = UIKit.label("PRESS ANY BUTTON", UIKit.MUSTARD, 0, HORIZONTAL_ALIGNMENT_CENTER)
	UIKit.place(press_label, Control.PRESET_CENTER_BOTTOM, -120, -80, 240, 12)
	press_label.add_theme_color_override("font_outline_color", UIKit.INK)
	press_label.add_theme_constant_override("outline_size", 4)
	add_child(press_label)
	var ver := UIKit.label("v%s  -  Godot 4.7.2  -  an original game" % SaveService.GAME_VERSION, UIKit.DIM)
	UIKit.place(ver, Control.PRESET_BOTTOM_LEFT, 6, -14, 300, 10)
	ver.add_theme_color_override("font_outline_color", UIKit.INK)
	ver.add_theme_constant_override("outline_size", 3)
	add_child(ver)
	main_box = UIKit.vbox(3)
	UIKit.place(main_box, Control.PRESET_CENTER_BOTTOM, -90, -176, 180, 170)
	main_box.visible = false
	add_child(main_box)
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 20
	add_child(menu_layer)
	if Audio.unlocked:
		_start()

func _process(delta: float) -> void:
	_animate_layers(delta)
	if not started:
		blink += delta
		press_label.modulate.a = 0.55 + 0.45 * cos(blink * 3.2)
		press_label.text = {"touch": "TAP TO START", "gamepad": "PRESS ANY BUTTON"}.get(InputPrompts.kind, "PRESS ANY KEY")

func _input(event: InputEvent) -> void:
	if started:
		return
	if (event is InputEventKey or event is InputEventJoypadButton or event is InputEventMouseButton or event is InputEventScreenTouch) and event.is_pressed():
		get_viewport().set_input_as_handled()
		Audio.unlocked = true
		_start()

func _start() -> void:
	if started:
		return
	started = true
	press_label.visible = false
	Audio.play_music("title", 0.5)
	_build_main()

func _build_main() -> void:
	for c in main_box.get_children():
		c.queue_free()
	main_box.visible = true
	var btns: Array = []
	if SaveService.any_save():
		btns.append(UIKit.button("Continue", _continue, 180))
	btns.append(UIKit.button("New Game", func(): _slots("new"), 180))
	if SaveService.any_save():
		btns.append(UIKit.button("Load Game", func(): _slots("load"), 180))
	btns.append(UIKit.button("Manage Saves", func(): _slots("manage"), 180))
	btns.append(UIKit.button("Settings", func(): push_menu(SettingsMenu.new()), 180))
	btns.append(UIKit.button("Controls", func(): push_menu(ControlsMenu.new()), 180))
	btns.append(UIKit.button("Credits", func(): Story.credits_return = "title"; SceneFlow.goto("res://scenes/credits.tscn"), 180))
	if not OS.has_feature("web"):
		btns.append(UIKit.button("Quit", func(): get_tree().quit(), 180))
	for b in btns:
		main_box.add_child(b)
	await get_tree().process_frame
	btns[0].grab_focus()

func _continue() -> void:
	var slot := SaveService.most_recent_slot()
	if slot > 0 and SaveService.load_game(slot):
		start_loaded_game()

func _slots(mode: String) -> void:
	var m := SlotMenu.new()
	m.mode = mode
	push_menu(m)

func start_new_game(slot: int) -> void:
	GameState.reset_new_game()
	Story.new_game()
	SaveService.current_slot = slot
	SaveService.save_game(slot)
	_close_menus()
	SceneFlow.goto("res://scenes/world.tscn")

func start_loaded_game() -> void:
	_close_menus()
	SceneFlow.goto("res://scenes/world.tscn")

func _close_menus() -> void:
	for m in menus:
		m.queue_free()
	menus.clear()

# menu host interface
func push_menu(m: Control) -> void:
	if not menus.is_empty():
		menus[-1].remember_focus()
		menus[-1].visible = false
	m.host = self
	menus.append(m)
	menu_layer.add_child(m)
	main_box.visible = false

func pop_menu(m: Control) -> void:
	menus.erase(m)
	m.queue_free()
	if menus.is_empty():
		_build_main()
	else:
		menus[-1].visible = true
		menus[-1].restore_focus()

func top_menu() -> Control:
	return menus[-1] if not menus.is_empty() else null

func toast(_m: String) -> void:
	pass


## Parallax title scene from ui2 title layers (sky, far, mid, street, hero). Returns false if the art is missing.
func _build_layers() -> bool:
	var names := [["title_sky", 0.0], ["title_far", 0.15], ["title_mid", 0.35], ["title_street", 0.7], ["title_hero", 1.0]]
	var any := false
	for n in names:
		var t := SpriteLib.tex("res://assets/ui2/%s.png" % n[0])
		if t == null:
			continue
		any = true
		var r := TextureRect.new()
		r.texture = t
		r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		r.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		r.offset_left = -16
		r.offset_right = 16
		add_child(r)
		layers.append({"node": r, "depth": float(n[1])})
	if any:
		var vig := TextureRect.new()
		var g := Gradient.new()
		g.colors = PackedColorArray([Color(0, 0, 0, 0), Color(0.02, 0.01, 0.03, 0.55)])
		var gt := GradientTexture2D.new()
		gt.gradient = g
		gt.fill = GradientTexture2D.FILL_RADIAL
		gt.fill_from = Vector2(0.5, 0.45)
		gt.fill_to = Vector2(1.15, 0.45)
		vig.texture = gt
		vig.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		vig.stretch_mode = TextureRect.STRETCH_SCALE
		vig.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vig.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		add_child(vig)
	return any

func _animate_layers(delta: float) -> void:
	drift_t += delta
	for L in layers:
		var r: TextureRect = L.node
		var d: float = L.depth
		r.position.x = -16.0 + sin(drift_t * 0.12) * 12.0 * d
		r.position.y = cos(drift_t * 0.09) * 2.0 * d
	if logo and logo.modulate.a >= 1.0:
		logo.position.y = sin(drift_t * 0.8) * 1.2
