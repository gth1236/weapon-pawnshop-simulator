class_name WeaponData
extends RefCounted

var truth: WeaponTrueState
var known: WeaponKnownState
var seller: Dictionary
var final_purchase_price = 0
var current_appraised_price = 0
var purchase_day = 1
var judgement = PlayerJudgement.new()

func _init(actual: WeaponTrueState, knowledge: WeaponKnownState, owner: Dictionary) -> void:
	truth = actual
	known = knowledge
	seller = owner.duplicate(true)
