class_name PerfStats
extends RefCounted
## Session frame-time statistics (real time, gameplay only; menus and pauses excluded). Feeds the optional
## Show FPS readout and the end-of-game run summary, so testers can report real-device performance.

static var frames := 0
static var seconds := 0.0
static var slow_20 := 0          # frames over 20 ms (below ~50 FPS)
static var slow_33 := 0          # frames over 33 ms (below ~30 FPS)
static var worst_ms := 0.0
# rolling window for the on-screen readout
static var _win_frames := 0
static var _win_t := 0.0
static var _win_worst := 0.0
static var shown_fps := 0.0
static var shown_worst := 0.0

static func tick(delta: float, counting: bool) -> void:
	var ms := delta * 1000.0
	_win_frames += 1
	_win_t += delta
	_win_worst = maxf(_win_worst, ms)
	if _win_t >= 0.5:
		shown_fps = _win_frames / _win_t
		shown_worst = _win_worst
		_win_frames = 0
		_win_t = 0.0
		_win_worst = 0.0
	if not counting or delta > 0.5:   # ignore loading hitches and backgrounded tabs
		return
	frames += 1
	seconds += delta
	worst_ms = maxf(worst_ms, ms)
	if ms > 20.0:
		slow_20 += 1
	if ms > 33.4:
		slow_33 += 1

static func avg_fps() -> float:
	return frames / seconds if seconds > 0.0 else 0.0

static func device_line() -> String:
	var gpu := RenderingServer.get_video_adapter_name()
	var api := RenderingServer.get_video_adapter_api_version()
	return "%s · %s %s" % [OS.get_name(), gpu if gpu != "" else "unknown GPU", api]
