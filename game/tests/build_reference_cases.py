"""Offline verification only. Godot never invokes Python at runtime.

Run from the repository root: python -B game/tests/build_reference_cases.py
"""
from dataclasses import asdict
from pathlib import Path
import json
import random
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from simulator.config import load_config
from simulator.guest_generator import generate_guest
from simulator.weapon_generator import generate_weapon
from simulator.price_calculator import calculate_price
from simulator.buyer_fit import calculate_buyer_fit
from simulator.economy_simulation import roll_market, create_shop_state, InventoryItem, process_buyer
from simulator.reputation_simulation import completed_trade_reputation_delta
from simulator.progression import customer_progression_distributions

config = load_config()
assert (ROOT / "config/balance.json").read_bytes() == (ROOT / "game/data/balance.json").read_bytes()
# Godot-only slice rule: special property contributes nothing. Apply it to an
# in-memory reference config only; never edit the source config or simulator.
config["price"]["special_values"] = {key: 0.0 for key in config["price"]["special_values"]}
cases = []
for index in range(128):
    rng = random.Random(index + 431)
    reputation, trades = index * 7, index * 4
    seller = generate_guest(rng, config, reputation, trades, 1)
    market = roll_market(rng, config)
    weapon, known = generate_weapon(rng, config, seller, market)
    price = calculate_price(config, seller, weapon, *market[weapon.item_class])
    buyer_data = asdict(generate_guest(rng, config, reputation, trades, 8))
    # Include incompatible and all quality levels, while giving sales broad coverage.
    if index % 5:
        buyer_data["guest_class"] = weapon.item_class
        buyer_data["preferred_weapon_type"] = weapon.item_type
    buyer_data["role"] = "BUY_FROM_SHOP"
    from simulator.models import Guest
    buyer = Guest(**buyer_data)
    fit = calculate_buyer_fit(config, buyer, weapon)
    state = create_shop_state(config)
    state.reputation = reputation
    state.inventory.append(InventoryItem(1, weapon, seller, 1, 1, price.asking_price,
                                         price.appraised_price, price.appraised_price, 0, known))
    sale = process_buyer(config, rng, state, buyer, market, 1)
    cases.append({"weapon": asdict(weapon), "seller": asdict(seller), "buyer": buyer_data,
                  "market": market, "price": asdict(price), "fit": asdict(fit) if fit else {},
                  "purchase_delta": completed_trade_reputation_delta(config, seller, price.asking_price / price.appraised_price),
                  "reputation": reputation, "sale": {"success": sale["transaction_type"] == "SELL_TO_CUSTOMER",
                  "cash": state.cash, "reputation": state.reputation, "profit": state.realized_profit},
                  "progression": customer_progression_distributions(config, reputation, trades), "trades": trades})
destination = ROOT / "game/tests/reference_cases.json"
destination.write_text(json.dumps(cases, separators=(",", ":")), encoding="utf-8")
print(f"Wrote {len(cases)} Python reference cases; runtime config matches source byte-for-byte.")
