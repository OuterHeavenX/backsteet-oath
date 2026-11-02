class_name UIKit
extends RefCounted
## Shared theme + widget helpers. Pixel font at 8px (or the 12px heading font in Large Text mode).

const INK := Color("1a1220")
const CREAM := Color("e8d8b0")
const MUSTARD := Color("f0c040")
const DANGER := Color("e04a4a")
const XPC := Color("4af0f0")
const CASHC := Color("7af04a")
const DIM := Color("9a8f86")
const PANEL_BG := Color(0.102, 0.071, 0.125, 0.94)

static var _theme: Theme
static var font_small: Font
static var font_big: Font

static func load_fonts() -> void:
	font_small = _load_font("res://assets/fonts/oath_pixel.ttf")
	font_big = _load_font("res://assets/fonts/oath_big.ttf")
	if font_big == null:
		font_big = font_small

static func _load_font(path: String) -> Font:
	if not ResourceLoader.exists(path):
		return null
	var f = load(path)
	if f is FontFile:
		f.antialiasing = TextServer.FONT_ANTIALIASING_NONE
		f.hinting = TextServer.HINTING_NONE
		f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_DISABLED
		f.generate_mipmaps = false
		f.allow_system_fallback = false
	return f

static func base_size() -> int:
	return 12 if Settings.large_text else 8

static func body_font() -> Font:
	if Settings.large_text and font_big:
		return font_big
	return font_small

static func build_theme() -> Theme:
	if font_small == null:
		load_fonts()
	var t := Theme.new()
	var f := body_font()
	if f:
		t.default_font = f
	t.default_font_size = base_size()
	var panel := _panel_box(PANEL_BG, CREAM, 2)
	t.set_stylebox("panel", "PanelContainer", panel)
	t.set_stylebox("panel", "Panel", panel)
	var bn := _panel_box(Color(0.2, 0.14, 0.22, 0.96), Color(0.55, 0.45, 0.4), 1)
	var bf := _panel_box(Color(0.42, 0.3, 0.12, 1.0), MUSTARD, 2)
	var bp := _panel_box(Color(0.6, 0.45, 0.15, 1.0), MUSTARD, 2)
	var bd := _panel_box(Color(0.15, 0.12, 0.16, 0.9), Color(0.3, 0.27, 0.3), 1)
	var touch_pad := 5 if InputPrompts.kind == "touch" else 2
	for s in [bn, bf, bp, bd]:
		s.content_margin_left = 6; s.content_margin_right = 6; s.content_margin_top = touch_pad; s.content_margin_bottom = touch_pad
	t.set_stylebox("normal", "Button", bn)
	t.set_stylebox("hover", "Button", bf)
	t.set_stylebox("focus", "Button", bf)
	t.set_stylebox("pressed", "Button", bp)
	t.set_stylebox("disabled", "Button", bd)
	t.set_color("font_color", "Button", CREAM)
	t.set_color("font_hover_color", "Button", Color.WHITE)
	t.set_color("font_focus_color", "Button", Color.WHITE)
	t.set_color("font_pressed_color", "Button", Color.WHITE)
	t.set_color("font_disabled_color", "Button", DIM)
	t.set_color("font_color", "Label", CREAM)
	t.set_color("default_color", "RichTextLabel", CREAM)
	t.set_constant("separation", "VBoxContainer", 3)
	t.set_constant("separation", "HBoxContainer", 4)
	var grab := StyleBoxFlat.new()
	grab.bg_color = MUSTARD
	grab.set_corner_radius_all(0)
	var slider_bg := StyleBoxFlat.new()
	slider_bg.bg_color = Color(0.25, 0.2, 0.25)
	slider_bg.content_margin_top = 2; slider_bg.content_margin_bottom = 2
	t.set_stylebox("slider", "HSlider", slider_bg)
	t.set_stylebox("grabber_area", "HSlider", grab)
	t.set_stylebox("grabber_area_highlight", "HSlider", grab)
	t.set_icon("grabber", "HSlider", _square_icon(6, CREAM))
	t.set_icon("grabber_highlight", "HSlider", _square_icon(6, MUSTARD))
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.3, 0.25, 0.3, 0.8)
	t.set_stylebox("scroll", "VScrollBar", sb)
	var sg := StyleBoxFlat.new()
	sg.bg_color = MUSTARD
	t.set_stylebox("grabber", "VScrollBar", sg)
	t.set_stylebox("grabber_highlight", "VScrollBar", sg)
	t.set_stylebox("grabber_pressed", "VScrollBar", sg)
	var empty := StyleBoxEmpty.new()
	t.set_stylebox("panel", "ScrollContainer", empty)
	t.set_stylebox("focus", "ScrollContainer", empty)
	_theme = t
	if f:
		ThemeDB.fallback_font = f
	ThemeDB.fallback_font_size = base_size()
	return t

