class_name ShopMenu
extends Menu
## Food / manual / workbench shops. Exact prices and effects shown before buying;
## a short lockout prevents accidental double purchases.

var shop_id := ""
var shop: Dictionary = {}
var info: Label
var cash_label: Label
var lock_until := 0
var rows: VBoxContainer

static func effect_text(id: String) -> String:
	var it: Dictionary = Content.item(id)
	var parts: Array = []
	var heal := int(it.get("heal", 0))
	if heal >= 999:
		parts.append("Full HP")
	elif heal > 0:
		parts.append("+%d HP" % heal)
	for s in it.get("bonus", {}):
		var room_left: int = int(Content.food_caps.get(s, 8)) - int(GameState.food.get(s, 0))
		var tag := "" if room_left > 0 else " (maxed)"
		parts.append("%s +%d permanent%s" % [s.to_upper(), int(it.bonus[s]), tag])
	if it.get("revive", false):
		parts.append("Auto-revive once")
	return ", ".join(parts)

func build() -> void:
	shop = Content.shops.get(shop_id, {})
	var c := make_frame(shop.get("name", "Shop"), Vector2(520, 270))
	var top := UIKit.hbox(8)
	c.add_child(top)
	top.add_child(UIKit.label(Content.character_name(shop.get("keeper", "")) + ": \"" + shop.get("greet", "") + "\"", UIKit.CREAM))
	cash_label = UIKit.label("", UIKit.CASHC)
	cash_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cash_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top.add_child(cash_label)
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(500, 190)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	rows = UIKit.vbox(2)
	sc.add_child(rows)
	info = UIKit.wrap_label("", 500, UIKit.DIM)
	c.add_child(info)
	var buttons: Array = []
	match shop.get("kind", "food"):
		"food":
			for id in shop.get("stock", []):
				buttons.append(_food_row(id))
		"skills":
			for entry in shop.get("stock", []):
				var sid: String = entry[0]
				var req: String = entry[1]
				buttons.append(_skill_row(sid, req))
			if shop_id == "rec":
				buttons.append(_respec_row())
		"upgrades":
			for line in shop.get("stock", []):
				buttons.append(_upgrade_row(line))
	var leave := UIKit.button("Leave", close, 160)
	rows.add_child(leave)
	buttons.append(leave)
	_refresh_cash()
	first_focus = buttons[0] if not buttons.is_empty() else leave

func _refresh_cash() -> void:
	cash_label.text = "Cash $%d   HP %d/%d" % [GameState.cash, GameState.hp, GameState.max_hp()]

func _locked() -> bool:
	if Time.get_ticks_msec() < lock_until:
		return true
	lock_until = Time.get_ticks_msec() + 350
	return false

func _food_row(id: String) -> Button:
	var it: Dictionary = Content.item(id)
	var h := UIKit.hbox(6)
	h.add_child(UIKit.icon_rect(SpriteLib.icon(it.get("icon", id)), 16))
	var b := UIKit.button("%s  $%d" % [it.get("name", id), int(it.get("price", 0))], func(): _buy_food(id), 190)
	b.focus_entered.connect(func(): info.text = "%s  %s%s" % [it.get("desc", ""), effect_text(id), "  (can take out)" if it.get("takeout", false) else ""])
	h.add_child(b)
	h.add_child(UIKit.label(effect_text(id), UIKit.DIM))
	rows.add_child(h)
	return b

func _buy_food(id: String) -> void:
	if _locked():
		return
	var it: Dictionary = Content.item(id)
	var price := int(it.get("price", 0))
	if GameState.cash < price:
		Audio.sfx("deny")
		info.text = "Not enough cash. You need $%d." % price
		return
	var choice := 0
	if it.get("takeout", false):
		var opts := ["Eat it now", "Take it to go (bag %d/%d)" % [GameState.bag.size(), Content.bag_size], "Never mind"]
		var m := _ChoiceMenu.new()
		m.question = "%s for $%d?" % [it.get("name", id), price]
		m.options = opts
		host.push_menu(m)
		await m.closed
		choice = m.result
		if choice == 2 or choice < 0:
			return
		if choice == 1 and GameState.bag_full():
			Audio.sfx("deny")
			info.text = "Your bag is full."
			return
	if it.get("revive", false):
		choice = 1
		if GameState.bag_full():
			Audio.sfx("deny")
			info.text = "Your bag is full."
			return
	if not GameState.spend(price):
		Audio.sfx("deny")
		return
	Audio.sfx("purchase")
	if choice == 1:
		GameState.add_to_bag(id)
		info.text = "Packed %s to go." % it.get("name", id)
	else:
		var res := GameState.consume(id)
		Audio.sfx("eat" if it.kind == "food" else "heal", -2.0)
		var msg := "Ate %s. +%d HP." % [it.get("name", id), int(res.heal)]
		for s in res.bonus:
			msg += " %s +%d!" % [s.to_upper(), int(res.bonus[s])]
		if not res.capped.is_empty():
			msg += " (Some stats are at their food cap.)"
		info.text = msg
	_sync_player()
	_refresh_cash()
	SaveService.save_game()

func _sync_player() -> void:
	var w = host
	if w and w.get("room") and w.room and w.room.player:
		w.room.player.refresh_stats()
		w.room.player.hp = GameState.hp

