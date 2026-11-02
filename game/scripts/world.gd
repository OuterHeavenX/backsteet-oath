extends Node
## Gameplay root: hosts the current Room, HUD, dialogue, menus, touch controls.
## Handles transitions, pausing (menus, focus loss, controller disconnect), defeat and autosave.

var room: Room
var room_holder: Node2D
var ui_layer: CanvasLayer
var menu_layer: CanvasLayer
var hud: HUD
var dialogue: DialogueBox
var touch: Node
var rotate_overlay: Control
var menus: Array = []
var transitioning := false
var sim_hold := false
var defeated := false
var retry_info: Dictionary = {}

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().root.theme = UIKit.build_theme()
	room_holder = Node2D.new()
	room_holder.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(room_holder)
	ui_layer = CanvasLayer.new()
	ui_layer.layer = 10
	add_child(ui_layer)
	hud = HUD.new()
	hud.world = self
	ui_layer.add_child(hud)
	dialogue = DialogueBox.new()
	ui_layer.add_child(dialogue)
	touch = TouchControls.new()
	touch.world = self
	ui_layer.add_child(touch)
	touch.layout_changed.connect(_layout_ui)
	get_viewport().size_changed.connect(_layout_ui)
	menu_layer = CanvasLayer.new()
	menu_layer.layer = 20
	add_child(menu_layer)
	rotate_overlay = RotateOverlay.new()
	menu_layer.add_child(rotate_overlay)
	if OS.is_debug_build():
		var dbg := DebugOverlay.new()
		dbg.world = self
		add_child(dbg)
	GameState.leveled_up.connect(_on_leveled)
	InputPrompts.pad_disconnected.connect(_on_pad_disconnected)
	Story.world = self
	Quests.world = self
	_layout_ui()
	_load_room(GameState.room, GameState.spawn, true)
	if OS.has_feature("web"):
		var q = JavaScriptBridge.eval("window.location.search", true)
		debug_fps = q != null and "bo_debug" in str(q)
	else:
		debug_fps = "--bo-debug" in OS.get_cmdline_user_args()

var debug_fps := false
var _fps_t := 0.0
var _frame_max_ms := 0.0
func _process(delta: float) -> void:
	if not debug_fps:
		return
	_fps_t += delta
	_frame_max_ms = maxf(_frame_max_ms, delta * 1000.0)
	if _fps_t >= 5.0:
		var fps := Engine.get_frames_per_second()
		var en := room.enemies_alive() if room else 0
		var pp: Vector2 = room.player.position if room and room.player else Vector2.ZERO
		print("BO_PERF fps=%d worst_frame_ms=%.1f room=%s enemies=%d actors=%d player=%d,%d state=%s touch=%s" % [fps, _frame_max_ms, room.room_id if room else "-", en, room.actors.size() if room else 0, int(pp.x), int(pp.y), room.player.state if room and room.player else "-", str(touch.visible)])
		_fps_t = 0.0
		_frame_max_ms = 0.0

## The playfield is always 360 px tall. Taller screens (tablets, 16:10) get extra space: with touch
## controls it becomes a control deck under the street; otherwise the street is centered.
func playfield_top() -> float:
	var h := get_viewport().get_visible_rect().size.y
	var extra := h - 360.0
	if extra <= 0.5:
		return 0.0
	if touch and touch.active and extra >= 72.0:
		return 0.0
	return floorf(extra * 0.5)

func camera_center_y() -> float:
	return get_viewport().get_visible_rect().size.y * 0.5 - playfield_top()

func _layout_ui() -> void:
	var vs := get_viewport().get_visible_rect().size
	var top := playfield_top()
	for c in [hud, dialogue]:
		if c:
			c.set_anchors_preset(Control.PRESET_TOP_LEFT)
			c.position = Vector2(0, top)
			c.size = Vector2(vs.x, 360.0)

func _on_leveled(level: int, gains: Dictionary) -> void:
	hud.show_level_up(level, gains)
	Audio.sfx("level_up")
	if room and room.player:
		room.player.refresh_stats()
		room.spawn_fx("levelup_burst", Vector2(0, -24), 0.0, room.player)

func on_level_up() -> void:
	pass

# ---------------------------------------------------------------- rooms
func _load_room(id: String, spawn: String, first: bool = false) -> void:
	if room:
		room.queue_free()
		room = null
	if not Content.rooms.has(id):
		id = "oq_kettle"
		spawn = "west"
	GameState.room = id
	GameState.spawn = spawn
	GameState.enter_room(id)
	var r := Room.new()
	r.process_mode = Node.PROCESS_MODE_PAUSABLE
	room_holder.add_child(r)
	r.build(id, spawn, self)
	room = r
	var rd: Dictionary = Content.room(id)
	if rd.get("hub", false):
		GameState.hub_room = id
	if rd.get("bus_stop", false):
		GameState.bus_stops[id] = true
	Audio.play_music(rd.get("music", "old_quarter"))
	Audio.play_ambient(_ambient_for(rd))
	hud.set_bosses([])
	hud.refresh_objective()
	room.player.lock_input(12)
	await Story.on_room_enter(room, first)
	if is_instance_valid(room) and room.room_id == id and not room.cutscene and not room.combat_active():
		autosave()

func _ambient_for(rd: Dictionary) -> String:
	if rd.get("kind", "") == "interior":
		return ""
	if rd.get("weather", "") == "rain":
		return "rain_loop"
	match rd.get("district", ""):
		"ironworks", "warehouse": return "industrial_loop"
		"neon_mile": return "neon_buzz_loop"
	return "street_loop"

