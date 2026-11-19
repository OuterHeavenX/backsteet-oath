class_name Tutor
extends Node
## Teach-through-play tips. One tip is on screen at a time and it stays until the player actually performs
## the action (a real gameplay event) or skips it from the pause menu. Tips never gate progression.
##
## State lives in GameState.flags as "tip_<id>": 1 armed, 2 done, 3 skipped, so tips survive saving, loading,
## retries and room changes, and never repeat once learned. Saves made before this system simply have no
## armed tips. Text is re-formatted for the current input device every frame it is shown.

const ARMED := 1
const DONE := 2
const SKIPPED := 3
## A tip that has been up this long without success yields to another armed tip that has an opportunity,
## so one unmet tip can never hide the rest.
const ROTATE_SECONDS := 14.0
const CELEBRATE_SECONDS := 1.1
## Technique reminders retire by themselves after this much screen time ("infrequent, dismissible").
const REMINDER_SECONDS := 24.0

## Ordered: earlier tips win when several have an opportunity.
## done: the gameplay event that completes it. when: opportunity test (see _opportunity). timed: informational
## tips with no single action complete after this many seconds on screen.
const ORDER := ["move", "combo", "guard", "throw", "door", "eat", "run", "shoulder", "blocker", "lights", "unblockable", "food", "save"]
const TIPS := {
	"move": {"text": "Move with {move}. Line up level with a Chain Dog to reach him.", "done": "lane", "when": "enemy"},
	"combo": {"text": "Press {punch} three times for a combo. The third hit knocks them down.", "done": "combo3", "when": "enemy"},
	"guard": {"text": "Hold {guard} to block hits from the front.", "done": "block", "when": "enemy"},
	"throw": {"text": "Pick up the bottle with {interact}, then throw it with {interact} or {punch}.", "done": "throw", "when": "throwable"},
	"door": {"text": "Walk up into a doorway to go inside. Dot has a plate waiting in the Lucky Spoon.", "done": "door", "when": "door"},
	"eat": {"text": "Talk to Dot at the counter with {interact}. The first meal is on the house.", "done": "eat", "when": "diner"},
	"run": {"text": "Double-tap a direction, or hold {run}, to run.", "done": "run", "when": "always"},
	"shoulder": {"text": "Shoulder Charge: while running, press {punch}.", "done": "skill:shoulder", "when": "enemy"},
	"blocker": {"text": "A blocker stops punches from the front. Finish a full combo, throw something heavy, or get behind them.", "done": "guard_broken", "when": "blocker"},
	"lights": {"text": "Moles only come out in full dark. Relight a work light with {interact}, or hit Kowal as she winds up on one.", "done": "relight", "when": "lights"},
	"unblockable": {"text": "A purple flash with a low double thump cannot be blocked. Step out of the lane or jump.", "done": "", "when": "always", "timed": 7.0},
	"food": {"text": "Food heals, and most dishes add a small permanent bonus. The menu shows what each one does.", "done": "", "when": "always", "timed": 7.0},
	"save": {"text": "Progress saves by itself when you enter a room. The Journal ({pause}) always shows where to go.", "done": "", "when": "quiet", "timed": 7.0},
}
## Attack id -> technique id, for technique reminders and the "used it" acknowledgement.
const SKILL_ATTACKS := {
	"shoulder": "shoulder", "rising_kick": "rising", "spin_sweep": "sweep", "heel_drop": "heel", "punch_rapid": "rapid",
	"guard_counter": "counter", "giant_spin": "giant", "slam_land": "slam", "oath_breaker": "oath"
}

var world: Node
var shown := ""             # tip currently on screen ("" = none)
var shown_t := 0.0
var celebrate_t := 0.0
var celebrate_text := ""
var gap_t := 0.0
var _rot_block: Dictionary = {}   # id -> seconds this tip must wait after yielding its turn

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_PAUSABLE

# ---------------------------------------------------------------- state
func enabled() -> bool:
	return Settings.show_hints

func state(id: String) -> int:
	return int(GameState.flags.get("tip_" + id, 0))

func _set_state(id: String, s: int) -> void:
	GameState.flags["tip_" + id] = s

## Arms a tip (no-op if it was ever armed, learned or skipped, unless force).
func arm(id: String, force: bool = false) -> void:
	if not _def(id).is_empty() and (state(id) == 0 or force):
		_set_state(id, ARMED)

## True while the tip is still waiting to be learned and tips are switched on.
func is_pending(id: String) -> bool:
	return enabled() and state(id) == ARMED