## Anchors a control to a preset and sets offsets relative to the anchor point (robust at any size).
static func place(c: Control, preset: int, x: float, y: float, w: float, h: float) -> void:
	c.set_anchors_preset(preset)
	c.offset_left = x
	c.offset_top = y
	c.offset_right = x + w
	c.offset_bottom = y + h

## Theme inheritance stops at CanvasLayers, so every UI root gets the theme explicitly.
static func apply(c: Control) -> void:
	c.theme = theme()

static func theme() -> Theme:
	if _theme == null:
		build_theme()
	return _theme

static func _panel_box(bg: Color, border: Color, bw: int) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(bw)
	s.set_corner_radius_all(0)
	s.content_margin_left = 8; s.content_margin_right = 8; s.content_margin_top = 6; s.content_margin_bottom = 6
	s.anti_aliasing = false
	return s

static func _square_icon(n: int, c: Color) -> Texture2D:
	var img := Image.create(n, n + 4, false, Image.FORMAT_RGBA8)
	img.fill(c)
	return ImageTexture.create_from_image(img)

static func panel_style(bg: Color = PANEL_BG, border: Color = CREAM, bw: int = 2) -> StyleBoxFlat:
	return _panel_box(bg, border, bw)

# ---------------------------------------------------------------- widgets
static func label(text: String, color: Color = CREAM, size: int = 0, align: int = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", color)
	if size > 0:
		l.add_theme_font_size_override("font_size", size)
	l.horizontal_alignment = align
	return l

static func heading(text: String, color: Color = MUSTARD) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_color_override("font_color", color)
	if font_big:
		l.add_theme_font_override("font", font_big)
		l.add_theme_font_size_override("font_size", 12 if not Settings.large_text else 24)
	return l

static func wrap_label(text: String, width: float, color: Color = CREAM) -> Label:
	var l := label(text, color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	l.custom_minimum_size = Vector2(width, 0)
	return l

static func button(text: String, cb: Callable, min_w: float = 0.0) -> Button:
	var b := Button.new()
	b.text = text
	b.focus_mode = Control.FOCUS_ALL
	b.alignment = HORIZONTAL_ALIGNMENT_LEFT
	if min_w > 0.0:
		b.custom_minimum_size = Vector2(min_w, 0)
	b.pressed.connect(func():
		Audio.sfx("ui_confirm", -6.0, 0.0)
		cb.call())
	b.focus_entered.connect(func(): Audio.sfx("ui_move", -10.0, 0.0))
	return b

static func icon_rect(tex: Texture2D, size: int = 16) -> TextureRect:
	var r := TextureRect.new()
	r.texture = tex
	r.custom_minimum_size = Vector2(size, size)
	r.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
	r.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	return r

static func panel(min_size: Vector2 = Vector2.ZERO) -> PanelContainer:
	var p := PanelContainer.new()
	p.custom_minimum_size = min_size
	return p

static func vbox(sep: int = 3) -> VBoxContainer:
	var v := VBoxContainer.new()
	v.add_theme_constant_override("separation", sep)
	return v

static func hbox(sep: int = 4) -> HBoxContainer:
	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", sep)
	return h

static func spacer(h: float = 4.0) -> Control:
	var c := Control.new()
	c.custom_minimum_size = Vector2(0, h)
	return c

static func bar(value: float, maxv: float, w: float, h: float, fill: Color, back: Color = Color(0.15, 0.1, 0.15)) -> Control:
	var c := ColorRect.new()
	c.color = back
	c.custom_minimum_size = Vector2(w, h)
	var f := ColorRect.new()
	f.color = fill
	f.size = Vector2(maxf(0.0, w * clampf(value / maxf(maxv, 1.0), 0.0, 1.0)), h)
	c.add_child(f)
	return c

static func fmt_time(sec: float) -> String:
	var s := int(sec)
	return "%d:%02d:%02d" % [s / 3600, (s / 60) % 60, s % 60]

static func link_focus_vertical(buttons: Array) -> void:
	var n := buttons.size()
	for i in n:
		var b: Control = buttons[i]
		b.focus_neighbor_top = b.get_path_to(buttons[(i - 1 + n) % n])
		b.focus_neighbor_bottom = b.get_path_to(buttons[(i + 1) % n])
