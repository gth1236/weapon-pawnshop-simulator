class_name VisualAssets
extends RefCounted

const SHOP = preload("res://assets/backgrounds/shop_background.png")
const APPRAISAL = preload("res://assets/backgrounds/appraisal_background.png")
const TABLE = preload("res://assets/props/item_table.png")
const STATUS = preload("res://assets/ui/day_money_info.png")
const ITEM_INTERFACE = preload("res://assets/ui/item_interface.png")
const BUTTON = preload("res://assets/ui/button_panel_godot_pack/button_panel_9patch.png")
const DIALOGUE = preload("res://assets/ui/chat_panel_godot_pack/dialogue_panel_9patch.png")
const FONT = preload("res://assets/fonts/Hakgyoansim Nadeuri OTF L.otf")
const CHARACTERS = {
	"WARRIOR": preload("res://assets/characters/warrior.png"),
	"MAGE": preload("res://assets/characters/mage.png"),
	"ROGUE": preload("res://assets/characters/rogue.png"),
	"ARCHER": preload("res://assets/characters/archer.png"),
	"GUNNER": preload("res://assets/characters/gunner.png"),
	"CLERIC": preload("res://assets/characters/cleric.png")}
const WEAPONS = {
	"one_handed_sword": preload("res://assets/weapons/one_handed_sword.png"),
	"greatsword": preload("res://assets/weapons/greatsword.png"),
	"spear": preload("res://assets/weapons/spear.png"),
	"axe": preload("res://assets/weapons/axe.png"),
	"staff": preload("res://assets/weapons/staff.png"),
	"wand": preload("res://assets/weapons/wand.png"),
	"grimoire": preload("res://assets/weapons/grimoire.png"),
	"dagger": preload("res://assets/weapons/dagger.png"),
	"throwing_weapon": preload("res://assets/weapons/throwing_weapon.png"),
	"bow": preload("res://assets/weapons/bow.png"),
	"crossbow": preload("res://assets/weapons/crossbow.png"),
	"gun": preload("res://assets/weapons/gun.png"),
	"heavy_weapon": preload("res://assets/weapons/heavy_weapon.png"),
	"gauntlet": preload("res://assets/weapons/gauntlet.png"),
	"mace": preload("res://assets/weapons/mace.png")}

static func enabled(node: Node) -> bool:
	while node != null:
		if node.has_meta("painted_ui"):
			return node.get_meta("painted_ui")
		node = node.get_parent()
	return false

static func image(parent: Node, texture: Texture2D, rect: Rect2) -> TextureRect:
	var node = TextureRect.new()
	node.texture = texture
	node.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	node.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(node)
	UIFactory.at(node, rect)
	return node

# Scale the complete nine-patch uniformly, including its un-stretched corners.
# Source pixels/margins come from the supplied pack; no asset files are rewritten.
static func patch(parent: Node, texture: Texture2D, rect: Rect2, margins: Vector4, pixel_scale = 1.0, region = Rect2()) -> NinePatchRect:
	var node = NinePatchRect.new()
	node.texture = texture
	node.region_rect = region
	node.patch_margin_left = int(margins.x)
	node.patch_margin_top = int(margins.y)
	node.patch_margin_right = int(margins.z)
	node.patch_margin_bottom = int(margins.w)
	node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	node.scale = Vector2.ONE * pixel_scale
	parent.add_child(node)
	# No deferred size: button resize signals own the live patch geometry.
	node.position = rect.position
	node.size = rect.size / pixel_scale
	return node

static func skin_button(button: Button) -> void:
	for state in ["normal", "hover", "pressed", "hover_pressed", "disabled"]:
		button.add_theme_stylebox_override(state, StyleBoxEmpty.new())
	var focus = StyleBoxFlat.new()
	focus.bg_color = Color.TRANSPARENT
	focus.border_color = Color("ffe3a0")
	focus.set_border_width_all(2)
	focus.set_corner_radius_all(5)
	button.add_theme_stylebox_override("focus", focus)
	var art = patch(button, BUTTON, Rect2(Vector2.ZERO, button.size), Vector4(90, 70, 90, 70), 0.22)
	art.show_behind_parent = true
	var update = func():
		art.size = button.size / art.scale
		art.modulate = Color(0.55, 0.55, 0.55) if button.disabled else Color("e8c99b") if button.button_pressed else Color(1.17, 1.12, 1.05) if button.is_hovered() else Color.WHITE
	button.resized.connect(update)
	button.draw.connect(update)
	button.mouse_entered.connect(func(): button.queue_redraw())
	button.mouse_exited.connect(func(): button.queue_redraw())
	button.add_theme_color_override("font_color", Color("fff3de"))
	button.add_theme_color_override("font_hover_color", Color.WHITE)
	button.add_theme_color_override("font_pressed_color", Color("ffdf99"))
	button.add_theme_color_override("font_disabled_color", Color("b7ada1"))
	update.call()