func is_learned(id: String) -> bool:
	return state(id) == DONE

func armed_ids() -> Array:
	var out: Array = []
	for id in ORDER:
		if state(id) == ARMED:
			out.append(id)
	for k in GameState.flags.keys():
		var key := str(k)
		if key.begins_with("tip_skill_") and int(GameState.flags[k]) == ARMED:
			out.append(key.substr(4))
	return out

func any_armed() -> bool:
	return not armed_ids().is_empty()

func _def(id: String) -> Dictionary:
	if TIPS.has(id):
		return TIPS[id]
	if id.begins_with("skill_"):
		var sid := id.substr(6)
		var sk: Dictionary = Content.skill(sid)
		if sk.is_empty():
			return {}
		return {"text": "%s: %s" % [sk.get("name", sid), input_text(sk)], "done": "skill:" + sid, "when": "enemy", "reminder": true}
	return {}

## "{guard} + {punch}" style input line from a technique's input tokens (formatted for the device later).
static func input_text(sk: Dictionary) -> String:
	var parts: Array = []
	var toks: Array = sk.get("input", [])
	for tok in toks:
		match str(tok):
			"+": parts.append("+")
			">": parts.append("then")
			"hold": parts.append("(hold a second, then release)")
			_: parts.append("{" + str(tok) + "}")
	var how := str(sk.get("how", ""))
	if parts.is_empty():
		return how
	var s := " ".join(parts)
	if toks.size() > 1 and toks.count(toks[0]) == toks.size():
		s += " (keep pressing)"
	# keep the situation the move needs: "While running", "While in the air", "After a PERFECT guard"...
	if how.begins_with("While") or how.begins_with("After"):
		var ctx := how.split(",")[0]
		if ctx != how:
			s = ctx + ": " + s
	return s

## A newly learned technique gets a reminder that shows at the start of fights until it is used once.
## (Automatic techniques such as Quick Hands have nothing to press, so they get no reminder.)
func arm_skill(skill_id: String) -> void:
	var id := "skill_" + skill_id
	if state(id) == 0 and not Content.skill(skill_id).is_empty() and not str(Content.skill(skill_id).get("how", "")).begins_with("Automatic"):
		_set_state(id, ARMED)
		GameState.flags["tipt_" + id] = 0.0

# ---------------------------------------------------------------- events
## Called from gameplay when something actually happened (a blocked hit, a thrown object, a door entered...).
func notify(ev: String) -> void:
	if ev == "perfect":
		ev = "block"
	for id in armed_ids():
		var d := _def(id)
		if str(d.get("done", "")) == ev and ev != "":
			_complete(id)

func _complete(id: String) -> void:
	if state(id) != ARMED:
		return
	_set_state(id, DONE)
	if shown == id and enabled():
		celebrate_text = _format(id)
		celebrate_t = CELEBRATE_SECONDS
		Audio.sfx("quest_update", -8.0, 0.0)
	if shown == id:
		shown = ""
		shown_t = 0.0

## Puts an armed tip on screen now because its moment has come (e.g. something to throw just landed).
## The tip it replaces simply waits its turn again.
func prefer(id: String) -> void:
	if state(id) != ARMED or shown == id:
		return
	if shown != "":
		_rot_block[shown] = ROTATE_SECONDS
	_rot_block.erase(id)
	shown = id
	shown_t = 0.0

func skip(id: String) -> void:
	if state(id) == ARMED:
		_set_state(id, SKIPPED)
	if shown == id:
		shown = ""
		shown_t = 0.0

func skip_current() -> void:
	if shown != "":
		skip(shown)

func skip_all() -> void:
	for id in armed_ids():
		skip(id)

# ---------------------------------------------------------------- selection
func _room() -> Node:
	return world.room if world and is_instance_valid(world.room) else null

func _opportunity(id: String) -> bool:
	var r := _room()
	if r == null or r.player == null:
		return false
	match str(_def(id).get("when", "always")):
		"enemy":
			return r.enemies_alive() > 0
		"quiet":
			return r.enemies_alive() == 0
		"throwable":
			if r.player.held != "" or r.player.carried_actor != null:
				return true
			for pk in r.pickups:
				if pk.kind == "weapon" and not pk.collected and r.on_screen(pk, 0):
					return true
			for pr in r.props:
				if pr.liftable and not pr.broken and r.on_screen(pr, 0):
					return true
			return false
		"door":
			return r.enemies_alive() == 0 and not r.data.get("doors", []).is_empty()
		"diner":
			return r.room_id == "int_diner"
		"lights":
			return r.lights_contest
		"blocker":
			for a in r.actors:
				if a is Enemy and not a.dead and a.team == Actor.TEAM_ENEMY and (a as Enemy).arche_id == "blocker" and r.on_screen(a, 0):
					return true
			return false
	return true

