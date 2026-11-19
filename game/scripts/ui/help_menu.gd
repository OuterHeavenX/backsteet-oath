class_name HelpMenu
extends Menu
## Controls, the fighting tips reference and (when the opt-in log is on) the playtest notes, behind one pause
## entry so the pause menu stays short enough for Large text on a 360-line screen.

func build() -> void:
	var c := make_frame("HELP & TIPS", Vector2(240, 0))
	var btns: Array = []
	btns.append(UIKit.button("Controls", func(): host.push_menu(ControlsMenu.new()), 220))
	btns.append(UIKit.button("Fighting tips", func(): host.push_menu(TipsMenu.new()), 220))
	if Settings.playtest_log:
		btns.append(UIKit.button("Playtest notes", func(): host.push_menu(PlaytestMenu.new()), 220))
	for b in btns:
		c.add_child(b)
	first_focus = btns[0]
