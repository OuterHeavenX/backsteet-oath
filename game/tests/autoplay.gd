extends Node
## Autoplay bot. Plays the main campaign using only InputMap actions (the same path as a
## keyboard or controller): no cheats, no teleports, no stat edits. Verifies completability and
## measures an efficient-player duration in game time. Run:
##   godot --headless --fixed-fps 60 res://tests/autoplay.tscn
## Writes a JSON report to user://autoplay_report.json (or $AUTOPLAY_REPORT).

const TARGETS := {
	"intro": ["oq_kettle", 500.0],
	"find_mara": ["int_garage", 0.0],
	"chain_dogs": ["oq_chainlot", 1150.0],
	"market": ["cm_canalwalk", 1380.0],
	"pikes": ["cm_pier", 800.0],
	"ironworks": ["int_switch", 0.0],
	"foundry": ["iy_foundry", 1000.0],
	"neon": ["int_arcade", 0.0],
	"rooftops": ["nm_rooftops", 1250.0],
	"floodgate": ["fr_bridge", 700.0],
	"dockgate": ["fr_dockgate", 1000.0],
	"warehouse": ["rw_office", 520.0],
	"rook": ["rw_floor", 600.0],
}

var w: Node = null
var frames := 0
var held: Dictionary = {}
var stage_log: Array = []
var last_stage := ""
var deaths := 0
var counters := {"dialogue": 0, "cutscene": 0, "menu": 0, "combat": 0, "explore": 0, "loading": 0}
var room_time: Dictionary = {}
var last_pos := Vector2.ZERO
var still := 0
var punch_cd := 0
var combo_n := 0
var queue: Array = []   # [frame, action, pressed]
var done := false
var max_frames := 60 * 60 * 150
var notes: Array = []
var stuck_events := 0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	Audio.unlocked = true
	Settings.difficulty = OS.get_environment("AUTOPLAY_DIFF") if OS.get_environment("AUTOPLAY_DIFF") != "" else "normal"
	GameState.reset_new_game()
	Story.new_game()
	Story.credits_return = "title"
	SaveService.current_slot = 3
	w = load("res://scenes/world.tscn").instantiate()
	get_tree().root.add_child.call_deferred(w)

func _act(a: String, on: bool, strength: float = 1.0) -> void:
	if bool(held.get(a, false)) == on and on:
		return
	held[a] = on
	var ev := InputEventAction.new()
	ev.action = a
	ev.pressed = on
	ev.strength = strength if on else 0.0
	Input.parse_input_event(ev)

func _tap(a: String) -> void:
	_act(a, true)
	queue.append([frames + 2, a, false])

func _release_all() -> void:
	for a in held.keys():
		if held[a]:
			_act(a, false)

var blocked_t := 0
var detour := 0.0
func _move(dir: Vector2) -> void:
	var t := 0.25
	if w and w.room and w.room.player and absf(dir.x) > t and dir.y == 0.0:
		var p: Player = w.room.player
		if absf(p.vel.x) < 5.0 and p.state in ["idle", "walk", "run"]:
			blocked_t += 1
		else:
			blocked_t = maxi(0, blocked_t - 2)
		if blocked_t > 12 and detour == 0.0:
			var mid: float = (w.room.walk_top + w.room.walk_bot) * 0.5
			detour = 1.0 if p.position.y < mid else -1.0
		if detour != 0.0:
			dir.y = detour
			if blocked_t <= 0:
				detour = 0.0
	else:
		detour = 0.0
	_set_axis("move_right", dir.x > t)
	_set_axis("move_left", dir.x < -t)
	_set_axis("move_down", dir.y > t)
	_set_axis("move_up", dir.y < -t)

func _set_axis(a: String, on: bool) -> void:
	if on != bool(held.get(a, false)):
		_act(a, on)

