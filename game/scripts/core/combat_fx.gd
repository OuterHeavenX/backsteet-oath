class_name CombatFX
extends RefCounted
## Combat presentation driven by real combat events. It never changes damage, hitstun or hit timing.
## - impact(): a material-specific burst, directional debris, KO burst and a directional camera impulse
## - arc(): a smear arc when an attack reaches its contact frame
## - dust(): footstep, landing, slide and fall dust

const MATERIAL := {
	"wrench": "metal", "baton": "metal", "pipe": "metal", "chain": "metal", "belt": "metal", "road_sign": "metal",
	"trash_can": "metal", "bat": "wood", "broom": "wood", "crate": "wood", "bottle": "glass", "brick": "stone",
	"newspaper": "soft", "fish": "soft", "tire": "soft", "spatula": "metal"
}
const DEBRIS := {"metal": "spark_streak", "wood": "chip_wood", "glass": "shard_glass", "stone": "chunk_stone",
	"soft": "scrap_paper"}
const KICK_ANIMS := ["kick", "kick_c", "jump_kick", "dropkick", "rising_kick", "sweep"]
const ARC_FOR := {
	"punch_a": "arc_punch", "punch_b": "arc_punch", "punch_c": "arc_heavy", "jump_punch": "arc_punch",
	"run_punch": "arc_punch", "kick": "arc_kick", "kick_c": "arc_heavy", "jump_kick": "arc_kick",
	"dropkick": "arc_kick", "rising_kick": "arc_rising", "sweep": "arc_sweep", "swing": "arc_swing"
}

static func material_of(attacker: Node, d: Dictionary) -> String:
	var w := str(d.get("weapon", ""))
	if w == "" and attacker and attacker is Actor and (attacker as Actor).held != "":
		w = (attacker as Actor).held
	if w != "":
		return MATERIAL.get(w, "metal")
	if attacker and attacker is Actor and str((attacker as Actor).atk.get("anim", "")) in KICK_ANIMS:
		return "kick"
	return "fist"

static func is_heavy(d: Dictionary, dmg: int) -> bool:
	return d.get("knockdown", false) or int(d.get("hitstop", 3)) >= 6 or dmg >= 14

## Called once per landed hit, from Actor.take_damage_and_react.
static func impact(room: Node, attacker: Node, target: Actor, d: Dictionary, dir: int, dmg: int) -> void:
	var mat := material_of(attacker, d)
	var heavy := is_heavy(d, dmg)
	var p: Vector2 = target.hit_point() + Vector2(-dir * 4, 0)
	var name := "hit_light"
	match mat:
		"fist": name = "hit_heavy" if heavy else "hit_light"
		"kick": name = "hit_heavy" if heavy else "hit_kick"
		_: name = "hit_" + mat
	if not FX.has_v2(name):
		name = str(d.get("fx", "hit_spark"))
	room.spawn_fx(name, p, 0.0, null, -1, dir)
	var full := Settings.effects_full()
	if DEBRIS.has(mat):
		var n := (7 if heavy else 4) if full else 2
		room.spawn_directional_debris(DEBRIS[mat], p, dir, n, mat == "metal")
	if heavy and full:
		room.spawn_fx("dust_slide" if FX.has_v2("dust_slide") else "dust", target.position + Vector2(-dir * 6, 1), 0.0, null, -1, dir)
	if target.hp <= 0:
		room.spawn_fx("ko_burst" if FX.has_v2("ko_burst") else "hit_heavy", p, 0.0)
	# a quiet material layer under the attack's own sound (levels kept low: not verified by ear)
	var base_sfx := str(d.get("sfx", ""))
	if mat == "metal" and not base_sfx.contains("metal"):
		Audio.sfx("metal_clang", -14.0, 0.12)
	elif mat == "wood" and heavy:
		Audio.sfx("crate_fall", -14.0, 0.12)
	elif heavy and mat in ["fist", "kick"]:
		Audio.sfx("slam", -15.0, 0.1)
	var k := 1.6 if heavy else 0.7
	if mat in ["metal", "stone"]:
		k += 0.4
	room.impulse(Vector2(dir, -0.25 if heavy else 0.0), k)

## Smear arc at the attacker's contact frame (shown on whiffs too, like a real swing).
static func arc(room: Node, a: Actor) -> void:
	var anim := str(a.atk.get("anim", ""))
	var arc_name: String = ARC_FOR.get(anim, "")
	if arc_name == "" or a.atk.get("projectile", false):
		return
	if a.held != "" and anim == "swing" and Content.weapon(a.held).get("family", "") in ["long", "heavy"]:
		arc_name = "arc_heavy"
	if not FX.has_v2(arc_name):
		return
	var col := Color(1.0, 0.97, 0.9, 0.8)
	if a.team == Actor.TEAM_ENEMY:
		col = Color(1.0, 0.82, 0.78, 0.65)
	if a.held != "":
		var m: String = MATERIAL.get(a.held, "metal")
		col = {"metal": Color(0.85, 0.92, 1.0, 0.85), "wood": Color(1.0, 0.9, 0.75, 0.8), "glass": Color(0.8, 1.0, 0.95, 0.8)}.get(m, col)
	var f := FX.make_strip(arc_name)
	f.modulate = col
	a.visual.add_child(f)
	# arc anchors are the attacker's feet for a 48 u adult; scale for heavies and kids
	var k := clampf(a.height / 48.0, 0.8, 1.3)
	f.scale = Vector2(k, k)
	f.position = Vector2.ZERO
	f.z_index = 1
