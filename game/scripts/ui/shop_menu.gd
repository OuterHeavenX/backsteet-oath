class_name ShopMenu
extends Menu
## Food / manual / workbench shops. Exact prices and effects shown before buying;
## a short lockout prevents accidental double purchases.
##
## Every price on screen and every charge comes from GameState.price_for(shop_id, list price), so the two can
## never differ; while the shop's discount applies the list price is shown beside it. Focusing a row shows
## what the purchase would change right now (Preview / PreviewText: the game's own numbers, never charged).

var shop_id := ""
var shop: Dictionary = {}
var info: Label
var preview: Label
var cash_label: Label
var lock_until := 0
var rows: VBoxContainer
var _effects: Dictionary = {}      # item id -> the row's effect label (refreshed after a meal)
var _focused := ""                 # item id of the focused food row

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

## What this shop charges for something with the given list price.
func price_of(base: int) -> int:
	return GameState.price_for(shop_id, base)

func build() -> void:
	shop = Content.shops.get(shop_id, {})
	_effects.clear()
	var c := make_frame(shop.get("name", "Shop"), Vector2(520, 270))
	var top := UIKit.hbox(8)
	c.add_child(top)
	top.add_child(UIKit.label(Content.character_name(shop.get("keeper", "")) + ": \"" + shop.get("greet", "") + "\"", UIKit.CREAM))
	cash_label = UIKit.label("", UIKit.CASHC)
	cash_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cash_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top.add_child(cash_label)
	var note := PreviewText.discount_note(shop_id)
	if note != "":
		c.add_child(UIKit.wrap_label(note, 500, UIKit.CASHC))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(500, 138 if Settings.large_text else 160)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	rows = UIKit.vbox(2)
	sc.add_child(rows)
	info = UIKit.wrap_label("", 500, UIKit.DIM)
	c.add_child(info)
	preview = UIKit.wrap_label("", 500, UIKit.CREAM)
	preview.custom_minimum_size = Vector2(500, 2 * (UIKit.base_size() + 3))
	c.add_child(preview)
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
	leave.focus_entered.connect(func(): _show("", ""))
	rows.add_child(leave)
	buttons.append(leave)
	_refresh_cash()
	first_focus = buttons[0] if not buttons.is_empty() else leave
	if not InputPrompts.device_changed.is_connected(_on_device_changed):
		InputPrompts.device_changed.connect(_on_device_changed)

## Technique inputs are written for the device in use: redraw them when it changes.
func _on_device_changed(_kind: String) -> void:
	if shop.get("kind", "") == "skills" and is_top() and is_inside_tree():
		rebuild()

func _show(desc: String, what_changes: String, warn: bool = false) -> void:
	info.text = desc
	preview.text = what_changes
	preview.add_theme_color_override("font_color", UIKit.MUSTARD if warn else UIKit.CREAM)

func _refresh_cash() -> void:
	cash_label.text = "Cash $%d   HP %d/%d" % [GameState.cash, GameState.hp, GameState.max_hp()]

func _locked() -> bool:
	if Time.get_ticks_msec() < lock_until:
		return true
	lock_until = Time.get_ticks_msec() + 350
	return false

# ---------------------------------------------------------------- food
func _food_row(id: String) -> Button:
	var it: Dictionary = Content.item(id)
	var h := UIKit.hbox(6)
	h.add_child(UIKit.icon_rect(SpriteLib.icon(it.get("icon", id)), 16))
	var b := UIKit.button("%s  %s" % [it.get("name", id), PreviewText.price(shop_id, int(it.get("price", 0)))], func(): _buy_food(id), 190)
	b.focus_entered.connect(func(): _focus_food(id))
	h.add_child(b)
	var eff := UIKit.label(effect_text(id), UIKit.DIM)
	_effects[id] = eff
	h.add_child(eff)
	rows.add_child(h)
	return b

func _focus_food(id: String) -> void:
	_focused = id
	var it: Dictionary = Content.item(id)
	var p := PreviewText.food(id)
	_show("%s  %s%s" % [it.get("desc", ""), effect_text(id), "  (can take out)" if it.get("takeout", false) else ""], p.text, p.no_effect)

## After a meal the caps and the HP have moved: bring the row labels and the focused preview up to date.
func _refresh_food() -> void:
	for id in _effects:
		_effects[id].text = effect_text(id)
	if _focused != "":
		var p := PreviewText.food(_focused)
		preview.text = p.text
		preview.add_theme_color_override("font_color", UIKit.MUSTARD if p.no_effect else UIKit.CREAM)

func _buy_food(id: String) -> void:
	if _locked():
		return
	var it: Dictionary = Content.item(id)
	var price := price_of(int(it.get("price", 0)))
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
	if choice == 0 and Preview.food(id).no_effect:
		# The preview says eating this now changes nothing at all: do not take money for it.
		Audio.sfx("deny")
		info.text = "%s would do nothing for you right now, so nothing was charged." % it.get("name", id)
		return
	if GameState.cash < price or not GameState.spend(price):
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
	_refresh_food()
	SaveService.save_game()

