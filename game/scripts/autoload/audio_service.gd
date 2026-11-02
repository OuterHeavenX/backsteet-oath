extends Node
## Music with crossfade, pooled SFX with per-sound voice limits, ambient loops, bus volumes.
## Browser note: audio only starts after the first user gesture (title screen waits for a press).

const MUSIC_DIR := "res://assets/audio/music/"
const SFX_DIR := "res://assets/audio/sfx/"
const POOL := 18
const MAX_SAME := 3
const MIN_GAP_MS := 35

var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _active_music: AudioStreamPlayer
var _current_music := ""
var _ambient: AudioStreamPlayer
var _current_ambient := ""
var _pool: Array[AudioStreamPlayer] = []
var _cache: Dictionary = {}
var _last_play: Dictionary = {}
var _tween: Tween
var unlocked := false   # becomes true after first user input (browser autoplay policy)
var _pending_music := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_setup_buses()
	_music_a = _make_player("Music", Node.PROCESS_MODE_ALWAYS)
	_music_b = _make_player("Music", Node.PROCESS_MODE_ALWAYS)
	_ambient = _make_player("SFX", Node.PROCESS_MODE_PAUSABLE)
	_active_music = _music_a
	for i in POOL:
		_pool.append(_make_player("SFX", Node.PROCESS_MODE_PAUSABLE))
	Settings.changed.connect(apply_volumes)
	apply_volumes()
	if not OS.has_feature("web"):
		unlocked = true

func _input(event: InputEvent) -> void:
	if not unlocked and (event is InputEventKey or event is InputEventMouseButton or event is InputEventScreenTouch or event is InputEventJoypadButton) and event.is_pressed():
		unlocked = true
		if _pending_music != "":
			var m := _pending_music
			_pending_music = ""
			play_music(m, 0.4)

func _setup_buses() -> void:
	for bus_name in ["Music", "SFX"]:
		if AudioServer.get_bus_index(bus_name) == -1:
			var idx := AudioServer.bus_count
			AudioServer.add_bus(idx)
			AudioServer.set_bus_name(idx, bus_name)
			AudioServer.set_bus_send(idx, "Master")

func _make_player(bus: String, mode: int) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = bus
	p.process_mode = mode
	add_child(p)
	return p

func apply_volumes() -> void:
	_set_bus("Master", Settings.master_volume)
	_set_bus("Music", Settings.music_volume)
	_set_bus("SFX", Settings.sfx_volume)

func _set_bus(bus_name: String, v: float) -> void:
	var i := AudioServer.get_bus_index(bus_name)
	if i < 0:
		return
	AudioServer.set_bus_mute(i, v <= 0.001)
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(v, 0.001)))

func _stream(path: String) -> AudioStream:
	if _cache.has(path):
		return _cache[path]
	var s: AudioStream = null
	if ResourceLoader.exists(path):
		s = load(path)
	_cache[path] = s
	return s

func play_music(id: String, fade: float = 0.8) -> void:
	if id == _current_music and _active_music.playing:
		return
	if not unlocked:
		_pending_music = id
		_current_music = ""
		return
	var stream := _stream(MUSIC_DIR + id + ".ogg")
	_current_music = id
	var old := _active_music
	var new_p := _music_b if old == _music_a else _music_a
	if _tween and _tween.is_valid():
		_tween.kill()
	if stream == null and not old.playing:
		_active_music = new_p
		return
	_tween = create_tween().set_parallel(true)
	if stream:
		if stream is AudioStreamOggVorbis:
			stream.loop = not id in ["victory", "defeat"]
		new_p.stream = stream
		new_p.volume_db = -40.0
		new_p.play()
		_tween.tween_property(new_p, "volume_db", 0.0, fade)
	if old.playing:
		_tween.tween_property(old, "volume_db", -40.0, fade)
		_tween.chain().tween_callback(old.stop)
	_active_music = new_p

func stop_music(fade: float = 0.6) -> void:
	_current_music = ""
	_pending_music = ""
	if _tween and _tween.is_valid():
		_tween.kill()
	if not _music_a.playing and not _music_b.playing:
		return
	_tween = create_tween().set_parallel(true)
	for p in [_music_a, _music_b]:
		if p.playing:
			_tween.tween_property(p, "volume_db", -40.0, fade)
	_tween.chain().tween_callback(func():
		_music_a.stop()
		_music_b.stop())

func current_music() -> String:
	return _current_music

func duck_music(on: bool) -> void:
	var target := -8.0 if on else 0.0
	if _active_music.playing:
		create_tween().tween_property(_active_music, "volume_db", target, 0.25)

func play_ambient(id: String) -> void:
	if id == _current_ambient:
		return
	_current_ambient = id
	if id == "":
		_ambient.stop()
		return
	var s := _stream(SFX_DIR + id + ".ogg")
	if s == null:
		_ambient.stop()
		return
	if s is AudioStreamOggVorbis:
		s.loop = true
	_ambient.stream = s
	_ambient.volume_db = -10.0
	_ambient.play()

## Plays a one-shot. Limits repeats of the same sound so crowds of hits never clip or stack.
func sfx(id: String, volume_db: float = 0.0, pitch_var: float = 0.06) -> void:
	if id == "" or not unlocked:
		return
	var now := Time.get_ticks_msec()
	if now - int(_last_play.get(id, -1000)) < MIN_GAP_MS:
		return
	var s := _stream(SFX_DIR + id + ".ogg")
	if s == null:
		return
	var same := 0
	var free_p: AudioStreamPlayer = null
	var oldest: AudioStreamPlayer = null
	for p in _pool:
		if p.playing:
			if p.get_meta("id", "") == id:
				same += 1
				if oldest == null:
					oldest = p
		elif free_p == null:
			free_p = p
	if same >= MAX_SAME and oldest:
		free_p = oldest
	if free_p == null:
		return
	_last_play[id] = now
	free_p.stop()
	free_p.stream = s
	free_p.set_meta("id", id)
	free_p.volume_db = volume_db
	free_p.pitch_scale = 1.0 + randf_range(-pitch_var, pitch_var)
	free_p.play()

func stop_all_sfx() -> void:
	for p in _pool:
		p.stop()
