"""Time-based seller → inventory → buyer economy simulation."""
import csv
import json
import math
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
from .models import WeaponKnownState


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
    known_state: WeaponKnownState | None = None

    def days_in_inventory(self, day): return day - self.purchase_day


@dataclass
class ShopState:
    cash: float
    debt_remaining: float
    inventory_capacity: int
    reputation: float = 0.0
    shop_trade_count: int = 0
    shop_purchase_count: int = 0
    shop_sale_count: int = 0
    inventory: list = field(default_factory=list)
    realized_profit: float = 0.0
    margins: list = field(default_factory=list)
    holding_days: list = field(default_factory=list)
    counters: Counter = field(default_factory=Counter)
    inventory_expansion_count: int = 0
    inventory_expansion_spending: float = 0.0
    total_operating_cost_paid: float = 0.0
    weeks_with_negative_cash: int = 0
    cash_deficit_events: int = 0
    minimum_cash: float = float("inf")
    first_expansion_day: int | None = None
    capacity_days: Counter = field(default_factory=Counter)
    enforce_capacity: bool = True
    mandatory_debt_payment_total: float = 0.0
    optional_debt_payment_total: float = 0.0
    debt_fully_repaid_week: int | None = None
    scrap_count: int = 0
    scrap_revenue: float = 0.0
    scrap_cost_basis: float = 0.0
    scrap_realized_loss: float = 0.0
    inventory_actions: list = field(default_factory=list)

    @property
    def debt(self):
        """Compatibility alias: debt is now the outstanding balance."""
        return self.debt_remaining

    @property
    def total_debt_repayment(self):
        return self.mandatory_debt_payment_total + self.optional_debt_payment_total

    @property
    def cash_deficit(self):
        return self.cash < 0


def create_shop_state(config, starting_cash=None, starting_debt=None, enforce_capacity=True):
    economy = config["economy"]
    cash = float(economy["starting_cash"] if starting_cash is None else starting_cash)
    debt = float(economy["starting_debt"] if starting_debt is None else starting_debt)
    if not math.isfinite(cash) or not math.isfinite(debt) or debt < 0:
        raise ValueError("starting cash must be finite; starting debt must be finite and non-negative")
    if debt and not economy["debt_repayment"]["enabled"]:
        raise ValueError("Debt is disabled in current game rules; enable it only in a historical experiment config")
    return ShopState(cash=cash, debt_remaining=debt, inventory_capacity=economy["initial_inventory_capacity"],
                     minimum_cash=cash, enforce_capacity=enforce_capacity,
                     debt_fully_repaid_week=0 if debt == 0 else None)


def weekly_operating_cost(config, week):
    if week < 1:
        raise ValueError("week must be positive")
    costs = config["economy"]["weekly_operating_cost"]
    return costs["first_week"] + (week - 1) * costs["weekly_increase"]


def observe_cash(state, previous_cash):
    state.minimum_cash = min(state.minimum_cash, state.cash)
    # A deficit event means entry/re-entry into cash < 0, not every negative payment.
    if previous_cash >= 0 and state.cash < 0:
        state.cash_deficit_events += 1


def pay_weekly_operating_cost(config, state, week, multiplier=1):
    cost = weekly_operating_cost(config, week) * multiplier
    previous = state.cash
    state.cash -= cost
    state.total_operating_cost_paid += cost
    observe_cash(state, previous)
    state.weeks_with_negative_cash += int(state.cash < 0)
    return cost


def repayment_policy(config, policy=None):
    settings = config["economy"]["debt_repayment"]
    policy = settings["default_policy"] if policy is None else policy
    if policy not in settings["policies"]:
        raise ValueError(f"Unknown debt repayment policy: {policy}")
    return policy, settings["policies"][policy]


def _repay_debt(state, amount, week):
    payment = min(amount, state.debt_remaining)
    previous = state.cash
    state.cash -= payment
    state.debt_remaining -= payment
    observe_cash(state, previous)
    if state.debt_remaining == 0 and state.debt_fully_repaid_week is None:
        state.debt_fully_repaid_week = week
    return payment


