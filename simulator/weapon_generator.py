from .config import weighted_choice
from .models import StatLine, WeaponTrueState
from .appraisal import create_player_knowledge, isolated_appraisal_rng


def _bracket(value: int) -> str:
    if value == 100:
        return "STABILITY_100"
    for floor in (80, 60, 40, 20, 0):
        if value >= floor:
            return f"STABILITY_{floor}_PLUS" if floor else "STABILITY_BELOW_20"
    raise AssertionError("unreachable")


def _table_for_value(tables, value):
    for range_name, table in tables.items():
        low, high = map(int, range_name.split("-"))
        if low <= value <= high:
            return table
    raise ValueError(f"no configured range contains {value}")


def _numeric_line(rng, stat_id, category, grade, reference, ranges, relevant=True):
    low, high = ranges[grade]
    return StatLine(stat_id, category, grade, round(reference * rng.uniform(low, high)), "FLAT", relevant)


def _stat_lines(rng, cfg, target_class, tier, normal_grade, high_grade, unique_grade):
    profile = cfg["class_profiles"][target_class]
    lines = []
    if normal_grade != "NONE":
        lines.append(_numeric_line(rng, profile[0], "NORMAL", normal_grade, cfg["normal_reference"][str(tier)], cfg["normal_ranges"]))
        if normal_grade == "MIXED":
            other = rng.choice([x for x in cfg["normal_stat_ids"] if x != profile[0]])
            lines.append(_numeric_line(rng, other, "NORMAL", normal_grade, cfg["normal_reference"][str(tier)], cfg["normal_ranges"], False))
    if high_grade != "NONE":
        lines.append(_numeric_line(rng, profile[1], "HIGH", high_grade, cfg["high_reference"][str(tier)], cfg["high_ranges"]))
    elif rng.random() < cfg["none_high_opposite_chance"]:
        opposite = "magic_power" if profile[1] == "attack" else "attack"
        low, high = cfg["irrelevant_high_range"]
        lines.append(StatLine(opposite, "HIGH", "NONE", round(cfg["high_reference"][str(tier)] * rng.uniform(low, high)), "FLAT", False))
    if unique_grade != "NONE":
        stat_id = rng.choice(list(cfg["unique_ranges"]))
        low, high = cfg["unique_ranges"][stat_id][unique_grade]
        lines.append(StatLine(stat_id, "UNIQUE", unique_grade, round(rng.uniform(low, high), 1), "PERCENT", True))
    return lines


def generate_weapon(rng, config, guest, market_state):
    guest_cfg, cfg, numeric = config["guest"], config["weapon"], config["numeric_stats"]
    compatible = weighted_choice(rng, cfg["compatibility_weights"]) == "compatible"
    all_types = {weapon for pool in cfg["class_weapon_pools"].values() for weapon in pool}
    if compatible:
        generation_mode = "OWN_CLASS"
        item_type, item_class = rng.choice(cfg["class_weapon_pools"][guest.guest_class]), guest.guest_class
    else:
        generation_mode = weighted_choice(rng, cfg["foreign_mode_weights"])
        item_type = rng.choice(sorted(all_types - set(cfg["class_weapon_pools"][guest.guest_class])))
        item_class = rng.choice([name for name, pool in cfg["class_weapon_pools"].items() if item_type in pool])

    bracket = next(key for key in guest_cfg["tier_by_level"] if int(key.split("-")[0]) <= guest.level <= int(key.split("-")[1]))
    tier = int(weighted_choice(rng, guest_cfg["tier_by_level"][bracket]))
    if generation_mode == "FOREIGN_RAW":
        normal_grade = weighted_choice(rng, cfg["foreign_raw_normal_stat_weights"])
        high_grade = weighted_choice(rng, cfg["foreign_raw_high_stat_weights"])
        unique = weighted_choice(rng, cfg["foreign_raw_unique_weights"])
        reinforce, refining, amp_count, amplification = "UNENHANCED", 0, "UNAPPLIED", "UNAPPLIED"
        amp_lines = []
    else:
        normal_grade = weighted_choice(rng, guest_cfg["stat_grade_by_power"][guest.power])
        high_roll = weighted_choice(rng, guest_cfg["stat_grade_by_power"][guest.power])
        high_grade = {"MIXED": "LOW"}.get(high_roll, high_roll)
        unique = weighted_choice(rng, guest_cfg["unique_by_tendency"][guest.tendency])
        reinforce = weighted_choice(rng, guest_cfg["reinforce_by_tendency"][guest.tendency])
        band = weighted_choice(rng, guest_cfg["refining_band_by_achievement"][guest.achievement])
        refining = rng.randint(*map(int, band.split("-")))
        amp_count = weighted_choice(rng, guest_cfg["amplification_count_by_title"][guest.title])
        quality = weighted_choice(rng, cfg["amplification_quality_weights"])
        amplification = amp_count if amp_count in ("UNAPPLIED", "ZERO_LINE") else f"{amp_count}_{quality}"
        amp_lines = []
        count_words = {"ONE_LINE": 1, "TWO_LINE": 2, "THREE_LINE": 3}
        for _ in range(count_words.get(amp_count, 0)):
            stat_id = rng.choice(numeric["normal_stat_ids"])
            low, high = numeric["amplification_ranges"][quality]
            value = round(numeric["normal_reference"][str(tier)] * rng.uniform(low, high))
            amp_lines.append(StatLine(stat_id, "AMPLIFICATION", quality, value, "FLAT", stat_id == numeric["class_profiles"][item_class][0]))

    load_cfg = cfg["processing_load"]
    processing_load = (load_cfg["reinforcement"][reinforce] + refining * load_cfg["refining_level_multiplier"] + load_cfg["amplification"][amp_count])
    class_power, class_popularity = market_state[item_class]
    market_load = cfg["market_processing_load"]
    popularity_load = market_load["class_popularity"][class_popularity]
    class_power_load = market_load["class_power"][class_power]
    effective_processing_load = processing_load + popularity_load + class_power_load
    stability_table = _table_for_value(cfg["stability_by_processing_load"], effective_processing_load)
    stability_range = weighted_choice(rng, stability_table)
    stability = rng.randint(*map(int, stability_range.split("-")))
    weapon = WeaponTrueState(
        item_type, item_class, compatible, generation_mode, tier, normal_grade, high_grade,
        weighted_choice(rng, cfg["special_stat_weights"]), unique, reinforce, refining,
        amplification, processing_load, popularity_load, class_power_load, effective_processing_load,
        stability, _bracket(stability),
        tuple(_stat_lines(rng, numeric, item_class, tier, normal_grade, high_grade, unique)), tuple(amp_lines),
    )
    return weapon, create_player_knowledge(config, weapon, isolated_appraisal_rng(rng))
