extends Control
## Title screen. Waits for a first press (browser audio policy), then shows the main menu.

var menus: Array = []
var menu_layer: CanvasLayer
var press_label: Label
var main_box: VBoxContainer
var started := false
var blink := 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().paused = false
	get_tree().root.theme = UIKit.build_theme()
	UIKit.apply(self)
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg_tex := SpriteLib.tex("res://assets/bg/title_bg.png")
	if bg_tex:
		var bg := TextureRect.new()
		bg.texture = bg_tex
		bg.set_anchors_preset(Control.PRESET_FULL_RECT)
		bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		bg.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		add_child(bg)
	else:
		var cr := ColorRect.new()
		cr.color = Color(0.16, 0.1, 0.16)
		cr.set_anchors_preset(Control.PRESET_FULL_RECT)
		add_child(cr)
	var logo_tex := SpriteLib.ui("logo")
	var top := CenterContainer.new()
	top.set_anchors_preset(Control.PRESET_CENTER_TOP)
	top.position = Vector2(-240, 18)
	top.size = Vector2(480, 130)
	add_child(top)
	if logo_tex:
		var lr := TextureRect.new()
		lr.texture = logo_tex
		lr.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		top.add_child(lr)
	else:
		var l := UIKit.heading("BACKSTREET OATH")
		l.add_theme_font_size_override("font_size", 24)
		top.add_child(l)
	var sub := UIKit.label("Bellwether, 1988", UIKit.CREAM, 0, HORIZONTAL_ALIGNMENT_CENTER)
	sub.set_anchors_preset(Control.PRESET_CENTER_TOP)
	sub.position = Vector2(-100, 150)
	sub.size = Vector2(200, 10)
	sub.add_theme_color_override("font_outline_color", UIKit.INK)
	sub.add_theme_constant_override("outline_size", 4)
	add_child(sub)
	press_label = UIKit.label("PRESS ANY BUTTON", UIKit.MUSTARD, 0, HORIZONTAL_ALIGNMENT_CENTER)
	press_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	press_label.position = Vector2(-120, -80)
	press_label.size = Vector2(240, 12)
	press_label.add_theme_color_override("font_outline_color", UIKit.INK)
	press_label.add_theme_constant_override("outline_size", 4)
	add_child(press_label)
	var ver := UIKit.label("v%s  -  Godot 4.7.2  -  an original game" % SaveService.GAME_VERSION, UIKit.DIM)
	ver.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	ver.position = Vector2(6, -14)
	ver.add_theme_color_override("font_outline_color", UIKit.INK)
	ver.add_theme_constant_override("outline_size", 3)
	add_child(ver)
	main_box = UIKit.vbox(3)
	main_box.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	main_box.position = Vector2(-90, -150)
	main_box.size = Vector2(180, 140)
	main_box.visible = false
	add_child(main_box)
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 20
	add_child(menu_layer)
	if Audio.unlocked:
		_start()

func _process(delta: float) -> void:
	if not started:
		blink += delta
		press_label.visible = int(blink * 2.0) % 2 == 0

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
		var pc := PanelContainer.new()
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
