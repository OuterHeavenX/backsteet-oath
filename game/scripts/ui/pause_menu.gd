class_name PauseMenu
extends Menu

func build() -> void:
	var c := make_frame("PAUSED", Vector2(240, 0))
	var info := "%s  -  %s" % [Content.room(GameState.room).get("name", ""), Content.district_name(Content.room(GameState.room).get("district", ""))]
	c.add_child(UIKit.label(info, UIKit.DIM))
	c.add_child(UIKit.label("Playtime " + UIKit.fmt_time(float(GameState.stats.get("playtime", 0.0))), UIKit.DIM))
	c.add_child(UIKit.spacer(2))
	var btns: Array = []
	btns.append(UIKit.button("Resume", close, 220))
	btns.append(UIKit.button("Status & Bag", func(): host.push_menu(StatusMenu.new()), 220))
	btns.append(UIKit.button("Journal", func(): host.push_menu(JournalMenu.new()), 220))
	btns.append(UIKit.button("Map", func(): host.push_menu(MapMenu.new()), 220))
	var safe: bool = Content.room(GameState.room).get("safe", false)
	var save_btn := UIKit.button("Save Game" if safe else "Save Game (safe rooms only)", _save, 220)
	save_btn.disabled = not safe
	btns.append(save_btn)
	btns.append(UIKit.button("Settings", func(): host.push_menu(SettingsMenu.new()), 220))
	btns.append(UIKit.button("Controls", func(): host.push_menu(ControlsMenu.new()), 220))
	btns.append(UIKit.button("Quit to Title", _quit, 220))
	for b in btns:
		c.add_child(b)
	c.add_child(UIKit.spacer(2))
	c.add_child(UIKit.wrap_label("Progress autosaves when you enter a room. Diner, noodle bar, canteen, arcade and bait shop are safe hubs.", 220, UIKit.DIM))
	first_focus = btns[0]

func _save() -> void:
	var m := SlotMenu.new()
	m.mode = "save"
	host.push_menu(m)

func _quit() -> void:
	var yes: bool = await ConfirmMenu.ask(host, "Quit to the title screen? Progress since your last autosave (last room entered) will be kept; anything after it is lost.")
	if yes:
		host.quit_to_title()
