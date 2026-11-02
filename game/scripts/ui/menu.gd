class_name Menu
extends Control
## Base class for stacked menus. Full-screen dim + centered panel, reliable Back (ui_cancel),
## remembers focus, works with keyboard, controller, mouse and touch.

signal closed

var host: Node           # object with push_menu/pop_menu (World or Title)
var first_focus: Control
var back_allowed := true
var dim: ColorRect
var root_panel: PanelContainer
var content: VBoxContainer
var _last_focus: Control

func _init() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP

func make_frame(title: String, min_size: Vector2 = Vector2(300, 200)) -> VBoxContainer:
	dim = ColorRect.new()
	dim.color = Color(0.05, 0.03, 0.07, 0.6)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(dim)
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(center)
	root_panel = UIKit.panel(min_size)
	center.add_child(root_panel)
	content = UIKit.vbox(4)
	root_panel.add_child(content)
	if title != "":
		var h := UIKit.heading(title)
		content.add_child(h)
	return content

func _ready() -> void:
	UIKit.apply(self)
	build()
	await get_tree().process_frame
	focus_first()

## Override to construct the menu.
func build() -> void:
	pass

func focus_first() -> void:
	if first_focus and is_instance_valid(first_focus) and first_focus.is_visible_in_tree():
		first_focus.grab_focus()
		return
	var b := _find_focusable(self)
	if b:
		b.grab_focus()

func _find_focusable(n: Node) -> Control:
	for c in n.get_children():
		if c is Control and c.focus_mode == Control.FOCUS_ALL and c.is_visible_in_tree() and not (c is Button and c.disabled):
			return c
		var r := _find_focusable(c)
		if r:
			return r
	return null

func _unhandled_input(event: InputEvent) -> void:
	if not is_top():
		return
	if event.is_action_pressed("ui_cancel") or (event.is_action_pressed("pause") and not event.is_action_pressed("ui_accept")):
		if back_allowed:
			get_viewport().set_input_as_handled()
			Audio.sfx("ui_cancel", -6.0, 0.0)
			close()
	elif event is InputEventJoypadButton or event is InputEventKey:
		# recover focus if it was lost (e.g. after a mouse click on empty space)
		var f := get_viewport().gui_get_focus_owner()
		if f == null or not is_ancestor_of(f):
			focus_first()

func is_top() -> bool:
	if host and host.has_method("top_menu"):
		return host.top_menu() == self
	return true

func close() -> void:
	closed.emit()
	if host and host.has_method("pop_menu"):
		host.pop_menu(self)
	else:
		queue_free()

func remember_focus() -> void:
	_last_focus = get_viewport().gui_get_focus_owner()

func restore_focus() -> void:
	if _last_focus and is_instance_valid(_last_focus) and _last_focus.is_visible_in_tree():
		_last_focus.grab_focus()
	else:
		focus_first()

func rebuild() -> void:
	var idx := -1
	var f := get_viewport().gui_get_focus_owner()
	var btns := _all_buttons(self)
	if f:
		idx = btns.find(f)
	for c in get_children():
		c.queue_free()
	first_focus = null
	await get_tree().process_frame
	build()
	await get_tree().process_frame
	var nb := _all_buttons(self)
	if idx >= 0 and idx < nb.size():
		nb[idx].grab_focus()
	else:
		focus_first()

func _all_buttons(n: Node) -> Array:
	var out: Array = []
	for c in n.get_children():
		if c is BaseButton or c is Slider:
			out.append(c)
		out.append_array(_all_buttons(c))
	return out