def pay_mandatory_debt(config, state, week):
    if not config["economy"]["debt_repayment"]["enabled"]:
        return 0
    payment = _repay_debt(state, config["economy"]["debt_repayment"]["mandatory_weekly_payment"], week)
    state.mandatory_debt_payment_total += payment
    return payment


def pay_optional_debt(config, state, week, policy=None):
    if not config["economy"]["debt_repayment"]["enabled"]:
        return 0
    _, settings = repayment_policy(config, policy)
    excess = max(0.0, state.cash - settings["reserve_threshold"])
    payment = _repay_debt(state, excess * settings["excess_repayment_fraction"], week)
    state.optional_debt_payment_total += payment
    return payment


def settle_week(config, state, week, policy=None, operating_cost_multiplier=1):
    """Called after Sunday's last customer; retain an auditable ordered ledger."""
    repayment_policy(config, policy)
    negative_weeks_before = state.weeks_with_negative_cash
    ledger = {"cash_before_settlement": state.cash, "debt_before_settlement": state.debt_remaining}
    ledger["weekly_operating_cost"] = pay_weekly_operating_cost(config, state, week, operating_cost_multiplier)
    ledger["cash_after_operating_cost"] = state.cash
    ledger["mandatory_debt_payment"] = pay_mandatory_debt(config, state, week)
    ledger["cash_after_mandatory_repayment"] = state.cash
    ledger["debt_after_mandatory_repayment"] = state.debt_remaining
    ledger["optional_debt_payment"] = pay_optional_debt(config, state, week, policy)
    ledger["cash_after_optional_repayment"] = state.cash
    # Mandatory repayment can be the first negative point of the settlement.
    # The trial loop additionally includes negative cash observed during trading.
    state.weeks_with_negative_cash = negative_weeks_before + int(state.cash < 0)
    return ledger


def expand_inventory(config, state, day=None):
    """Player-selected game action: buy exactly one slot, independently of items."""
    economy = config["economy"]
    cost = economy["inventory_expansion_cost"]
    if state.inventory_capacity >= economy["maximum_inventory_capacity"] or state.cash < cost:
        return False
    before = state.cash
    state.cash -= cost
    state.inventory_capacity += 1
    state.inventory_expansion_count += 1
    state.inventory_expansion_spending += cost
    if state.first_expansion_day is None:
        state.first_expansion_day = day
    observe_cash(state, before)
    state.inventory_actions.append({"action": "EXPAND_INVENTORY", "day": day, "cost": cost,
                                   "capacity": state.inventory_capacity, "cash_before": before, "cash_after": state.cash})
    return True


def scrap_inventory_item(config, state, item_id, day=None):
    """Explicit junk-shop action; never part of the automatic customer loop."""
    item = next((item for item in state.inventory if item.item_id == item_id), None)
    if item is None:
        raise ValueError(f"Item is not owned by this shop: {item_id}")
    cost = item.final_purchase_price
    revenue = round(cost * config["economy"]["scrap_purchase_price_ratio"])
    before = state.cash
    state.cash += revenue
    state.inventory.remove(item)
    state.scrap_count += 1
    state.scrap_revenue += revenue
    state.scrap_cost_basis += cost
    state.scrap_realized_loss += cost - revenue
    observe_cash(state, before)
    row = {"action": "SCRAP", "day": day, "item_id": item_id, "scrap_revenue": revenue,
           "scrap_cost_basis": cost, "scrap_realized_loss": cost-revenue,
           "cash_before": before, "cash_after": state.cash}
    state.inventory_actions.append(row)
    return row


