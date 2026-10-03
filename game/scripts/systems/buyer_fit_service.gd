class_name BuyerFitService
extends RefCounted

static func cumulative(value: String, probabilities: Dictionary, order: Array) -> float:
	var total = 0.0
	for key in order:
		total += probabilities.get(key, 0.0)
		if key == value:
			break
	return clampf(total, 0, 1)

static func calculate(config: Dictionary, buyer: Dictionary, w: Dictionary) -> Dictionary:
	if buyer.guest_class != w.item_class:
		return {}
	var cfg = config.economy.buyer_fit
	var gc = config.guest
	var orders = cfg.quality_order
	var tiers = Balance.band_table(gc.tier_by_level, buyer.level)
	var max_tier = 0.0
	for probability in tiers.values():
		max_tier = maxf(max_tier, probability)
	var stats = gc.stat_grade_by_power[buyer.power]
	var high = {}
	for key in stats:
		high["LOW" if key == "MIXED" else key] = stats[key]
	var reinforcement = gc.reinforce_by_tendency[buyer.tendency].duplicate()
	reinforcement.UNENHANCED = 0.0
	var refining = cfg.refining_zero_probability
	for band in gc.refining_band_by_achievement[buyer.achievement]:
		var bounds = band.split("-")
		for level in range(int(bounds[0]), int(bounds[1]) + 1):
			if level <= w.refining_level:
				refining += (1 - cfg.refining_zero_probability) * gc.refining_band_by_achievement[buyer.achievement][band] / (int(bounds[1]) - int(bounds[0]) + 1)
	var count = gc.amplification_count_by_title[buyer.title]
	var amp = {"UNAPPLIED": count.UNAPPLIED, "ZERO_LINE": count.ZERO_LINE}
	for prefix in ["ONE_LINE", "TWO_LINE", "THREE_LINE"]:
		for grade in ["LOW", "HIGH"]:
			amp[prefix + "_" + grade] = count[prefix] * config.weapon.amplification_quality_weights[grade]
	var components = {
		"tier": tiers.get(str(int(w.tier)), 0.0) / max_tier,
		"weapon_preference": 1.0 if w.item_type == buyer.preferred_weapon_type else cfg.non_preferred_weapon_fit,
		"normal_stat": cumulative(w.normal_stat_grade, stats, orders.normal_stat),
		"high_stat": cumulative(w.high_stat_grade, high, orders.high_stat),
		"reinforcement": cumulative(w.reinforcement_grade, reinforcement, orders.reinforcement),
		"refining": refining,
		"amplification": cumulative(w.amplification_grade, amp, orders.amplification),
		"unique_stat": cumulative(w.unique_stat_grade, gc.unique_by_tendency[buyer.tendency], orders.unique_stat)}
	var score = 0.0
	for key in components:
		score += cfg.weights[key] * components[key]
	return {"score": clampf(score, 0, 100), "components": components, "tier_fit": components.tier, "preference_match": w.item_type == buyer.preferred_weapon_type}

static func interest(config: Dictionary, score: float) -> Dictionary:
	for band in config.economy.interest_bands:
		if score >= band.minimum:
			return band
	return {}

static func choose(config: Dictionary, rng: RandomNumberGenerator, buyer: Dictionary, inventory: Array) -> Dictionary:
	var best = []
	var best_score = -INF
	for item in inventory:
		var fit = calculate(config, buyer, item.truth.values)
		if fit.is_empty():
			continue
		if fit.score > best_score + 1e-9:
			best.clear()
			best_score = fit.score
		if absf(fit.score - best_score) < 1e-9:
			best.append({"item": item, "fit": fit})
	if best.is_empty():
		return {"failure": "NO_COMPATIBLE_ITEM"}
	var result = Balance.pick(rng, best)
	result.failure = "NO_INTEREST" if interest(config, result.fit.score).is_empty() else ""
	return result
