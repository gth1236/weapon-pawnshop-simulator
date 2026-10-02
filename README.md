# RPG Weapon Pawnshop Balance Simulator

This Python-only debug simulator implements the generation and price rules in
`rpg_weapon_pawnshop_core_system_spec_v0_2.txt`. It deliberately contains no
Godot project or game client.

## Run

Python 3.10 or later is required; there are no third-party dependencies.

```bash
python simulator/main.py --count 10000 --seed 12345
```

The command prints distributions, price percentiles, up to 20 readable samples,
and a 1,000-trial reputation projection at 10/25/30/50/60/100/120/200/240 completed trades,
then writes every generated guest/weapon pair to
`output/simulation_results.csv`. Use `--count` for any positive sample size,
`--samples 0` to suppress examples, `--output` to change the CSV destination,
and `output/progression_report.csv`. Use `--config` to load another balance file,
`--progression-output` to move that report, or `--reputation-trials 0` to skip
the reputation projection or another positive value to change its sample size.
The same command runs 100 24-week economy trials by default. Use
`--economy-trials`, `--economy-weeks`, `--starting-cash`, or
`--economy-trials 0` to tune or disable this analysis.

## Structure

- `config/balance.json`: all probability, price, numeric-stat, and temporary
  debug values. `metadata.temporary_values` identifies every unfinished group.
- `simulator/models.py`: separate true weapon, player-known weapon, guest,
  concrete stat-line, price, and result records.
- `simulator/config.py`: config loading and probability-table validation.
- `simulator/guest_generator.py`: independent uniform guest rolls and the
  configurable temporary progression rolls.
- `simulator/weapon_generator.py`: compatibility, weapon, tier, internal grade,
  concrete numeric stat, processing, and stability generation.
- `simulator/price_calculator.py`: pure spec price and asking-price formulas.
- `simulator/buyer_fit.py`: buyer compatibility, fit components, interest bands,
  and deterministic best-inventory selection.
- `simulator/economy_simulation.py`: day/week visits, cash, inventory, market
  revaluation, purchases, sales, Monte Carlo summaries, and economy CSV export.
- `simulator/reputation_simulation.py`: fair-value purchase strategy and
  reputation checkpoint Monte Carlo simulation.
- `simulator/simulation.py`: seeded orchestration and CSV export.
- `simulator/report.py`: distributions, percentiles, and readable examples.
- `simulator/main.py`: command-line entry point.
- `tests/test_simulator.py`: deterministic, validation, distribution, and price
  floor checks.

## Temporary/TODO balance assumptions

The specification leaves several tables unfinished. Neutral debug defaults are
isolated in config for kindness; reputation-to-level and power; trade-count-to-
achievement and title; incompatible stat quality; special stats; amplification
quality; reputation/trade-count progression anchors; foreign-raw quality;
processing-load contributions; conditional stability; and concrete numeric
display values. These are marked in `metadata.temporary_values`. Special-stat grades are generated
for pricing, but no concrete special line is invented because the required
tier/stat numeric ranges remain unspecified.

The simulator treats one run as one weekly market snapshot: each class receives
one independently uniform power and popularity state, reused for all records.
This follows the weekly market rule rather than rerolling the market per guest.

## Fair-value purchase strategy

“Normal price” is defined as offering the hidden true appraised price. An offer
at least as large as the asking price completes immediately; lower offers are
treated as a refusal because detailed counteroffers remain TODO in the spec.
Checkpoint counts refer to completed trades, while rejected visits still apply
the specified no-purchase or failed-scam reputation effect. Reported mean and
median values therefore include the visits required to reach each checkpoint.

Positive reputation deltas use the multiplier selected from the current
reputation before that delta is applied. Negative and zero deltas are never
decayed. Reputation remains a float internally; console output rounds to two
decimal places and CSV output retains the numeric value. The temporary decay
bands are stored under `reputation.positive_decay`.

Customer progression linearly interpolates editable config anchors. Reputation
controls kindness, level bracket, and power, while completed trade count
independently controls title and achievement. Every anchor retains non-zero
probability for low-end categories. Class, tendency, knowledge, and purpose
remain independent uniform rolls.

Stability is no longer rolled independently. Reinforcement, refining level, and
amplification category produce a temporary `processing_load`; the matching
`stability_by_processing_load` probability table then generates stability. Both
the load contributions and conditional tables are explicitly temporary config.
Market popularity and class power add pressure to the base processing load using
the weapon's `item_class`, never the carrying guest's class.

Incompatible weapons are split by temporary config into 90% `FOREIGN_RAW` and
10% `FOREIGN_WORKED`. Raw foreign items use separate stat/unique tables and are
always `UNENHANCED`, refining `0`, and `UNAPPLIED`; worked foreign items reuse
the normal guest-driven processing rules. `UNENHANCED` has the requested +0.10
reinforcement value. `OWN_CLASS`, `FOREIGN_RAW`, and `FOREIGN_WORKED` summaries
are printed and `generation_mode`, `item_class`, base load, market loads, and
effective load are exported to the item CSV.

## Temporary economy loop

The first four visitors sell to the shop; later roles use the configurable
50/50 seller/buyer table. A balanced automated policy accepts seller asking
prices at or below appraisal when cash permits. Inventory is reappraised against
the current weekly market. Buyers consider only matching `item_class` inventory,
choose the highest fit item, and make at most one fit/knowledge-adjusted offer.
The shop lists at current appraisal plus 20% and accepts no less than current
appraisal or purchase cost plus 5%. These price, interest, haggle, reputation,
starting-cash, and visit-rate values are explicitly temporary config.

Economy output includes `economy_weekly_report.csv`, a first-trial
`economy_transactions.csv`, and `inventory_snapshot.csv`. The model intentionally
does **not** include buyer affordability/budget, operating expenses, taxes,
loans, or interactive negotiation; buyer affordability/budget is still TODO.
