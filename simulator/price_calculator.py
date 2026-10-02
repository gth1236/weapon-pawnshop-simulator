from .models import PriceResult


def calculate_price(config, guest, weapon, class_power, class_popularity):
    cfg = config["price"]
    refining = cfg["refining_values"][str(weapon.refining_level)]
    effective = refining * (0.4 * cfg["normal_coefficients"][weapon.normal_stat_grade] + 0.6 * cfg["high_coefficients"][weapon.high_stat_grade])
    modifier = sum((
        cfg["market_power_values"][class_power], cfg["market_popularity_values"][class_popularity],
        cfg["normal_values"][weapon.normal_stat_grade], cfg["high_values"][weapon.high_stat_grade],
        cfg["special_values"][weapon.special_stat_grade], cfg["unique_values"][weapon.unique_stat_grade],
        cfg["reinforce_values"][weapon.reinforcement_grade], cfg["amplification_values"][weapon.amplification_grade], effective,
    ))
    multiplier_set = cfg["stability_multipliers"]["at_least_2" if modifier >= 2 else "below_2"]
    threshold = next(str(x) for x in (100, 80, 60, 40, 20, 0) if weapon.stability >= x)
    stability_multiplier = multiplier_set[threshold]
    base = cfg["base_prices"][str(weapon.tier)]
    appraised = round(max(base * (1 + modifier) * stability_multiplier, base * cfg["minimum_price_ratio"]))
    normal_asking = appraised * cfg["purpose_multipliers"][guest.purpose] * cfg["knowledge_multipliers"][guest.knowledge]
    asking = max(normal_asking, appraised * cfg["scammer_minimum_multiplier"]) if guest.kindness == "SCAMMER" else normal_asking
    return PriceResult(base, modifier, effective, stability_multiplier, appraised, round(asking))
