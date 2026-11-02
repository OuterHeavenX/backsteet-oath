class_name SettingsMenu
extends Menu
## Audio, accessibility, difficulty, display and touch options. Saved immediately.

var info: Label

func build() -> void:
	var c := make_frame("SETTINGS", Vector2(380, 0))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(360, 230)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	var v := UIKit.vbox(2)
	sc.add_child(v)
	var S := Settings
	var items: Array = []
	items.append([Widgets.slider("Master volume", S.master_volume, func(x): S.master_volume = x; S.save_settings(), 340), "Overall volume."])
	items.append([Widgets.slider("Music", S.music_volume, func(x): S.music_volume = x; S.save_settings(), 340), "Music volume."])
	items.append([Widgets.slider("Sound effects", S.sfx_volume, func(x): S.sfx_volume = x; S.save_settings(), 340), "Hits, footsteps, menus."])
	items.append([Widgets.cycler("Difficulty", ["Normal", "Relaxed"], 0 if S.difficulty == "normal" else 1, func(i): S.difficulty = ["normal", "relaxed"][i]; S.save_settings(), 340), "Relaxed: 40% less damage taken, fewer enemies attack at once, wider perfect-guard window. All content stays."])
	items.append([Widgets.cycler("Screen shake", ["Off", "Low", "Full"], [0.0, 0.5, 1.0].find(snappedf(S.screen_shake, 0.5)), func(i): S.screen_shake = [0.0, 0.5, 1.0][i]; S.save_settings(), 340), "Camera shake on heavy hits."])
	items.append([Widgets.cycler("Hit flashes", ["Off", "Low", "Full"], [0.0, 0.5, 1.0].find(snappedf(S.flash, 0.5)), func(i): S.flash = [0.0, 0.5, 1.0][i]; S.save_settings(), 340), "White flash on hit and red flash on enemy wind-ups. Wind-ups still show a softer tint at Off."])
	items.append([Widgets.cycler("Text speed", ["Slow", "Normal", "Fast", "Instant"], S.text_speed, func(i): S.text_speed = i; S.save_settings(), 340), "Dialogue typing speed."])
	items.append([Widgets.cycler("Large text", ["Off", "On"], 1 if S.large_text else 0, func(i): S.large_text = i == 1; S.save_settings(); _apply_text(), 340), "Bigger, chunkier font for menus, HUD and dialogue."])
	items.append([Widgets.cycler("Control hints", ["On", "Off"], 0 if S.show_hints else 1, func(i): S.show_hints = i == 0; S.save_settings(), 340), "Short on-screen tips about controls."])
	items.append([Widgets.cycler("Touch controls", ["Auto", "On", "Off"], ["auto", "on", "off"].find(S.touch_controls), func(i): S.touch_controls = ["auto", "on", "off"][i]; S.save_settings(), 340), "Auto shows the on-screen pad when you touch the screen."])
	items.append([Widgets.cycler("Stick deadzone", ["10%", "15%", "20%", "25%", "30%", "40%", "50%"], maxi(0, [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5].find(snappedf(S.deadzone, 0.05))), func(i): S.deadzone = [0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5][i]; S.apply_input_map(); S.save_settings(), 340), "Raise this if your character drifts with a worn stick."])
	if not OS.has_feature("web"):
		items.append([Widgets.cycler("Fullscreen", ["Off", "On"], 1 if S.fullscreen else 0, func(i): S.set_fullscreen(i == 1), 340), "Toggle fullscreen (F11 also works)."])
	else:
		items.append([UIKit.button("Toggle fullscreen", func(): S.set_fullscreen(DisplayServer.window_get_mode() != DisplayServer.WINDOW_MODE_FULLSCREEN), 340), "Browser fullscreen (itch.io's fullscreen button also works)."])
	for it in items:
		var ctl: Control = it[0]
		var desc: String = it[1]
		ctl.focus_entered.connect(func(): info.text = desc)
		v.add_child(ctl)
	info = UIKit.wrap_label("", 360, UIKit.DIM)
	c.add_child(info)
	var back := UIKit.button("Back", close, 120)
	c.add_child(back)
	first_focus = items[0][0]

func _apply_text() -> void:
	get_tree().root.theme = UIKit.build_theme()
	UIKit.apply(self)
	var w = host
	if w and w.get("dialogue"):
		UIKit.apply(w.dialogue)
		UIKit.apply(w.hud)
	rebuild()
