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
	UIKit.place(top, Control.PRESET_CENTER_TOP, -200, 8, 400, 120)
	add_child(top)
	if logo_tex:
		logo = TextureRect.new()
		logo.texture = logo_tex
		logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		logo.custom_minimum_size = Vector2(400, 120)
		logo.pivot_offset = Vector2(200, 60)
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
	UIKit.place(sub, Control.PRESET_CENTER_TOP, -100, 126, 200, 12)
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
	UIKit.place(main_box, Control.PRESET_BOTTOM_LEFT, 34, -192, 176, 170)
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


## Parallax title scene from the ui2 title layers. Each layer is drawn at density 2 (half its texel size),
## bottom-anchored and centred, and drifts by its own parallax factor. Returns false if the art is missing.
func _build_layers() -> bool:
	var meta := SpriteLib.ui2_meta()
	var any := false
	for n in ["title_sky", "title_far", "title_mid", "title_street", "title_hero"]:
		var t := SpriteLib.ui2_half(n)
		if t == null:
			continue
		any = true
		var m: Dictionary = meta.get(n, {})
		var r := TextureRect.new()
		r.texture = t
		r.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var hs := 0.7 if n == "title_hero" else 1.0
		r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		r.stretch_mode = TextureRect.STRETCH_SCALE
		r.size = t.get_size() * hs
		add_child(r)
		var feet: Array = m.get("feet", [])
		layers.append({"node": r, "depth": float(m.get("parallax", 0.3)), "hero": n == "title_hero",
			"feet": Vector2(float(feet[0]), float(feet[1])) / 2.0 * hs if feet.size() == 2 else Vector2.ZERO})
	if any:
		var vig := TextureRect.new()
		var g := Gradient.new()
		g.colors = PackedColorArray([Color(0, 0, 0, 0), Color(0.02, 0.01, 0.03, 0.5)])
		var gt := GradientTexture2D.new()
		gt.gradient = g
		gt.fill = GradientTexture2D.FILL_RADIAL
		gt.fill_from = Vector2(0.45, 0.4)
		gt.fill_to = Vector2(1.2, 0.4)
		vig.texture = gt
		vig.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		vig.stretch_mode = TextureRect.STRETCH_SCALE
		vig.mouse_filter = Control.MOUSE_FILTER_IGNORE
		vig.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		add_child(vig)
	return any

func _animate_layers(delta: float) -> void:
	drift_t += delta
	var vs := get_viewport_rect().size
	for L in layers:
		var r: TextureRect = L.node
		var d: float = L.depth
		var sway := sin(drift_t * 0.11) * 14.0 * d
		if L.hero:
			var feet: Vector2 = L.feet
			r.position = Vector2(vs.x * 0.8 - feet.x + sway, vs.y - 6.0 - feet.y)
		else:
			r.position = Vector2((vs.x - r.size.x) * 0.5 + sway, vs.y - r.size.y)
	if logo and logo.modulate.a >= 1.0:
		logo.position.y = sin(drift_t * 0.8) * 1.2
