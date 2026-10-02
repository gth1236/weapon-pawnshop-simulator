"""Run repayment policies on matching seeds and write a Korean comparison."""
import json
import statistics
from pathlib import Path

from .economy_design_report import number, percent, policy_report_lines, table
from .economy_simulation import export_economy_reports, export_rows, run_economy_monte_carlo


PREVIOUS_SUMMARY = Path(__file__).resolve().parents[1]/"output"/"economy_12_weeks"/"economy_summary.json"


def run_debt_policy_comparison(config, trials, seed, weeks, starting_cash, starting_debt,
                               output_dir, previous_summary=None):
    output_dir=Path(output_dir)
    summaries={}; weekly_by_policy={}
    for policy in config["economy"]["debt_repayment"]["policies"]:
        print(f"Running {policy}: {trials} trials, seed={seed}", flush=True)
        result=run_economy_monte_carlo(config,trials,seed,weeks,starting_cash,starting_debt,
                                      debt_repayment_policy=policy)
        summaries[policy]=export_economy_reports(result,output_dir/policy)
        weekly_by_policy[policy]=[{"trial":i+1,**row} for i,trial in enumerate(result["trial_results"])
                                   for row in trial["weekly"]]
        # Keep compact summaries/weekly ledgers, not three large transaction pools.
        del result
    previous_path=Path(previous_summary) if previous_summary is not None else PREVIOUS_SUMMARY
    previous=json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else None
    comparison=build_comparison(summaries,weekly_by_policy,previous,previous_path)
    (output_dir/"debt_policy_comparison.json").write_text(json.dumps(comparison,ensure_ascii=False,indent=2),encoding="utf-8")
    export_rows(comparison["final_comparison"],output_dir/"debt_policy_comparison.csv")
    export_rows(comparison["paired_differences"],output_dir/"debt_policy_paired_differences.csv")
    report=write_comparison_report(summaries,weekly_by_policy,comparison,config,output_dir)
    return report


def build_comparison(summaries,weekly_by_policy,previous,previous_path):
    baseline=summaries["mandatory_only"]
    # Exports use JSON string keys; in-memory Monte Carlo uses integer keys.
    summaries=json.loads(json.dumps(summaries))
    final_week=max(map(int,summaries["mandatory_only"]["checkpoints"]))
    final_rows=[]
    for policy,data in summaries.items():
        final_rows.append({"policy":policy,"week":final_week,**{
            key:value for key,value in data["checkpoints"][str(final_week)].items()
            if not isinstance(value,dict)},**data["analytics"],
            "ever_negative_cash_trial_rate":data["checkpoints"][str(final_week)]["ever_negative_cash_trial_rate"]})
    # Only scalar analytics go into the comparison CSV.
    final_rows=[{key:value for key,value in row.items() if not isinstance(value,(dict,list))} for row in final_rows]
    indexed={policy:{(row["trial"],int(row["week"])):row for row in rows} for policy,rows in weekly_by_policy.items()}
    differences=[]
    for policy in summaries:
        if policy=="mandatory_only": continue
        for week in map(int,summaries[policy]["checkpoints"]):
            row={"policy":policy,"week":week}
            for metric in ("cash","debt_remaining","net_worth_after_debt","shop_purchase_count",
                           "shop_trade_count","missed_purchase_due_to_cash","inventory_expansion_spending"):
                values=[indexed[policy][trial,week][metric]-indexed["mandatory_only"][trial,week][metric]
                        for trial in range(1,baseline["trials"]+1)]
                row[metric+"_difference_mean"]=statistics.fmean(values)
                row[metric+"_difference_median"]=statistics.median(values)
            differences.append(row)
    return {"trials_per_policy":baseline["trials"],"seed":baseline["seed"],"weeks":final_week,
            "method":"same trial seeds, market/arrival/visitor random streams; each policy keeps endogenous progression",
            "previous_summary_source":str(previous_path) if previous is not None else None,
            "previous_summary":previous,"policies":summaries,"final_comparison":final_rows,
            "paired_differences":differences}


