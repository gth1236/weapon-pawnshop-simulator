import json
import math
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
    for group in ["tier_by_adventurer_level", "stat_grade_by_adventurer_power", "unique_by_equipment_tendency", "reinforce_by_equipment_tendency", "refining_band_by_achievement_rank", "amplification_count_by_title_rank"]:
        for key, table in guest[group].items():
            validate_weights(table, f"guest.{group}.{key}")
    for name in ["compatibility_weights", "foreign_mode_weights", "foreign_raw_normal_stat_weights", "foreign_raw_high_stat_weights", "foreign_raw_unique_weights", "amplification_quality_weights"]:
        validate_weights(weapon[name], f"weapon.{name}")
    for key, table in weapon["stability_by_processing_load"].items():
        validate_weights(table, f"weapon.stability_by_processing_load.{key}")
    validate_weights(config["reputation"]["no_purchase_deltas"], "reputation.no_purchase_deltas")
    validate_weights(config["economy"]["visitor_roles"], "economy.visitor_roles")
    if sum(config["economy"]["buyer_fit"]["weights"].values()) != 100:
        raise ConfigError("economy.buyer_fit.weights must sum to 100")
    economy = config["economy"]
    for key in ("starting_cash", "starting_debt"):
        value=economy[key]
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
            raise ConfigError(f"economy.{key} must be finite and non-negative")
    for key in ("weeks","trials","initial_inventory_capacity","maximum_inventory_capacity"):
        if type(economy[key]) is not int or economy[key] < 1:
            raise ConfigError(f"economy.{key} must be a positive integer")
    if economy["initial_inventory_capacity"] > economy["maximum_inventory_capacity"]:
        raise ConfigError("inventory initial capacity exceeds maximum")
    cost=economy["inventory_expansion_cost"]
    if not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost < 0:
        raise ConfigError("inventory expansion cost must be finite and non-negative")
    scrap_ratio=economy["scrap_purchase_price_ratio"]
    if not isinstance(scrap_ratio,(int,float)) or not math.isfinite(scrap_ratio) or not 0 <= scrap_ratio <= 1:
        raise ConfigError("scrap purchase price ratio must be between 0 and 1")
    for cost in economy["weekly_operating_cost"].values():
        if not isinstance(cost,(int,float)) or not math.isfinite(cost) or cost < 0:
            raise ConfigError("weekly operating costs must be finite and non-negative")
    policies=config["simulation_policies"]
    if policies["inventory_expansion"] not in ("EXPAND_IF_BLOCKED_AND_AFFORDABLE", "MANUAL_ONLY"):
        raise ConfigError("unsupported inventory expansion policy")
    if policies["cash_deficit"] != "ALLOW_NEGATIVE_CASH_CONTINUE_TRADING":
        raise ConfigError("unsupported cash deficit rule")
    if policies["purchase"] != "BUY_IF_ASK_AT_MOST_TRUE_APPRAISAL" or policies["sale"] != "ACCEPT_IF_OFFER_MEETS_APPRAISAL_AND_COST_FLOOR":
        raise ConfigError("unsupported automatic trade policy")
    if policies["scrap"] != "MANUAL_ONLY":
        raise ConfigError("automatic scrap policies are not implemented")
    if economy["days_per_week"] != 7 or economy["weeks_per_month"] != 4:
        raise ConfigError("time unit must be 7 days/week and 4 weeks/month")
    repayment = economy["debt_repayment"]
    if type(repayment["enabled"]) is not bool:
        raise ConfigError("debt repayment enabled must be a boolean")
    if not repayment["enabled"] and economy["starting_debt"] != 0:
        raise ConfigError("current debt-disabled rules require starting_debt = 0")
    amount = repayment["mandatory_weekly_payment"]
    if not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
        raise ConfigError("mandatory weekly debt payment must be finite and non-negative")
    if set(repayment["policies"]) != {"mandatory_only", "moderate", "aggressive"}:
        raise ConfigError("debt repayment policies must include mandatory_only, moderate and aggressive")
    if repayment["default_policy"] not in repayment["policies"]:
        raise ConfigError("unknown default debt repayment policy")
    for name, policy in repayment["policies"].items():
        reserve, fraction = policy["reserve_threshold"], policy["excess_repayment_fraction"]
        if not isinstance(reserve, (int, float)) or not math.isfinite(reserve) or reserve < 0:
            raise ConfigError(f"{name}: reserve must be finite and non-negative")
        if not isinstance(fraction, (int, float)) or not math.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ConfigError(f"{name}: repayment fraction must be between 0 and 1")
    if repayment["policies"]["mandatory_only"]["excess_repayment_fraction"] != 0:
        raise ConfigError("mandatory_only must have zero optional repayment fraction")
    appraisal=config["appraisal"]
    probability=appraisal["unassisted_correct_probability"]
    if not isinstance(probability,(int,float)) or not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ConfigError("appraisal correct probability must be between 0 and 1")
    from .appraisal import PROPERTY_FIELDS, property_domain
    if set(appraisal["property_tools"]) != set(PROPERTY_FIELDS):
        raise ConfigError("appraisal tool mapping must cover every hidden property")
    for name,tool in appraisal["property_tools"].items():
        if not isinstance(tool,str) or not tool.strip() or len(property_domain(config,name)) < 2:
            raise ConfigError(f"{name}: tool identifier and at least two possible values required")
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
