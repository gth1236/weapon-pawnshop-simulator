from collections import Counter
from dataclasses import fields
from math import ceil

from .models import format_stat_line


def _distribution(label, values):
    counts, total = Counter(values), len(values)
    lines = [f"\n{label}:"]
    lines.extend(f"  {key}: {count:,} ({count / total:.2%})" for key, count in sorted(counts.items(), key=lambda x: str(x[0])))
    return "\n".join(lines)


def _percentile(sorted_values, percent):
    index = (len(sorted_values) - 1) * percent
    lower, upper = int(index), ceil(index)
    if lower == upper:
        return sorted_values[lower]
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * (index - lower)


def build_report(records):
    categories = {
        "guest_kindness": [x.guest.kindness for x in records], "guest_class": [x.guest.guest_class for x in records],
        "guest_level": [x.guest.level for x in records], "guest_power": [x.guest.power for x in records],
        "guest_tendency": [x.guest.tendency for x in records], "guest_achievement": [x.guest.achievement for x in records],
        "guest_title": [x.guest.title for x in records], "guest_knowledge": [x.guest.knowledge for x in records],
        "guest_purpose": [x.guest.purpose for x in records], "item_type": [x.weapon.item_type for x in records],
        "item_compatible": [x.weapon.compatible for x in records], "item_tier": [x.weapon.tier for x in records],
        "generation_mode": [x.weapon.generation_mode for x in records], "item_class": [x.weapon.item_class for x in records],
        "normal_stat_grade": [x.weapon.normal_stat_grade for x in records], "high_stat_grade": [x.weapon.high_stat_grade for x in records],
        "unique_stat_grade": [x.weapon.unique_stat_grade for x in records], "reinforcement_grade": [x.weapon.reinforcement_grade for x in records],
        "refining_level": [x.weapon.refining_level for x in records], "amplification_grade": [x.weapon.amplification_grade for x in records],
        "processing_load": [x.weapon.processing_load for x in records],
        "effective_processing_load": [x.weapon.effective_processing_load for x in records],
        "stability": [x.weapon.stability for x in records], "class_power": [x.class_power for x in records], "class_popularity": [x.class_popularity for x in records],
    }
    output = [f"SIMULATION SUMMARY ({len(records):,} records)"]
    output.extend(_distribution(key, values) for key, values in categories.items())
    for attribute in [x.name for x in fields(records[0].price)]:
        values = sorted(getattr(x.price, attribute) for x in records)
        output.append(f"\n{attribute}: mean={sum(values)/len(values):,.2f}, median={_percentile(values, .5):,.2f}, min={values[0]:,.2f}, max={values[-1]:,.2f}, p10={_percentile(values,.1):,.2f}, p25={_percentile(values,.25):,.2f}, p75={_percentile(values,.75):,.2f}, p90={_percentile(values,.9):,.2f}, p95={_percentile(values,.95):,.2f}, p99={_percentile(values,.99):,.2f}")
    return "\n".join(output)


def build_generation_mode_report(records):
    output = ["GENERATION MODE ANALYSIS"]
    for mode in ("OWN_CLASS", "FOREIGN_RAW", "FOREIGN_WORKED"):
        selected = [record for record in records if record.weapon.generation_mode == mode]
        if not selected:
            continue
        prices = sorted(record.price.appraised_price for record in selected)
        tiers = sorted(record.weapon.tier for record in selected)
        output.append(
            f"\n{mode}: count={len(selected):,} ({len(selected)/len(records):.2%}), "
            f"tier mean={sum(tiers)/len(tiers):.2f} median={_percentile(tiers,.5):.2f}, "
            f"price mean={sum(prices)/len(prices):,.2f} median={_percentile(prices,.5):,.2f} "
            f"p90={_percentile(prices,.9):,.2f} p99={_percentile(prices,.99):,.2f}, "
            f"stability mean={sum(x.weapon.stability for x in selected)/len(selected):.2f}, "
            f"processing load mean={sum(x.weapon.processing_load for x in selected)/len(selected):.2f}, "
            f"effective load mean={sum(x.weapon.effective_processing_load for x in selected)/len(selected):.2f}"
        )
        for label, getter in (
            ("stability", lambda x: x.weapon.stability_bracket),
            ("reinforcement", lambda x: x.weapon.reinforcement_grade),
            ("refining", lambda x: x.weapon.refining_level),
            ("amplification", lambda x: x.weapon.amplification_grade),
            ("processing_load", lambda x: x.weapon.processing_load),
            ("effective_processing_load", lambda x: x.weapon.effective_processing_load),
        ):
            output.append(_distribution(f"  {label}", [getter(record) for record in selected]))
    return "\n".join(output)


def format_samples(records, count=20):
    blocks = []
    for record in records[:count]:
        g, w, p = record.guest, record.weapon, record.price
        stats = "\n".join(f"  {format_stat_line(line)}" for line in (*w.stat_lines, *w.amplification_lines)) or "  (none)"
        blocks.append(f"""Customer #{record.record_id:03d}
Class: {g.guest_class}\nLevel: {g.level}\nPower: {g.power}\nTendency: {g.tendency}\nAchievement: {g.achievement}\nTitle: {g.title}\nMarket Knowledge: {g.knowledge}\nPurpose: {g.purpose}
Weapon: Tier {w.tier} {w.item_type}\nItem Class: {w.item_class}\nCompatible: {'Yes' if w.compatible else 'No'}\nGeneration Mode: {w.generation_mode}
True Stats:\n{stats}
Reinforcement: {w.reinforcement_grade}\nRefining: +{w.refining_level}\nAmplification: {w.amplification_grade}\nProcessing Load: {w.processing_load} + popularity {w.popularity_load} + class power {w.class_power_load} = {w.effective_processing_load}\nStability: {w.stability}%
Base Price: {p.base_price:,} G\nAppraised Price: {p.appraised_price:,} G\nCustomer Asking Price: {p.asking_price:,} G
Internal Grades: Normal={w.normal_stat_grade}, High={w.high_stat_grade}, Special={w.special_stat_grade}, Unique={w.unique_stat_grade}""")
    return "\n\n".join(blocks)
