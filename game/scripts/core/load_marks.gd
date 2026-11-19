class_name LoadMarks
extends Node
## Debug-only timing markers for the load tests (tools/webtest/load_test.js). SceneFlow creates this node only
## when the page URL contains `bo_debug` (web) or the game is started with `-- --bo-debug` (desktop), so it
## costs players nothing. One console line per milestone, once per scene:
##   BO_MARK title_ready ms=<engine msec>    the title screen has drawn its first frames
##   BO_MARK world_ready ms=...              a room is built and has drawn its first frames
##   BO_MARK dialogue ms=...                 a dialogue box is open (the load test skips the intro here)
##   BO_MARK control ms=...                  the player can act: no fade, cutscene, dialogue, menu or input lock

var _scene_id := 0
var _frames := 0
var _done: Dictionary = {}

static func wanted() -> bool:
	if OS.has_feature("web"):
		var q = JavaScriptBridge.eval("window.location.search", true)
		return q != null and "bo_debug" in str(q)
	return "--bo-debug" in OS.get_cmdline_user_args()

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

func _mark(name: String) -> void:
	if _done.has(name):
		return
	_done[name] = true
	print("BO_MARK %s ms=%d" % [name, Time.get_ticks_msec()])

func _process(_d: float) -> void:
	var sc := get_tree().current_scene
	if sc == null:
		return
	if sc.get_instance_id() != _scene_id:
		_scene_id = sc.get_instance_id()
		_frames = 0
		_done.clear()
	_frames += 1
	if _frames < 3:          # let the scene draw before calling it ready
		return
	if sc.scene_file_path.ends_with("title.tscn"):
		_mark("title_ready")
		return
	var room = sc.get("room")
	if room == null or not is_instance_valid(room) or room.get("player") == null or room.player == null:
		return
	_mark("world_ready")
	if sc.dialogue_active():
		_mark("dialogue")
	var p = room.player
	if get_tree().paused or SceneFlow.busy or sc.transitioning or room.cutscene or sc.dialogue_active():
		return
	if not p.control_enabled or p.input_lock > 0 or not sc.menus.is_empty():
		return
	_mark("control")
