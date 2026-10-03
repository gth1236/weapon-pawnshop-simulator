class_name ProgressionService
extends RefCounted

static func interpolate(table: Dictionary, value: float) -> Dictionary:
	var anchors = table.anchors
	if value <= anchors[0].value:
		return anchors[0].weights.duplicate()
	if value >= anchors.back().value:
		return anchors.back().weights.duplicate()
	for i in range(anchors.size() - 1):
		var a = anchors[i]
		var b = anchors[i + 1]
		if a.value <= value and value <= b.value:
			var fraction = (value - a.value) / (b.value - a.value)
			var result = {}
			var total = 0.0
			for key in a.weights:
				result[key] = lerpf(a.weights[key], b.weights[key], fraction)
				total += result[key]
			for key in result:
				result[key] = maxf(0, result[key]) / total
			return result
	return {}

static func apply_delta(config: Dictionary, reputation: float, raw: float) -> float:
	if raw <= 0:
		return raw
	var multiplier = config.reputation.positive_decay.ranges[0].multiplier
	for band in config.reputation.positive_decay.ranges:
		if reputation >= band.minimum:
			multiplier = band.multiplier
	return raw * multiplier

static func purchase_delta(config: Dictionary, guest: Dictionary, ratio: float) -> float:
	var cfg = config.reputation
	for band in cfg.satisfaction_thresholds[guest.purpose]:
		if band.max == null or ratio < band.max or (band.inclusive and ratio == band.max):
			var satisfaction = band.result
			if satisfaction == "HUMILIATED" and guest.kindness in cfg.non_humiliating_kindness:
				satisfaction = "DISSATISFIED"
			return cfg.satisfaction_deltas[satisfaction] + cfg.kindness_deltas.get(guest.kindness, 0)
	return 0
