class_name DefeatMenu
extends Menu
## Fair defeat: keep XP, skills, quests and progress; lose a modest capped amount of cash.

var loss := 0
var boss_retry := false
var retry_room := ""
var retry_enabled := false

func _init() -> void:
	super._init()
	back_allowed = false

func build() -> void:
	var c := make_frame("KNOCKED OUT!", Vector2(320, 0))
	var hub_name: String = Content.room(GameState.hub_room).get("name", "the diner")
	c.add_child(UIKit.wrap_label("Nico hits the pavement. You keep all XP, techniques, items and story progress.", 300))
	c.add_child(UIKit.label("Dropped cash: $%d  (20%%, max $40)" % loss, UIKit.DANGER))
	c.add_child(UIKit.spacer(4))
	var first: Control = null
	if retry_enabled:
		var label_t := "Retry the fight (full HP, no cutscene)" if boss_retry else "Get up and try this street again"
		var b := UIKit.button(label_t, func(): host.retry_here(loss), 300)
		c.add_child(b)
		first = b
	var h := UIKit.button("Wake up at %s (full HP)" % hub_name, func(): host.respawn_at_hub(loss), 300)
	c.add_child(h)
	if first == null:
		first = h
	c.add_child(UIKit.wrap_label("Tip: eat at shops before big fights, carry takeout food, and use Guard. Relaxed difficulty is in Settings.", 300, UIKit.DIM))
	first_focus = first
