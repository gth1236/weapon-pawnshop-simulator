"""Time-based seller → inventory → buyer economy simulation."""
import csv
import random
import statistics
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .buyer_fit import choose_inventory_item, interest_band
from .config import weighted_choice
from .guest_generator import generate_guest
from .price_calculator import calculate_price
from .progression import customer_progression_distributions
from .reputation_simulation import apply_reputation_delta, completed_trade_reputation_delta, _percentile
from .weapon_generator import generate_weapon


@dataclass
class InventoryItem:
    item_id: int
    weapon: object
    seller_guest: object
    purchase_day: int
    purchase_week: int
    final_purchase_price: int
    purchase_appraised_price: int
    current_appraised_price: int
    shop_listing_price: int

    def days_in_inventory(self, day): return day - self.purchase_day


@dataclass
class ShopState:
    cash: float
    reputation: float = 0.0
    shop_trade_count: int = 0
    shop_purchase_count: int = 0
    shop_sale_count: int = 0
    inventory: list = field(default_factory=list)
    realized_profit: float = 0.0
    margins: list = field(default_factory=list)
    holding_days: list = field(default_factory=list)
    counters: Counter = field(default_factory=Counter)


def roll_market(rng, config):
    powers = list(config["price"]["market_power_values"]); popularities = list(config["price"]["market_popularity_values"])
    return {name: (rng.choice(powers), rng.choice(popularities)) for name in config["guest"]["classes"]}


def revalue_item(config, item, market):
    power, popularity = market[item.weapon.item_class]
    return calculate_price(config, item.seller_guest, item.weapon, power, popularity).appraised_price


def _transaction_base(day, guest, state):
    return {"day": day, "week": (day - 1) // 7 + 1, "customer_role": guest.role, "guest_class": guest.guest_class,
            "preferred_weapon_type": guest.preferred_weapon_type, "transaction_type": "NONE", "item_id": None,
            "item_class": None, "item_type": None, "item_tier": None, "buyer_fit_score": None,
            "tier_fit": None, "preference_match": None, "fit_band": None, "purchase_price": None,
            "purchase_appraised_price": None, "current_appraised_price": None, "listing_price": None,
            "buyer_offer_price": None, "final_sale_price": None, "gross_profit": None, "margin_rate": None,
            "haggle_count": None, "outcome": None, "reputation_before": state.reputation,
            "reputation_delta": 0.0, "reputation_after": state.reputation, "trade_count": state.shop_trade_count,
            "cash_before": state.cash, "cash_after": state.cash, "days_in_inventory": None}


def _finish(row, state, delta=0.0):
    row.update(reputation_delta=delta, reputation_after=state.reputation, trade_count=state.shop_trade_count, cash_after=state.cash)
    return row


def process_seller(config, rng, state, guest, market, day, item_id):
    row = _transaction_base(day, guest, state)
    weapon, _ = generate_weapon(rng, config, guest, market)
    power, popularity = market[weapon.item_class]
    price = calculate_price(config, guest, weapon, power, popularity)
    row.update(item_id=item_id, item_class=weapon.item_class, item_type=weapon.item_type, item_tier=weapon.tier,
               purchase_appraised_price=price.appraised_price, current_appraised_price=price.appraised_price)
    if price.asking_price > price.appraised_price:
        outcome = "REJECTED_SCAMMER" if guest.kindness == "SCAMMER" else "REJECTED_OVERPRICED"
        state.counters[outcome] += 1
        raw = config["reputation"]["failed_scam_delta"] if guest.kindness == "SCAMMER" else float(weighted_choice(rng, config["reputation"]["no_purchase_deltas"]))
        delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
        row["outcome"] = outcome; return _finish(row, state, delta), item_id
    if state.cash < price.asking_price:
        state.counters["MISSED_PURCHASE_DUE_TO_CASH"] += 1; row["outcome"] = "MISSED_PURCHASE_DUE_TO_CASH"
        raw = float(weighted_choice(rng, config["reputation"]["no_purchase_deltas"]))
        delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
        return _finish(row, state, delta), item_id
    state.cash -= price.asking_price; state.shop_purchase_count += 1; state.shop_trade_count += 1
    raw = completed_trade_reputation_delta(config, guest, price.asking_price / price.appraised_price)
    delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
    listing = round(price.appraised_price * (1 + config["economy"]["listing_markup"]))
    state.inventory.append(InventoryItem(item_id, weapon, guest, day, row["week"], price.asking_price, price.appraised_price, price.appraised_price, listing))
    state.counters["SUCCESSFUL_PURCHASE"] += 1
    row.update(transaction_type="BUY_FROM_CUSTOMER", outcome="SUCCESSFUL_PURCHASE", purchase_price=price.asking_price, listing_price=listing)
    return _finish(row, state, delta), item_id + 1


