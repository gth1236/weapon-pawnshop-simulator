import csv
import json
import random
import statistics
from math import ceil
from pathlib import Path

from .config import weighted_choice
from .guest_generator import generate_guest
from .price_calculator import calculate_price
from .progression import customer_progression_distributions
from .weapon_generator import generate_weapon


def _percentile(values, fraction):
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = int(index), ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (index - lower)


def satisfaction_for_ratio(config, selling_purpose, offer_ratio):
    for band in config["reputation"]["satisfaction_thresholds"][selling_purpose]:
        maximum = band["max"]
        if maximum is None or offer_ratio < maximum or (band["inclusive"] and offer_ratio == maximum):
            return band["result"]
    raise ValueError(f"no satisfaction band for {selling_purpose} at {offer_ratio}")


def positive_reputation_multiplier(config, current_reputation):
    ranges = config["reputation"]["positive_decay"]["ranges"]
    eligible = [band for band in ranges if current_reputation >= band["minimum"]]
    return (eligible[-1] if eligible else ranges[0])["multiplier"]


def apply_reputation_delta(config, current_reputation, raw_delta):
    return raw_delta * positive_reputation_multiplier(config, current_reputation) if raw_delta > 0 else raw_delta


def completed_trade_reputation_delta(config, guest, offer_ratio):
    cfg = config["reputation"]
    satisfaction = satisfaction_for_ratio(config, guest.selling_purpose, offer_ratio)
    if satisfaction == "HUMILIATED" and guest.trade_attitude in cfg["non_humiliating_trade_attitude"]:
        satisfaction = "DISSATISFIED"
    return cfg["satisfaction_deltas"][satisfaction] + cfg["trade_attitude_deltas"].get(guest.trade_attitude, 0)


def simulate_fair_value_strategy(config, trials, seed, checkpoints=None):
    checkpoints = tuple(checkpoints or config["analysis"]["reputation_checkpoints"])
    if trials < 1 or not checkpoints or min(checkpoints) < 1:
        raise ValueError("trials and checkpoints must be positive")
    rng = random.Random(seed)
    results = {checkpoint: [] for checkpoint in checkpoints}
    power_states = list(config["price"]["market_balance_values"])
    popularity_states = list(config["price"]["market_popularity_values"])
    for _ in range(trials):
        reputation, completed = 0.0, 0
        market = {name: (rng.choice(power_states), rng.choice(popularity_states)) for name in config["guest"]["classes"]}
        while completed < max(checkpoints):
            guest = generate_guest(rng, config, reputation, completed)
            weapon, _ = generate_weapon(rng, config, guest, market)
            price = calculate_price(config, guest, weapon, *market[weapon.required_class])
            if price.appraised_price >= price.asking_price:
                completed += 1
                raw_delta = completed_trade_reputation_delta(config, guest, 1.0)
                reputation += apply_reputation_delta(config, reputation, raw_delta)
                if completed in results:
                    results[completed].append(reputation)
            else:
                raw_delta = config["reputation"]["failed_scam_delta"] if guest.trade_attitude == "SCAMMER" else float(weighted_choice(rng, config["reputation"]["no_purchase_deltas"]))
                reputation += apply_reputation_delta(config, reputation, raw_delta)
    reference = config["analysis"]["successful_trade_reference_per_week"]
    summaries = {}
    for checkpoint, values in results.items():
        median = statistics.median(values)
        summaries[checkpoint] = {
            "estimated_week": checkpoint / reference,
            "mean": statistics.fmean(values), "median": median,
            "minimum": min(values), "maximum": max(values),
            "p10": _percentile(values, .1), "p90": _percentile(values, .9),
            "distributions": customer_progression_distributions(config, median, checkpoint),
        }
    return summaries


def export_progression_csv(results, path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for trades, stats in results.items():
        row = {"successful_trades": trades, "estimated_week": stats["estimated_week"],
               "mean_reputation": stats["mean"], "median_reputation": stats["median"],
               "minimum_reputation": stats["minimum"], "maximum_reputation": stats["maximum"],
               "p10_reputation": stats["p10"], "p90_reputation": stats["p90"]}
        row.update({f"{name}_probabilities": json.dumps(weights, sort_keys=True) for name, weights in stats["distributions"].items()})
        rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0]); writer.writeheader(); writer.writerows(rows)


def format_reputation_report(results, trials, detailed_checkpoints):
    lines = [f"FAIR-VALUE PURCHASE REPUTATION ({trials:,} trials)", "Offer = true appraised price; reputation stays float internally; checkpoints count completed trades."]
    for trades, stats in results.items():
        lines.append(f"  {trades:>3} trades (~week {stats['estimated_week']:g}): mean={stats['mean']:.2f}, median={stats['median']:.2f}, min={stats['minimum']:.2f}, max={stats['maximum']:.2f}, p10={stats['p10']:.2f}, p90={stats['p90']:.2f}")
        if trades in detailed_checkpoints:
            for name, weights in stats["distributions"].items():
                lines.append(f"    {name}: " + ", ".join(f"{key}={value:.1%}" for key, value in weights.items()))
    return "\n".join(lines)
