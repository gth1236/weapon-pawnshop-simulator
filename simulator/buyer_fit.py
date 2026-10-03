"""Temporary, config-driven buyer-to-inventory fit model."""
from dataclasses import dataclass


@dataclass(frozen=True)
class BuyerFit:
    score: float
    components: dict[str, float]
    tier_fit: float
    preference_match: bool


def cumulative_quality_fit(value, probabilities, order):
    index = order.index(value)
    return max(0.0, min(1.0, sum(probabilities.get(name, 0.0) for name in order[:index + 1])))


def _level_bracket(config, adventurer_level):
    return next(name for name in config["guest"]["tier_by_adventurer_level"] if int(name.split("-")[0]) <= adventurer_level <= int(name.split("-")[1]))


def _refining_probabilities(config, achievement_rank):
    zero = config["economy"]["buyer_fit"]["refining_zero_probability"]
    exact = {level: 0.0 for level in range(11)}; exact[0] = zero
    for band, probability in config["guest"]["refining_band_by_achievement_rank"][achievement_rank].items():
        low, high = map(int, band.split("-"))
        for level in range(low, high + 1):
            exact[level] += (1 - zero) * probability / (high - low + 1)
    return exact


def _amplification_probabilities(config, title_rank):
    count = config["guest"]["amplification_count_by_title_rank"][title_rank]
    quality = config["weapon"]["amplification_quality_weights"]
    result = {name: 0.0 for name in config["economy"]["buyer_fit"]["quality_order"]["amplification"]}
    result["UNAPPLIED"], result["ZERO_LINE"] = count["UNAPPLIED"], count["ZERO_LINE"]
    for prefix in ("ONE_LINE", "TWO_LINE", "THREE_LINE"):
        for grade in ("LOW", "HIGH"):
            result[f"{prefix}_{grade}"] = count[prefix] * quality[grade]
    return result


def calculate_buyer_fit(config, buyer, weapon):
    if weapon.item_type not in config["weapon"]["class_weapon_pools"][buyer.adventurer_class]:
        return None
    fit_cfg = config["economy"]["buyer_fit"]
    orders, weights = fit_cfg["quality_order"], fit_cfg["weights"]
    tier_table = config["guest"]["tier_by_adventurer_level"][_level_bracket(config, buyer.adventurer_level)]
    tier_fit = tier_table.get(str(weapon.tier), 0.0) / max(tier_table.values())
    stat_probs = config["guest"]["stat_grade_by_adventurer_power"][buyer.adventurer_power]
    high_probs = {("LOW" if key == "MIXED" else key): value for key, value in stat_probs.items()}
    reinforce_probs = dict(config["guest"]["reinforce_by_equipment_tendency"][buyer.equipment_tendency]); reinforce_probs["UNENHANCED"] = 0.0
    components = {
        "tier": tier_fit,
        "weapon_preference": 1.0 if weapon.item_type == buyer.preferred_weapon_type else fit_cfg["non_preferred_weapon_fit"],
        "normal_stat": cumulative_quality_fit(weapon.normal_stat_grade, stat_probs, orders["normal_stat"]),
        "high_stat": cumulative_quality_fit(weapon.high_stat_grade, high_probs, orders["high_stat"]),
        "reinforcement": cumulative_quality_fit(weapon.reinforcement_grade, reinforce_probs, orders["reinforcement"]),
        "refining": sum(probability for level, probability in _refining_probabilities(config, buyer.achievement_rank).items() if level <= weapon.refining_level),
        "amplification": cumulative_quality_fit(weapon.amplification_grade, _amplification_probabilities(config, buyer.title_rank), orders["amplification"]),
        "unique_stat": cumulative_quality_fit(weapon.unique_stat_grade, config["guest"]["unique_by_equipment_tendency"][buyer.equipment_tendency], orders["unique_stat"]),
    }
    score = sum(weights[name] * value for name, value in components.items())
    return BuyerFit(max(0.0, min(100.0, score)), components, tier_fit, weapon.item_type == buyer.preferred_weapon_type)


def interest_band(config, score):
    return next((band for band in config["economy"]["interest_bands"] if score >= band["minimum"]), None)


def choose_inventory_item(config, rng, buyer, inventory):
    scored = [(item, calculate_buyer_fit(config, buyer, item.weapon)) for item in inventory]
    scored = [(item, fit) for item, fit in scored if fit is not None]
    if not scored:
        return None, None, "NO_COMPATIBLE_ITEM"
    best_score = max(fit.score for _, fit in scored)
    best = [(item, fit) for item, fit in scored if abs(fit.score - best_score) < 1e-9]
    item, fit = rng.choice(best)
    if interest_band(config, fit.score) is None:
        return item, fit, "NO_INTEREST"
    return item, fit, None
