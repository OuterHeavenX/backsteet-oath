class_name JournalMenu
extends Menu
## Current objective (replayable without cutscenes), story notes and side-job status.

var info: Label

func build() -> void:
	var c := make_frame("JOURNAL", Vector2(540, 280))
	c.add_child(UIKit.label("CURRENT OBJECTIVE", UIKit.MUSTARD))
	c.add_child(UIKit.wrap_label(Story.objective_text(), 520, Color.WHITE))
	var detail := Story.objective_detail()
	if detail != "":
		c.add_child(UIKit.wrap_label(detail, 520, UIKit.DIM))
	var sc := ScrollContainer.new()
	sc.custom_minimum_size = Vector2(520, 170)
	sc.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	sc.follow_focus = true
	c.add_child(sc)
	var v := UIKit.vbox(2)
	sc.add_child(v)
	v.add_child(UIKit.label("SIDE JOBS", UIKit.MUSTARD))
	var any := false
	var first: Control = null
	for qid in Content.quests:
		var q: Dictionary = Content.quests[qid]
		var st := Quests.state(qid)
		if st == "inactive":
			continue
		any = true
		var tag := {"active": "[ACTIVE]", "done": "[DONE]", "failed": "[RETRY]"}.get(st, "")
		var col: Color = UIKit.CREAM if st == "active" else UIKit.DIM
		var b := UIKit.button("%s %s" % [tag, q.name], func(): pass, 500)
		b.add_theme_color_override("font_color", col)
		var step_text := Quests.step_text(qid)
		b.focus_entered.connect(func(): info.text = "%s  Given by %s. %s  Reward: %s" % [q.get("desc", ""), Content.character_name(q.giver), step_text, q.get("reward_text", "")])
		v.add_child(b)
		v.add_child(UIKit.wrap_label("   " + step_text, 500, UIKit.DIM))
		if first == null:
			first = b
	if not any:
		v.add_child(UIKit.wrap_label("No side jobs yet. Talk to people around town; a few of them could use a hand.", 500, UIKit.DIM))
	v.add_child(UIKit.spacer(4))
	v.add_child(UIKit.label("NOTES", UIKit.MUSTARD))
	var notes: Dictionary = Content.story.get("notes", {})
	if GameState.notes.is_empty():
		v.add_child(UIKit.label("Nothing yet.", UIKit.DIM))
	for n in GameState.notes:
		v.add_child(UIKit.wrap_label("- " + str(notes.get(n, n)), 500, UIKit.CREAM))
	info = UIKit.wrap_label("", 520, UIKit.DIM)
	c.add_child(info)
	var close_b := UIKit.button("Close", close, 120)
	c.add_child(close_b)
	first_focus = first if first else close_b