def process_buyer(config, rng, state, guest, market, day):
    row = _transaction_base(day, guest, state)
    state.counters["BUYER_VISITS"] += 1
    item, fit, failure = choose_inventory_item(config, rng, guest, state.inventory)
    if failure:
        state.counters[failure] += 1; row["outcome"] = failure
        if fit: row.update(buyer_fit_score=fit.score, tier_fit=fit.tier_fit, preference_match=fit.preference_match)
        return _finish(row, state)
    current = revalue_item(config, item, market); item.current_appraised_price = current
    listing = round(current * (1 + config["economy"]["listing_markup"])); item.shop_listing_price = listing
    band = interest_band(config, fit.score)
    ceiling = current * (band["price_multiplier"] + config["economy"]["knowledge_price_adjustment"][guest.knowledge])
    offer = round(min(listing * (1 - band["desired_discount"]), ceiling))
    minimum = max(current, item.final_purchase_price * (1 + config["economy"]["minimum_profit_over_cost"]))
    row.update(item_id=item.item_id, item_class=item.weapon.item_class, item_type=item.weapon.item_type, item_tier=item.weapon.tier,
               buyer_fit_score=fit.score, tier_fit=fit.tier_fit, preference_match=fit.preference_match, fit_band=band["name"],
               purchase_price=item.final_purchase_price, purchase_appraised_price=item.purchase_appraised_price,
               current_appraised_price=current, listing_price=listing, buyer_offer_price=offer, haggle_count=band["haggles"],
               days_in_inventory=item.days_in_inventory(day))
    if offer < minimum:
        state.counters["PRICE_NEGOTIATION_FAILURE"] += 1; row["outcome"] = "PRICE_NEGOTIATION_FAILURE"
        return _finish(row, state)
    gross = offer - item.final_purchase_price; margin = gross / item.final_purchase_price
    state.cash += offer; state.inventory.remove(item); state.shop_sale_count += 1; state.shop_trade_count += 1
    state.realized_profit += gross; state.margins.append(margin); state.holding_days.append(item.days_in_inventory(day))
    raw = config["economy"]["sale_reputation_by_haggles"][str(band["haggles"])]
    delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
    state.counters["BUYER_PURCHASES"] += 1
    row.update(transaction_type="SELL_TO_CUSTOMER", outcome="BUYER_PURCHASES", final_sale_price=offer, gross_profit=gross, margin_rate=margin)
    return _finish(row, state, delta)


def snapshot(config, state, market, week, day):
    values = [revalue_item(config, item, market) for item in state.inventory]
    for item, value in zip(state.inventory, values): item.current_appraised_price = value
    cost = sum(item.final_purchase_price for item in state.inventory); value = sum(values)
    return {"week": week, "cash": state.cash, "inventory_count": len(state.inventory), "inventory_cost_basis": cost,
            "inventory_value": value, "unrealized_gain": value-cost, "net_worth": state.cash+value,
            "reputation": state.reputation, "shop_purchase_count": state.shop_purchase_count,
            "shop_sale_count": state.shop_sale_count, "shop_trade_count": state.shop_trade_count,
            "realized_profit": state.realized_profit, "mean_margin": statistics.fmean(state.margins) if state.margins else 0,
            "median_margin": statistics.median(state.margins) if state.margins else 0,
            "mean_holding_days": statistics.fmean(state.holding_days) if state.holding_days else 0,
            "median_holding_days": statistics.median(state.holding_days) if state.holding_days else 0,
            "sell_through_rate": state.shop_sale_count/state.shop_purchase_count if state.shop_purchase_count else 0,
            **state.counters}


def run_economy_trial(config, seed, weeks=None, starting_cash=None):
    rng=random.Random(seed); weeks=weeks or config["economy"]["weeks"]
    state=ShopState(float(starting_cash if starting_cash is not None else config["economy"]["starting_cash"]))
    market=roll_market(rng,config); transactions=[]; checkpoints={}; visitor=0; item_id=1
    for day in range(1,weeks*7+1):
        if day > 1 and (day-1)%7==0: market=roll_market(rng,config)
        visits=rng.randint(config["economy"]["daily_visitors"]["minimum"],config["economy"]["daily_visitors"]["maximum"])
        for _ in range(visits):
            visitor += 1; guest=generate_guest(rng,config,state.reputation,state.shop_trade_count,visitor)
            state.counters[f"{guest.role}_VISITS"] += 1
            if guest.role=="SELL_TO_SHOP": row,item_id=process_seller(config,rng,state,guest,market,day,item_id)
            else: row=process_buyer(config,rng,state,guest,market,day)
            transactions.append(row)
        week=(day-1)//7+1
        if day%7==0 and week in config["economy"]["checkpoints"]: checkpoints[week]=snapshot(config,state,market,week,day)
    return {"checkpoints":checkpoints,"transactions":transactions,"inventory":state.inventory,"state":state,"market":market}