func _physics_process(_d: float) -> void:
	if done:
		return
	frames += 1
	for q in queue.duplicate():
		if frames >= int(q[0]):
			_act(q[1], q[2])
			queue.erase(q)
	if frames > max_frames:
		_finish("timeout")
		return
	if GameState.has_flag("game_complete") and Story.credits_return == "world":
		_finish("complete")
		return
	if w == null or not is_instance_valid(w) or not w.is_inside_tree():
		return
	if GameState.stage != last_stage:
		stage_log.append({"stage": GameState.stage, "t": snappedf(frames / 60.0, 0.1), "level": GameState.level, "deaths": deaths})
		print("[bot] t=%.1f stage=%s lvl=%d cash=%d deaths=%d" % [frames / 60.0, GameState.stage, GameState.level, GameState.cash, deaths])
		last_stage = GameState.stage
	var room: Node = w.room
	if room == null or w.transitioning:
		counters.loading += 1
		return
	room_time[room.room_id] = int(room_time.get(room.room_id, 0)) + 1
	if w.top_menu() != null:
		counters.menu += 1
		_handle_menu(w.top_menu())
		return
	if w.dialogue.active:
		counters.dialogue += 1
		_release_movement()
		if w.dialogue.choosing:
			_tap("ui_accept")
		elif frames % 5 == 0:
			_tap("punch")
		return
	if room.cutscene or Story.busy and room.player and not room.player.control_enabled:
		counters.cutscene += 1
		_release_movement()
		return
	var p: Player = room.player
	if p == null or p.dead:
		_release_all()
		return
	var target := _pick_enemy(room, p)
	if target:
		counters.combat += 1
		_fight(room, p, target)
	else:
		counters.explore += 1
		_act("guard", false)
		_navigate(room, p)
	# stuck watchdog
	if p.position.distance_to(last_pos) < 0.5 and not w.dialogue.active:
		still += 1
	else:
		still = 0
	last_pos = p.position
	if still > 60 * 8:
		stuck_events += 1
		notes.append("stuck in %s at %s (stage %s)" % [room.room_id, str(p.position), GameState.stage])
		still = 0
		_tap("jump")
		_move(Vector2(randf_range(-1, 1), randf_range(-1, 1)))

func _release_movement() -> void:
	for a in ["move_left", "move_right", "move_up", "move_down", "guard", "run"]:
		if held.get(a, false):
			_act(a, false)

func _handle_menu(m: Control) -> void:
	_release_movement()
	if frames % 10 != 0:
		return
	if m is DefeatMenu:
		deaths += 1
		print("[bot] defeated in %s (stage %s, lvl %d)" % [w.room.room_id if w.room else "?", GameState.stage, GameState.level])
		_tap("ui_accept")
	else:
		_tap("ui_cancel")

func _pick_enemy(room: Node, p: Player) -> Actor:
	var best: Actor = null
	var bd := INF
	for a in room.actors:
		if not (a is Enemy) or a.team != Actor.TEAM_ENEMY or a.dead:
			continue
		if not room.on_screen(a, -20) and not room.exits_locked and not room.boss_active:
			continue
		var d := absf(a.position.x - p.position.x) + absf(a.position.y - p.position.y) * 2.0
		if d < bd:
			bd = d
			best = a
	return best

func _fight(room: Node, p: Player, e: Actor) -> void:
	# dodge falling crates
	for h in room.hazards:
		var hp: Vector2 = h.pos
		if absf(hp.x - p.position.x) < 30 and absf(hp.y - p.position.y) < 20:
			_act("guard", false)
			_move(Vector2(0, 1.0 if p.position.y < hp.y + 1 or p.position.y < room.walk_top + 30 else -1.0) if p.position.y > room.walk_top + 30 else Vector2(0, 1))
			return
	# defend against wind-ups aimed at us
	for a in room.actors:
		if a is Enemy and a.team == Actor.TEAM_ENEMY and not a.dead and a.state == "attack" and a.attack_phase() == 0:
			var dx: float = p.position.x - a.position.x
			var close := absf(dx) < 80 and absf(p.position.y - a.position.y) < 26
			if not close:
				continue
			if a.atk.get("unblockable", false):
				if a.atk.get("low", false) and int(a.atk.get("startup", 10)) - a.atk_t <= 8 and p.can_act():
					_tap("jump")
					return
				_move(Vector2(-signf(dx) * -1.0, 1.0 if p.position.y < 290 else -1.0))
				return
			if signf(dx) == float(a.facing) and randf() < 0.85:
				if signf(a.position.x - p.position.x) != float(p.facing) and absf(dx) > 2:
					_move(Vector2(signf(a.position.x - p.position.x), 0))
				_act("guard", true)
				return
	_act("guard", false)
	if p.state == "guard":
		return
	var dx2 := e.position.x - p.position.x
	var dy2 := e.position.y - p.position.y
	var side := -signf(dx2) if dx2 != 0 else -1.0
	var want_x := e.position.x + side * 22.0
	var mv := Vector2.ZERO
	if absf(dy2) > 3.0:
		mv.y = signf(dy2)
	if absf(p.position.x - want_x) > 6.0 and (absf(dx2) > 30 or absf(dx2) < 12):
		mv.x = signf(want_x - p.position.x)
	if mv != Vector2.ZERO:
		_move(mv)
	else:
		_move(Vector2.ZERO)
	# grab dizzy / downed enemies and throw them
	if (e.state == "dizzy" or e.lying) and e.liftable and absf(dx2) < 24 and absf(dy2) < 10 and p.carried_actor == null and p.can_act() and not e.is_boss:
		_tap("interact")
		return
	if p.carried_actor:
		_move(Vector2.ZERO)
		if frames % 20 == 0:
			_tap("punch")
		return
	punch_cd -= 1
	if absf(dy2) <= 5 and absf(dx2) <= 34 and absf(dx2) >= 6 and punch_cd <= 0:
		if signf(dx2) != float(p.facing):
			_move(Vector2(signf(dx2), 0))
			return
		combo_n += 1
		if combo_n % 4 == 0:
			_tap("kick")
			punch_cd = 22
		else:
			_tap("punch")
			punch_cd = 9
		if combo_n % 4 == 3:
			punch_cd = 10

