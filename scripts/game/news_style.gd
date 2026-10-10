class_name NewsStyle
extends RefCounted
## The game's TV-news look (user's theme A): colours and the small builders every screen uses.

const RED := Color("#D7263D")
const NAVY := Color("#1A2433")
const INK := Color(0.1, 0.14, 0.2, 0.86)
const CREAM := Color("#F7F1E6")
const AMBER := Color("#F2C46B")
const GREEN := Color("#7BC67E")
const DIM := Color("#9AA7B4")


static func box(color: Color, radius: int = 8, padding: int = 12) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(radius)
	style.content_margin_left = padding
	style.content_margin_right = padding
	style.content_margin_top = padding * 0.6
	style.content_margin_bottom = padding * 0.6
	return style


static func label(text: String, size: int, color: Color = CREAM, shadow: bool = true) -> Label:
	var result := Label.new()
	result.text = text
	result.add_theme_font_size_override("font_size", size)
	result.add_theme_color_override("font_color", color)
	if shadow:
		result.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.45))
		result.add_theme_constant_override("shadow_offset_x", 2)
		result.add_theme_constant_override("shadow_offset_y", 2)
	return result


static func panel(color: Color, radius: int = 8, padding: int = 12) -> PanelContainer:
	var result := PanelContainer.new()
	result.add_theme_stylebox_override("panel", box(color, radius, padding))
	return result


static func button(text: String, size: int = 22) -> Button:
	var result := Button.new()
	result.text = text
	result.alignment = HORIZONTAL_ALIGNMENT_LEFT
	result.add_theme_font_size_override("font_size", size)
	result.add_theme_color_override("font_color", CREAM)
	result.add_theme_color_override("font_focus_color", NAVY)
	result.add_theme_color_override("font_hover_color", NAVY)
	result.add_theme_color_override("font_pressed_color", NAVY)
	result.add_theme_stylebox_override("normal", box(INK, 6, 14))
	result.add_theme_stylebox_override("hover", box(AMBER, 6, 14))
	result.add_theme_stylebox_override("focus", box(AMBER, 6, 14))
	result.add_theme_stylebox_override("pressed", box(AMBER.darkened(0.15), 6, 14))
	return result


## "7:42" from seconds.
static func clock(seconds: float) -> String:
	var whole: int = int(seconds)
	return "%d:%02d" % [whole / 60, whole % 60]


## "12,450" with thousands separators.
static func points(value: int) -> String:
	var text: String = str(absi(value))
	var result: String = ""
	while text.length() > 3:
		result = "," + text.substr(text.length() - 3) + result
		text = text.substr(0, text.length() - 3)
	return ("-" if value < 0 else "") + text + result