func change_room(id: String, spawn: String) -> void:
	if transitioning:
		return
	transitioning = true
	if room and room.player:
		room.player.control_enabled = false
		GameState.hp = room.player.hp
	await SceneFlow.fade_out(0.22)
	Story.on_room_exit(room)
	_load_room(id, spawn)
	await get_tree().process_frame
	transitioning = false
	await SceneFlow.fade_in(0.22)

func autosave() -> void:
	if room and room.player:
		GameState.hp = maxi(room.player.hp, 1)
	if SaveService.save_game():
		pass

func is_sim_paused() -> bool:
	return sim_hold

func dialogue_active() -> bool:
	return dialogue.active

# ---------------------------------------------------------------- dialogue helpers
func say(id: String) -> void:
	var lines := Content.lines(id)
	if lines.is_empty():
		push_warning("missing dialogue " + id)
		return
	await say_lines(lines)

func say_lines(lines: Array) -> void:
	var was_cut := room.cutscene if room else false
	if room and not was_cut:
		room.set_cutscene(true)
	await dialogue.play(lines)
	if room and not was_cut:
		room.set_cutscene(false)

func ask(line: Array, options: Array) -> int:
	var was_cut := room.cutscene if room else false
	if room and not was_cut:
		room.set_cutscene(true)
	var r := await dialogue.ask(line, options)
	if room and not was_cut:
		room.set_cutscene(false)
	return r

func toast(msg: String, col: Color = UIKit.CREAM) -> void:
	hud.toast(Story.format_text(msg), col)

func hint(msg: String, dur: float = 6.0) -> void:
	hud.show_hint(Story.format_text(msg), dur)

func bark(actor: Actor, line_id: String) -> void:
	var lines := Content.lines(line_id)
	if lines.is_empty():
		return
	var l: Array = lines[0]
	hud.toast("%s: %s" % [Content.character_name(l[0]), Story.format_text(l[2])], Color(1, 0.8, 0.6), 2.4)

func boss_bar(bosses) -> void:
	hud.set_bosses(bosses if bosses else [])

# ---------------------------------------------------------------- menus
func push_menu(m: Control) -> void:
	if not menus.is_empty():
		menus[-1].remember_focus()
		menus[-1].visible = false
	m.host = self
	menus.append(m)
	menu_layer.add_child(m)
	get_tree().paused = true
	touch.visible_for_menus(true)
	Audio.sfx("ui_open", -6.0, 0.0)

func pop_menu(m: Control) -> void:
	menus.erase(m)
	m.queue_free()
	if menus.is_empty():
		get_tree().paused = false
		touch.visible_for_menus(false)
		if room and room.player:
			room.player.lock_input(10)
	else:
		menus[-1].visible = true
		menus[-1].restore_focus()
	Audio.sfx("ui_close", -8.0, 0.0)

func top_menu() -> Control:
	return menus[-1] if not menus.is_empty() else null

func close_all_menus() -> void:
	for m in menus.duplicate():
		m.queue_free()
	menus.clear()
	get_tree().paused = false
	touch.visible_for_menus(false)

func can_open_menu() -> bool:
	return menus.is_empty() and not transitioning and not dialogue.active and not defeated and room != null and not room.cutscene

func _unhandled_input(event: InputEvent) -> void:
	if not can_open_menu():
		return
	if event.is_action_pressed("pause"):
		get_viewport().set_input_as_handled()
		open_pause()
	elif event.is_action_pressed("status"):
		get_viewport().set_input_as_handled()
		push_menu(StatusMenu.new())

func open_pause() -> void:
	if can_open_menu():
		push_menu(PauseMenu.new())

func open_shop(shop_id: String) -> void:
	var m := ShopMenu.new()
	m.shop_id = shop_id
	push_menu(m)
	await m.closed

func open_bus() -> void:
	if not GameState.check(Content.services.bus.get("requires", "")):
		toast("No buses are running. The Chain Dogs keep jumping the drivers.")
		return
	var m := MapMenu.new()
	m.bus_mode = true
	push_menu(m)

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		if can_open_menu() and not OS.has_feature("editor_hint"):
			open_pause()

func _on_pad_disconnected() -> void:
	if can_open_menu():
		open_pause()
		toast("Controller disconnected. Game paused.")

# ---------------------------------------------------------------- defeat
func on_player_defeated() -> void:
	if defeated:
		return
	defeated = true
	GameState.stats.deaths = int(GameState.stats.get("deaths", 0)) + 1
	Audio.play_music("defeat", 0.3)
	var loss := GameState.defeat_penalty()
	await get_tree().create_timer(1.2).timeout
	var m := DefeatMenu.new()
	m.loss = loss
	m.boss_retry = room != null and room.boss_active
	m.retry_room = room.room_id if room else ""
	m.retry_enabled = Story.can_retry_here(room)
	push_menu(m)

func respawn_at_hub(loss: int) -> void:
	GameState.spend(loss)
	GameState.hp = GameState.max_hp()
	defeated = false
	close_all_menus()
	Story.on_defeat_reset()
	await SceneFlow.fade_out(0.3)
	_load_room(GameState.hub_room, "south")
	await get_tree().process_frame
	await SceneFlow.fade_in(0.4)
	toast("You came to at %s. Lost $%d." % [Content.room(GameState.hub_room).get("name", "the diner"), loss])

func retry_here(loss: int) -> void:
	GameState.spend(loss)
	GameState.hp = GameState.max_hp()
	defeated = false
	close_all_menus()
	var rid := room.room_id
	var spawn := Story.retry_spawn(room)
	Story.on_defeat_reset()
	await SceneFlow.fade_out(0.3)
	_load_room(rid, spawn)
	await get_tree().process_frame
	await SceneFlow.fade_in(0.4)

func quit_to_title() -> void:
	close_all_menus()
	get_tree().paused = false
	SceneFlow.goto("res://scenes/title.tscn")
