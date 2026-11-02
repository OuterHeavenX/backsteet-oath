class_name MapMenu
extends Menu
## District map with current location. In bus mode, lists unlocked stops for fast travel.

var bus_mode := false
const DISTRICTS := ["old_quarter", "canal_market", "ironworks", "neon_mile", "underline", "floodgate", "warehouse"]
const DEFAULT_POS := {"old_quarter": [60, 150], "canal_market": [135, 120], "ironworks": [215, 150], "neon_mile": [290, 110], "floodgate": [365, 150], "warehouse": [430, 125], "underline": [329, 203]}

func build() -> void:
	var c := make_frame("BUS STOP" if bus_mode else "BELLWETHER", Vector2(500, 0))
	var map_tex := SpriteLib.ui("map")
	var holder := Control.new()
	holder.clip_contents = true
	var scale_f := 1.0
	if map_tex:
		scale_f = minf(480.0 / map_tex.get_width(), 200.0 / map_tex.get_height())
	holder.custom_minimum_size = Vector2(480, 200) if map_tex == null else map_tex.get_size() * scale_f
	holder.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	c.add_child(holder)
	if map_tex:
		var tr := TextureRect.new()
		tr.texture = map_tex
		tr.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		tr.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		tr.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		holder.add_child(tr)
	else:
		var bg := ColorRect.new()
		bg.color = Color(0.85, 0.78, 0.6)
		bg.size = Vector2(480, 200)
		holder.add_child(bg)
		var river := ColorRect.new()
		river.color = Color(0.35, 0.55, 0.75)
		river.position = Vector2(0, 170)
		river.size = Vector2(480, 18)
		holder.add_child(river)
	var cur_d: String = Content.room(GameState.room).get("district", "old_quarter")
	for d in DISTRICTS:
		var p: Array = Content.map_meta.get(d, DEFAULT_POS[d])
		var pos := Vector2(float(p[0]), float(p[1])) * scale_f
		var known := _district_known(d)
		var dot := ColorRect.new()
		dot.color = UIKit.DANGER if d == cur_d else (UIKit.MUSTARD if known else Color(0.4, 0.35, 0.35))
		dot.size = Vector2(6, 6)
		dot.position = pos - Vector2(3, 3)
		holder.add_child(dot)
		var l := UIKit.label(Content.district_name(d) if known else "???", UIKit.INK if map_tex == null else Color.WHITE, 0, HORIZONTAL_ALIGNMENT_CENTER)
		l.add_theme_color_override("font_outline_color", UIKit.INK)
		l.add_theme_constant_override("outline_size", 3 if map_tex else 0)
		l.visible = d != "underline" or map_tex == null   # the v2 map art has the Underline label baked in
		l.position = pos + Vector2(-50, 4)
		l.size = Vector2(100, 10)
		holder.add_child(l)
		if d == cur_d:
			var you := UIKit.label("YOU", UIKit.DANGER, 0, HORIZONTAL_ALIGNMENT_CENTER)
			you.position = pos + Vector2(-20, -14)
			you.size = Vector2(40, 10)
			you.add_theme_color_override("font_outline_color", Color.WHITE)
			you.add_theme_constant_override("outline_size", 3)
			holder.add_child(you)
	c.add_child(UIKit.label("Location: %s, %s" % [Content.room(GameState.room).get("name", ""), Content.district_name(cur_d)], UIKit.CREAM))
	if bus_mode:
		var bus: Dictionary = Content.services.bus
		c.add_child(UIKit.label("River Line bus  -  $%d per ride. Stops unlock when you visit them." % int(bus.price), UIKit.DIM))
		var first: Control = null
		for stop in bus.stops:
			if stop == GameState.room:
				continue
			var unlocked := GameState.bus_stops.has(stop)
			var b := UIKit.button(("Ride to %s" % bus.stops[stop]) if unlocked else "??? (not visited)", func(): _ride(stop), 300)
			b.disabled = not unlocked
			c.add_child(b)
			if first == null and unlocked:
				first = b
		var cancel := UIKit.button("Stay here", close, 300)
		c.add_child(cancel)
		first_focus = first if first else cancel
	else:
		var close_b := UIKit.button("Close", close, 120)
		c.add_child(close_b)
		first_focus = close_b

func _district_known(d: String) -> bool:
	for rid in GameState.visited:
		if Content.room(rid).get("district", "") == d:
			return true
	return false

func _ride(stop: String) -> void:
	var price := int(Content.services.bus.price)
	if not GameState.spend(price):
		Audio.sfx("deny")
		host.toast("Not enough cash for the fare.")
		return
	Audio.sfx("bus_horn")
	var w = host
	w.close_all_menus()
	w.change_room(stop, "x:%d" % _stop_x(stop))

func _stop_x(stop: String) -> int:
	for p in Content.room(stop).get("props", []):
		if p.type == "bus_stop":
			return int(p.x) + 30
	return 80
