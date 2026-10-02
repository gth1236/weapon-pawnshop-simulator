import copy
import random
import unittest
from dataclasses import asdict

from simulator.appraisal import (PROPERTY_FIELDS, apply_appraisal_tool,
    create_player_knowledge, isolated_appraisal_rng, property_domain)
from simulator.config import load_config
from simulator.economy_simulation import (InventoryItem, create_shop_state,
    expand_inventory, scrap_inventory_item, run_economy_trial, settle_week)
from simulator.simulation import run_simulation
from simulator.price_calculator import calculate_price


class ReferenceRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        cls.record = run_simulation(cls.config, 1, 12345)[0]
        cls.weapon = cls.record.weapon

    def knowledge(self, probability=None, seed=123):
        config = copy.deepcopy(self.config)
        if probability is not None:
            config['appraisal']['unassisted_correct_probability'] = probability
        return create_player_knowledge(config, self.weapon, random.Random(seed))

    def stocked(self, cost=10000):
        state = create_shop_state(self.config)
        state.inventory.append(InventoryItem(1, self.weapon, self.record.guest,
            1, 1, cost, cost, cost, cost))
        return state

    def test_reference_defaults(self):
        state = create_shop_state(self.config)
        self.assertEqual((state.cash, state.debt_remaining, state.inventory_capacity), (100000, 0, 10))
        self.assertEqual(self.config['economy']['maximum_inventory_capacity'], 20)

    def test_disabled_debt_has_no_settlement_payments(self):
        state = create_shop_state(self.config)
        settle_week(self.config, state, 1, 'aggressive')
        self.assertEqual((state.cash, state.debt_remaining, state.total_debt_repayment), (98000, 0, 0))

    def test_all_ten_expansions_cost_exactly_ten_thousand(self):
        state = create_shop_state(self.config)
        for capacity in range(11, 21):
            before = state.cash
            self.assertTrue(expand_inventory(self.config, state))
            self.assertEqual((state.inventory_capacity, before-state.cash), (capacity, 10000))
        self.assertFalse(expand_inventory(self.config, state))
        self.assertEqual(state.inventory_capacity, 20)

    def test_manual_expansion_requires_cash(self):
        state = create_shop_state(self.config, starting_cash=9999)
        self.assertFalse(expand_inventory(self.config, state))
        self.assertEqual((state.cash, state.inventory_capacity), (9999, 10))

    def test_tier_always_exact(self):
        known = self.knowledge(0)
        self.assertEqual(known.item_tier.knowledge_state, 'EXACT')
        self.assertEqual(known.item_tier.displayed_value, self.weapon.tier)

    def test_all_concrete_stats_always_exact(self):
        known = self.knowledge(0)
        lines = list(self.weapon.stat_lines) + list(self.weapon.amplification_lines)
        self.assertEqual(len(known.known_stat_lines), len(lines))
        for field, line in zip(known.known_stat_lines.values(), lines):
            self.assertEqual(field.knowledge_state, 'EXACT')
            self.assertEqual(field.displayed_value, dict(stat_id=line.stat_id,
                actual_value=line.actual_value, display_unit=line.display_unit))

    def test_hidden_truth_and_guess_are_separate(self):
        original = asdict(self.weapon)
        known = self.knowledge(0)
        for name in PROPERTY_FIELDS:
            self.assertIsNone(getattr(known, name).known_exact_value)
            self.assertEqual(getattr(known, name).knowledge_state, 'UNAPPRAISED_GUESS')
        self.assertEqual(asdict(self.weapon), original)

    def test_incorrect_guesses_are_different_and_valid(self):
        for seed in range(100):
            known = self.knowledge(0, seed)
            for name, attribute in PROPERTY_FIELDS.items():
                displayed = getattr(known, name).displayed_value
                self.assertNotEqual(displayed, getattr(self.weapon, attribute))
                self.assertIn(displayed, property_domain(self.config, name))

    def test_correct_guesses_still_marked_as_guesses(self):
        known = self.knowledge(1)
        for name, attribute in PROPERTY_FIELDS.items():
            field = getattr(known, name)
            self.assertEqual(field.displayed_value, getattr(self.weapon, attribute))
            self.assertEqual(field.knowledge_state, 'UNAPPRAISED_GUESS')

    def test_guess_seed_reproducible(self):
        self.assertEqual(self.knowledge(), self.knowledge())

    def test_each_property_approximately_half_correct(self):
        self.assertEqual(self.config['appraisal']['unassisted_correct_probability'], .5)
        rng = random.Random(12345)
        counts = dict.fromkeys(PROPERTY_FIELDS, 0)
        for _ in range(2000):
            known = create_player_knowledge(self.config, self.weapon, rng)
            for name, attribute in PROPERTY_FIELDS.items():
                counts[name] += getattr(known, name).displayed_value == getattr(self.weapon, attribute)
        for count in counts.values():
            self.assertTrue(900 < count < 1100, count)

    def test_tool_reveals_exact_true_property_only(self):
        for name, attribute in PROPERTY_FIELDS.items():
            known = self.knowledge(0)
            before = asdict(known)
            tool = self.config['appraisal']['property_tools'][name]
            field = apply_appraisal_tool(self.config, self.weapon, known, name, {tool})
            self.assertEqual(field.knowledge_state, 'EXACT')
            self.assertEqual(field.displayed_value, getattr(self.weapon, attribute))
            for other in PROPERTY_FIELDS.keys() - {name}:
                self.assertEqual(asdict(getattr(known, other)), before[other])

    def test_tool_requires_ownership(self):
        with self.assertRaises(PermissionError):
            apply_appraisal_tool(self.config, self.weapon, self.knowledge(), 'refining', set())

    def test_player_view_does_not_leak_internal_stat_grades(self):
        view = self.knowledge().player_view()
        self.assertEqual(set(view), {'tier', 'concrete_stats', 'properties'})
        for line in view['concrete_stats']:
            self.assertEqual(set(line['displayed_value']), {'stat_id', 'actual_value', 'display_unit'})
        for field in view['properties'].values():
            self.assertEqual(set(field), {'knowledge_state', 'displayed_value'})

    def test_price_uses_truth_despite_changed_knowledge(self):
        record = self.record
        for probability in (0, 1):
            known = self.knowledge(probability)
            known.refining.displayed_value = 0
            price = calculate_price(self.config, record.guest, self.weapon,
                record.class_power, record.class_popularity)
            self.assertEqual(price.true_appraised_price, record.price.appraised_price)

    def test_appraisal_rng_does_not_advance_generation_rng(self):
        rng = random.Random(12345)
        before = rng.getstate()
        create_player_knowledge(self.config, self.weapon, isolated_appraisal_rng(rng))
        self.assertEqual(rng.getstate(), before)

    def test_guess_probability_does_not_change_truth_or_prices(self):
        changed = copy.deepcopy(self.config)
        changed['appraisal']['unassisted_correct_probability'] = 0
        baseline = run_simulation(self.config, 50, 987)
        alternate = run_simulation(changed, 50, 987)
        self.assertEqual([(r.weapon, r.price) for r in baseline], [(r.weapon, r.price) for r in alternate])

    def test_scrap_cash_inventory_and_separate_statistics(self):
        state = self.stocked()
        scrap_inventory_item(self.config, state, 1)
        self.assertEqual(state.cash, 105000)
        self.assertEqual(state.inventory, [])
        self.assertEqual((state.scrap_count, state.scrap_revenue, state.scrap_cost_basis,
            state.scrap_realized_loss), (1, 5000, 10000, 5000))

    def test_scrap_preserves_reputation_trade_and_normal_sale_statistics(self):
        state = self.stocked()
        before = copy.deepcopy(state)
        scrap_inventory_item(self.config, state, 1)
        for name in ('reputation', 'shop_trade_count', 'shop_purchase_count', 'shop_sale_count',
                     'counters', 'realized_profit', 'margins', 'holding_days'):
            self.assertEqual(getattr(state, name), getattr(before, name))

    def test_scrap_rounding_matches_existing_round_convention(self):
        for cost, revenue in ((101, 50), (103, 52)):
            state = self.stocked(cost)
            scrap_inventory_item(self.config, state, 1)
            self.assertEqual(state.scrap_revenue, revenue)
            self.assertEqual(state.scrap_realized_loss, cost-revenue)

    def test_scrap_rejects_unowned_or_already_scrapped_item(self):
        state = self.stocked()
        before = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            scrap_inventory_item(self.config, state, 999)
        self.assertEqual(state, before)
        scrap_inventory_item(self.config, state, 1)
        with self.assertRaises(ValueError):
            scrap_inventory_item(self.config, state, 1)
        self.assertEqual(state.scrap_count, 1)

    def test_scrap_can_recover_negative_cash(self):
        state = self.stocked()
        state.cash = -1000
        scrap_inventory_item(self.config, state, 1)
        self.assertEqual(state.cash, 4000)

    def test_baseline_never_scraps_and_is_reproducible(self):
        first = run_economy_trial(self.config, 12345, weeks=2)
        second = run_economy_trial(self.config, 12345, weeks=2)
        self.assertEqual(first, second)
        self.assertEqual(first['state'].scrap_count, 0)
