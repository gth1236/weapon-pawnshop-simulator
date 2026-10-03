class_name PlayerJudgement
extends RefCounted

# Player interpretation is neither weapon truth nor appraisal knowledge.
const SECTIONS = ["normal_stat", "high_stat", "unique_property", "reinforcement", "refining", "amplification", "stability"]
var entries: Dictionary = {}

static func option_count(section: String) -> int:
	return 3 if section == "unique_property" else 8 if section == "amplification" else 4

func _init() -> void:
	for section in SECTIONS:
		entries[section] = {"grade": -1, "included": false}

static func revealed(visible: Dictionary, section: String) -> bool:
	if section in ["normal_stat", "high_stat"]:
		return true
	return visible.properties.has(section) and visible.properties[section].knowledge_state == "EXACT"

func choose(section: String, grade: int, visible: Dictionary) -> bool:
	if not entries.has(section) or grade < 0 or grade >= option_count(section) or not revealed(visible, section):
		return false
	entries[section].grade = grade
	return true

func include(section: String, enabled: bool, visible: Dictionary) -> bool:
	if not entries.has(section) or entries[section].grade < 0 or not revealed(visible, section):
		return false
	entries[section].included = enabled
	return true