def run_economy_monte_carlo(config, trials, seed, weeks=None, starting_cash=None):
    if trials < 1: raise ValueError("trials must be positive")
    trial_results=[run_economy_trial(config,seed+i,weeks,starting_cash) for i in range(trials)]
    checkpoints={}
    for week in config["economy"]["checkpoints"]:
        rows=[trial["checkpoints"][week] for trial in trial_results]
        summary={"week":week}
        for key in dict.fromkeys(key for row in rows for key in row):
            if key=="week": continue
            values=[row.get(key,0) for row in rows]
            summary[key+"_mean"]=statistics.fmean(values); summary[key+"_median"]=statistics.median(values)
            if key in ("cash","inventory_value","net_worth","reputation","shop_trade_count"):
                summary[key+"_p10"]=_percentile(values,.1); summary[key+"_p90"]=_percentile(values,.9)
        median_rep=summary["reputation_median"]; median_trades=summary["shop_trade_count_median"]
        summary["customer_distributions"]=customer_progression_distributions(config,median_rep,median_trades)
        checkpoints[week]=summary
    transactions=[row for trial in trial_results for row in trial["transactions"]]
    final_inventory=[item for trial in trial_results for item in trial["inventory"]]
    return {"checkpoints":checkpoints,"transactions":transactions,"final_inventory":final_inventory,"sample_trial":trial_results[0],"trials":trials,"config":config}


def economy_analytics(result):
    tx=result["transactions"]; buys=[r for r in tx if r["transaction_type"]=="BUY_FROM_CUSTOMER"]; sales=[r for r in tx if r["transaction_type"]=="SELL_TO_CUSTOMER"]
    buyers=[r for r in tx if r["customer_role"]=="BUY_FROM_SHOP"]
    fits=[r for r in buyers if r["buyer_fit_score"] is not None]
    inventory=result["final_inventory"]
    analytics={"mean_purchase_price":statistics.fmean(r["purchase_price"] for r in buys) if buys else 0,
      "mean_sale_price":statistics.fmean(r["final_sale_price"] for r in sales) if sales else 0,
      "mean_margin":statistics.fmean(r["margin_rate"] for r in sales) if sales else 0,
      "median_margin":statistics.median(r["margin_rate"] for r in sales) if sales else 0,
      "mean_holding_days":statistics.fmean(r["days_in_inventory"] for r in sales) if sales else 0,
      "sell_through_rate":len(sales)/len(buys) if buys else 0,
      "buyer_success_rate":len(sales)/len(buyers) if buyers else 0,
      "buyer_failures":Counter(r["outcome"] for r in buyers if r["transaction_type"]=="NONE"),
      "mean_success_fit":statistics.fmean(r["buyer_fit_score"] for r in sales) if sales else 0,
      "mean_failed_fit":statistics.fmean(r["buyer_fit_score"] for r in fits if r["transaction_type"]=="NONE") if any(r["transaction_type"]=="NONE" for r in fits) else 0,
      "cash_misses":sum(r["outcome"]=="MISSED_PURCHASE_DUE_TO_CASH" for r in tx)}
    end_day=max(r["day"] for r in tx)
    for days in result["config"]["economy"]["long_inventory_days"]:
        analytics[f"inventory_{days}_plus_rate"]=sum(end_day-item.purchase_day>=days for item in inventory)/len(inventory) if inventory else 0
    analytics["fit_bands"]={}
    for band in {r["fit_band"] for r in fits if r["fit_band"]}:
        rows=[r for r in fits if r["fit_band"]==band]; sold=[r for r in rows if r["transaction_type"]=="SELL_TO_CUSTOMER"]
        analytics["fit_bands"][band]={"visits":len(rows),"success_rate":len(sold)/len(rows),"average_sale_price":statistics.fmean(r["final_sale_price"] for r in sold) if sold else 0,"average_margin":statistics.fmean(r["margin_rate"] for r in sold) if sold else 0,"average_haggles":statistics.fmean(r["haggle_count"] for r in rows)}
    analytics["preference"] = {}
    for matched in (True, False):
        rows=[r for r in fits if r["preference_match"] is matched]; sold=[r for r in rows if r["transaction_type"]=="SELL_TO_CUSTOMER"]
        analytics["preference"]["MATCH" if matched else "NON_PREFERRED"]={"visits":len(rows),"success_rate":len(sold)/len(rows) if rows else 0,"average_fit":statistics.fmean(r["buyer_fit_score"] for r in rows) if rows else 0,"average_holding_days":statistics.fmean(r["days_in_inventory"] for r in sold) if sold else 0,"average_margin":statistics.fmean(r["margin_rate"] for r in sold) if sold else 0}
    analytics["tier_fit"]={}
    for low,high in ((0,.25),(.25,.5),(.5,.75),(.75,1.01)):
        rows=[r for r in fits if low <= r["tier_fit"] < high]; sold=[r for r in rows if r["transaction_type"]=="SELL_TO_CUSTOMER"]
        analytics["tier_fit"][f"{low:.2f}-{min(high,1):.2f}"]={"candidates":len(rows),"success_rate":len(sold)/len(rows) if rows else 0,"average_fit":statistics.fmean(r["buyer_fit_score"] for r in rows) if rows else 0,"average_sale_price":statistics.fmean(r["final_sale_price"] for r in sold) if sold else 0}
    stale=Counter((item.weapon.item_class,item.weapon.item_type,item.weapon.tier) for item in inventory if end_day-item.purchase_day>=30)
    analytics["top_stale_items"]=stale.most_common(10)
    return analytics


