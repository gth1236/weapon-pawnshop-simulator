class_name AppraisalService
extends RefCounted

const FIELDS = {"reinforcement": "reinforcement_grade", "refining": "refining_level", "amplification": "amplification_grade", "stability": "stability", "unique_property": "unique_stat_grade"}

static func domain(config: Dictionary, property: String) -> Array:
	var tables = {"reinforcement": "reinforce_values", "amplification": "amplification_values", "unique_property": "unique_values"}
	if tables.has(property):
		return config.price[tables[property]].keys()
	var result = []
	if property == "refining":
		for key in config.price.refining_values:
			result.append(int(key))
	else:
		for table in config.weapon.stability_by_processing_load.values():
			for bounds in table:
				var parts = bounds.split("-")
				for value in range(int(parts[0]), int(parts[1]) + 1):
					if value not in result:
						result.append(value)
	result.sort()
	return result

static func create_knowledge(config: Dictionary, truth: WeaponTrueState, rng: RandomNumberGenerator) -> WeaponKnownState:
	var known = WeaponKnownState.new()
	var w = truth.values
	known.item_type = w.item_type
	known.item_class = w.item_class
	known.tier = int(w.tier)
	for group in ["stat_lines", "amplification_lines"]:
		for source in w[group]:
			known.get(group).append({"stat_id": source.stat_id, "actual_value": source.actual_value, "display_unit": source.display_unit})
	for property in FIELDS:
		var actual = w[FIELDS[property]]
		var displayed = actual
		if rng.randf() >= config.appraisal.unassisted_correct_probability:
			var alternatives = domain(config, property)
			alternatives.erase(actual)
			displayed = Balance.pick(rng, alternatives)
		known.properties[property] = WeaponKnownState.field(displayed, "UNAPPRAISED_GUESS")
	return known

static func reveal(config: Dictionary, item: WeaponData, property: String, owned_tools: Array) -> bool:
	if not FIELDS.has(property) or config.appraisal.property_tools[property] not in owned_tools:
		return false
	item.known.properties[property] = WeaponKnownState.field(item.truth.values[FIELDS[property]], "EXACT")
	return true
