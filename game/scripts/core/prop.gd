class_name Prop
extends Node2D
## Y-sorted scenery. Solid props block movement via their ground footprint.
## Crates/barrels break (dropping contents); crates and trash cans can be lifted and thrown.

const BREAKABLE := {"crate": 18, "barrel": 22, "fish_crate": 14, "newsbox": 0}
const LIFTABLE := {"crate": "crate", "trash_can": "trash_can"}
const NAMES := {"crate": "Crate", "trash_can": "Trash Can", "bus_stop": "Bus Stop"}

var room: Node
var type := ""
var footprint := Vector2.ZERO
var breakable := false
var broken := false
var liftable := false
var lift_weapon := ""
var hp := 1.0
var contents: Dictionary = {}
var persist_key := ""
var spr: Sprite2D
var half_w := 10.0
var depth_r := 4.0
var z := 0.0
var shake_t := 0
var index := -1

func setup(r: Node, t: String, pos: Vector2, idx: int, cont: Dictionary) -> void:
	room = r
	type = t
	index = idx
	position = pos
	contents = cont
	var meta: Dictionary = Content.props_meta.get(t, {})
	var tex := SpriteLib.prop(t)
	spr = Sprite2D.new()
	spr.texture = tex
	spr.centered = false
	var anchor: Array = meta.get("anchor", [tex.get_width() / 2.0, tex.get_height()])
	spr.offset = -Vector2(float(anchor[0]), float(anchor[1]))
	add_child(spr)
	var fp: Array = meta.get("footprint", [tex.get_width() - 4, 8])
	footprint = Vector2(float(fp[0]), float(fp[1]))
	if t.begins_with("counter") or t == "workbench":
		footprint.y = maxf(footprint.y, position.y - float(room.walk_top) + 2.0)
	half_w = maxf(footprint.x / 2.0, 6.0)
	depth_r = maxf(footprint.y / 2.0, 3.0)
	if BREAKABLE.has(t) and int(BREAKABLE[t]) > 0:
		breakable = true
		hp = float(BREAKABLE[t])
	if LIFTABLE.has(t):
		liftable = true
		lift_weapon = LIFTABLE[t]
	persist_key = "%s:prop%d" % [room.room_id, idx]
	if contents.has("key") and GameState.is_collected(persist_key):
		contents = {}

func is_solid() -> bool:
	return not broken and footprint.y > 0.0

func ground_rect() -> Rect2:
	return Rect2(position.x - footprint.x / 2.0, position.y - footprint.y, footprint.x, footprint.y)

func cur_height() -> float:
	return float(spr.texture.get_height()) if spr and spr.texture else 24.0

func is_hittable() -> bool:
	return breakable and not broken

func receive_hit(_attacker: Node, _d: Dictionary, raw: float, _dir: int) -> String:
	if not breakable or broken:
		return "miss"
	hp -= raw
	shake_t = 8
	Audio.sfx("crate_break" if hp <= 0 else "weapon_hit_blunt", -4.0)
	if hp <= 0:
		break_open()
	return "hit"

func break_open() -> void:
	if broken:
		return
	broken = true
	room.spawn_debris("debris_wood" if type != "fish_crate" else "splash", position + Vector2(0, -12))
	Audio.sfx("crate_break")
	_drop_contents()
	room.remove_prop(self)

func lifted() -> void:
	broken = true
	_drop_contents()
	room.remove_prop(self)

func _drop_contents() -> void:
	if contents.has("cash"):
		room.spawn_cash(int(contents.cash), position + Vector2(0, 2))
	if contents.has("heal"):
		room.spawn_heal(int(contents.heal), position + Vector2(0, 2))
	if contents.has("key"):
		room.spawn_key(str(contents.key), position + Vector2(0, 3), persist_key)
	if contents.has("weapon"):
		room.spawn_weapon_pickup(str(contents.weapon), position + Vector2(0, 3), -1, 10.0)
	if contents.has("event"):
		Story.on_prop_event(str(contents.event), room)
	contents = {}

func _physics_process(_d: float) -> void:
	if shake_t > 0:
		shake_t -= 1
		spr.position.x = (1.0 if shake_t % 2 == 0 else -1.0)
	elif spr:
		spr.position.x = 0.0

func label() -> String:
	return NAMES.get(type, type.capitalize())