func _suppressed() -> bool:
	var r := _room()
	if r == null or world == null:
		return true
	return r.cutscene or world.dialogue_active() or world.transitioning or world.defeated or r.player == null or r.player.dead

func _pick() -> String:
	var best := ""
	for id in armed_ids():
		if _rot_block.has(id) or not _opportunity(id):
			continue
		best = id
		break
	if best == "":
		# everything with an opportunity is resting after its turn: let the first one back in
		for id in armed_ids():
			if _opportunity(id):
				return id
	return best

func _format(id: String) -> String:
	var t := str(_def(id).get("text", ""))
	if id == "door":
		var r := _room()
		if r == null or r.room_id != "oq_kettle" or GameState.has_flag("dot_meal_done"):
			t = "Walk up into a doorway to go inside."
	return Story.format_text(t)

func current_text() -> String:
	return _format(shown) if shown != "" else ""

func _process(delta: float) -> void:
	if world == null or world.hud == null:
		return
	for k in _rot_block.keys():
		_rot_block[k] = float(_rot_block[k]) - delta
		if float(_rot_block[k]) <= 0.0:
			_rot_block.erase(k)
	if celebrate_t > 0.0:
		celebrate_t -= delta
		world.hud.set_lesson(celebrate_text, true)
		if celebrate_t <= 0.0:
			gap_t = 0.5
		return
	if not enabled() or _suppressed():
		world.hud.set_lesson("", false)
		return
	if gap_t > 0.0:
		gap_t -= delta
		world.hud.set_lesson("", false)
		return
	_poll_lane()
	if shown != "" and (state(shown) != ARMED or not _opportunity(shown)):
		shown = ""
		shown_t = 0.0
	if shown == "":
		shown = _pick()
		shown_t = 0.0
	if shown == "":
		world.hud.set_lesson("", false)
		return
	shown_t += delta
	var d := _def(shown)
	if d.has("timed") and shown_t >= float(d.timed):
		_set_state(shown, DONE)
		shown = ""
		world.hud.set_lesson("", false)
		return
	if d.get("reminder", false):
		var key := "tipt_" + shown
		var tot := float(GameState.flags.get(key, 0.0)) + delta
		GameState.flags[key] = tot
		if tot >= REMINDER_SECONDS:
			_set_state(shown, SKIPPED)
			shown = ""
			world.hud.set_lesson("", false)
			return
		# a reminder is a glance at the start of a fight, not a banner for the whole fight
		if shown_t >= 6.0:
			_rot_block[shown] = 45.0
			shown = ""
			world.hud.set_lesson("", false)
			return
	elif shown_t >= ROTATE_SECONDS:
		# yield to another armed tip that has an opportunity right now
		for id in armed_ids():
			if id != shown and not _rot_block.has(id) and _opportunity(id):
				_rot_block[shown] = ROTATE_SECONDS
				shown = id
				shown_t = 0.0
				break
	world.hud.set_lesson(current_text(), false)

## "move" completes when the player is lined up with an enemy within punching distance.
func _poll_lane() -> void:
	if state("move") != ARMED:
		return
	var r := _room()
	if r == null or r.player == null:
		return
	for a in r.actors:
		if a is Enemy and not a.dead and a.team == Actor.TEAM_ENEMY:
			if absf(a.position.x - r.player.position.x) < 64.0 and absf(a.position.y - r.player.position.y) <= 8.0:
				notify("lane")
				return

# ---------------------------------------------------------------- reference page
## Every basic tip plus the inputs of learned techniques, formatted for the current device.
func reference_lines() -> Array:
	var out: Array = []
	for id in ["move", "combo", "guard", "throw", "run", "blocker", "unblockable", "food", "save"]:
		out.append(Story.format_text(str(TIPS[id].text)).replace("Pick up the bottle", "Pick things up").replace(" Dot has a plate waiting in the Lucky Spoon.", ""))
	out.append(Story.format_text("Grab a dizzy or floored enemy with {interact}, then throw them with {interact} or {punch}."))
	out.append(Story.format_text("Tap {guard} just before a hit lands for a PERFECT guard that staggers the attacker. It is a bonus, never required."))
	return out
