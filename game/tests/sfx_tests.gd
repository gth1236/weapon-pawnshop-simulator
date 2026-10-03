extends SceneTree

var events: Array = []
var failures = 0
var checks = 0
var sfx: Node

func check(ok: bool, label: String) -> void:
	checks += 1
	if not ok:
		failures += 1
		push_error(label)

func _initialize() -> void:
	run.call_deferred()

func expect(cue: String, action: Callable) -> void:
	events.clear()
	action.call()
	check(events == [cue], "Exactly one cue: " + cue + " got " + str(events))

func run() -> void:
	sfx = root.get_node("Sfx")
	sfx.played.connect(func(cue): events.append(cue))
	for cue in sfx.STREAMS:
		var stream = sfx.STREAMS[cue]
		check(stream is AudioStreamMP3 and stream.get_length() > 0, "Imported audio: " + cue)
		sfx.play(cue)
		await create_timer(0.05).timeout
		check(sfx.player.playing and sfx.player.get_playback_position() > 0, "Audio playback advances: " + cue)
	sfx.volume_db = -12
	check(sfx.player.volume_db == -12, "Shared volume control")
	var scene = load("res://scenes/main.tscn").instantiate()
	root.add_child(scene)
	await process_frame
	expect("click", func(): scene.next_button.pressed.emit())
	expect("click", func(): scene.table_button.pressed.emit())
	var detail = scene.detail
	expect("appraisal", func(): detail.row_buttons.refining.pressed.emit())
	await create_timer(0.36).timeout
	expect("click", func(): detail.row_buttons.refining.pressed.emit())
	expect("click", func(): detail.grade_buttons.back().pressed.emit())
	expect("check", func(): detail.toggles.refining.button_pressed = true)
	events.clear()
	detail.refresh_controls()
	detail.toggles.refining.button_pressed = true
	check(events.is_empty(), "Refresh and unchanged checkbox are silent")
	expect("check", func(): detail.toggles.refining.button_pressed = false)
	for section in PlayerJudgement.SECTIONS:
		detail.row_buttons[section].pressed.emit()
		await create_timer(0.36).timeout
		detail.grade_buttons.back().pressed.emit()
		detail.toggles[section].button_pressed = true
	expect("gold", func(): detail.buy_button.pressed.emit())
	check(scene.day.state.seller_trades == 1, "Seller purchase committed")
	scene.inventory_button.pressed.emit()
	var inventory = scene.inventory_screen
	inventory.slot_buttons[0].pressed.emit()
	expect("gold", func(): inventory.confirmation.confirmed.emit())
	check(scene.day.state.scrapped_items == 1, "Scrap committed")
	events.clear()
	scene.refresh()
	check(events.is_empty(), "Repeated state refresh does not replay gold")
	# Real buyer transactions from parity fixtures, including success and failure.
	var cases = JSON.parse_string(FileAccess.get_file_as_string("res://tests/reference_cases.json"))
	var successes = 0
	var misses = 0
	for sample in cases:
		var day = scene.day
		day.state.inventory.clear()
		var truth = WeaponTrueState.new(sample.weapon)
		var owned = WeaponData.new(truth, AppraisalService.create_knowledge(day.config, truth, day.rng), sample.seller)
		owned.final_purchase_price = 1
		day.state.inventory.append(owned)
		day.guest = sample.buyer.duplicate(true)
		day.guest.name = "검증 손님"
		day.guest.adventurer_level = day.guest.get("adventurer_level", 1)
		day.market = sample.market
		day.phase = "BUYER"
		var previous = day.state.buyer_trades
		events.clear()
		scene.next_button.pressed.emit()
		if day.state.buyer_trades > previous:
			successes += 1
			check(events == ["gold"], "Buyer success replaces click")
		else:
			misses += 1
			check(events == ["click"], "Buyer failure has no gold")
		if successes > 0 and misses > 0:
			break
	check(successes > 0 and misses > 0, "Buyer success and failure exercised")
	scene.queue_free()
	sfx.player.stop()
	await create_timer(0.2).timeout
	print("SFX CHECKS: %d | FAILURES: %d" % [checks, failures])
	quit(0 if failures == 0 else 1)
