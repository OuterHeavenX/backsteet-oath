class_name PerfDebug
extends RefCounted
## Profiling switches for the performance harness (tests/perf.gd) and the screenshot tool (tests/shots.gd).
## Nothing in the shipped game fills `disabled`, so every system stays on for players; the checks are made
## when a room is built (or once per hit for combat FX), never per frame.
##
## System names (comma separated in PERF_DISABLE / SHOT_DISABLE):
##   grade        the whole colour grade + bloom screen pass (same as Settings.post_fx = false)
##   bloom        keep the grade, drop the bloom (no blurred screen read)
##   haze         atmospheric haze material on the far/mid layers and lanes
##   parallax     the sky/far/mid parallax layers (overdraw behind the base layer)
##   fg           foreground framing sprites
##   glows        additive light glows (static and following)
##   lightmap     the authored lightmap (actors and props fall back to flat light)
##   rim cast reflect   actor rim light, directional cast shadows, wet-ground reflections
##   ambient      ambient particle emitters (steam, drips, sparks, dust motes ...)
##   clouds windows lanes pigeons sway water signs shafts passers   background life, per type
##   life         all background life types above at once
##   combat_fx    impact bursts, debris, smear arcs and the camera impulse
##   rain actor_shader hud   applied by the harness itself (see tests/perf.gd)

const LIFE := ["clouds", "windows", "lanes", "pigeons", "sway", "water", "signs", "shafts", "passers"]

static var disabled: Dictionary = {}

static func off(sys: String) -> bool:
	return not disabled.is_empty() and disabled.has(sys)

static func set_from(csv: String) -> void:
	disabled.clear()
	for s in csv.split(",", false):
		var k := s.strip_edges()
		if k == "life":
			for l in LIFE:
				disabled[l] = true
		elif k != "" and k != "none":
			disabled[k] = true
