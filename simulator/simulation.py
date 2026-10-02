import csv
import random
from pathlib import Path

from .guest_generator import generate_guest
from .models import SimulationRecord
from .price_calculator import calculate_price
from .weapon_generator import generate_weapon


def run_simulation(config, count: int, seed: int):
    if count < 1:
        raise ValueError("count must be at least 1")
    rng = random.Random(seed)
    records = []
    power_states = list(config["price"]["market_power_values"])
    popularity_states = list(config["price"]["market_popularity_values"])
    # One market snapshot per run, matching a single in-game week.
    market = {name: (rng.choice(power_states), rng.choice(popularity_states)) for name in config["guest"]["classes"]}
    for number in range(1, count + 1):
        guest = generate_guest(rng, config)
        weapon, known = generate_weapon(rng, config, guest, market)
        class_power, class_popularity = market[weapon.item_class]
        price = calculate_price(config, guest, weapon, class_power, class_popularity)
        records.append(SimulationRecord(number, guest, weapon, known, class_power, class_popularity, price))
    return records


def export_csv(records, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [record.flat_dict() for record in records]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
