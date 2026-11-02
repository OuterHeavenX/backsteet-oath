class_name UIKit
extends RefCounted
## Shared theme + widget helpers. Pixel font at 8px (or the 12px heading font in Large Text mode).

const INK := Color("1a1220")
const CREAM := Color("f1e6c8")
const MUSTARD := Color("f2b83a")
const DANGER := Color("e5484d")
const XPC := Color("5fd3e8")
const CASHC := Color("8fe36b")
const DIM := Color("a89c92")
const PANEL_BG := Color(0.09, 0.065, 0.115, 0.93)
const EDGE := Color(0.95, 0.88, 0.72, 0.28)

static var _theme: Theme
static var font_small: Font      # body (Barlow SemiBold)
static var font_big: Font        # display (Bungee)
static var font_bold: Font       # emphasis (Barlow Bold)
static var font_num: Font        # numbers (Barlow Condensed Bold)

static func load_fonts() -> void:
	font_small = _load_font("res://assets/fonts/ofl/Barlow-SemiBold.ttf")
	font_big = _load_font("res://assets/fonts/ofl/Bungee-Regular.ttf")
	font_bold = _load_font("res://assets/fonts/ofl/Barlow-Bold.ttf")
	font_num = _load_font("res://assets/fonts/ofl/BarlowCondensed-Bold.ttf")
	if font_small == null:
		font_small = _load_font("res://assets/fonts/oath_pixel.ttf")
	if font_big == null:
		font_big = font_small
	if font_bold == null:
		font_bold = font_small
	if font_num == null:
		font_num = font_bold

static func _load_font(path: String) -> Font:
	if not ResourceLoader.exists(path):
		return null
	var f = load(path)
	if f is FontFile:
		f.antialiasing = TextServer.FONT_ANTIALIASING_GRAY
		f.hinting = TextServer.HINTING_LIGHT
		f.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_AUTO
		f.generate_mipmaps = true
		f.allow_system_fallback = true
	return f

static func base_size() -> int:
	return 13 if Settings.large_text else 10

static func body_font() -> Font:
	return font_small

static func build_theme() -> Theme:
	if font_small == null:
		load_fonts()
	var t := Theme.new()
	var f := body_font()
	if f:
		t.default_font = f
	t.default_font_size = base_size()
	var panel := _panel_box(PANEL_BG, EDGE, 1)
	panel.shadow_color = Color(0, 0, 0, 0.35)
	panel.shadow_size = 4
	panel.shadow_offset = Vector2(0, 2)
	t.set_stylebox("panel", "PanelContainer", panel)
	t.set_stylebox("panel", "Panel", panel)
	var bn := _panel_box(Color(0.17, 0.125, 0.2, 0.92), Color(0.55, 0.45, 0.42, 0.55), 1)
	var bf := _panel_box(MUSTARD, Color(1.0, 0.9, 0.6), 1)
	var bp := _panel_box(Color(0.85, 0.6, 0.15), Color(1.0, 0.9, 0.6), 1)
	var bd := _panel_box(Color(0.12, 0.1, 0.13, 0.85), Color(0.3, 0.27, 0.3, 0.5), 1)
	var touch_pad := 5 if InputPrompts.kind == "touch" else 2
	for sb_ in [bn, bf, bp, bd]:
		sb_.content_margin_left = 7; sb_.content_margin_right = 7; sb_.content_margin_top = touch_pad; sb_.content_margin_bottom = touch_pad + 1
		sb_.set_corner_radius_all(3)
	t.set_stylebox("normal", "Button", bn)
	t.set_stylebox("hover", "Button", bf)
	t.set_stylebox("focus", "Button", bf)
	t.set_stylebox("pressed", "Button", bp)
	t.set_stylebox("disabled", "Button", bd)
	t.set_color("font_color", "Button", CREAM)
	t.set_color("font_hover_color", "Button", INK)
	t.set_color("font_focus_color", "Button", INK)
	t.set_color("font_pressed_color", "Button", INK)
	t.set_color("font_hover_pressed_color", "Button", INK)
	t.set_color("font_disabled_color", "Button", DIM)
	t.set_color("font_color", "Label", CREAM)
	t.set_color("default_color", "RichTextLabel", CREAM)
	t.set_constant("separation", "VBoxContainer", 3)
	t.set_constant("separation", "HBoxContainer", 4)
	t.set_constant("line_spacing", "Label", -1)
	var grab := StyleBoxFlat.new()
	grab.bg_color = MUSTARD
	grab.set_corner_radius_all(2)
	var slider_bg := StyleBoxFlat.new()
	slider_bg.bg_color = Color(0.25, 0.2, 0.25)
	slider_bg.set_corner_radius_all(2)
	slider_bg.content_margin_top = 2; slider_bg.content_margin_bottom = 2
	t.set_stylebox("slider", "HSlider", slider_bg)
	t.set_stylebox("grabber_area", "HSlider", grab)
	t.set_stylebox("grabber_area_highlight", "HSlider", grab)
	t.set_icon("grabber", "HSlider", _square_icon(6, CREAM))
	t.set_icon("grabber_highlight", "HSlider", _square_icon(6, MUSTARD))
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(0.3, 0.25, 0.3, 0.6)
	sb.set_corner_radius_all(2)
	t.set_stylebox("scroll", "VScrollBar", sb)
	var sg := StyleBoxFlat.new()
	sg.bg_color = MUSTARD
	sg.set_corner_radius_all(2)
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
	s.set_corner_radius_all(4)
	s.content_margin_left = 8; s.content_margin_right = 8; s.content_margin_top = 6; s.content_margin_bottom = 6
	s.anti_aliasing = true
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
		l.add_theme_font_size_override("font_size", 13 if not Settings.large_text else 17)
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
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
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

## Text with an outline (for text drawn over the world).
static func outlined(l: Label, size: int = 4) -> Label:
	l.add_theme_color_override("font_outline_color", Color(0.06, 0.04, 0.08, 0.95))
	l.add_theme_constant_override("outline_size", size)
	return l

static func num_label(text: String, color: Color = CREAM, size: int = 11) -> Label:
	var l := label(text, color, size)
	if font_num:
		l.add_theme_font_override("font", font_num)
	return l

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
