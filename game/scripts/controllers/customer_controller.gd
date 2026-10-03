class_name CustomerController
extends RefCounted

static func generate(config: Dictionary, rng: RandomNumberGenerator, state: ShopState, role: String, number: int) -> Dictionary:
	var cfg = config.guest
	var rep = config.progression.reputation
	var trades = config.progression.trade_count
	var adventurer_class = Balance.pick(rng, cfg.classes)
	var level_band = Balance.weighted(rng, ProgressionService.interpolate(rep.adventurer_level, state.reputation))
	return {"name": "여행자 %02d" % number, "role": role, "adventurer_class": adventurer_class,
		"adventurer_level": Balance.roll_range(rng, level_band),
		"trade_attitude": Balance.weighted(rng, ProgressionService.interpolate(rep.trade_attitude, state.reputation)),
		"adventurer_power": Balance.weighted(rng, ProgressionService.interpolate(rep.adventurer_power, state.reputation)),
		"equipment_tendency": Balance.pick(rng, cfg.tendencies),
		"achievement_rank": Balance.weighted(rng, ProgressionService.interpolate(trades.achievement_rank, state.trade_count)),
		"title_rank": Balance.weighted(rng, ProgressionService.interpolate(trades.title_rank, state.trade_count)),
		"market_knowledge": Balance.pick(rng, cfg.market_knowledge), "selling_purpose": Balance.pick(rng, cfg.purposes),
		"preferred_weapon_type": Balance.pick(rng, config.weapon.class_weapon_pools[adventurer_class]) if role == "BUY_FROM_SHOP" else null}
