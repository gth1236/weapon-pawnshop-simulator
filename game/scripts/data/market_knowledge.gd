class_name MarketKnowledge
extends RefCounted

# Player observations are separate from DayController.market (economic truth).
# TODO: radio/TV interactions may record reported hints, never auto-select judgements.
var observations: Dictionary = {}

func _init(classes: Array) -> void:
	for adventurer_class in classes:
		observations[adventurer_class] = {"class_popularity": null, "class_balance": null}

func record_hint(adventurer_class: String, axis: String, reported_value: String, source: String) -> void:
	if observations.has(adventurer_class) and axis in PlayerJudgement.MARKET_SECTIONS:
		observations[adventurer_class][axis] = {"reported_value": reported_value, "source": source}
