import copy
import random
import unittest
from dataclasses import asdict, replace

from simulator.appraisal import PROPERTY_FIELDS
from simulator.buyer_fit import calculate_buyer_fit
from simulator.config import load_config
from simulator.guest_generator import generate_guest
from simulator.price_calculator import calculate_price
from simulator.weapon_generator import generate_weapon


class MarketRuleTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config()
        self.guest = generate_guest(random.Random(4), self.config)
        self.market = {name: ("NORMAL", "NORMAL") for name in self.config["guest"]["classes"]}
        self.weapon, self.known = generate_weapon(random.Random(7), self.config, self.guest, self.market)

    def test_retired_property_absent_from_schema_and_config(self):
        self.assertFalse(any("special" in key for key in asdict(self.weapon)))
        self.assertFalse(any("special" in key for key in PROPERTY_FIELDS))
        for group in (self.config["price"], self.config["weapon"], self.config["appraisal"]["property_tools"]):
            self.assertFalse(any("special" in key for key in group))
        self.assertNotIn("market_processing_load", self.config["weapon"])
        self.assertNotIn("popularity_load", asdict(self.weapon))

    def test_every_weapon_uses_buyer_pool_not_origin_class(self):
        pools = self.config["weapon"]["class_weapon_pools"]
        types = set().union(*map(set, pools.values()))
        for adventurer_class, pool in pools.items():
            buyer = replace(self.guest, adventurer_class=adventurer_class, role="BUY_FROM_SHOP")
            for item_type in types:
                weapon = replace(self.weapon, item_type=item_type, required_class="WARRIOR")
                self.assertEqual(calculate_buyer_fit(self.config, buyer, weapon) is not None, item_type in pool)

    def test_staff_and_future_shared_weapon(self):
        for name in ("MAGE", "CLERIC"):
            buyer = replace(self.guest, adventurer_class=name)
            self.assertIsNotNone(calculate_buyer_fit(self.config, buyer, replace(self.weapon, item_type="staff")))
        config = copy.deepcopy(self.config)
        config["weapon"]["class_weapon_pools"]["CLERIC"].append("bow")
        buyer = replace(self.guest, adventurer_class="CLERIC")
        self.assertIsNotNone(calculate_buyer_fit(config, buyer, replace(self.weapon, item_type="bow")))

    def test_market_contributions_and_full_price_formula(self):
        price = self.config["price"]
        self.assertEqual(price["market_balance_values"], {"WEAK": -.2, "NORMAL": 0, "STRONG": .2})
        self.assertEqual(price["market_popularity_values"], {"UNPOPULAR": -.2, "NORMAL": 0, "POPULAR": .2})
        # Stable fixture: all non-market contributions total 1.0, stability 60 => multiplier 1.
        weapon = replace(self.weapon, tier=1, normal_stat_grade="ADEQUATE", high_stat_grade="ADEQUATE",
                         unique_stat_grade="NONE", reinforcement_grade="GOOD", refining_level=0,
                         amplification_grade="TWO_LINE_LOW", stability=60)
        for balance, b in price["market_balance_values"].items():
            for popularity, p in price["market_popularity_values"].items():
                result = calculate_price(self.config, self.guest, weapon, balance, popularity)
                self.assertAlmostEqual(result.item_value_modifier, 1 + b + p)
                self.assertEqual(result.true_appraised_price, round(1000 * (2 + b + p)))

    def test_normal_default_role_probability(self):
        self.assertEqual(self.config["economy"]["visitor_roles"], {"SELL_TO_SHOP": .55, "BUY_FROM_SHOP": .45})


if __name__ == "__main__":
    unittest.main()
