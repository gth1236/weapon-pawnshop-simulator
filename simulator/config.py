import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "balance.json"


class ConfigError(ValueError):
    pass


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    validate_config(config)
    return config


def validate_weights(weights: dict[str, float], name: str) -> None:
    if not weights:
        raise ConfigError(f"{name}: probability table is empty")
    if any(not isinstance(value, (int, float)) or value < 0 for value in weights.values()):
        raise ConfigError(f"{name}: weights must be non-negative numbers")
    if abs(sum(weights.values()) - 1.0) > 1e-8:
        raise ConfigError(f"{name}: weights sum to {sum(weights.values())}, expected 1.0")


def validate_config(config: dict[str, Any]) -> None:
    guest = config["guest"]
    weapon = config["weapon"]
    for group in ["tier_by_level", "stat_grade_by_power", "unique_by_tendency", "reinforce_by_tendency", "refining_band_by_achievement", "amplification_count_by_title"]:
        for key, table in guest[group].items():
            validate_weights(table, f"guest.{group}.{key}")
    for name in ["compatibility_weights", "foreign_mode_weights", "foreign_raw_normal_stat_weights", "foreign_raw_high_stat_weights", "foreign_raw_unique_weights", "special_stat_weights", "amplification_quality_weights"]:
        validate_weights(weapon[name], f"weapon.{name}")
    for key, table in weapon["stability_by_processing_load"].items():
        validate_weights(table, f"weapon.stability_by_processing_load.{key}")
    validate_weights(config["reputation"]["no_purchase_deltas"], "reputation.no_purchase_deltas")
    validate_weights(config["economy"]["visitor_roles"], "economy.visitor_roles")
    if sum(config["economy"]["buyer_fit"]["weights"].values()) != 100:
        raise ConfigError("economy.buyer_fit.weights must sum to 100")
    for axis, variables in config["progression"].items():
        if axis == "temporary":
            continue
        for variable, progression in variables.items():
            anchors = progression["anchors"]
            values = [anchor["value"] for anchor in anchors]
            if values != sorted(set(values)):
                raise ConfigError(f"progression.{axis}.{variable}: anchors must be unique and increasing")
            expected_keys = set(anchors[0]["weights"])
            for anchor in anchors:
                if set(anchor["weights"]) != expected_keys:
                    raise ConfigError(f"progression.{axis}.{variable}: category keys differ between anchors")
                validate_weights(anchor["weights"], f"progression.{axis}.{variable}.{anchor['value']}")


def weighted_choice(rng, weights: dict[str, float]) -> str:
    point = rng.random()
    cumulative = 0.0
    for choice, weight in weights.items():
        cumulative += weight
        if point < cumulative:
            return choice
    return next(reversed(weights))
