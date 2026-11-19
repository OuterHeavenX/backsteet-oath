class_name ManualPreviewMenu
extends Menu
## A look at a technique before paying for it (or a refresher on one already learned): a small Nico doing
## the move, how to do it on the device in use, what it is for, and what it does against a named fighter.
## Looking is free and changes nothing; the shop charges only if the player presses Buy here.

var skill_id := ""
var shop_id := ""            # the shop selling it; "" = just looking (learned techniques, Status menu)
var wants_to_buy := false
var _how: Label

func build() -> void:
	var s: Dictionary = Content.skill(skill_id)
	var c := make_frame(str(s.get("name", skill_id)), Vector2(450, 0))
	var h := UIKit.hbox(10)
	c.add_child(h)
	var demo := MoveDemo.new()
	demo.skill_id = skill_id
	demo.custom_minimum_size = Vector2(128, 104)
	h.add_child(demo)
	var v := UIKit.vbox(3)
	h.add_child(v)
	_how = UIKit.wrap_label("", 300, UIKit.MUSTARD)
	v.add_child(_how)
	_refresh_how()
	v.add_child(UIKit.wrap_label(str(s.get("desc", "")), 300, UIKit.CREAM))
	for line in PreviewText.technique(skill_id):
		v.add_child(UIKit.wrap_label(line, 300, UIKit.DIM))
	c.add_child(UIKit.spacer(2))
	var buying := shop_id != "" and not GameState.has_skill(skill_id)
	if buying:
		var price := GameState.price_for(shop_id, int(s.get("price", 0)))
		var short := price - GameState.cash
		c.add_child(UIKit.label("Price %s. You have $%d." % [PreviewText.price(shop_id, int(s.get("price", 0))), GameState.cash],
			UIKit.CASHC if short <= 0 else UIKit.DIM))
		var buy := UIKit.button(("Buy for $%d" % price) if short <= 0 else ("Not enough cash ($%d short)" % short), _buy, 240)
		c.add_child(buy)
		var no := UIKit.button("Not now", close, 240)
		c.add_child(no)
		first_focus = buy if short <= 0 else no
	else:
		if GameState.has_skill(skill_id):
			c.add_child(UIKit.label("Learned.", UIKit.CASHC))
		var ok := UIKit.button("Close", close, 240)
		c.add_child(ok)
		first_focus = ok
	if not InputPrompts.device_changed.is_connected(_on_device_changed):
		InputPrompts.device_changed.connect(_on_device_changed)

func _refresh_how() -> void:
	_how.text = "How: " + PreviewText.technique_how(skill_id)

func _on_device_changed(_kind: String) -> void:
	if is_instance_valid(_how):
		_refresh_how()

func _buy() -> void:
	if GameState.cash < GameState.price_for(shop_id, int(Content.skill(skill_id).get("price", 0))):
		Audio.sfx("deny")
		return
	wants_to_buy = true
	close()

## Shows the preview and returns true if the player pressed Buy. Nothing is charged here.
static func ask(host_node: Node, sid: String, shop: String = "") -> bool:
	var m := ManualPreviewMenu.new()
	m.skill_id = sid
	m.shop_id = shop
	host_node.push_menu(m)
	await m.closed
	return m.wants_to_buy