func _navigate(room: Node, p: Player) -> void:
	var stage := GameState.stage
	var target_room := ""
	var target_x := 0.0
	if stage == "return_home":
		if not GameState.has_flag("setback_fought"):
			target_room = "oq_brickrow"
			target_x = 700.0
		else:
			target_room = "int_garage"
	elif TARGETS.has(stage):
		target_room = TARGETS[stage][0]
		target_x = TARGETS[stage][1]
	else:
		_move(Vector2.ZERO)
		return
	if room.room_id == target_room:
		var mid: float = (room.walk_top + room.walk_bot) * 0.5
		var tx := clampf(target_x, 20.0, room.width - 20.0)
		if target_x <= 0.0:
			_move(Vector2.ZERO)
			return
		var mv := Vector2(signf(tx - p.position.x) if absf(tx - p.position.x) > 8 else 0.0, signf(mid - p.position.y) if absf(mid - p.position.y) > 20 else 0.0)
		_move(mv)
		_set_axis("run", absf(tx - p.position.x) > 120)
		return
	var step := _next_step(room.room_id, target_room)
	if step.is_empty():
		notes.append("no path from %s to %s" % [room.room_id, target_room])
		_move(Vector2.ZERO)
		return
	match step.kind:
		"exit":
			match step.side:
				"west":
					_move(Vector2(-1, 0)); _set_axis("run", true)
				"east":
					_move(Vector2(1, 0)); _set_axis("run", true)
				"south":
					var cx: float = (float(step.x0) + float(step.x1)) * 0.5
					if absf(p.position.x - cx) > 10:
						_move(Vector2(signf(cx - p.position.x), 1))
					else:
						_move(Vector2(0, 1))
		"door":
			var dxp: float = float(step.x) - p.position.x
			if absf(dxp) > 8:
				_move(Vector2(signf(dxp), -1 if p.position.y > room.walk_top + 14 else 0))
				_set_axis("run", absf(dxp) > 120)
			else:
				_set_axis("run", false)
				_move(Vector2(0, -1))
				if frames % 20 == 0:
					_tap("interact")

## BFS over the room graph (exits + doors whose requirements are met).
func _next_step(from: String, to: String) -> Dictionary:
	var prev := {from: null}
	var first := {}
	var q := [from]
	while not q.is_empty():
		var cur: String = q.pop_front()
		if cur == to:
			break
		var r: Dictionary = Content.room(cur)
		var edges: Array = []
		for side in r.get("exits", {}):
			var e: Dictionary = r.exits[side]
			if e.has("requires") and not GameState.check(e.requires):
				continue
			edges.append([e.to, {"kind": "exit", "side": side, "x0": e.get("x0", 0), "x1": e.get("x1", 0)}])
		for d in r.get("doors", []):
			if d.has("requires") and not GameState.check(d.requires):
				continue
			edges.append([d.to, {"kind": "door", "x": d.x}])
		for ed in edges:
			var nxt: String = ed[0]
			if prev.has(nxt):
				continue
			prev[nxt] = cur
			first[nxt] = ed[1] if cur == from else first[cur]
			q.append(nxt)
	return first.get(to, {})

func _finish(result: String) -> void:
	done = true
	_release_all()
	var total := frames / 60.0
	var rep := {
		"result": result, "game_seconds": snappedf(total, 0.1), "minutes": snappedf(total / 60.0, 0.01),
		"deaths": deaths, "final_level": GameState.level, "cash": GameState.cash, "stage": GameState.stage,
		"breakdown_seconds": {}, "stages": stage_log, "room_seconds": {}, "notes": notes, "stuck_events": stuck_events,
		"enemies_defeated": int(GameState.stats.get("defeated", 0)), "difficulty": Settings.difficulty,
		"engine": Engine.get_version_info().string
	}
	for k in counters:
		rep.breakdown_seconds[k] = snappedf(counters[k] / 60.0, 0.1)
	for k in room_time:
		rep.room_seconds[k] = snappedf(room_time[k] / 60.0, 0.1)
	var path := OS.get_environment("AUTOPLAY_REPORT")
	if path == "":
		path = "user://autoplay_report.json"
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify(rep, "  "))
	f.close()
	print("[bot] FINISHED result=%s minutes=%.1f deaths=%d level=%d" % [result, total / 60.0, deaths, GameState.level])
	print(JSON.stringify(rep))
	get_tree().quit(0 if result == "complete" else 1)