def export_rows(rows,path):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader();writer.writerows(rows)


def export_economy_reports(result, output_dir):
    output_dir=Path(output_dir)
    weekly=[]
    for row in result["checkpoints"].values():
        flat={k:v for k,v in row.items() if k!="customer_distributions"}
        for name,weights in row["customer_distributions"].items(): flat[name+"_probabilities"]=str(weights)
        weekly.append(flat)
    export_rows(weekly,output_dir/"economy_weekly_report.csv")
    export_rows(result["sample_trial"]["transactions"],output_dir/"economy_transactions.csv")
    end_day=max(r["day"] for r in result["sample_trial"]["transactions"])
    inventory=[]
    for item in result["sample_trial"]["inventory"]:
        inventory.append({"item_id":item.item_id,"item_class":item.weapon.item_class,"item_type":item.weapon.item_type,"item_tier":item.weapon.tier,"purchase_day":item.purchase_day,"purchase_week":item.purchase_week,"final_purchase_price":item.final_purchase_price,"purchase_appraised_price":item.purchase_appraised_price,"current_appraised_price":item.current_appraised_price,"shop_listing_price":item.shop_listing_price,"days_in_inventory":item.days_in_inventory(end_day)})
    export_rows(inventory,output_dir/"inventory_snapshot.csv")


def format_economy_report(result):
    lines=[f"ECONOMY SIMULATION ({result['trials']:,} trials)"]
    for week,row in result["checkpoints"].items():
        lines.append(f"Week {week}: cash median={row['cash_median']:,.0f} G, inventory value median={row['inventory_value_median']:,.0f} G, net worth median={row['net_worth_median']:,.0f} G, reputation median={row['reputation_median']:.2f}, trades median={row['shop_trade_count_median']:.0f}")
        for name, weights in row["customer_distributions"].items():
            lines.append(f"  {name}: " + ", ".join(f"{key}={value:.1%}" for key,value in weights.items()))
    a=economy_analytics(result)
    lines.append(f"Overall: purchase mean={a['mean_purchase_price']:,.0f} G, sale mean={a['mean_sale_price']:,.0f} G, margin mean/median={a['mean_margin']:.1%}/{a['median_margin']:.1%}, holding={a['mean_holding_days']:.1f} days, sell-through={a['sell_through_rate']:.1%}, buyer success={a['buyer_success_rate']:.1%}, cash misses={a['cash_misses']}")
    lines.append("Buyer failures: "+", ".join(f"{k}={v}" for k,v in a['buyer_failures'].items()))
    lines.append("Preference: "+", ".join(f"{k} success={v['success_rate']:.1%} fit={v['average_fit']:.1f} hold={v['average_holding_days']:.1f}d margin={v['average_margin']:.1%}" for k,v in a['preference'].items()))
    lines.append("Tier fit: "+", ".join(f"{k} n={v['candidates']} success={v['success_rate']:.1%} fit={v['average_fit']:.1f}" for k,v in a['tier_fit'].items()))
    lines.append("Long inventory: "+", ".join(f"{days}+d={a[f'inventory_{days}_plus_rate']:.1%}" for days in result['config']['economy']['long_inventory_days']))
    return "\n".join(lines)
