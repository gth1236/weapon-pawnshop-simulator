class_name UIFactory
extends RefCounted

const BACKGROUND = Color("111923")
const PANEL = Color("1b2938")
const INK = Color("e2eaf0")
const MUTED = Color("9aafbf")
const ACCENT = Color("d7b477")

static func setup_theme(root: Control) -> void:
	var theme = Theme.new()
	var font = SystemFont.new()
	font.font_names = PackedStringArray(["Malgun Gothic", "Noto Sans CJK KR", "sans-serif"])
	theme.default_font = font
	theme.default_font_size = 24
	root.theme = theme

static func at(node: Control, rect: Rect2) -> Control:
	node.position = rect.position
	node.size = rect.size
	# Reflow autowrapped labels after their final width is assigned.
	node.set_deferred("size", rect.size)
	return node

static func backdrop(parent: Control) -> void:
	var background = ColorRect.new()
	background.color = BACKGROUND
	background.mouse_filter = Control.MOUSE_FILTER_STOP
	parent.add_child(background)
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

static func panel(parent: Node, rect: Rect2, color = PANEL) -> Panel:
	var node = Panel.new()
	var style = StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = Color("42596c")
	style.set_border_width_all(2)
	style.set_corner_radius_all(8)
	node.add_theme_stylebox_override("panel", style)
	parent.add_child(node)
	at(node, rect)
	return node

static func label(parent: Node, text: String, size = 26) -> Label:
	var node = Label.new()
	node.size = Vector2(1920, 100)
	node.text = text
	node.add_theme_font_size_override("font_size", size)
	node.add_theme_color_override("font_color", INK)
	node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(node)
	return node

static func button(parent: Node, text: String, action: Callable) -> Button:
	var node = Button.new()
	node.text = text
	node.custom_minimum_size.y = 44
	node.pressed.connect(action)
	parent.add_child(node)
	return node

static func clear(parent: Node) -> void:
	for child in parent.get_children():
		parent.remove_child(child)
		child.queue_free()

static func money(value: int) -> String:
	var digits = str(absi(value))
	var output = ""
	for i in range(digits.length()):
		if i > 0 and (digits.length() - i) % 3 == 0:
			output += ","
		output += digits[i]
	return ("-" if value < 0 else "") + output + " 골드"

static func stat_text(line: Dictionary) -> String:
	return TextCatalog.stat(line)
