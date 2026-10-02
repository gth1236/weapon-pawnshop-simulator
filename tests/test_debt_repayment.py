import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from simulator.config import ConfigError, load_config, validate_config
from simulator.economy_simulation import (
    create_shop_state, pay_mandatory_debt, pay_optional_debt, settle_week,
    run_economy_trial, run_economy_monte_carlo, weekly_operating_cost,
)


class DebtRepaymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config()
        # Preserve legacy repayment regression coverage with an explicit opt-in fixture.
        cls.config["economy"]["debt_repayment"]["enabled"] = True
        cls.config["economy"]["starting_debt"] = 100000

    def state(self, cash=50000, debt=100000):
        return create_shop_state(self.config, cash, debt)

    def test_starting_debt_remaining(self):
        state = create_shop_state(self.config)
        self.assertEqual(state.debt_remaining, 100000)
        self.assertEqual(state.debt, state.debt_remaining)
        self.assertIsNone(state.debt_fully_repaid_week)

    def test_new_operating_costs(self):
        self.assertEqual([weekly_operating_cost(self.config,w) for w in (1,2,12)], [2000,4000,24000])
        self.assertEqual(sum(weekly_operating_cost(self.config,w) for w in range(1,13)),156000)

    def test_mandatory_payment_and_balance(self):
        state = self.state()
        self.assertEqual(pay_mandatory_debt(self.config,state,1),5000)
        self.assertEqual((state.cash,state.debt_remaining),(45000,95000))
        self.assertEqual(state.mandatory_debt_payment_total,5000)
        self.assertEqual(state.total_debt_repayment,5000)

    def test_mandatory_final_partial_payment(self):
        state = self.state(debt=3000)
        self.assertEqual(pay_mandatory_debt(self.config,state,4),3000)
        self.assertEqual((state.debt_remaining,state.cash,state.debt_fully_repaid_week),(0,47000,4))
        self.assertEqual(pay_mandatory_debt(self.config,state,5),0)
        self.assertEqual((state.cash,state.debt_fully_repaid_week),(47000,4))

    def test_zero_debt_has_no_mandatory_payment(self):
        state = self.state(debt=0)
        self.assertEqual(pay_mandatory_debt(self.config,state,1),0)
        self.assertEqual(state.cash,50000)
        self.assertEqual(state.debt_fully_repaid_week,0)

    def test_mandatory_payment_allows_negative_cash_without_new_debt(self):
        state = self.state(cash=3000)
        pay_mandatory_debt(self.config,state,1)
        self.assertEqual((state.cash,state.debt_remaining),(-2000,95000))
        self.assertEqual((state.minimum_cash,state.cash_deficit_events),(-2000,1))
        pay_mandatory_debt(self.config,state,2)
        self.assertEqual((state.cash,state.debt_remaining,state.cash_deficit_events),(-7000,90000,1))

    def test_mandatory_only_has_no_optional_payment(self):
        state = self.state(cash=1000000)
        self.assertEqual(pay_optional_debt(self.config,state,1,"mandatory_only"),0)
        self.assertEqual(state.debt_remaining,100000)

    def test_moderate_threshold(self):
        for cash in (-100,0,49999,50000):
            state = self.state(cash=cash)
            self.assertEqual(pay_optional_debt(self.config,state,1,"moderate"),0)
            self.assertEqual(state.cash,cash)

    def test_moderate_repayment_half_excess(self):
        state = self.state(cash=70000)
        self.assertEqual(pay_optional_debt(self.config,state,1,"moderate"),10000)
        self.assertEqual((state.cash,state.debt_remaining),(60000,90000))
        state = self.state(cash=50001)
        self.assertEqual(pay_optional_debt(self.config,state,1,"moderate"),0.5)

    def test_aggressive_threshold(self):
        for cash in (-100,0,29999,30000):
            state = self.state(cash=cash)
            self.assertEqual(pay_optional_debt(self.config,state,1,"aggressive"),0)

    def test_aggressive_repayment_all_excess(self):
        state = self.state(cash=70000)
        self.assertEqual(pay_optional_debt(self.config,state,1,"aggressive"),40000)
        self.assertEqual((state.cash,state.debt_remaining),(30000,60000))

    def test_optional_capped_at_remaining_and_stops_after_payoff(self):
        for policy in ("moderate","aggressive"):
            state = self.state(cash=70000,debt=6000)
            self.assertEqual(pay_optional_debt(self.config,state,2,policy),6000)
            self.assertEqual((state.cash,state.debt_remaining,state.debt_fully_repaid_week),(64000,0,2))
            self.assertEqual(pay_optional_debt(self.config,state,3,policy),0)
            self.assertEqual(pay_mandatory_debt(self.config,state,3),0)
            self.assertEqual(state.optional_debt_payment_total,6000)
            self.assertEqual(state.total_debt_repayment,6000)

    def test_repayment_preserves_net_worth_at_payment(self):
        state = self.state(cash=77000)
        before = state.cash-state.debt_remaining
        pay_mandatory_debt(self.config,state,1)
        pay_optional_debt(self.config,state,1,"moderate")
        self.assertEqual(state.cash-state.debt_remaining,before)

    def test_settlement_order_and_audit_ledger(self):
        state = self.state(cash=77000)
        state.reputation=123
        state.shop_trade_count=45
        ledger=settle_week(self.config,state,1,"moderate")
        self.assertEqual(ledger["cash_before_settlement"],77000)
        self.assertEqual(ledger["cash_after_operating_cost"],75000)
        self.assertEqual(ledger["mandatory_debt_payment"],5000)
        self.assertEqual(ledger["cash_after_mandatory_repayment"],70000)
        self.assertEqual(ledger["optional_debt_payment"],10000)
        self.assertEqual(ledger["cash_after_optional_repayment"],60000)
        self.assertEqual((state.cash,state.debt_remaining),(60000,85000))
        self.assertEqual((state.reputation,state.shop_trade_count),(123,45))

    def test_settlement_counts_week_made_negative_by_mandatory_payment(self):
        state = self.state(cash=6000)
        ledger = settle_week(self.config,state,1,"mandatory_only")
        self.assertEqual(ledger["cash_after_operating_cost"],4000)
        self.assertEqual(state.cash,-1000)
        self.assertEqual(state.weeks_with_negative_cash,1)
        settle_week(self.config,state,2,"mandatory_only")
        self.assertEqual(state.weeks_with_negative_cash,2)

    def test_checkpoint_after_last_customer_and_all_payments(self):
        trial=run_economy_trial(self.config,12345,weeks=2,debt_repayment_policy="aggressive")
        for row in trial["weekly"]:
            last=[tx for tx in trial["transactions"] if tx["day"]==row["week"]*7][-1]
            self.assertEqual(row["cash_before_settlement"],last["cash_after"])
            self.assertEqual(row["cash"],row["cash_after_optional_repayment"])
            self.assertEqual(row["debt_remaining"],row["debt_after_mandatory_repayment"]-row["optional_debt_payment"])
            self.assertEqual(row["net_worth_after_debt"],row["cash"]+row["inventory_value"]-row["debt_remaining"])

    def test_mandatory_only_twelve_weeks_and_twenty_week_payoff(self):
        result=run_economy_trial(self.config,12345,weeks=24,starting_cash=0)
        self.assertEqual(result["checkpoints"][12]["debt_remaining"],40000)
        self.assertIsNone(result["checkpoints"][12]["debt_fully_repaid_week"])
        self.assertEqual(result["state"].debt_fully_repaid_week,20)
        self.assertEqual(result["state"].mandatory_debt_payment_total,100000)
        self.assertEqual(result["weekly"][20]["mandatory_debt_payment"],0)

    def test_debt_and_cash_conservation_for_all_policies(self):
        for policy in ("mandatory_only","moderate","aggressive"):
            trial=run_economy_trial(self.config,9,weeks=12,debt_repayment_policy=policy)
            for row in trial["weekly"]:
                self.assertAlmostEqual(row["debt_remaining"]+row["total_debt_repayment"],100000)
                self.assertAlmostEqual(row["cash"],row["cash_before_settlement"]-row["weekly_operating_cost"]
                    -row["mandatory_debt_payment"]-row["optional_debt_payment"])
                self.assertGreaterEqual(row["debt_remaining"],0)

    def test_same_seed_reproducibility_and_common_arrival_market_streams(self):
        trials=[]
        for policy in ("mandatory_only","moderate","aggressive"):
            a=run_economy_trial(self.config,42,weeks=3,debt_repayment_policy=policy)
            b=run_economy_trial(self.config,42,weeks=3,debt_repayment_policy=policy)
            self.assertEqual(a["weekly"],b["weekly"])
            self.assertEqual(a["transactions"],b["transactions"])
            trials.append(a)
        for trial in trials[1:]:
            self.assertEqual(trial["market"],trials[0]["market"])
            self.assertEqual([r["day"] for r in trial["transactions"]],[r["day"] for r in trials[0]["transactions"]])

    def test_unpaid_summary_uses_none_not_zero_week(self):
        result=run_economy_monte_carlo(self.config,2,12345,weeks=12)
        row=result["checkpoints"][12]
        self.assertEqual(row["debt_fully_repaid_trial_rate"],0)
        self.assertIsNone(row["debt_fully_repaid_week_mean"])
        self.assertIsNone(row["debt_fully_repaid_week_median"])

    def test_cli_policy_and_comparison_exports(self):
        from simulator.main import main
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            config_path = Path(directory)/"historical_config.json"
            config_path.write_text(json.dumps(self.config),encoding="utf-8")
            main(["--economy-only","--economy-trials","2","--economy-weeks","2","--starting-cash","77000",
                  "--debt-repayment-policy","moderate","--skip-economy-comparisons","--economy-output-dir",directory,
                  "--config",str(config_path)])
            data=json.loads((Path(directory)/"economy_summary.json").read_text(encoding="utf-8"))
            self.assertEqual(data["debt_repayment_policy"],"moderate")
            self.assertEqual(data["starting_debt"],100000)
            main(["--compare-debt-policies","--economy-trials","2","--economy-weeks","2","--economy-output-dir",directory,
                  "--config",str(config_path)])
            data=json.loads((Path(directory)/"debt_policy_comparison.json").read_text(encoding="utf-8"))
            self.assertEqual(set(data["policies"]),{"mandatory_only","moderate","aggressive"})
            self.assertEqual(len(data["final_comparison"]),3)
            self.assertTrue((Path(directory)/"DEBT_POLICY_COMPARISON_KO.md").exists())

    def test_invalid_policy_parameters_rejected(self):
        for key,value in (("reserve_threshold",-1),("excess_repayment_fraction",1.1)):
            config=copy.deepcopy(self.config)
            config["economy"]["debt_repayment"]["policies"]["moderate"][key]=value
            with self.assertRaises(ConfigError): validate_config(config)
        with self.assertRaises(ValueError): run_economy_trial(self.config,1,weeks=1,debt_repayment_policy="unknown")

    def test_current_flat_expansion_cost(self):
        self.assertEqual(self.config["economy"]["inventory_expansion_cost"],10000)
        self.assertNotIn("inventory_expansion_costs",self.config["economy"])

    def test_zero_starting_debt_disables_all_repayment_policies(self):
        baseline = None
        for policy in ("mandatory_only", "moderate", "aggressive"):
            # Surplus cash must not trigger optional payments when debt is absent.
            state = self.state(cash=200000, debt=0)
            ledger = settle_week(self.config, state, 1, policy)
            self.assertEqual((ledger["mandatory_debt_payment"], ledger["optional_debt_payment"]), (0, 0))
            self.assertEqual(state.cash, 198000)
            trial = run_economy_trial(self.config, 12345, weeks=12, starting_cash=50000,
                                       starting_debt=0, debt_repayment_policy=policy)
            for row in trial["weekly"]:
                self.assertEqual(row["debt_remaining"], 0)
                self.assertEqual(row["mandatory_debt_payment_total"], 0)
                self.assertEqual(row["optional_debt_payment_total"], 0)
                self.assertEqual(row["total_debt_repayment"], 0)
                self.assertEqual(row["cash"], row["cash_before_settlement"]-row["weekly_operating_cost"])
                self.assertEqual(row["net_worth"], row["cash"]+row["inventory_value"])
                self.assertEqual(row["net_worth_after_debt"], row["gross_assets"])
            self.assertEqual(trial["state"].total_operating_cost_paid, 156000)
            if baseline is None:
                baseline = trial
            else:
                self.assertEqual(trial["weekly"], baseline["weekly"])
                self.assertEqual(trial["transactions"], baseline["transactions"])