def ensure_inventory_space(config, state, purchase_price, day):
    """Simulation-only decision policy; the game calls expand_inventory explicitly."""
    if not state.enforce_capacity or len(state.inventory) < state.inventory_capacity:
        return True
    state.counters["INVENTORY_FULL_EVENTS"] += 1
    economy = config["economy"]
    if config["simulation_policies"]["inventory_expansion"] == "MANUAL_ONLY":
        return False
    if state.inventory_capacity < economy["maximum_inventory_capacity"]:
        cost = economy["inventory_expansion_cost"]
        if state.cash > 0 and state.cash >= cost + purchase_price:
            return expand_inventory(config, state, day)
    return False


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
    observe_cash(state, row["cash_before"])
    row.update(reputation_delta=delta, reputation_after=state.reputation, trade_count=state.shop_trade_count, cash_after=state.cash)
    row.update(inventory_count=len(state.inventory), inventory_capacity=state.inventory_capacity,
               debt=state.debt_remaining, debt_remaining=state.debt_remaining, cash_deficit=state.cash_deficit,
               inventory_expansion_count=state.inventory_expansion_count,
               inventory_expansion_spending=state.inventory_expansion_spending)
    return row


def process_seller(config, rng, state, guest, market, day, item_id):
    row = _transaction_base(day, guest, state)
    weapon, known = generate_weapon(rng, config, guest, market)
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
    if not ensure_inventory_space(config, state, price.asking_price, day):
        state.counters["MISSED_PURCHASE_DUE_TO_INVENTORY"] += 1
        row["outcome"] = "INVENTORY_FULL"
        raw = float(weighted_choice(rng, config["reputation"]["no_purchase_deltas"]))
        delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
        return _finish(row, state, delta), item_id
    if state.cash <= 0 or state.cash < price.asking_price:
        state.counters["MISSED_PURCHASE_DUE_TO_CASH"] += 1; row["outcome"] = "MISSED_PURCHASE_DUE_TO_CASH"
        raw = float(weighted_choice(rng, config["reputation"]["no_purchase_deltas"]))
        delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
        return _finish(row, state, delta), item_id
    state.cash -= price.asking_price; state.shop_purchase_count += 1; state.shop_trade_count += 1
    raw = completed_trade_reputation_delta(config, guest, price.asking_price / price.appraised_price)
    delta = apply_reputation_delta(config, state.reputation, raw); state.reputation += delta
    listing = round(price.appraised_price * (1 + config["economy"]["listing_markup"]))
    state.inventory.append(InventoryItem(item_id, weapon, guest, day, row["week"], price.asking_price, price.appraised_price, price.appraised_price, listing, known))
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
    return {"week": week, "cash": state.cash, "debt": state.debt_remaining,
            "scrap_count": state.scrap_count, "scrap_revenue": state.scrap_revenue,
            "scrap_cost_basis": state.scrap_cost_basis, "scrap_realized_loss": state.scrap_realized_loss,
            "debt_remaining": state.debt_remaining,
            "mandatory_debt_payment_total": state.mandatory_debt_payment_total,
            "optional_debt_payment_total": state.optional_debt_payment_total,
            "total_debt_repayment": state.total_debt_repayment,
            "debt_fully_repaid_week": state.debt_fully_repaid_week,
            "gross_assets": state.cash+value, "net_worth_after_debt": state.cash+value-state.debt,
            "inventory_count": len(state.inventory), "inventory_capacity": state.inventory_capacity,
            "free_slots": state.inventory_capacity-len(state.inventory), "inventory_cost_basis": cost,
            "inventory_value": value, "unrealized_gain": value-cost, "net_worth": state.cash+value-state.debt,
            "weekly_operating_cost": weekly_operating_cost(config, week),
            "total_operating_cost_paid": state.total_operating_cost_paid,
            "gross_assets_before_operating_cost_ledger": state.cash+value+state.total_operating_cost_paid,
            "cash_before_operating_cost_ledger": state.cash+state.total_operating_cost_paid,
            "inventory_expansion_count": state.inventory_expansion_count,
            "inventory_expansion_spending": state.inventory_expansion_spending,
            "missed_purchase_due_to_cash": state.counters["MISSED_PURCHASE_DUE_TO_CASH"],
            "missed_purchase_due_to_inventory": state.counters["MISSED_PURCHASE_DUE_TO_INVENTORY"],
            "inventory_full_events": state.counters["INVENTORY_FULL_EVENTS"],
            "weeks_with_negative_cash": state.weeks_with_negative_cash,
            "cash_deficit_events": state.cash_deficit_events, "minimum_cash": state.minimum_cash,
            "cash_deficit": int(state.cash_deficit),
            "reputation": state.reputation, "shop_purchase_count": state.shop_purchase_count,
            "shop_sale_count": state.shop_sale_count, "shop_trade_count": state.shop_trade_count,
            "realized_profit": state.realized_profit, "mean_margin": statistics.fmean(state.margins) if state.margins else 0,
            "median_margin": statistics.median(state.margins) if state.margins else 0,
            "mean_holding_days": statistics.fmean(state.holding_days) if state.holding_days else 0,
            "median_holding_days": statistics.median(state.holding_days) if state.holding_days else 0,
            "sell_through_rate": state.shop_sale_count/state.shop_purchase_count if state.shop_purchase_count else 0,
            **state.counters}


