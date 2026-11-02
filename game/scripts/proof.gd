extends Node2D
# Platform proof: input, audio after gesture, persistent save counter, gamepad info.
var pos := Vector2(320, 200)
var label: Label
var boots := 0
var player: AudioStreamPlayer

func _ready() -> void:
	label = Label.new()
	label.position = Vector2(8, 8)
	add_child(label)
	var cfg := ConfigFile.new()
	if cfg.load("user://proof.cfg") == OK:
		boots = cfg.get_value("proof", "boots", 0)
	boots += 1
	cfg.set_value("proof", "boots", boots)
	var err := cfg.save("user://proof.cfg")
	print("PROOF_BOOT boots=%d save_err=%d persistent=%s" % [boots, err, str(OS.is_userfs_persistent())])
	player = AudioStreamPlayer.new()
	var gen := AudioStreamWAV.new()
	var data := PackedByteArray()
	for i in 8000:
		data.append(int(127 + 100 * sin(i * 0.12)) & 0xFF)
	gen.data = data
	gen.format = AudioStreamWAV.FORMAT_8_BITS
	gen.mix_rate = 22050
	player.stream = gen
	add_child(player)

func _unhandled_input(event: InputEvent) -> void:
	if event.is_pressed() and not event.is_echo():
		player.play()

func _process(delta: float) -> void:
	var v := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	pos += v * 120.0 * delta
	queue_redraw()
	label.text = "BACKSTREET OATH platform proof\nboots=%d  pads=%s\nfps=%d  size=%s" % [boots, str(Input.get_connected_joypads()), Engine.get_frames_per_second(), str(get_viewport_rect().size)]

func _draw() -> void:
	draw_rect(Rect2(pos - Vector2(8, 8), Vector2(16, 16)), Color(0.94, 0.75, 0.25))
