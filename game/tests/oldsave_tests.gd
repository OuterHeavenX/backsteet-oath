extends Node
## Loads real 1.3.0-rc1 save files (made by running that build's bot; one per story stage, under
## tests/fixtures/saves_1_3/) into this build and checks nothing breaks and nobody is pushed back into the
## new opening. Run: godot --headless --fixed-fps 60 res://tests/oldsave_tests.tscn

const DIR := "res://tests/fixtures/saves_1_3/"
var w: Node
var fails := 0
var passes := 0

func check(c: bool, n: String) -> void:
	if c:
		passes += 1
	else:
		fails += 1
		print("FAIL: ", n)

func frames(n: int) -> void:
	for i in n:
		await get_tree().physics_frame
		if w and is_instance_valid(w) and w.room and w.room.player:
			w.room.player.hp = w.room.player.max_hp
			GameState.hp = GameState.max_hp()

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.show_hints = true
	var files: Array = []
	var da := DirAccess.open(DIR)
	if da:
		for f in da.get_files():
			if f.ends_with(".json"):
				files.append(f)
	files.sort()
	check(files.size() >= 6, "1.3 save fixtures are present (%d)" % files.size())
	for f in files:
		await _one(f)
	print("OLD SAVE TESTS: %d passed, %d failed" % [passes, fails])
	get_tree().quit(fails)

func _one(fname: String) -> void:
	var text := FileAccess.get_file_as_string(DIR + fname)
	var d: Dictionary = SaveService.validate_payload_text(text)
	check(not d.is_empty(), "%s: accepted by the save validator" % fname)
	if d.is_empty():
		return
	check(str(d.get("game_version", "")).begins_with("1.3"), "%s: really is a 1.3 save (%s)" % [fname, str(d.get("game_version", ""))])
	if w and is_instance_valid(w):
		w.queue_free()
		await get_tree().process_frame
		await get_tree().process_frame
	get_tree().paused = false
	Story.busy = false
	GameState.from_dict(d.data)
	var stage := GameState.stage
	var lvl := GameState.level
	var cash := GameState.cash
	var skills: Array = GameState.skills.duplicate()
	var max_hp := GameState.max_hp()
	check(not GameState.has_flag("tutor_v2"), "%s: has no new-opening flag" % fname)
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)
	await get_tree().create_timer(1.0).timeout
	await frames(150)
	check(w.room != null and w.room.player != null, "%s: the world loads at stage %s in %s" % [fname, stage, GameState.room])
	if w.room == null:
		return
	# nothing from the new opening is forced on an existing game
	var opening_tips := 0
	for id in ["move", "combo", "guard", "throw", "door", "eat", "run", "shoulder"]:
		if w.tutor.state(id) != 0:
			opening_tips += 1
	check(opening_tips == 0, "%s: no opening tips are armed on an existing save" % fname)
	check(GameState.level == lvl and GameState.cash == cash and GameState.max_hp() == max_hp and GameState.skills == skills, "%s: loading changes nothing the player owns" % fname)
	# favours are only offered while the save is still in the Old Quarter chapter
	var past_duke := GameState.has_flag("boss_duke")
	check(Story._dot_meal_due() == (not past_duke) and Story._benny_lesson_due() == (not past_duke), "%s: opening favours offered only before Duke (past Duke: %s)" % [fname, str(past_duke)])
	# the town reflects the bosses this save has already beaten
	check((GameState.district_calm("old_quarter") == "clear") == past_duke, "%s: the Old Quarter is calm exactly when Duke is beaten" % fname)
	if GameState.has_flag("found_eli"):
		check(not GameState.check("!found_eli & !storage_run_done"), "%s: a save past the rescue will not get the shutter run" % fname)
	# a round trip through this build's save format keeps the story position
	var again: Dictionary = JSON.parse_string(JSON.stringify(SaveService.build_payload()))
	GameState.from_dict(again.data)
	check(GameState.stage == stage and GameState.level == lvl, "%s: re-saving in this build keeps the position" % fname)
	# completed saves can still start New Game+
	if GameState.has_flag("game_complete"):
		GameState.start_new_game_plus()
		check(GameState.ng_cycle == 1 and GameState.stage == "intro" and GameState.level == lvl and GameState.district_calm("old_quarter") == "", "%s: a completed 1.3 save starts New Game+ cleanly" % fname)
