import copy
import random
import unittest
from dataclasses import replace

from simulator.config import ConfigError, load_config, validate_config
from simulator.buyer_fit import calculate_buyer_fit, choose_inventory_item, interest_band
from simulator.economy_simulation import InventoryItem, revalue_item, roll_market, run_economy_trial
from simulator.guest_generator import generate_guest
from simulator.models import Guest, WeaponTrueState
from simulator.price_calculator import calculate_price
from simulator.progression import interpolated_weights
from simulator.reputation_simulation import apply_reputation_delta, satisfaction_for_ratio, simulate_fair_value_strategy
from simulator.simulation import run_simulation


class SimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()

    def test_seed_is_reproducible(self):
        first = [x.flat_dict() for x in run_simulation(self.config, 30, 42)]
        second = [x.flat_dict() for x in run_simulation(self.config, 30, 42)]
        self.assertEqual(first, second)

    def test_probability_validation_rejects_bad_sum(self):
        config = copy.deepcopy(self.config)
        config["weapon"]["compatibility_weights"]["compatible"] = 0.7
        with self.assertRaises(ConfigError):
            validate_config(config)

    def test_required_uniform_rolls_and_compatibility_are_sane(self):
        records = run_simulation(self.config, 30_000, 77)
        for getter, expected in [
            (lambda x: x.guest.guest_class, 1 / 6), (lambda x: x.guest.tendency, 1 / 4),
            (lambda x: x.guest.knowledge, 1 / 3), (lambda x: x.guest.purpose, 1 / 3),
        ]:
            counts = {}
            for record in records:
                counts[getter(record)] = counts.get(getter(record), 0) + 1
            self.assertTrue(all(abs(count / len(records) - expected) < 0.02 for count in counts.values()))
        compatible = sum(record.weapon.compatible for record in records) / len(records)
        self.assertAlmostEqual(compatible, 0.8, delta=0.02)

    def test_price_formula_and_floor(self):
        guest = Guest("NORMAL", "WARRIOR", 1, "NORMAL", "VERY_CARELESS", "NONE", "NONE", "NONE", "GREEDY_SELLING")
        weapon = WeaponTrueState(
            item_type="axe", item_class="WARRIOR", compatible=True, generation_mode="OWN_CLASS", tier=1,
            normal_stat_grade="NONE", high_stat_grade="NONE", special_stat_grade="NONE_RELEVANT",
            unique_stat_grade="NONE", reinforcement_grade="BAD", refining_level=1,
            amplification_grade="ZERO_LINE", processing_load=1, popularity_load=0,
            class_power_load=0, effective_processing_load=1, stability=0,
            stability_bracket="STABILITY_BELOW_20", stat_lines=(), amplification_lines=(),
        )
        result = calculate_price(self.config, guest, weapon, "WEAK", "UNPOPULAR")
        self.assertEqual(result.appraised_price, 100)
        self.assertEqual(result.asking_price, 100)

    def test_stability_depends_on_processing_load_table(self):
        config = copy.deepcopy(self.config)
        for table in config["weapon"]["stability_by_processing_load"].values():
            table.update({key: 0.0 for key in table})
            table["100-100"] = 1.0
        records = run_simulation(config, 100, 9)
        self.assertTrue(all(record.weapon.stability == 100 for record in records))
        self.assertTrue(all(record.weapon.effective_processing_load >= record.weapon.processing_load for record in records))

    def test_satisfaction_boundaries_match_spec(self):
        self.assertEqual(satisfaction_for_ratio(self.config, "EMERGENCY_CASH", 0.4), "SATISFIED")
        self.assertEqual(satisfaction_for_ratio(self.config, "UPGRADE_PURCHASE", 0.5), "DISSATISFIED")
        self.assertEqual(satisfaction_for_ratio(self.config, "GREEDY_SELLING", 1.0), "SATISFIED")

    def test_reputation_strategy_is_seeded_and_has_checkpoints(self):
        first = simulate_fair_value_strategy(self.config, 20, 123)
        second = simulate_fair_value_strategy(self.config, 20, 123)
        self.assertEqual(first, second)
        self.assertEqual(set(first), {10, 25, 30, 50, 60, 100, 120, 200, 240})

    def test_reputation_decay_only_reduces_positive_changes(self):
        self.assertEqual(apply_reputation_delta(self.config, 0, 6), 6)
        self.assertEqual(apply_reputation_delta(self.config, 300, 6), 3)
        self.assertAlmostEqual(apply_reputation_delta(self.config, 900, 6), 1.2)
        self.assertEqual(apply_reputation_delta(self.config, 900, -5), -5)

    def test_progression_quality_is_monotonic_and_keeps_low_categories(self):
        score_tables = {
            "guest_level": {"1-10": 0, "11-30": 1, "31-50": 2, "51-70": 3, "71-90": 4, "91-120": 5},
            "guest_power": {"VERY_LOW": 0, "LOW": 1, "NORMAL": 2, "HIGH": 3, "VERY_HIGH": 4},
        }
        for name, scores in score_tables.items():
            table = self.config["progression"]["reputation"][name]
            qualities = []
            for value in (0, 100, 250, 500, 800):
                weights = interpolated_weights(table, value)
                qualities.append(sum(weights[key] * scores[key] for key in scores))
                self.assertTrue(all(weight > 0 for weight in weights.values()))
            self.assertEqual(qualities, sorted(qualities))
        kindness = self.config["progression"]["reputation"]["guest_kindness"]
        low, high = interpolated_weights(kindness, 0), interpolated_weights(kindness, 800)
        self.assertGreater(high["GENEROUS"], low["GENEROUS"])
        self.assertLessEqual(high["RUDE"] + high["SCAMMER"], low["RUDE"] + low["SCAMMER"])

    def test_trade_progression_quality_is_monotonic(self):
        scores = {"guest_title": {"NONE": 0, "C": 1, "B": 2, "A": 3, "S": 4},
                  "guest_achievement": {"NONE": 0, "SOME": 1, "GOOD": 2, "VERY_GOOD": 3}}
        for name, mapping in scores.items():
            table = self.config["progression"]["trade_count"][name]
            values = [sum(interpolated_weights(table, count)[key] * score for key, score in mapping.items()) for count in (0, 25, 50, 100, 200, 400)]
            self.assertEqual(values, sorted(values))

    def test_generation_modes_and_foreign_raw_invariants(self):
        records = run_simulation(self.config, 30_000, 901)
        counts = {mode: sum(r.weapon.generation_mode == mode for r in records) for mode in ("OWN_CLASS", "FOREIGN_RAW", "FOREIGN_WORKED")}
        self.assertAlmostEqual(counts["OWN_CLASS"] / len(records), .8, delta=.02)
        self.assertAlmostEqual(counts["FOREIGN_RAW"] / (counts["FOREIGN_RAW"] + counts["FOREIGN_WORKED"]), .9, delta=.02)
        raw = [r for r in records if r.weapon.generation_mode == "FOREIGN_RAW"]
        self.assertTrue(all((not r.weapon.compatible and r.weapon.item_class != r.guest.guest_class and r.weapon.refining_level == 0 and r.weapon.reinforcement_grade == "UNENHANCED" and r.weapon.amplification_grade == "UNAPPLIED") for r in raw))
        self.assertEqual(self.config["price"]["reinforce_values"]["UNENHANCED"], .1)

    def test_market_pressure_is_in_effective_load(self):
        for record in run_simulation(self.config, 1000, 88):
            weapon = record.weapon
            expected_popularity = self.config["weapon"]["market_processing_load"]["class_popularity"][record.class_popularity]
            expected_power = self.config["weapon"]["market_processing_load"]["class_power"][record.class_power]
            self.assertEqual(weapon.popularity_load, expected_popularity)
            self.assertEqual(weapon.class_power_load, expected_power)
            self.assertEqual(weapon.effective_processing_load, weapon.processing_load + expected_popularity + expected_power)

    def test_higher_effective_load_has_lower_configured_stability(self):
        tables = self.config["weapon"]["stability_by_processing_load"]
        midpoints = {"0-19": 9.5, "20-39": 29.5, "40-59": 49.5, "60-79": 69.5, "80-99": 89.5, "100-100": 100}
        expected = [sum(midpoints[band] * probability for band, probability in table.items()) for table in tables.values()]
        self.assertEqual(expected, sorted(expected, reverse=True))

    def test_visitor_roles_force_first_four_then_balance(self):
        rng = random.Random(12)
        guests = [generate_guest(rng, self.config, visitor_number=index) for index in range(1, 10005)]
        self.assertTrue(all(guest.role == "SELL_TO_SHOP" for guest in guests[:4]))
        seller_rate = sum(guest.role == "SELL_TO_SHOP" for guest in guests[4:]) / 10000
        self.assertAlmostEqual(seller_rate, .5, delta=.02)

    def _buyer_and_weapons(self):
        records = run_simulation(self.config, 1000, 55)
        first = records[0]
        buyer = replace(first.guest, role="BUY_FROM_SHOP", guest_class=first.weapon.item_class,
                        preferred_weapon_type=first.weapon.item_type)
        compatible = [record.weapon for record in records if record.weapon.item_class == buyer.guest_class]
        incompatible = next(record.weapon for record in records if record.weapon.item_class != buyer.guest_class)
        return buyer, compatible, incompatible

    def test_buyer_fit_filters_class_and_rewards_preference(self):
        buyer, weapons, incompatible = self._buyer_and_weapons()
        preferred = calculate_buyer_fit(self.config, buyer, weapons[0])
        nonpreferred = calculate_buyer_fit(self.config, replace(buyer, preferred_weapon_type="not_this"), weapons[0])
        self.assertIsNone(calculate_buyer_fit(self.config, buyer, incompatible))
        self.assertGreater(preferred.score, nonpreferred.score)
        self.assertTrue(0 <= preferred.score <= 100)

    def test_quality_fit_is_non_decreasing_and_best_item_is_selected(self):
        buyer, weapons, _ = self._buyer_and_weapons()
        base = weapons[0]
        scores = [calculate_buyer_fit(self.config, buyer, replace(base, normal_stat_grade=grade)).score
                  for grade in ("NONE", "MIXED", "ADEQUATE", "EXCELLENT")]
        self.assertEqual(scores, sorted(scores))
        items = [InventoryItem(i, weapon, buyer, 1, 1, 100, 100, 100, 120) for i, weapon in enumerate(weapons[:20], 1)]
        selected, fit, failure = choose_inventory_item(self.config, random.Random(4), buyer, items)
        self.assertIsNone(failure if fit.score >= 40 else selected)
        self.assertEqual(fit.score, max(calculate_buyer_fit(self.config, buyer, item.weapon).score for item in items))

    def test_interest_haggles_decrease_with_fit(self):
        bands = self.config["economy"]["interest_bands"]
        self.assertEqual([band["haggles"] for band in bands], sorted((band["haggles"] for band in bands), reverse=False))
        self.assertIsNone(interest_band(self.config, 39.999))

    def test_economy_transactions_move_cash_inventory_and_trade_count(self):
        result = run_economy_trial(self.config, 123, weeks=2)
        purchases = [row for row in result["transactions"] if row["transaction_type"] == "BUY_FROM_CUSTOMER"]
        sales = [row for row in result["transactions"] if row["transaction_type"] == "SELL_TO_CUSTOMER"]
        self.assertTrue(all(row["cash_after"] < row["cash_before"] for row in purchases))
        self.assertTrue(all(row["cash_after"] > row["cash_before"] for row in sales))
        self.assertEqual(result["state"].shop_trade_count, len(purchases) + len(sales))

    def test_market_change_revalues_inventory(self):
        result = run_economy_trial(self.config, 321, weeks=1)
        item = result["inventory"][0]
        weak = {name: ("WEAK", "UNPOPULAR") for name in self.config["guest"]["classes"]}
        strong = {name: ("STRONG", "POPULAR") for name in self.config["guest"]["classes"]}
        self.assertGreater(revalue_item(self.config, item, strong), revalue_item(self.config, item, weak))

    def test_economy_seed_reproducibility(self):
        first = run_economy_trial(self.config, 777, weeks=2)
        second = run_economy_trial(self.config, 777, weeks=2)
        self.assertEqual(first["checkpoints"], second["checkpoints"])
        self.assertEqual(first["transactions"], second["transactions"])


if __name__ == "__main__":
    unittest.main()
