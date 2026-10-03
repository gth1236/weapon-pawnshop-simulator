import copy
import contextlib
import csv
import io
import json
import random
import tempfile
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from simulator.config import ConfigError, load_config, validate_config
from simulator.economy_simulation import (
    InventoryItem, create_shop_state, ensure_inventory_space, pay_weekly_operating_cost,
    add_economy_comparisons, export_economy_reports,
    process_buyer, process_seller, roll_market, run_economy_trial,
    run_economy_monte_carlo, snapshot, weekly_operating_cost,
)
from simulator.simulation import run_simulation


class EconomyConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        record = run_simulation(cls.config, 1, 55)[0]
        cls.guest, cls.weapon = record.guest, record.weapon
        cls.market = roll_market(random.Random(1), cls.config)

    def full_state(self, cash=50000, capacity=10):
        state = create_shop_state(self.config, cash)
        state.inventory_capacity = capacity
        state.inventory = [InventoryItem(i, self.weapon, self.guest, 1, 1, 100, 100, 100, 120)
                           for i in range(capacity)]
        return state

    def seller(self, state, ask=100):
        price = SimpleNamespace(asking_price=ask, appraised_price=ask)
        with patch("simulator.economy_simulation.generate_weapon", return_value=(self.weapon, None)), \
             patch("simulator.economy_simulation.calculate_price", return_value=price):
            return process_seller(self.config, random.Random(2), state, self.guest, self.market, 3, 100)

    def test_starting_cash(self):
        self.assertEqual(create_shop_state(self.config).cash, 100000)

    def test_starting_debt(self):
        self.assertEqual(create_shop_state(self.config).debt, 0)

    def test_initial_capacity(self):
        self.assertEqual(create_shop_state(self.config).inventory_capacity, 10)

    def test_capacity_never_exceeded(self):
        trial = run_economy_trial(self.config, 9)
        self.assertTrue(all(row["inventory_count"] <= row["inventory_capacity"] <= 20 for row in trial["transactions"]))

    def test_full_blocks_purchase(self):
        state = self.full_state(100)
        row, item_id = self.seller(state)
        self.assertEqual(row["outcome"], "INVENTORY_FULL")
        self.assertEqual(state.counters["MISSED_PURCHASE_DUE_TO_INVENTORY"], 1)
        self.assertEqual((len(state.inventory), item_id, state.shop_trade_count), (10, 100, 0))

    def test_expansion_is_one_slot_and_cost_paid(self):
        state = self.full_state()
        row, _ = self.seller(state)
        self.assertEqual(state.inventory_capacity, 11)
        self.assertEqual(len(state.inventory), 11)
        self.assertEqual(state.cash, 50000 - 10000 - 100)
        self.assertEqual(state.inventory_expansion_spending, 10000)
        self.assertEqual(state.inventory_expansion_count, 1)
        self.assertEqual(row["outcome"], "SUCCESSFUL_PURCHASE")

    def test_maximum_capacity_blocks_expansion(self):
        state = self.full_state(1000000, 20)
        self.assertFalse(ensure_inventory_space(self.config, state, 100, 1))
        self.assertEqual((state.cash, state.inventory_capacity), (1000000, 20))

    def test_expansion_requires_cost_and_purchase_cash(self):
        for cash in (9999, 10000, 10099):
            with self.subTest(cash=cash):
                state = self.full_state(cash)
                self.assertFalse(ensure_inventory_space(self.config, state, 100, 1))
                self.assertEqual((state.cash, state.inventory_capacity), (cash, 10))
        state = self.full_state(10100)
        row, _ = self.seller(state)
        self.assertEqual((row["outcome"], state.cash), ("SUCCESSFUL_PURCHASE", 0))

    def test_first_week_operating_cost(self):
        self.assertEqual(weekly_operating_cost(self.config, 1), 2000)

    def test_operating_cost_formula_and_total(self):
        for week in range(1, 25):
            self.assertEqual(weekly_operating_cost(self.config, week), week*2000)
        self.assertEqual(sum(weekly_operating_cost(self.config, week) for week in range(1, 13)), 156000)

    def test_sunday_cost_after_last_customer(self):
        trial = run_economy_trial(self.config, 7, weeks=2)
        for week in (1, 2):
            last = [row for row in trial["transactions"] if row["day"] == week*7][-1]
            snap = trial["checkpoints"][week]
            self.assertEqual(snap["cash"], last["cash_after"]-weekly_operating_cost(self.config, week)
                             -snap["mandatory_debt_payment"]-snap["optional_debt_payment"])
            self.assertEqual(snap["reputation"], last["reputation_after"])
            self.assertEqual(snap["shop_trade_count"], last["trade_count"])

    def test_cost_allows_negative_and_keeps_debt(self):
        state = create_shop_state(self.config, 1000)
        pay_weekly_operating_cost(self.config, state, 1)
        self.assertEqual((state.cash, state.debt), (-1000, 0))
        self.assertTrue(state.cash_deficit)
        self.assertEqual((state.cash_deficit_events, state.minimum_cash), (1, -1000))
        pay_weekly_operating_cost(self.config, state, 2)
        self.assertEqual(state.cash_deficit_events, 1)

    def test_nonpositive_cash_blocks_seller(self):
        for cash in (0, -100):
            state = create_shop_state(self.config, cash)
            row, _ = self.seller(state)
            self.assertEqual(row["outcome"], "MISSED_PURCHASE_DUE_TO_CASH")
            self.assertFalse(state.inventory)

    def test_buyer_sale_recovers_negative_cash(self):
        state = self.full_state(-50, 1)
        buyer = replace(self.guest, role="BUY_FROM_SHOP", market_knowledge="NONE")
        fit = SimpleNamespace(score=90, tier_fit=1, preference_match=True)
        with patch("simulator.economy_simulation.choose_inventory_item", return_value=(state.inventory[0], fit, None)), \
             patch("simulator.economy_simulation.revalue_item", return_value=100):
            row = process_buyer(self.config, random.Random(1), state, buyer, self.market, 2)
        self.assertEqual(row["outcome"], "BUYER_PURCHASES")
        self.assertEqual(state.cash, 70)
        self.assertFalse(state.cash_deficit)

    def test_net_worth_includes_debt(self):
        state = self.full_state()
        row = snapshot(self.config, state, self.market, 1, 7)
        self.assertEqual(row["gross_assets"], state.cash+row["inventory_value"])
        self.assertEqual(row["net_worth_after_debt"], row["gross_assets"])
        self.assertEqual(row["net_worth"], row["net_worth_after_debt"])

    def test_reproducibility_and_overrides(self):
        historical = copy.deepcopy(self.config)
        historical["economy"]["debt_repayment"]["enabled"] = True
        a = run_economy_trial(historical, 77, 3, 60000, 200000)
        b = run_economy_trial(historical, 77, 3, 60000, 200000)
        self.assertEqual(a["transactions"], b["transactions"])
        self.assertEqual(a["checkpoints"], b["checkpoints"])
        self.assertEqual(a["state"].debt_remaining, 185000)
        self.assertIn(3, a["checkpoints"])

    def test_short_and_24_week_monte_carlo(self):
        self.assertEqual(set(run_economy_monte_carlo(self.config, 2, 1, weeks=2)["checkpoints"]), {1, 2})
        self.assertIn(24, run_economy_monte_carlo(self.config, 2, 1, weeks=24)["checkpoints"])

    def test_capacity_residence_covers_duration(self):
        state = run_economy_trial(self.config, 8, 2)["state"]
        self.assertAlmostEqual(sum(state.capacity_days.values()), 14)

    def test_invalid_expansion_cost_rejected(self):
        config = copy.deepcopy(self.config)
        config["economy"]["inventory_expansion_cost"] = -1
        with self.assertRaises(ConfigError): validate_config(config)

    def test_no_cost_pair_shares_arrivals_and_market(self):
        a = run_economy_trial(self.config, 1, 2)
        b = run_economy_trial(self.config, 1, 2, operating_cost_multiplier=0)
        self.assertEqual(a["market"], b["market"])
        self.assertEqual([r["day"] for r in a["transactions"]], [r["day"] for r in b["transactions"]])
        self.assertEqual(b["state"].total_operating_cost_paid, 0)
        # Both branches are identical before the first Sunday payment.
        self.assertEqual(a["transactions"][:sum(r["day"]<=7 for r in a["transactions"])],
                         b["transactions"][:sum(r["day"]<=7 for r in b["transactions"])])

    def test_counterfactual_replays_same_offered_guests_and_seller_items(self):
        a = run_economy_trial(self.config, 1, 12)
        b = run_economy_trial(self.config, 1, 12, operating_cost_multiplier=0,
                              replay_flow=a["visitor_flow"])
        for left, right in zip(a["transactions"], b["transactions"]):
            for key in ("day", "customer_role", "adventurer_class", "preferred_weapon_type"):
                self.assertEqual(left[key], right[key])
            if left["customer_role"] == "SELL_TO_SHOP":
                for key in ("item_type", "required_class", "item_tier", "purchase_appraised_price"):
                    self.assertEqual(left[key], right[key])

    def test_cli_overrides_and_complete_export(self):
        from simulator.main import main
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            historical = copy.deepcopy(self.config)
            historical["economy"]["debt_repayment"]["enabled"] = True
            config_path = Path(directory)/"historical_config.json"
            config_path.write_text(json.dumps(historical),encoding="utf-8")
            main(["--economy-only", "--economy-trials", "2", "--economy-weeks", "3", "--starting-cash", "65000",
                  "--starting-debt", "120000", "--skip-economy-comparisons", "--economy-output-dir", directory,
                  "--config", str(config_path)])
            summary = json.loads((Path(directory)/"economy_summary.json").read_text(encoding="utf-8"))
            self.assertEqual((summary["starting_cash"], summary["starting_debt"]), (65000, 120000))
            self.assertEqual(set(summary["checkpoints"]), {"1", "2", "3"})
            with (Path(directory)/"economy_trial_weekly_report.csv").open(encoding="utf-8") as handle:
                self.assertEqual(len(list(csv.DictReader(handle))), 6)
            self.assertTrue((Path(directory)/"DESIGN_ANALYSIS_KO.md").exists())

    def test_paired_comparison_and_empty_inventory_export(self):
        result = run_economy_monte_carlo(self.config, 2, 15, weeks=1, starting_cash=0)
        add_economy_comparisons(result, starting_cash=0)
        self.assertIn("no_operating_cost", result["comparisons"])
        self.assertFalse(result["sample_trial"]["inventory"])
        with tempfile.TemporaryDirectory() as directory:
            export_economy_reports(result, directory)
            self.assertIn("item_id", (Path(directory)/"inventory_snapshot.csv").read_text(encoding="utf-8"))
