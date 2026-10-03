class_name SellerNegotiation
extends RefCounted

var current_asking: int
var last_offer = -1
var remaining_offer_attempts: int
var status = "OPEN"

func _init(config: Dictionary, guest: Dictionary, asking: int) -> void:
	current_asking = asking
	remaining_offer_attempts = int(config.seller_negotiation.attempts_by_selling_purpose[guest.selling_purpose])

# The spec defines 1/2/2 total attempts and immediate acceptance at asking.
# Counter reduction is a deterministic demo policy, not a finalized Python rule.
func evaluate(config: Dictionary, guest: Dictionary, offer: int) -> String:
	if status != "OPEN":
		return status
	last_offer = offer
	remaining_offer_attempts -= 1
	if offer >= current_asking:
		status = "ACCEPTED"
	elif remaining_offer_attempts <= 0:
		status = "FAILED"
	else:
		var policy = config.seller_negotiation
		if guest.market_knowledge not in policy.hold_asking_market_knowledge and guest.trade_attitude not in policy.hold_asking_trade_attitude:
			current_asking = mini(current_asking, maxi(offer + 1, Balance.money(current_asking * (1.0 - policy.counter_discount))))
	return status
