class_name WeaponKnownState
extends RefCounted

var item_type = ""
var required_class = ""
var tier = 1
var stat_lines: Array = []
var amplification_lines: Array = []
var properties: Dictionary = {}

static func field(value = null, state = "UNKNOWN") -> Dictionary:
	return {"knowledge_state": state, "known_exact_value": value if state == "EXACT" else null,
		"known_min_value": null, "known_max_value": null, "displayed_value": value}

func player_view() -> Dictionary:
	var visible = {}
	for key in properties:
		var entry = properties[key]
		visible[key] = {"knowledge_state": entry.knowledge_state,
			"displayed_value": entry.displayed_value if entry.knowledge_state == "EXACT" else null}
	return {"item_type": item_type, "required_class": required_class, "tier": tier,
		"stat_lines": stat_lines.duplicate(true), "amplification_lines": amplification_lines.duplicate(true),
		"properties": visible}
