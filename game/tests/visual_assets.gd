extends SceneTree

var checks = 0
var failures = 0

func check(ok: bool, description: String) -> void:
	checks += 1
	if not ok:
		failures += 1
		push_error(description)

func _initialize() -> void:
	run.call_deferred()

func inspect_art(node: Node) -> void:
	if node is NinePatchRect or node is TextureRect:
		check(node.mouse_filter == Control.MOUSE_FILTER_IGNORE, "Decorative art must not intercept input")
		if node is NinePatchRect and node.get_parent() is Button:
			check(node.get_global_rect().is_equal_approx(node.get_parent().get_global_rect()), "Button art fills the live click target")
	for child in node.get_children():
		inspect_art(child)

func run() -> void:
	var scene = load("res://scenes/main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	scene.next_button.pressed.emit()
	var day = scene.day
	var original = day.item
	check(scene.theme.default_font == VisualAssets.FONT, "Supplied font is shared through Theme")
	check(VisualAssets.CHARACTERS.size() == 6, "Six character mappings")
	check(VisualAssets.WEAPONS.size() == 15, "Fifteen weapon mappings")
	for adventurer_class in day.config.guest.classes:
		day.guest.adventurer_class = adventurer_class
		scene.refresh()
		var texture = VisualAssets.CHARACTERS.get(adventurer_class)
		check(texture != null and texture.get_size() == Vector2(1024, 1024), "Character imported: " + adventurer_class)
		check(scene.portrait_image.texture == texture and scene.portrait_image.visible, "Current class portrait is connected")
		check(scene.portrait_image.stretch_mode == TextureRect.STRETCH_KEEP_ASPECT_CENTERED, "Portrait aspect preserved")
	var types = []
	for pool in day.config.weapon.class_weapon_pools.values():
		for item_type in pool:
			if item_type not in types:
				types.append(item_type)
	for item_type in types:
		var values = original.truth.values.duplicate(true)
		values.item_type = item_type
		var truth = WeaponTrueState.new(values)
		day.item = WeaponData.new(truth, AppraisalService.create_knowledge(day.config, truth, day.rng), original.seller)
		scene.refresh()
		var texture = VisualAssets.WEAPONS.get(item_type)
		check(texture != null and texture.get_size() == Vector2(1024, 1024), "Weapon imported: " + item_type)
		check(scene.weapon_image.texture == texture, "Seller table texture matches item type")
		scene.table_button.pressed.emit()
		check(scene.detail.weapon_image != null and scene.detail.weapon_image.texture == texture, "Appraisal texture matches item type")
		check(scene.detail.weapon_image.stretch_mode == TextureRect.STRETCH_KEEP_ASPECT_CENTERED, "Weapon aspect preserved")
		await process_frame
		await process_frame
		inspect_art(scene.detail)
		scene.detail.close_panel()
	check(not VisualAssets.enabled(scene.inventory_screen), "Inventory art remains out of scope")
	check(not VisualAssets.enabled(scene.receipt), "Receipt art remains out of scope")
	inspect_art(scene)
	scene.queue_free()
	await process_frame
	print("ASSET CHECKS: %d | FAILURES: %d" % [checks, failures])
	quit(0 if failures == 0 else 1)
