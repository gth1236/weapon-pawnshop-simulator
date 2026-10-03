class_name WeaponTrueState
extends RefCounted

var values: Dictionary

func _init(source: Dictionary = {}) -> void:
	values = source.duplicate(true)
	for group in ["stat_lines", "amplification_lines"]:
		if values.has(group):
			for line in values[group]:
				line.make_read_only()
			values[group].make_read_only()
	values.make_read_only()
