class_name ConfirmMenu
extends Menu
## Yes/No confirmation. Defaults focus to "No" for destructive actions.

signal answered(yes: bool)
var question := "Are you sure?"
var yes_text := "Yes"
var no_text := "No"
var default_no := true

func build() -> void:
	var c := make_frame("", Vector2(260, 0))
	c.add_child(UIKit.wrap_label(question, 240))
	c.add_child(UIKit.spacer(4))
	var y := UIKit.button(yes_text, func(): _answer(true), 240)
	var n := UIKit.button(no_text, func(): _answer(false), 240)
	c.add_child(y)
	c.add_child(n)
	first_focus = n if default_no else y

func _answer(v: bool) -> void:
	answered.emit(v)
	close()

func close() -> void:
	if not is_queued_for_deletion():
		super.close()

static func ask(host_node: Node, q: String, destructive: bool = true) -> bool:
	var m := ConfirmMenu.new()
	m.question = q
	m.default_no = destructive
	var result := [false]
	m.answered.connect(func(v): result[0] = v)
	host_node.push_menu(m)
	await m.closed
	return result[0]
