class_name WeaponGenerator
extends RefCounted

static func numeric_line(rng: RandomNumberGenerator, stat: String, category: String, grade: String, reference: float, ranges: Dictionary, relevant = true) -> Dictionary:
	var bounds = ranges[grade]
	return line(stat, category, grade, Balance.money(reference * rng.randf_range(bounds[0], bounds[1])), "FLAT", relevant)

static func line(stat: String, category: String, grade: String, value: float, unit: String, relevant: bool) -> Dictionary:
	return {"stat_id": stat, "category": category, "internal_grade": grade, "actual_value": value, "display_unit": unit, "is_relevant": relevant}

static func generate(config: Dictionary, rng: RandomNumberGenerator, guest: Dictionary, market: Dictionary) -> WeaponData:
	var cfg = config.weapon
	var gc = config.guest
	var numeric = config.numeric_stats
	var w = {}
	w.seller_class_compatible = Balance.weighted(rng, cfg.compatibility_weights) == "seller_class_compatible"
	w.required_class = guest.adventurer_class
	w.generation_mode = "OWN_CLASS"
	if w.seller_class_compatible:
		w.item_type = Balance.pick(rng, cfg.class_weapon_pools[guest.adventurer_class])
	else:
		w.generation_mode = Balance.weighted(rng, cfg.foreign_mode_weights)
		var foreign = []
		for pool in cfg.class_weapon_pools.values():
			for item_type in pool:
				if item_type not in cfg.class_weapon_pools[guest.adventurer_class] and item_type not in foreign:
					foreign.append(item_type)
		foreign.sort()
		w.item_type = Balance.pick(rng, foreign)
		var classes = []
		for candidate in cfg.class_weapon_pools:
			if w.item_type in cfg.class_weapon_pools[candidate]:
				classes.append(candidate)
		w.required_class = Balance.pick(rng, classes)
	w.tier = int(Balance.weighted(rng, Balance.band_table(gc.tier_by_adventurer_level, guest.adventurer_level)))
	var amp_count = "UNAPPLIED"
	w.amplification_lines = []
	if w.generation_mode == "FOREIGN_RAW":
		w.normal_stat_grade = Balance.weighted(rng, cfg.foreign_raw_normal_stat_weights)
		w.high_stat_grade = Balance.weighted(rng, cfg.foreign_raw_high_stat_weights)
		w.unique_stat_grade = Balance.weighted(rng, cfg.foreign_raw_unique_weights)
		w.reinforcement_grade = "UNENHANCED"
		w.refining_level = 0
		w.amplification_grade = "UNAPPLIED"
	else:
		w.normal_stat_grade = Balance.weighted(rng, gc.stat_grade_by_adventurer_power[guest.adventurer_power])
		w.high_stat_grade = Balance.weighted(rng, gc.stat_grade_by_adventurer_power[guest.adventurer_power])
		if w.high_stat_grade == "MIXED":
			w.high_stat_grade = "LOW"
		w.unique_stat_grade = Balance.weighted(rng, gc.unique_by_equipment_tendency[guest.equipment_tendency])
		w.reinforcement_grade = Balance.weighted(rng, gc.reinforce_by_equipment_tendency[guest.equipment_tendency])
		w.refining_level = Balance.roll_range(rng, Balance.weighted(rng, gc.refining_band_by_achievement_rank[guest.achievement_rank]))
		amp_count = Balance.weighted(rng, gc.amplification_count_by_title_rank[guest.title_rank])
		var quality = Balance.weighted(rng, cfg.amplification_quality_weights)
		w.amplification_grade = amp_count if amp_count in ["UNAPPLIED", "ZERO_LINE"] else amp_count + "_" + quality
		for i in range({"ONE_LINE": 1, "TWO_LINE": 2, "THREE_LINE": 3}.get(amp_count, 0)):
			var stat = Balance.pick(rng, numeric.normal_stat_ids)
			w.amplification_lines.append(numeric_line(rng, stat, "AMPLIFICATION", quality, numeric.normal_reference[str(w.tier)], numeric.amplification_ranges, stat == numeric.class_profiles[w.required_class][0]))
	w.processing_load = cfg.processing_load.reinforcement[w.reinforcement_grade] + w.refining_level * cfg.processing_load.refining_level_multiplier + cfg.processing_load.amplification[amp_count]
	w.effective_processing_load = w.processing_load
	w.stability = Balance.roll_range(rng, Balance.weighted(rng, Balance.band_table(cfg.stability_by_processing_load, int(w.effective_processing_load))))
	w.stability_bracket = "STABILITY_BELOW_20"
	for threshold in [100, 80, 60, 40, 20]:
		if w.stability >= threshold:
			w.stability_bracket = "STABILITY_100" if threshold == 100 else "STABILITY_%d_PLUS" % threshold
			break
	w.stat_lines = []
	var profile = numeric.class_profiles[w.required_class]
	if w.normal_stat_grade != "NONE":
		w.stat_lines.append(numeric_line(rng, profile[0], "NORMAL", w.normal_stat_grade, numeric.normal_reference[str(w.tier)], numeric.normal_ranges))
		if w.normal_stat_grade == "MIXED":
			var others = numeric.normal_stat_ids.duplicate()
			others.erase(profile[0])
			w.stat_lines.append(numeric_line(rng, Balance.pick(rng, others), "NORMAL", "MIXED", numeric.normal_reference[str(w.tier)], numeric.normal_ranges, false))
	if w.high_stat_grade != "NONE":
		w.stat_lines.append(numeric_line(rng, profile[1], "HIGH", w.high_stat_grade, numeric.high_reference[str(w.tier)], numeric.high_ranges))
	elif rng.randf() < numeric.none_high_opposite_chance:
		var opposite = "magic_power" if profile[1] == "attack" else "attack"
		var bounds = numeric.irrelevant_high_range
		w.stat_lines.append(line(opposite, "HIGH", "NONE", Balance.money(numeric.high_reference[str(w.tier)] * rng.randf_range(bounds[0], bounds[1])), "FLAT", false))
	if w.unique_stat_grade != "NONE":
		var stat = Balance.pick(rng, numeric.unique_ranges.keys())
		var bounds = numeric.unique_ranges[stat][w.unique_stat_grade]
		w.stat_lines.append(line(stat, "UNIQUE", w.unique_stat_grade, Balance.money(rng.randf_range(bounds[0], bounds[1]) * 10.0) / 10.0, "PERCENT", true))
	var truth = WeaponTrueState.new(w)
	var knowledge_rng = RandomNumberGenerator.new()
	knowledge_rng.seed = int(rng.state) ^ 7183921
	return WeaponData.new(truth, AppraisalService.create_knowledge(config, truth, knowledge_rng), guest)