def run_economy_trial(config, seed, weeks=None, starting_cash=None, starting_debt=None,
                      operating_cost_multiplier=1, enforce_capacity=True, replay_flow=None,
                      debt_repayment_policy=None):
    weeks=config["economy"]["weeks"] if weeks is None else weeks
    if weeks < 1: raise ValueError("weeks must be positive")
    policy, _ = repayment_policy(config, debt_repayment_policy)
    state=create_shop_state(config, starting_cash, starting_debt, enforce_capacity)
    # Separate exogenous streams and one stream per visitor keep paired experiments aligned.
    market_rng=random.Random(f"{seed}:market"); arrival_rng=random.Random(f"{seed}:arrivals")
    market=roll_market(market_rng,config); transactions=[]; checkpoints={}; weekly=[]; visitor=0; item_id=1; visitor_flow=[]
    days_per_week=config["economy"]["days_per_week"]
    negative_during_week=state.cash < 0
    for day in range(1,weeks*days_per_week+1):
        if day > 1 and (day-1)%days_per_week==0: market=roll_market(market_rng,config)
        visits=arrival_rng.randint(config["economy"]["daily_visitors"]["minimum"],config["economy"]["daily_visitors"]["maximum"])
        for _ in range(visits):
            # Fractional days assume visits evenly spaced; capacities sum to the full duration.
            state.capacity_days[state.inventory_capacity] += 1 / visits
            visitor += 1; rng=random.Random(f"{seed}:visitor:{visitor}")
            progression_state=(state.reputation,state.shop_trade_count) if replay_flow is None else replay_flow[visitor-1]
            visitor_flow.append(progression_state)
            guest=generate_guest(rng,config,*progression_state,visitor)
            state.counters[f"{guest.role}_VISITS"] += 1
            if guest.role=="SELL_TO_SHOP": row,item_id=process_seller(config,rng,state,guest,market,day,item_id)
            else: row=process_buyer(config,rng,state,guest,market,day)
            transactions.append(row)
            negative_during_week |= state.cash < 0
        week=(day-1)//days_per_week+1
        if day%days_per_week==0:
            previous_negative_weeks=state.weeks_with_negative_cash
            settlement=settle_week(config,state,week,policy,operating_cost_multiplier)
            negative_during_week |= state.cash < 0
            state.weeks_with_negative_cash=previous_negative_weeks+int(negative_during_week)
            negative_during_week=False
            row=snapshot(config,state,market,week,day)
            row.update(settlement)
            weekly.append(row)
            if week in config["economy"]["checkpoints"] or week == weeks: checkpoints[week]=row
    return {"checkpoints":checkpoints,"weekly":weekly,"transactions":transactions,"inventory":state.inventory,
            "state":state,"market":market,"end_day":weeks*days_per_week,"visitor_flow":visitor_flow,
            "debt_repayment_policy":policy}

