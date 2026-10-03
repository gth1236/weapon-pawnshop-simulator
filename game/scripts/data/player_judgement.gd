class_name PlayerJudgement
extends RefCounted

# Player interpretation is neither weapon truth nor appraisal knowledge.
const MARKET_SECTIONS = ["class_popularity", "class_balance"]
const SECTIONS = ["normal_stat", "high_stat", "unique_property", "reinforcement", "refining", "amplification", "stability", "class_popularity", "class_balance"]
var entries: Dictionary = {}

static func option_count(section: String) -> int:
	return 3 if section == "unique_property" or section in MARKET_SECTIONS else 8 if section == "amplification" else 4

func _init() -> void:
	for section in SECTIONS:
		entries[section] = {"selected_value_tier": -1, "included": false}

static func revealed(visible: Dictionary, section: String) -> bool:
	if section in ["normal_stat", "high_stat"] or section in MARKET_SECTIONS:
		return true
	return visible.properties.has(section) and visible.properties[section].knowledge_state == "EXACT"

func choose(section: String, selected_value_tier: int, visible: Dictionary) -> bool:
	if not entries.has(section) or selected_value_tier < 0 or selected_value_tier >= option_count(section) or not revealed(visible, section):
		return false
	entries[section].selected_value_tier = selected_value_tier
	return true

func include(section: String, enabled: bool, visible: Dictionary) -> bool:
	if not entries.has(section) or entries[section].selected_value_tier < 0 or not revealed(visible, section):
		return false
	entries[section].included = enabled
	return true
