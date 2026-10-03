class_name PriceCalculator
extends RefCounted

static func value(config: Dictionary, w: Dictionary, market: Array) -> Dictionary:
	var c = config.price
	var effective = c.refining_values[str(int(w.refining_level))] * (0.4 * c.normal_coefficients[w.normal_stat_grade] + 0.6 * c.high_coefficients[w.high_stat_grade])
	var modifier = Balance.sum_values([c.market_balance_values[market[0]], c.market_popularity_values[market[1]], c.normal_values[w.normal_stat_grade], c.high_values[w.high_stat_grade], c.unique_values[w.unique_stat_grade], c.reinforce_values[w.reinforcement_grade], c.amplification_values[w.amplification_grade], effective])
	return {"true_appraised_price": finish(c, int(w.tier), modifier, w.stability), "modifier": modifier, "effective_refining": effective}

static func finish(c: Dictionary, tier: int, modifier: float, stability = null) -> int:
	var multiplier = 1.0
	if stability != null:
		for threshold in [100, 80, 60, 40, 20, 0]:
			if stability >= threshold:
				multiplier = c.stability_multipliers["at_least_2" if modifier >= 2 else "below_2"][str(threshold)]
				break
	var base = c.base_prices[str(tier)]
	return Balance.money(maxf(base * (1 + modifier) * multiplier, base * c.minimum_price_ratio))

static func calculate(config: Dictionary, item: WeaponData, market: Dictionary) -> Dictionary:
	var result = value(config, item.truth.values, market[item.truth.values.required_class])
	var guest = item.seller
	var asking = result.true_appraised_price * config.price.selling_purpose_multipliers[guest.selling_purpose] * config.price.market_knowledge_multipliers[guest.market_knowledge]
	if guest.trade_attitude == "SCAMMER":
		asking = maxf(asking, result.true_appraised_price * config.price.scammer_minimum_multiplier)
	result.asking_price = Balance.money(asking)
	return result

# Only player-chosen grades enter this estimate. No truth, market, or actual revealed
# contribution is read; revealed knowledge gates eligibility only.
static func estimate(config: Dictionary, visible: Dictionary, judgement: PlayerJudgement) -> int:
	var modifier = 0.0
	var stability = null
	var mapping = config.player_estimate
	for section in PlayerJudgement.SECTIONS:
		var entry = judgement.entries[section]
		if not entry.included or entry.selected_value_tier < 0 or not PlayerJudgement.revealed(visible, section):
			continue
		var rule = mapping[section]
		if section == "stability":
			stability = rule.representatives[entry.selected_value_tier]
			continue
		var contribution = config.price[rule.table][rule.keys[entry.selected_value_tier]]
		if rule.has("factors"):
			contribution *= rule.factors[entry.selected_value_tier]
		if section == "refining":
			var normal_coefficient = 1.0
			var high_coefficient = 1.0
			var normal = judgement.entries.normal_stat
			var high = judgement.entries.high_stat
			if normal.included and normal.selected_value_tier >= 0:
				normal_coefficient = config.price.normal_coefficients[mapping.normal_stat.keys[normal.selected_value_tier]]
			if high.included and high.selected_value_tier >= 0:
				high_coefficient = config.price.high_coefficients[mapping.high_stat.keys[high.selected_value_tier]]
			contribution *= 0.4 * normal_coefficient + 0.6 * high_coefficient
		modifier += contribution
	return finish(config.price, visible.tier, modifier, stability)
