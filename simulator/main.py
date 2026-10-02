import argparse
from pathlib import Path

if __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.config import DEFAULT_CONFIG, load_config
from simulator.economy_simulation import export_economy_reports, format_economy_report, run_economy_monte_carlo
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
    parser.add_argument("--economy-trials", type=int, default=100)
    parser.add_argument("--economy-weeks", type=int, default=24)
    parser.add_argument("--starting-cash", type=float)
    parser.add_argument("--economy-output-dir", type=Path, default=Path("output"))
    args = parser.parse_args(argv)
    config = load_config(args.config)
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
    if args.economy_trials:
        economy = run_economy_monte_carlo(config, args.economy_trials, args.seed + 2, args.economy_weeks, args.starting_cash)
        export_economy_reports(economy, args.economy_output_dir)
        print("\n\n" + format_economy_report(economy))
    print(f"\nCSV written to {args.output}")


if __name__ == "__main__":
    main()
