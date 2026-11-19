class_name MoveDemo
extends Control
## A small looping Nico performing a technique, for the manual preview. Presentation only: it reads the sprite
## sheet (SpriteLib) and the attack's timing (attacks.json) and never touches game state or plays a sound.
##
## The loop is: what the input asks for first (a run-up, a raised guard, a jump, a carried foe, a held kick),
## then the technique's own animation with its real start-up / active / recovery lengths, then a short rest.

const SCALE := 1.15

var skill_id := ""
var _sheet: Dictionary = {}
var _beats: Array = []      # [anim, ticks, mode]  mode: loop / hold / rise / attack / glow
var _atk: Dictionary = {}
var _beat := 0
var _t := 0
var _acc := 0.0

func _ready() -> void:
	clip_contents = true
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_sheet = SpriteLib.character("nico")
	_build()

func _build() -> void:
	_beats.clear()
	var sk: Dictionary = Content.skill(skill_id)
	var aid := Preview.technique_attack(skill_id)
	_atk = Content.attack(aid)
	var toks: Array = sk.get("input", [])
	match str(toks[0]) if not toks.is_empty() else "":
		"run": _beats.append(["run", 26, "loop"])
		"guard": _beats.append(["guard", 16, "hold"])
		"jump": _beats.append(["jump", 16, "rise"])
		"interact": _beats.append(["carry" if aid != "" else "pickup", 22, "loop"])
		"kick": _beats.append(["idle", 46, "glow"])
		"punch":
			_beats.append(["punch_a", 12, "hold"])
			_beats.append(["punch_b", 12, "hold"])
	if not _atk.is_empty():
		var n := int(_atk.get("startup", 4)) + int(_atk.get("active", 3)) + int(_atk.get("recovery", 8))
		_beats.append([str(_atk.get("anim", "punch_a")), maxi(n, 12), "attack"])
	_beats.append(["idle", 28, "loop"])

func _process(delta: float) -> void:
	_acc += delta * 60.0
	while _acc >= 1.0:
		_acc -= 1.0
		_t += 1
		if _t >= int(_beats[_beat][1]):
			_t = 0
			_beat = (_beat + 1) % _beats.size()
	queue_redraw()

## Frame of the anim for the current beat: attacks follow their start-up / active / recovery phases.
func _frame(ad: Dictionary, ticks: int, mode: String) -> int:
	var n: int = ad.frames.size()
	if n <= 1:
		return 0
	match mode:
		"loop", "glow":
			return int(float(_t) * float(ad.get("fps", 8.0)) / 60.0) % n
		"attack":
			var c := clampi(int(ad.get("contact", 1)), 0, n - 1)
			var s := int(_atk.get("startup", 4))
			var a := int(_atk.get("active", 3))
			if _t < s:
				return clampi(int(float(_t) / float(maxi(s, 1)) * float(c)), 0, maxi(c - 1, 0))
			if _t < s + a:
				return c + (int(_t / 3) % 2 if int(_atk.get("hits", 1)) > 1 and n - c > 1 else 0)
			return clampi(c + 1 + int(float(_t - s - a) / float(maxi(ticks - s - a, 1)) * float(n - 1 - c)), 0, n - 1)
	return clampi(int(float(_t) / float(maxi(ticks, 1)) * float(n)), 0, n - 1)

## Height above the floor: jumps rise, air techniques come down with the attack.
func _lift(ticks: int, mode: String) -> float:
	var u := float(_t) / float(maxi(ticks, 1))
	if mode == "rise":
		return 34.0 * sin(u * PI * 0.5)
	if mode == "attack" and _beat > 0 and str(_beats[_beat - 1][2]) == "rise":
		var fall := 0.25 if not _atk.get("air", false) else 0.6
		return 34.0 * clampf(1.0 - u / fall, 0.0, 1.0)
	return 0.0

func _draw() -> void:
	var floor_y := size.y - 12.0
	draw_rect(Rect2(Vector2.ZERO, size), Color(0.06, 0.045, 0.09, 0.85))
	draw_line(Vector2(6, floor_y), Vector2(size.x - 6, floor_y), Color(UIKit.EDGE, 0.5), 1.0)
	var rects: Array = _sheet.get("rects", [])
	if rects.is_empty() or _beats.is_empty():
		return
	var b: Array = _beats[_beat]
	var ad := SpriteLib.anim_def(_sheet, str(b[0]))
	var f := int(ad.frames[_frame(ad, int(b[1]), str(b[2]))])
	if f >= rects.size():
		return
	var k := float(_sheet.get("scale", 1.0)) * SCALE
	var lift := _lift(int(b[1]), str(b[2]))
	var feet := Vector2(size.x * 0.42, floor_y - lift)
	draw_set_transform(Vector2(size.x * 0.42, floor_y), 0.0, Vector2(1.0 - lift / 90.0, 0.35 * (1.0 - lift / 90.0)))
	draw_circle(Vector2.ZERO, 13.0, Color(0, 0, 0, 0.35))
	draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	var r: Rect2 = rects[f]
	var o: Vector2 = _sheet.offs[f]
	var tint := Color.WHITE
	if str(b[2]) == "glow":
		tint = Color.WHITE.lerp(Color(0.5, 1.0, 1.0), 0.5 + 0.5 * sin(float(_t) * 0.4))
	elif str(b[2]) == "attack" and _t < 6:
		tint = Color(0.6, 1.0, 1.0)     # the cyan flash a technique starts with in a fight
	draw_texture_rect_region(_sheet.texture, Rect2(feet + o * k, r.size * k), r, tint)
