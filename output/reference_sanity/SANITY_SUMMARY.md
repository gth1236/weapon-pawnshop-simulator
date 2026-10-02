# Reference implementation sanity result

seed=12345, 12 weeks, 100 trials. 90 tests passed (23 added).

All values below are medians. Currency: G. No balance conclusions.

| Week | Cash | Inventory count | Capacity | Inventory value | Net worth | Reputation | Trade count |
|---|---|---|---|---|---|---|---|
| 4 | 39,705.00 | 14.50 | 17.00 | 121,014.50 | 180,881.00 | 180.12 | 109.00 |
| 8 | 117,094.00 | 17.50 | 20.00 | 213,967.00 | 340,635.50 | 281.62 | 220.00 |
| 12 | 279,175.00 | 18.00 | 20.00 | 231,102.50 | 542,591.50 | 339.88 | 325.00 |

Audit: all 1,200 weekly rows have zero debt, repayments and scrap; net worth equals cash plus inventory value; capacity never exceeds 20; each expansion costs 10,000 G; each trial pays 156,000 G in operating costs.

Historical experiment outputs are preserved. Baseline uses automatic purchase/sale/expansion heuristics; scrap is manual only.