func _sync_player() -> void:
	var w = host
	if w and w.get("room") and w.room and w.room.player:
		w.room.player.refresh_stats()
		w.room.player.hp = GameState.hp

# ---------------------------------------------------------------- manuals
func _skill_row(sid: String, req: String) -> Button:
	var s: Dictionary = Content.skill(sid)
	var owned := GameState.has_skill(sid)
	var available := req == "" or GameState.check(req)
	var h := UIKit.hbox(6)
	h.add_child(UIKit.icon_rect(SpriteLib.icon(s.get("icon", "skill")), 16))
	var label_t := "%s  %s" % [s.name, PreviewText.price(shop_id, int(s.price))]
	if _free_lesson(sid):
		label_t = "%s  (free: Benny's lesson)" % s.name
	if owned:
		label_t = "%s  (learned)" % s.name
	elif not available:
		label_t = "???  (come back later)"
	var b := UIKit.button(label_t, func(): _buy_skill(sid, req), 210)
	b.focus_entered.connect(func():
		if available or owned:
			_show("%s  How: %s" % [s.desc, PreviewText.technique_how(sid)], "%s  Confirm to watch the move%s." % [
				" ".join(PreviewText.technique(sid)), "" if owned else " before you decide (looking is free)"])
		else:
			_show("This manual isn't on the shelf yet. Keep following the story.", ""))
	h.add_child(b)
	h.add_child(UIKit.label(PreviewText.technique_how(sid) if available or owned else "", UIKit.DIM))
	rows.add_child(h)
	return b

## Shoulder Charge is Benny's free first lesson while that offer stands.
func _free_lesson(sid: String) -> bool:
	return sid == "shoulder" and shop_id == "rec" and not GameState.has_skill(sid) and Story._benny_lesson_due()

## Pressing a manual opens its preview (the move, its input on this device, what it does). The preview is
## free; the charge below happens only if the player presses Buy there.
func _buy_skill(sid: String, req: String) -> void:
	if _locked():
		return
	if not GameState.has_skill(sid) and req != "" and not GameState.check(req):
		Audio.sfx("deny")
		return
	var s: Dictionary = Content.skill(sid)
	if _free_lesson(sid):
		# never sell what Benny is still offering to teach for nothing
		Audio.sfx("deny")
		_show("Benny teaches this one for free. Close the shop, talk to him again and take the lesson.", "")
		return
	var yes: bool = await ManualPreviewMenu.ask(host, sid, shop_id)
	var price := price_of(int(s.price))
	if not yes or GameState.has_skill(sid) or GameState.cash < price or not GameState.spend(price):
		return
	GameState.learn(sid)
	# the tips director reminds the player of a new move at the start of later fights until it is used once
	var tutor = host.get("tutor") if host else null
	if tutor:
		tutor.arm_skill(sid)
	Audio.sfx("purchase")
	Audio.sfx("quest_complete", -4.0)
	SaveService.save_game()
	rebuild()
	await get_tree().process_frame
	info.text = "Learned %s! %s" % [s.name, PreviewText.technique_how(sid)]

func _respec_row() -> Button:
	var r: Dictionary = Content.services.get("respec", {})
	var avail := GameState.check(r.get("requires", ""))
	var b := UIKit.button(("Refund stat points  %s" % PreviewText.price(shop_id, int(r.price))) if avail else "Refund stat points  (later)", _respec, 210)
	b.focus_entered.connect(func(): _show("Benny resets the stat points you've spent so you can redistribute them. Food and level gains are kept.", ""))
	b.disabled = not avail
	rows.add_child(b)
	return b

func _respec() -> void:
	if _locked():
		return
	var price := price_of(int(Content.services.respec.price))
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
	if yes and GameState.cash >= price and GameState.spend(price):
		GameState.respec()
		GameState.auto_alloc = false
		Audio.sfx("purchase")
		_sync_player()
		_refresh_cash()
		info.text = "Points refunded. Spend them in Status."

# ---------------------------------------------------------------- workbench
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
		text = ("%s  Tier %d  %s" % [u.name, tier + 1, PreviewText.price(shop_id, int(next.price))]) if avail else ("%s  Tier %d  (later)" % [u.name, tier + 1])
	var b := UIKit.button(text, func(): _buy_upgrade(line), 230)
	b.disabled = tier >= tiers.size()
	b.focus_entered.connect(func():
		var t: String = u.desc
		if not next.is_empty() and not avail:
			t += "  Mara needs better parts for the next tier. Keep going."
		_show(t, PreviewText.workbench(line)))
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
	var price := price_of(int(next.price))
	if GameState.cash < price:
		Audio.sfx("deny")
		info.text = "Not enough cash. You need $%d." % price
		return
	var yes: bool = await ConfirmMenu.ask(host, "Upgrade %s to tier %d for $%d?" % [u.name, tier + 1, price], false)
	if yes and GameState.upgrade_tier(line) == tier and GameState.cash >= price and GameState.spend(price):
		Preview.upgrade(line)
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
