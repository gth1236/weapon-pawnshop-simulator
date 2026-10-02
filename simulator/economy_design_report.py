"""Korean economy reports from exported, reproducible simulation results."""
import argparse
import csv
import json
import statistics
from pathlib import Path

from .config import load_config


def number(value):
    return "not_repaid" if value is None else f"{value:,.2f}"


def percent(value):
    return f"{value:.1%}"


def table(headers, rows):
    lines = ["", "| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in rows)
    return lines + [""]


def read_weekly(path):
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [{key: float(value) if value else None for key,value in row.items()} for row in csv.DictReader(handle)]


def policy_report_lines(data, weekly):
    c = data["checkpoints"]; a = data["analytics"]
    final = c[str(max(map(int,c)))]; policy = data["debt_repayment_policy"]
    lines = [f"## {policy}", "", f"{data['trials']:,} trials, seed {data['seed']}부터 연속 seed, {data['end_day']}일.",
             "금액 단위 G. 평균/중앙은 trial별 누적 통계이며 매입가·판매가·margin·보유일은 완료 거래를 합쳐 집계한다.",
             "각 변수 중앙값은 같은 trial에서 나오지 않을 수 있다. debt는 debt_remaining의 호환 별칭이다."]
    lines += table(["주", "현금 평균", "중앙", "p10", "p90", "부채 평균", "중앙", "p10", "p90"],
        [(w,*(number(r[key+suffix]) for key in ("cash","debt_remaining")
               for suffix in ("_mean","_median","_p10","_p90"))) for w,r in c.items()])
    lines += table(["주", "중앙 gross assets", "중앙 순자산", "중앙 재고 감정가", "중앙 재고수", "중앙 capacity", "중앙 평판", "중앙 매입/판매/거래수"],
        [(w,*(number(r[key+"_median"]) for key in ("gross_assets","net_worth_after_debt","inventory_value",
          "inventory_count","inventory_capacity","reputation")),
          " / ".join(number(r[key+"_median"]) for key in ("shop_purchase_count","shop_sale_count","shop_trade_count"))) for w,r in c.items()])
    lines += table(["주", "현금 실패 평균/중앙", "재고 실패 평균/중앙", "음수 경험 주수 평균/중앙", "종료 음수 trial", "음수 경험 trial"],
        [(w,*(number(r[key+"_mean"])+" / "+number(r[key+"_median"])
              for key in ("missed_purchase_due_to_cash","missed_purchase_due_to_inventory","weeks_with_negative_cash")),
          percent(r["negative_cash_trial_rate"]),percent(r["ever_negative_cash_trial_rate"])) for w,r in c.items()])
    lines += table(["주", "강제 상환 누적 평균/중앙", "조기 상환 누적 평균/중앙", "전체 상환 누적 평균/중앙", "완납 trial", "완납 평균/중앙 주차"],
        [(w,*(number(r[key+"_mean"])+" / "+number(r[key+"_median"])
              for key in ("mandatory_debt_payment_total","optional_debt_payment_total","total_debt_repayment")),
          percent(r["debt_fully_repaid_trial_rate"]),number(r["debt_fully_repaid_week_mean"])+" / "+number(r["debt_fully_repaid_week_median"])) for w,r in c.items()])
    lines += ["완납 시점은 그 checkpoint까지 완납한 trial만 집계한다. 미완납은 None/not_repaid이며, "
              "시작 부채 0인 override는 week 0으로 기록한다. 상환은 현금과 부채를 같은 금액 줄이므로 "
              "상환 자체로 순자산은 바뀌지 않지만, 이후 거래에 쓸 현금은 줄어든다."]
    lines += table(["주", "확장 횟수 평균/중앙", "확장비 평균/중앙", "capacity p10/중앙/p90"],
        [(w,*(number(r[key+"_mean"])+" / "+number(r[key+"_median"])
              for key in ("inventory_expansion_count","inventory_expansion_spending")),
          " / ".join(number(r["inventory_capacity"+suffix]) for suffix in ("_p10","_median","_p90"))) for w,r in c.items()])
    lines += table(["minimum_cash 평균", "중앙", "p10", "p90", "전체 최솟값"],
        [[number(final["minimum_cash"+suffix]) for suffix in ("_mean","_median","_p10","_p90","_minimum")]])
    lines += table(["평균 매입가", "평균 판매가", "평균 margin", "중앙 margin", "sell-through", "평균 판매 재고 보유일"],
        [[number(a["mean_purchase_price"]),number(a["mean_sale_price"]),percent(a["mean_margin"]),
          percent(a["median_margin"]),percent(a["sell_through_rate"]),number(a["mean_holding_days"])]])
    lines += ["Margin = (판매가 - 매입가) / 매입가. 운영비·확장비를 제외한다. Sell-through는 판매수/매입수이며, "
              "매입 중단으로도 높아질 수 있다. 보유일은 판매된 아이템 기준이고 미판매 재고는 종료 시점에 관측이 잘린다."]
    if "8" in c:
        s=data["strategic_liquidity"]["8"]
        lines += ["", "### Week 8 현금·투자·부채 여유", "",
            f"대표 매입가는 이 정책의 전체 성공 매입 평균 {number(s['reference_purchase_price'])} G를 사용한 분석용 proxy다. "
            "확장비와 다음 정산 비용은 실제 config/잔여 부채를 사용한다. 실제 다음 seller 가격이나 매출 예측은 아니다."]
        lines += table(["지표", "trial 비율"], [(label,percent(s[key])) for label,key in (
            ("양수 현금", "positive_cash_trial_rate"),
            ("양수 현금과 판매할 재고 보유", "positive_cash_and_inventory_trial_rate"),
            ("다음 주 운영비+강제 상환 확보", "cash_covers_next_required_settlement_rate"),
            ("대표 아이템 매입 가능(필요시 확장비 포함)", "can_buy_reference_item_rate"),
            ("다음 1칸 확장비+대표 아이템 매입비 확보", "can_fund_next_expansion_plus_reference_item_rate"),
            ("부채 남아 있음", "debt_outstanding_trial_rate"),
            ("부채가 남고 대표 아이템 매입 가능", "debt_outstanding_and_can_buy_reference_item_rate"),
            ("8주 내 강제 상환으로 음수 진입 경험", "mandatory_payment_caused_deficit_trial_rate"))])
        lines += ["대표 아이템 매입 가능률은 자금과 공간만 검사한다. buyer 수요/수익성을 보장하지 않는다. "
                  "확장 자금 확보율은 실제 full 여부와 별개이며 최대 capacity 도달 trial은 추가 확장 불가로 집계한다."]
    previous={}; flow=[]
    for week in sorted({int(r["week"]) for r in weekly}):
        rows=[r for r in weekly if r["week"]==week]; profits=[]; purchases=[]; sales=[]
        for row in rows:
            old=previous.get(row["trial"],{})
            profits.append(row["realized_profit"]-old.get("realized_profit",0))
            purchases.append(row["shop_purchase_count"]-old.get("shop_purchase_count",0))
            sales.append(row["shop_sale_count"]-old.get("shop_sale_count",0))
            previous[row["trial"]]=row
        flow.append((week,number(rows[0]["weekly_operating_cost"]),
            number(statistics.fmean(r["mandatory_debt_payment"] for r in rows)),
            number(statistics.fmean(r["optional_debt_payment"] for r in rows)),
            number(statistics.fmean(profits)),number(statistics.fmean(purchases)),number(statistics.fmean(sales))))
    lines += table(["주", "운영비", "평균 강제 상환", "평균 조기 상환", "평균 실현 gross profit", "평균 매입수", "평균 판매수"],flow)
    lines += ["주간 실현 이익은 재고 평가손익을 포함하지 않는다. 원금 상환은 비용이 아니지만 현금 유출이다. "
              "가격 거절이 먼저 적용되고, 재고와 현금 부족이 겹치면 기존 규칙대로 재고 실패만 기록한다.", ""]
    return lines


def write_design_report(output_dir, config):
    output_dir=Path(output_dir)
    data=json.loads((output_dir/"economy_summary.json").read_text(encoding="utf-8"))
    weekly=read_weekly(output_dir/"economy_trial_weekly_report.csv")
    e=data.get("balance_settings",config["economy"])
    lines=["# Python 경제·부채 상환 실험", "",
        f"시작 현금 {number(data['starting_cash'])} G, 시작 부채 {number(data['starting_debt'])} G. "
        f"운영비 = {e['weekly_operating_cost']['first_week']:,} + (week−1) × {e['weekly_operating_cost']['weekly_increase']:,}; "
        f"기간 총 운영비 {number(data['total_scheduled_operating_cost'])} G.",
        "일요일 마지막 고객 → 운영비 → 강제 상환 → 선택적 조기 상환 → checkpoint → 다음 주. "
        "부채와 현금은 상환액만큼 함께 감소하며 초과 상환하지 않는다. "
        "강제 지급은 음수 현금을 허용하고 새 대출·이자·파산은 생성하지 않는다.",
        "TEMPORARY: moderate/aggressive 조기 상환 정책, 자동 확장 정책, 음수 현금 허용. 자동 밸런스 조정 없음.", ""]
    if not e['debt_repayment']['enabled']:
        lines = ["# Python reference implementation sanity check", "",
            f"시작 현금 {number(data['starting_cash'])} G, 부채·상환·이자 없음. 순자산 = 현금 + 현재 재고 감정가.",
            f"운영비 = 2,000 × week; 기간 합계 {number(data['total_scheduled_operating_cost'])} G.",
            f"재고 {e['initial_inventory_capacity']} → {e['maximum_inventory_capacity']}칸, 슬롯당 확장비 {number(e['inventory_expansion_cost'])} G.",
            "확장·고물상 처분은 게임에서 플레이어 선택이다. baseline은 자동 매입·판매·확장 heuristic을 사용하고 자동 scrap은 하지 않는다.",
            "음수 현금 허용은 simulation-only 정책이며 실제 게임의 현금 부족 처리는 플레이 테스트 후 결정한다.", ""]
    lines += policy_report_lines(data,weekly)
    lines += ["전체 분위수·progression·capacity 체류 시간은 economy_summary.json과 economy_report.txt, "
        "각 trial의 모든 주간 정산은 economy_trial_weekly_report.csv에 기록한다. "
        "economy_transactions.csv와 inventory_snapshot.csv는 첫 trial의 표본이다.", ""]
    path=output_dir/"DESIGN_ANALYSIS_KO.md"
    path.write_text("\n".join(lines),encoding="utf-8")
    return path


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("output_dir",type=Path)
    parser.add_argument("--config",type=Path)
    args=parser.parse_args()
    print(write_design_report(args.output_dir,load_config(args.config) if args.config else load_config()))