func _skill_row(sid: String, req: String) -> Button:
	var s: Dictionary = Content.skill(sid)
	var owned := GameState.has_skill(sid)
	var available := req == "" or GameState.check(req)
	var h := UIKit.hbox(6)
	h.add_child(UIKit.icon_rect(SpriteLib.icon(s.get("icon", "skill")), 16))
	var label_t := "%s  $%d" % [s.name, int(s.price)]
	if owned:
		label_t = "%s  (learned)" % s.name
	elif not available:
		label_t = "???  (come back later)"
	var b := UIKit.button(label_t, func(): _buy_skill(sid, req), 210)
	b.disabled = owned
	b.focus_entered.connect(func():
		if available:
			info.text = "%s  How: %s" % [s.desc, Story.format_text(s.how)]
		else:
			info.text = "This manual isn't on the shelf yet. Keep following the story.")
	h.add_child(b)
	h.add_child(UIKit.label(Story.format_text(s.how) if available else "", UIKit.DIM))
	rows.add_child(h)
	return b

func _buy_skill(sid: String, req: String) -> void:
	if _locked() or GameState.has_skill(sid):
		return
	if req != "" and not GameState.check(req):
		Audio.sfx("deny")
		return
	var s: Dictionary = Content.skill(sid)
	var price := int(s.price)
	if GameState.cash < price:
		Audio.sfx("deny")
		info.text = "Not enough cash. You need $%d." % price
		return
	var yes: bool = await ConfirmMenu.ask(host, "Buy %s for $%d?\n%s" % [s.name, price, Story.format_text(s.how)], false)
	if not yes or not GameState.spend(price):
		return
	GameState.learn(sid)
	Audio.sfx("purchase")
	Audio.sfx("quest_complete", -4.0)
	SaveService.save_game()
	rebuild()
	await get_tree().process_frame
	info.text = "Learned %s! %s" % [s.name, Story.format_text(s.how)]

func _respec_row() -> Button:
	var r: Dictionary = Content.services.get("respec", {})
	var avail := GameState.check(r.get("requires", ""))
	var b := UIKit.button(("Refund stat points  $%d" % int(r.price)) if avail else "Refund stat points  (later)", _respec, 210)
	b.focus_entered.connect(func(): info.text = "Benny resets the stat points you've spent so you can redistribute them. Food and level gains are kept.")
	b.disabled = not avail
	rows.add_child(b)
	return b

func _respec() -> void:
	if _locked():
		return
	var price := int(Content.services.respec.price)
	var spent := 0
	for s in GameState.alloc:
		spent += int(GameState.alloc[s])
	if spent == 0:
		info.text = "You haven't spent any points yet."
		return
	if GameState.cash < price:
		Audio.sfx("deny")
		info.text = "Not enough cash."
		return
	var yes: bool = await ConfirmMenu.ask(host, "Refund %d stat points for $%d? Auto-spend will be turned off." % [spent, price], false)
	if yes and GameState.spend(price):
		GameState.respec()
		GameState.auto_alloc = false
		Audio.sfx("purchase")
		_sync_player()
		_refresh_cash()
		info.text = "Points refunded. Spend them in Status."

func _upgrade_row(line: String) -> Button:
	var u: Dictionary = Content.upgrades[line]
	var tier := GameState.upgrade_tier(line)
	var tiers: Array = u.tiers
	var h := UIKit.hbox(6)
	var text := "%s  (maxed)" % u.name
	var next: Dictionary = {}
	var avail := false
	if tier < tiers.size():
		next = tiers[tier]
		avail = GameState.check(next.get("requires", ""))
		text = ("%s  Tier %d  $%d" % [u.name, tier + 1, int(next.price)]) if avail else ("%s  Tier %d  (later)" % [u.name, tier + 1])
	var b := UIKit.button(text, func(): _buy_upgrade(line), 230)
	b.disabled = tier >= tiers.size()
	b.focus_entered.connect(func():
		var t: String = u.desc
		if not next.is_empty():
			t += "  Next: +%d power%s." % [int(next.power), (", +%d%% durability" % int(float(next.dur) * 100)) if float(next.dur) > 0 else ""]
			if not avail:
				t += " Mara needs better parts. Keep going."
		info.text = t)
	h.add_child(b)
	h.add_child(UIKit.label("*".repeat(tier) + ".".repeat(tiers.size() - tier), UIKit.MUSTARD))
	rows.add_child(h)
	return b

func _buy_upgrade(line: String) -> void:
	if _locked():
		return
	var u: Dictionary = Content.upgrades[line]
	var tier := GameState.upgrade_tier(line)
	if tier >= u.tiers.size():
		return
	var next: Dictionary = u.tiers[tier]
	if not GameState.check(next.get("requires", "")):
		Audio.sfx("deny")
		info.text = "Mara: \"I need parts I don't have yet. Ask me again later.\""
		return
	if GameState.cash < int(next.price):
		Audio.sfx("deny")
		info.text = "Not enough cash. You need $%d." % int(next.price)
		return
	var yes: bool = await ConfirmMenu.ask(host, "Upgrade %s to tier %d for $%d?" % [u.name, tier + 1, int(next.price)], false)
	if yes and GameState.spend(int(next.price)):
		GameState.upgrades[line] = tier + 1
		Audio.sfx("purchase")
		Audio.sfx("weapon_hit_metal", -6.0)
		SaveService.save_game()
		rebuild()

## Simple multiple-choice popup.
class _ChoiceMenu extends Menu:
	var question := ""
	var options: Array = []
	var result := -1
	func build() -> void:
		var c := make_frame("", Vector2(260, 0))
		c.add_child(UIKit.wrap_label(question, 240))
		for i in options.size():
			var b := UIKit.button(options[i], func(): result = i; close(), 240)
			c.add_child(b)
			if i == 0:
				first_focus = b
