class_name DebugOverlay
extends CanvasLayer
## Developer tools. Only instantiated when OS.is_debug_build() is true (editor / debug exports).
## Release exports never create this node, so none of these shortcuts exist for players.
## F1 overlay  F2 +500 XP  F3 travel to next room  F4 spawn enemies  F5 full heal  F6 delete slot 3

var world: Node
var label: Label
var shown := false
var room_ids: Array = []

func _ready() -> void:
	layer = 90
	process_mode = Node.PROCESS_MODE_ALWAYS
	label = Label.new()
	label.position = Vector2(4, 120)
	label.add_theme_color_override("font_color", Color(0.6, 1, 0.6))
	label.add_theme_color_override("font_outline_color", Color.BLACK)
	label.add_theme_constant_override("outline_size", 3)
	label.visible = false
	add_child(label)
	room_ids = Content.rooms.keys()

func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	match event.keycode:
		KEY_F1:
			shown = not shown
			label.visible = shown
		KEY_F2:
			GameState.add_xp(500)
		KEY_F3:
			var i := room_ids.find(GameState.room)
			world.change_room(room_ids[(i + 1) % room_ids.size()], "west")
		KEY_F4:
			if world.room:
				for id in ["dogs_brawler", "dogs_flanker", "dogs_thrower"]:
					world.room.spawn_enemy(id, world.room.player.position + Vector2(120, randf_range(-20, 20)), {})
		KEY_F5:
			GameState.hp = GameState.max_hp()
			if world.room and world.room.player:
				world.room.player.hp = GameState.hp
			GameState.stats_changed.emit()
		KEY_F6:
			SaveService.delete_slot(3)

func _process(_d: float) -> void:
	if not shown or world == null or world.room == null:
		return
	var r: Room = world.room
	var p: Player = r.player
	label.text = "DEBUG  fps %d  room %s  actors %d  enemies %d  tokens %d\nplayer %s z=%.0f state %s atk %s\nstage %s  lvl %d  xp %d/%d" % [
		Engine.get_frames_per_second(), r.room_id, r.actors.size(), r.enemies_alive(), r.tokens.size(),
		str(p.position.round()), p.z, p.state, p.atk_id, GameState.stage, GameState.level, GameState.xp, GameState.xp_needed(GameState.level)]
