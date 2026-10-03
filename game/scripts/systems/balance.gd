class_name Balance
extends RefCounted

static func load_config() -> Dictionary:
	var parsed = JSON.parse_string(FileAccess.get_file_as_string("res://data/balance.json"))
	assert(parsed is Dictionary, "Missing or invalid balance.json")
	parsed.player_estimate = JSON.parse_string(FileAccess.get_file_as_string("res://data/player_estimate.json"))
	parsed.seller_negotiation = JSON.parse_string(FileAccess.get_file_as_string("res://data/seller_negotiation.json"))
	return parsed

static func pick(rng: RandomNumberGenerator, values: Array):
	return values[rng.randi_range(0, values.size() - 1)]

static func weighted(rng: RandomNumberGenerator, weights: Dictionary) -> String:
	var point = rng.randf()
	var cumulative = 0.0
	for key in weights:
		cumulative += weights[key]
		if point < cumulative:
			return str(key)
	return str(weights.keys().back())

static func band_table(tables: Dictionary, value: int) -> Dictionary:
	for key in tables:
		var bounds = key.split("-")
		if value >= int(bounds[0]) and value <= int(bounds[1]):
			return tables[key]
	assert(false, "No configured range for %s" % value)
	return {}

static func roll_range(rng: RandomNumberGenerator, bounds: String) -> int:
	var parts = bounds.split("-")
	return rng.randi_range(int(parts[0]), int(parts[1]))

# Python round: ties to even, including odd purchase prices at the junk shop.
static func money(value: float) -> int:
	var lower = floori(value)
	var fraction = value - lower
	if fraction == 0.5:
		return lower if lower % 2 == 0 else lower + 1
	return lower + 1 if fraction > 0.5 else lower

# CPython 3.12+ sum uses compensated floating-point accumulation.
static func sum_values(values: Array) -> float:
	var total = 0.0
	var correction = 0.0
	for value in values:
		var next = total + value
		if absf(total) >= absf(value):
			correction += (total - next) + value
		else:
			correction += (value - next) + total
		total = next
	return total + correction
