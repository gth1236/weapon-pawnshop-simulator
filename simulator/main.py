import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.config import DEFAULT_CONFIG, load_config
from simulator.economy_simulation import add_economy_comparisons, export_economy_reports, format_economy_report, run_economy_monte_carlo
from simulator.report import build_generation_mode_report, build_report, format_samples
from simulator.reputation_simulation import export_progression_csv, format_reputation_report, simulate_fair_value_strategy
from simulator.simulation import export_csv, run_simulation


def main(argv=None):
    parser = argparse.ArgumentParser(description="RPG Weapon Pawnshop balance simulator")
    parser.add_argument("--count", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=12345)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=Path("output/simulation_results.csv"))
    parser.add_argument("--samples", type=int, default=20)
    parser.add_argument("--reputation-trials", type=int, default=1000, help="Monte Carlo trials for fair-value purchase reputation checkpoints; 0 disables")
    parser.add_argument("--progression-output", type=Path, default=Path("output/progression_report.csv"))
    parser.add_argument("--economy-trials", type=int, help="Defaults to economy.trials in config; 0 disables")
    parser.add_argument("--economy-weeks", type=int, help="Defaults to economy.weeks in config")
    parser.add_argument("--starting-cash", type=float)
    parser.add_argument("--starting-debt", type=float)
    parser.add_argument("--debt-repayment-policy", choices=("mandatory_only", "moderate", "aggressive"),
                        help="Defaults to economy.debt_repayment.default_policy in config")
    parser.add_argument("--compare-debt-policies", action="store_true",
                        help="Run all three repayment policies with the same seeds and export a Korean comparison report")
    parser.add_argument("--previous-economy-summary", type=Path,
                        help="Optional path to the previous high-operating-cost experiment JSON")
    parser.add_argument("--economy-only", action="store_true", help="Skip item-generation and reputation analyses")
    parser.add_argument("--skip-economy-comparisons", action="store_true", help="Skip paired no-cost/unlimited-inventory analyses")
    parser.add_argument("--economy-output-dir", type=Path, default=Path("output"))
    args = parser.parse_args(argv)
    config = load_config(args.config)
    if args.compare_debt_policies:
        from simulator.debt_policy_comparison import run_debt_policy_comparison
        trials=config["economy"]["trials"] if args.economy_trials is None else args.economy_trials
        if trials:
            report=run_debt_policy_comparison(config,trials,args.seed,args.economy_weeks,
                args.starting_cash,args.starting_debt,args.economy_output_dir,args.previous_economy_summary)
            print(f"Debt policy comparison written to {report}")
        return
    if args.economy_only:
        trials=config["economy"]["trials"] if args.economy_trials is None else args.economy_trials
        if trials:
            economy=run_economy_monte_carlo(config,trials,args.seed,args.economy_weeks,args.starting_cash,args.starting_debt,
                                           debt_repayment_policy=args.debt_repayment_policy)
            if not args.skip_economy_comparisons: add_economy_comparisons(economy,args.starting_cash,args.starting_debt)
            export_economy_reports(economy,args.economy_output_dir)
            print(format_economy_report(economy))
        return
    records = run_simulation(config, args.count, args.seed)
    export_csv(records, args.output)
    print(build_report(records))
    print("\n\n" + build_generation_mode_report(records))
    if args.samples:
        print("\n\nREADABLE SAMPLES\n" + format_samples(records, min(args.samples, len(records))))
    if args.reputation_trials:
        reputation = simulate_fair_value_strategy(config, args.reputation_trials, args.seed + 1)
        export_progression_csv(reputation, args.progression_output)
        print("\n\n" + format_reputation_report(reputation, args.reputation_trials, config["analysis"]["progression_distribution_checkpoints"]))
        print(f"Progression CSV written to {args.progression_output}")
    if args.economy_trials is None or args.economy_trials:
        economy = run_economy_monte_carlo(config, args.economy_trials, args.seed + 2, args.economy_weeks, args.starting_cash,args.starting_debt,
                                         debt_repayment_policy=args.debt_repayment_policy)
        if not args.skip_economy_comparisons: add_economy_comparisons(economy,args.starting_cash,args.starting_debt)
        export_economy_reports(economy, args.economy_output_dir)
        print("\n\n" + format_economy_report(economy))
    print(f"\nCSV written to {args.output}")


if __name__ == "__main__":
    main()