def write_comparison_report(summaries,weekly_by_policy,comparison,config,output_dir):
    summaries=comparison["policies"]; weeks=comparison["weeks"]
    e=config["economy"]; repayment=e["debt_repayment"]
    base=summaries["mandatory_only"]; old=comparison["previous_summary"]
    lines=[f"# {weeks}주 부채 상환 정책 Monte Carlo 비교", "",
        f"정책마다 {comparison['trials_per_policy']:,} trials, seed {comparison['seed']}부터 연속 seed. "
        f"시작 현금 {number(base['starting_cash'])} G, 시작 부채 {number(base['starting_debt'])} G.",
        "1주=7일, 1개월=4주. Python simulator only. 입력 config의 재고 용량·확장비와 "
        "EXPAND_IF_BLOCKED_AND_AFFORDABLE 정책, 매입·판매·fit·고객 생성·시장·progression을 유지했다.",
        "각 정책의 같은 trial 번호는 같은 seed·방문 수·시장·방문자별 난수 stream을 사용한다. "
        "정책별 거래와 평판 차이가 고객 품질에 반영되므로 이후 고객/아이템과 완료 거래는 같지 않을 수 있다. "
        "정책 비교에서 progression을 고정하지 않았다.", "",
        "## 수정 파일 및 설정", "",
        "수정: config/balance.json, simulator/config.py, simulator/economy_simulation.py, simulator/main.py, "
        "simulator/economy_design_report.py, tests/test_economy_constraints.py, README.md. "
        "추가: simulator/debt_policy_comparison.py, tests/test_debt_repayment.py.",
        "새 config: economy.debt_repayment.mandatory_weekly_payment/default_policy/policies, "
        "각 정책의 name/reserve_threshold/excess_repayment_fraction. 기존 weekly_operating_cost를 변경했다. "
        "moderate/aggressive는 metadata에도 TEMPORARY로 표기했다.",
        f"운영비 = {e['weekly_operating_cost']['first_week']:,} + (week−1)×{e['weekly_operating_cost']['weekly_increase']:,} "
        f"= 현재 설정에서 week×2,000 G. {weeks}주 합계 **{base['total_scheduled_operating_cost']:,} G**.",
        f"강제 상환 = min({repayment['mandatory_weekly_payment']:,}, debt_remaining). "
        "현금 부족 시에도 지불하며 부채를 늘리거나 신규 대출을 만들지 않는다. 부채 0 이후 지급액은 0.",
        "일요일 마지막 고객 → 운영비 → 강제 상환 → 조기 상환 → checkpoint. "
        "상환은 reputation/trade_count를 바꾸지 않는다. 순자산 = 현금+재고 감정가−남은 부채."]
    lines += table(["정책", "정산 후 reserve", "초과 현금 상환 비율", "성격"],
        [(s["name"],number(s["reserve_threshold"]),percent(s["excess_repayment_fraction"]),
          "강제 상환만" if policy=="mandatory_only" else "TEMPORARY simulation policy")
         for policy,s in repayment["policies"].items()])
    lines += ["조기 상환은 운영비와 강제 상환을 낸 뒤 남은 현금 기준이며, 남은 부채를 초과하지 않는다. "
        "50% 계산의 소수 G는 기존 float 현금 체계에서 유지한다. 상환 자체는 현금과 부채를 동일하게 줄여 "
        "순자산에 중립적이며, 정책 간 순자산 차이는 이후 거래·재고·평판의 차이로 생긴다.", "",
        f"## Week {weeks} 정책 비교", ""]
    rows=comparison["final_comparison"]
    metrics=[("중앙 현금","cash_median"),("중앙 남은 부채","debt_remaining_median"),
        ("중앙 gross assets","gross_assets_median"),("중앙 순자산","net_worth_after_debt_median"),
        ("중앙 평판","reputation_median"),("중앙 거래수","shop_trade_count_median"),
        ("중앙 재고수","inventory_count_median"),("중앙 capacity","inventory_capacity_median"),
        ("현금 매입실패 평균","missed_purchase_due_to_cash_mean"),
        ("재고 매입실패 평균","missed_purchase_due_to_inventory_mean"),
        ("조기 상환 누적 평균","optional_debt_payment_total_mean"),
        ("조기 상환 누적 중앙","optional_debt_payment_total_median")]
    lines += table(["지표",*summaries],[(label,*(number(r[key]) for r in rows)) for label,key in metrics]+
        [(label,*(percent(r[key]) for r in rows)) for label,key in (
            ("종료 음수 trial","negative_cash_trial_rate"),("음수 경험 trial","ever_negative_cash_trial_rate"),
            ("기간 내 완납 trial","debt_fully_repaid_trial_rate"))]+
        [("완납 평균/중앙 주차",*(number(r["debt_fully_repaid_week_mean"])+" / "+number(r["debt_fully_repaid_week_median"]) for r in rows))])
    lines += ["통계의 평균/중앙은 trial 단위다. 전체 상환 지출 합계는 각 정책의 평균 상환액×trial 수. "
        "checkpoint의 개별 중앙값을 더하거나 빼면 중앙 순자산과 일치하지 않을 수 있다.", "",
        "## 기존 고운영비·고정부채 실험과 비교", ""]
    if old:
        old_cost=old["total_scheduled_operating_cost"]; new_cost=base["total_scheduled_operating_cost"]
        old_weeks=old["end_day"]//e["days_per_week"]
        lines += [f"이전 데이터: {comparison['previous_summary_source']}. 이전 {old_weeks}주 총 운영비 "
            f"{old_cost:,} G, 새 {weeks}주 {new_cost:,} G: {old_cost-new_cost:,} G "
            f"({percent((old_cost-new_cost)/old_cost)}) 감소. "
            "기간이 다르게 override되면 이 합계 비교는 동일 기간 비교가 아님에 유의한다."]
        lines += table(["주", "이전 중앙 현금",*summaries],
            [(w,number(old["checkpoints"][str(w)]["cash_median"]),
              *(number(s["checkpoints"][str(w)]["cash_median"]) for s in summaries.values()))
             for w in (4,8,12) if str(w) in base["checkpoints"] and str(w) in old["checkpoints"]])
        old_final=old["checkpoints"][str(old_weeks)]
        lines += [f"이전 종료 중앙 순자산 {number(old_final['net_worth_after_debt_median'])} G, "
            f"음수 경험 trial {percent(old_final['ever_negative_cash_trial_rate'])}. "
            "이번에는 운영비 인하와 상환 도입을 함께 바꾸었으므로 이전 대비 차이를 상환 정책 하나의 효과로 해석하지 않는다."]
        lines += table(["실험", "평균 매입가", "평균 판매가", "평균/중앙 margin", "sell-through", "평균 보유일"],
            [(label,number(a["mean_purchase_price"]),number(a["mean_sale_price"]),
              percent(a["mean_margin"])+" / "+percent(a["median_margin"]),percent(a["sell_through_rate"]),number(a["mean_holding_days"]))
             for label,a in [("이전",old["analytics"])]+[(p,d["analytics"]) for p,d in summaries.items()]])
        lines += ["거래 가격/회전 변화는 운영비·상환에 따른 매입 가능 현금, 보유 재고와 progression 경로가 함께 달라진 결과다. "
            "판매 규칙이나 가격 공식을 변경한 결과는 아니다."]
    else:
        lines += ["이전 실험 JSON을 찾지 못해 이전 대비 실측 비교를 생략했다. --previous-economy-summary로 지정할 수 있다."]
    lines += ["", "## Week 8 전략적 운용과 정책별 trade-off", ""]
    if "8" in base["checkpoints"]:
        strategy=[(p,s["strategic_liquidity"]["8"]) for p,s in summaries.items()]
        lines += table(["정책", "음수 현금", "대표 아이템 매입 가능", "확장+대표 아이템 자금", "다음 필수 정산 자금", "부채 남음", "부채 남고 대표 매입 가능"],
            [(p,percent(summaries[p]["checkpoints"]["8"]["negative_cash_trial_rate"]),
              *(percent(s[key]) for key in ("can_buy_reference_item_rate","can_fund_next_expansion_plus_reference_item_rate",
                "cash_covers_next_required_settlement_rate","debt_outstanding_trial_rate","debt_outstanding_and_can_buy_reference_item_rate")))
             for p,s in strategy])
        lines += ["대표 매입가는 각 정책의 성공 매입 평균이며, 현금·공간 기준의 분석 proxy다. "
            "미래 매출을 더하지 않았다. 조기 상환 reserve는 지급 직후의 잔여 현금 기준이며, "
            "다음 주 운영비·강제 상환·아이템 매입·확장비를 별도로 확보하는 정책은 아니다."]
        for policy,s in strategy:
            r=summaries[policy]["checkpoints"]["8"]
            lines += [f"- {policy}: 8주 중앙 현금 {number(r['cash_median'])} G, 남은 부채 "
                f"평균/중앙 {number(r['debt_remaining_mean'])}/{number(r['debt_remaining_median'])} G. "
                f"강제 상환 직전 현금이 0 이상이었다가 상환으로 음수가 된 경험이 있는 trial은 "
                f"{percent(s['mandatory_payment_caused_deficit_trial_rate'])}. "
                f"부채가 남으면서 대표 매입 자금/공간을 확보한 trial은 "
                f"{percent(s['debt_outstanding_and_can_buy_reference_item_rate'])}."]
        lines += ["", "부채는 이제 순자산에서 차감되는 숫자에 더해 실제 주간 현금 압박으로 작동한다. "
            "다만 매입·재투자 선택권이 관측되는 trial 비율과 현금 부족 비율을 함께 보면, "
            "운영비 완화만으로 모든 trial에 8주차 운용 여유가 생긴 것은 아니다.", ""]
        lines += table(["조기 상환 정책 − mandatory_only", "주", "현금 차이 평균", "부채 차이 평균", "순자산 차이 평균", "매입수 차이 평균", "현금 실패 차이 평균", "확장비 차이 평균"],
            [(r["policy"],r["week"],*(number(r[key+"_difference_mean"]) for key in (
                "cash","debt_remaining","net_worth_after_debt","shop_purchase_count","missed_purchase_due_to_cash","inventory_expansion_spending")))
             for r in comparison["paired_differences"] if r["week"] in (8,12)])
        lines += ["차이는 같은 trial 번호끼리 뺀 대응 차이다. 조기 상환은 debt 부담을 앞당겨 줄이는 대신 "
            "그 자금을 아이템 매입·확장에 사용하는 선택을 줄인다. 완납 이후에는 강제 상환이 사라져 "
            "후반 현금 경로가 달라질 수 있으므로 현금 실패가 모든 trial에서 단조롭게 증가한다고 가정하지 않는다.",
            "양수 현금·매입 가능률·확장 자금률과 남은 부채를 함께 확인해야 한다. "
            "현재 음수 현금은 파산 판정이 아니며, 이 결과만으로 정책의 정답이나 balance를 자동 확정하지 않았다."]
        if "aggressive" in summaries:
            r=summaries["aggressive"]["checkpoints"][str(weeks)]
            baseline_final=base["checkpoints"][str(weeks)]
            lines += [f"aggressive의 종료 완납 비율은 {percent(r['debt_fully_repaid_trial_rate'])}, "
                f"mandatory_only는 {percent(baseline_final['debt_fully_repaid_trial_rate'])}. "
                f"동시에 누적 현금 부족 매입실패 평균은 {number(r['missed_purchase_due_to_cash_mean'])}회와 "
                f"{number(baseline_final['missed_purchase_due_to_cash_mean'])}회, 확장 지출 평균은 "
                f"{number(r['inventory_expansion_spending_mean'])} G와 "
                f"{number(baseline_final['inventory_expansion_spending_mean'])} G다. "
                "이번 표본에서 부채 감축과 거래/확장 자금 보유 사이의 차이가 관측되었다."]
    lines += ["", "## 정책별 모든 checkpoint와 주간 현금흐름", ""]
    for policy,data in summaries.items():
        lines += policy_report_lines(data,weekly_by_policy[policy])
    lines += ["## 다음 설계 결정", "",
        "- Week 8에 허용할 음수 현금 비율과, 부채가 남으면서 매입/재투자가 가능한 trial 비율의 목표를 정한다.",
        "- 다음 주 필수 정산액과 매입/확장 예산을 조기 상환 reserve에 포함할지 결정한다.",
        "- mandatory 5,000 G의 유예·기한·상한 여부, 조기 상환의 플레이어 선택 UX를 후속 설계에서 결정한다.",
        "- 운영비 곡선과 reserve/fraction 민감도 분석 범위를 정한다. 이번 실험에서는 추가 자동 조정하지 않았다.",
        "- 이자·재융자·신규 대출·파산·게임오버·이벤트는 TODO다. 상환 시스템만 이번에 구현했다.", "",
        "각 정책 폴더에 기존 CSV와 JSON/텍스트/한국어 보고서를 저장했다. 주간 CSV의 cash_before_settlement, "
        "cash_after_operating_cost, cash_after_mandatory_repayment, cash_after_optional_repayment로 정산 순서를 검증할 수 있다. "
        "debt_fully_repaid_week가 비어 있으면 아직 미완납이다. 기존 output/economy_12_weeks 결과는 보존했다.", ""]
    path=Path(output_dir)/"DEBT_POLICY_COMPARISON_KO.md"
    path.write_text("\n".join(lines),encoding="utf-8")
    return path