def run_economy_monte_carlo(config, trials=None, seed=12345, weeks=None, starting_cash=None,
                           starting_debt=None, operating_cost_multiplier=1, enforce_capacity=True,
                           retain_transactions=True, replay_trials=None, debt_repayment_policy=None):
    trials=config["economy"]["trials"] if trials is None else trials
    if trials < 1: raise ValueError("trials must be positive")
    trial_results=[]; transactions=[]
    for i in range(trials):
        trial=run_economy_trial(config,seed+i,weeks,starting_cash,starting_debt,
                                operating_cost_multiplier,enforce_capacity,
                                replay_flow=None if replay_trials is None else replay_trials[i]["visitor_flow"],
                                debt_repayment_policy=debt_repayment_policy)
        if retain_transactions: transactions.extend(trial["transactions"])
        if i: trial["transactions"]=[]
        trial_results.append(trial)
    checkpoints={}
    for week in trial_results[0]["checkpoints"]:
        rows=[trial["checkpoints"][week] for trial in trial_results]
        summary={"week":week}
        for key in dict.fromkeys(key for row in rows for key in row):
            if key in ("week", "debt_fully_repaid_week"): continue
            values=[row.get(key,0) for row in rows]
            summary[key+"_mean"]=statistics.fmean(values); summary[key+"_median"]=statistics.median(values)
            summary[key+"_p10"]=_percentile(values,.1); summary[key+"_p90"]=_percentile(values,.9)
            summary[key+"_minimum"]=min(values)
        # Average each trial's actual conditional progression probabilities, not probabilities at median state.
        distributions=[customer_progression_distributions(config,row["reputation"],row["shop_trade_count"]) for row in rows]
        summary["customer_distributions"]={name:{category:statistics.fmean(d[name][category] for d in distributions)
                 for category in weights} for name,weights in distributions[0].items()}
        summary["capacity_distribution"]={label:sum(low <= row["inventory_capacity"] <= high for row in rows)/trials
                for label,low,high in (("5",5,5),("6-9",6,9),("10-14",10,14),("15-19",15,19),("20",20,20))}
        summary["negative_cash_trial_rate"]=sum(row["cash"]<0 for row in rows)/trials
        summary["ever_negative_cash_trial_rate"]=sum(row["minimum_cash"]<0 for row in rows)/trials
        repaid_weeks=[row["debt_fully_repaid_week"] for row in rows if row["debt_fully_repaid_week"] is not None]
        summary["debt_fully_repaid_trial_rate"]=len(repaid_weeks)/trials
        summary["debt_fully_repaid_week_mean"]=statistics.fmean(repaid_weeks) if repaid_weeks else None
        summary["debt_fully_repaid_week_median"]=statistics.median(repaid_weeks) if repaid_weeks else None
        checkpoints[week]=summary
    final_inventory=[item for trial in trial_results for item in trial["inventory"]]
    first_days=[trial["state"].first_expansion_day for trial in trial_results if trial["state"].first_expansion_day is not None]
    capacity_days={str(capacity):statistics.fmean(trial["state"].capacity_days[capacity] for trial in trial_results)
                   for capacity in range(config["economy"]["initial_inventory_capacity"],config["economy"]["maximum_inventory_capacity"]+1)}
    return {"checkpoints":checkpoints,"transactions":transactions,"final_inventory":final_inventory,
            "sample_trial":trial_results[0],"trial_results":trial_results,"trials":trials,"config":config,
            "seed":seed,"end_day":trial_results[0]["end_day"],
            "debt_repayment_policy":trial_results[0]["debt_repayment_policy"],
            "first_expansion_day_mean":statistics.fmean(first_days) if first_days else None,
            "first_expansion_day_median":statistics.median(first_days) if first_days else None,
            "first_expansion_week_mean":statistics.fmean((day-1)//config["economy"]["days_per_week"]+1 for day in first_days) if first_days else None,
            "expanded_trial_rate":len(first_days)/trials,"capacity_days_mean":capacity_days}


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
    end_day=result["end_day"]
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


def export_rows(rows,path,fieldnames=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fieldnames = fieldnames or list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w",newline="",encoding="utf-8") as f:
        writer=csv.DictWriter(f,fieldnames=fieldnames);writer.writeheader();writer.writerows(rows)


def export_economy_reports(result, output_dir):
    output_dir=Path(output_dir)
    weekly=[]
    for row in result["checkpoints"].values():
        flat={k:v for k,v in row.items() if k not in ("customer_distributions", "capacity_distribution")}
        for name, probability in row["capacity_distribution"].items(): flat["capacity_"+name+"_rate"]=probability
        for name,weights in row["customer_distributions"].items(): flat[name+"_probabilities"]=str(weights)
        weekly.append(flat)
    export_rows(weekly,output_dir/"economy_weekly_report.csv")
    export_rows([{"trial":i+1, **row} for i,trial in enumerate(result["trial_results"]) for row in trial["weekly"]],
                output_dir/"economy_trial_weekly_report.csv")
    export_rows(result["sample_trial"]["transactions"],output_dir/"economy_transactions.csv")
    export_rows(result["sample_trial"]["state"].inventory_actions,output_dir/"inventory_actions.csv",
                fieldnames=["action","day","item_id","cost","capacity","scrap_revenue","scrap_cost_basis",
                            "scrap_realized_loss","cash_before","cash_after"])
    end_day=result["end_day"]
    inventory=[]
    for item in result["sample_trial"]["inventory"]:
        inventory.append({"item_id":item.item_id,"item_class":item.weapon.item_class,"item_type":item.weapon.item_type,"item_tier":item.weapon.tier,"purchase_day":item.purchase_day,"purchase_week":item.purchase_week,"final_purchase_price":item.final_purchase_price,"purchase_appraised_price":item.purchase_appraised_price,"current_appraised_price":item.current_appraised_price,"shop_listing_price":item.shop_listing_price,"days_in_inventory":item.days_in_inventory(end_day),
                          "player_visible_json":json.dumps(item.known_state.player_view(),ensure_ascii=False) if item.known_state else None})
    export_rows(inventory,output_dir/"inventory_snapshot.csv",fieldnames=["item_id","item_class","item_type","item_tier",
        "purchase_day","purchase_week","final_purchase_price","purchase_appraised_price","current_appraised_price",
        "shop_listing_price","days_in_inventory","player_visible_json"])
    summary={key:result[key] for key in ("checkpoints","trials","seed","end_day","first_expansion_day_mean",
           "first_expansion_day_median","first_expansion_week_mean","expanded_trial_rate","capacity_days_mean",
           "debt_repayment_policy")}
    summary["analytics"]=economy_analytics(result)
    summary["starting_cash"]=result["sample_trial"]["transactions"][0]["cash_before"]
    state=result["sample_trial"]["state"]
    summary["starting_debt"]=state.debt_remaining+state.total_debt_repayment
    summary["balance_settings"]=result["config"]["economy"]
    summary["simulation_policies"]=result["config"]["simulation_policies"]
    summary["strategic_liquidity"]=strategic_liquidity(result,summary["analytics"]["mean_purchase_price"])
    summary["comparisons"]=result.get("comparisons",{})
    summary["total_scheduled_operating_cost"]=sum(weekly_operating_cost(result["config"],week)
            for week in range(1,result["end_day"]//result["config"]["economy"]["days_per_week"]+1))
    with (output_dir/"economy_summary.json").open("w",encoding="utf-8") as handle:
        json.dump(summary,handle,ensure_ascii=False,indent=2)
    (output_dir/"economy_report.txt").write_text(format_economy_report(result),encoding="utf-8")
    from .economy_design_report import write_design_report
    write_design_report(output_dir,result["config"])
    return summary


def strategic_liquidity(result, reference_purchase_price):
    """Cash-only readiness proxies, not forecasts of future guests or prices."""
    economy=result["config"]["economy"]; output={}
    for week in result["checkpoints"]:
        counts=Counter()
        for trial in result["trial_results"]:
            row=trial["checkpoints"][week]
            cash, debt, capacity = row["cash"], row["debt_remaining"], row["inventory_capacity"]
            next_required=weekly_operating_cost(result["config"],week+1)+min(
                economy["debt_repayment"]["mandatory_weekly_payment"],debt)
            next_expansion=economy["inventory_expansion_cost"]
            can_expand=capacity<economy["maximum_inventory_capacity"] and next_expansion is not None
            item_space=row["inventory_count"]<capacity
            expansion_and_item=can_expand and cash>0 and cash>=next_expansion+reference_purchase_price
            can_buy=(cash>0 and cash>=reference_purchase_price and item_space) or expansion_and_item
            counts["positive_cash_trial_rate"] += cash>0
            counts["positive_cash_and_inventory_trial_rate"] += cash>0 and row["inventory_count"]>0
            counts["cash_covers_next_required_settlement_rate"] += cash>=next_required
            counts["can_buy_reference_item_rate"] += can_buy
            counts["can_fund_next_expansion_plus_reference_item_rate"] += expansion_and_item
            counts["debt_outstanding_trial_rate"] += debt>0
            counts["debt_outstanding_and_can_buy_reference_item_rate"] += debt>0 and can_buy
            counts["mandatory_payment_caused_deficit_trial_rate"] += any(
                r["cash_after_operating_cost"]>=0 and r["cash_after_mandatory_repayment"]<0
                for r in trial["weekly"] if r["week"]<=week)
        output[week]={key:value/result["trials"] for key,value in counts.items()}
        output[week]["reference_purchase_price"]=reference_purchase_price
    return output


def add_economy_comparisons(result, starting_cash=None, starting_debt=None):
    """Replay baseline visitor progression inputs for identical offered trade flow.

    The ledger add-back is the exact same-trades comparison. Re-simulation allows
    liquidity/inventory feedback. Completed trades differ but offered guests/items
    are held fixed at baseline: no counterfactual guest-progression feedback.
    """
    config=result["config"]; weeks=result["end_day"]//config["economy"]["days_per_week"]
    comparisons={}
    for label,cost_multiplier,capacity in (("no_operating_cost",0,True),("unlimited_inventory",1,False)):
        reference=run_economy_monte_carlo(config,result["trials"],result["seed"],weeks,
                    starting_cash,starting_debt,cost_multiplier,capacity,retain_transactions=False,
                    replay_trials=result["trial_results"],debt_repayment_policy=result["debt_repayment_policy"])
        checkpoints={}
        for week,actual in result["checkpoints"].items():
            other=reference["checkpoints"][week]
            entry={key:other[key] for key in ("cash_median","gross_assets_median","net_worth_after_debt_median",
                "inventory_count_median","inventory_value_median","shop_trade_count_median","mean_holding_days_mean")}
            for metric in ("cash","net_worth_after_debt"):
                differences=[b["checkpoints"][week][metric]-a["checkpoints"][week][metric]
                             for a,b in zip(result["trial_results"],reference["trial_results"])]
                entry[metric+"_paired_difference_mean"]=statistics.fmean(differences)
                entry[metric+"_paired_difference_median"]=statistics.median(differences)
            checkpoints[week]=entry
        inventory=reference["final_inventory"]
        stale={str(days):sum(reference["end_day"]-item.purchase_day>=days for item in inventory)/len(inventory) if inventory else 0
               for days in config["economy"]["long_inventory_days"]}
        holds=[day for trial in reference["trial_results"] for day in trial["state"].holding_days]
        comparisons[label]={"checkpoints":checkpoints,"long_inventory_rates":stale,
                    "mean_sold_holding_days":statistics.fmean(holds) if holds else 0,
                    "final_unsold_count":len(inventory),"final_unsold_30_plus_count":sum(reference["end_day"]-item.purchase_day>=30 for item in inventory)}
    result["comparisons"]=comparisons
    return result


def format_economy_report(result):
    lines=[f"ECONOMY SIMULATION ({result['trials']:,} trials, seed={result['seed']}, {result['end_day']} days)",
           f"Debt policy: {result['debt_repayment_policy']}; operating cost -> mandatory -> optional repayment.",
           "TEMPORARY early-repayment/expansion policies and negative-cash rule. No interest or new borrowing.",
           "Margins = (sale - purchase) / purchase, excluding operating and expansion costs."]
    for week,row in result["checkpoints"].items():
        lines.append(f"Week {week}: cash median={row['cash_median']:,.0f} G, inventory value median={row['inventory_value_median']:,.0f} G, net worth median={row['net_worth_median']:,.0f} G, reputation median={row['reputation_median']:.2f}, trades median={row['shop_trade_count_median']:.0f}")
        for metric in ("cash","debt_remaining","gross_assets","net_worth_after_debt","inventory_count","inventory_capacity",
                       "mandatory_debt_payment_total","optional_debt_payment_total","total_debt_repayment",
                       "free_slots","inventory_cost_basis","inventory_value","shop_purchase_count","shop_sale_count",
                       "shop_trade_count","realized_profit","mean_margin","median_margin","reputation",
                       "inventory_full_events","missed_purchase_due_to_inventory","missed_purchase_due_to_cash",
                       "inventory_expansion_count","inventory_expansion_spending","total_operating_cost_paid",
                       "weeks_with_negative_cash","cash_deficit_events","minimum_cash",
                       "cash_before_operating_cost_ledger","gross_assets_before_operating_cost_ledger"):
            lines.append(f"  {metric}: mean={row[metric+'_mean']:,.2f}, median={row[metric+'_median']:,.2f}, p10={row[metric+'_p10']:,.2f}, p90={row[metric+'_p90']:,.2f}, minimum={row[metric+'_minimum']:,.2f}")
        lines.append("  Capacity distribution: "+", ".join(f"{key}={value:.1%}" for key,value in row["capacity_distribution"].items()))
        lines.append(f"  Negative cash now/ever: {row['negative_cash_trial_rate']:.1%}/{row['ever_negative_cash_trial_rate']:.1%}")
        lines.append(f"  Debt fully repaid: {row['debt_fully_repaid_trial_rate']:.1%}; completion week mean/median (repaid only): {row['debt_fully_repaid_week_mean']}/{row['debt_fully_repaid_week_median']}")
        for name, weights in row["customer_distributions"].items():
            lines.append(f"  {name}: " + ", ".join(f"{key}={value:.1%}" for key,value in weights.items()))
    a=economy_analytics(result)
    lines.append(f"Overall: purchase mean={a['mean_purchase_price']:,.0f} G, sale mean={a['mean_sale_price']:,.0f} G, margin mean/median={a['mean_margin']:.1%}/{a['median_margin']:.1%}, holding={a['mean_holding_days']:.1f} days, sell-through={a['sell_through_rate']:.1%}, buyer success={a['buyer_success_rate']:.1%}, cash misses={a['cash_misses']}")
    lines.append("Buyer failures: "+", ".join(f"{k}={v}" for k,v in a['buyer_failures'].items()))
    lines.append("Preference: "+", ".join(f"{k} success={v['success_rate']:.1%} fit={v['average_fit']:.1f} hold={v['average_holding_days']:.1f}d margin={v['average_margin']:.1%}" for k,v in a['preference'].items()))
    lines.append("Tier fit: "+", ".join(f"{k} n={v['candidates']} success={v['success_rate']:.1%} fit={v['average_fit']:.1f}" for k,v in a['tier_fit'].items()))
    lines.append("Long inventory: "+", ".join(f"{days}+d={a[f'inventory_{days}_plus_rate']:.1%}" for days in result['config']['economy']['long_inventory_days']))
    lines.append(f"First expansion (expanded trials only): mean day={result['first_expansion_day_mean']}, median day={result['first_expansion_day_median']}, mean week={result['first_expansion_week_mean']}, expanded trials={result['expanded_trial_rate']:.1%}")
    lines.append("Capacity mean residence days (uniform visit spacing): "+str(result["capacity_days_mean"]))
    lines.append("Game rule: each expansion costs "+str(result["config"]["economy"]["inventory_expansion_cost"])+" G; automatic decisions are simulation-only.")
    lines.append("Scheduled operating costs total: "+str(sum(weekly_operating_cost(result["config"],week) for week in range(1,result["end_day"]//result["config"]["economy"]["days_per_week"]+1))))
    for label,comparison in result.get("comparisons",{}).items():
        lines.append(label+" (identical baseline guests/items replayed; liquidity changes completed trades; guest progression frozen):")
        for week,row in comparison["checkpoints"].items(): lines.append(f"  Week {week}: "+str(row))
        lines.append("  Holding/stale inventory: "+str({k:v for k,v in comparison.items() if k!="checkpoints"}))
    return "\n".join(lines)
