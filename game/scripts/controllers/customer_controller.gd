class_name CustomerController
extends RefCounted

static func generate(config: Dictionary, rng: RandomNumberGenerator, state: ShopState, role: String, number: int) -> Dictionary:
	var cfg = config.guest
	var rep = config.progression.reputation
	var trades = config.progression.trade_count
	var guest_class = Balance.pick(rng, cfg.classes)
	var level_band = Balance.weighted(rng, ProgressionService.interpolate(rep.guest_level, state.reputation))
	return {"name": "여행자 %02d" % number, "role": role, "guest_class": guest_class,
		"level": Balance.roll_range(rng, level_band),
		"kindness": Balance.weighted(rng, ProgressionService.interpolate(rep.guest_kindness, state.reputation)),
		"power": Balance.weighted(rng, ProgressionService.interpolate(rep.guest_power, state.reputation)),
		"tendency": Balance.pick(rng, cfg.tendencies),
		"achievement": Balance.weighted(rng, ProgressionService.interpolate(trades.guest_achievement, state.trade_count)),
		"title": Balance.weighted(rng, ProgressionService.interpolate(trades.guest_title, state.trade_count)),
		"knowledge": Balance.pick(rng, cfg.knowledge), "purpose": Balance.pick(rng, cfg.purposes),
		"preferred_weapon_type": Balance.pick(rng, config.weapon.class_weapon_pools[guest_class]) if role == "BUY_FROM_SHOP" else null}
