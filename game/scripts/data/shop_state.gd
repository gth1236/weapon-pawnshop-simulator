class_name ShopState
extends RefCounted

var day = 1
var week = 1
var cash = 0
var starting_cash = 0
var debt_remaining = 0
var capacity = 10
var reputation = 0.0
var trade_count = 0
var seller_trades = 0
var buyer_trades = 0
var refused_purchases = 0
var inventory: Array = []
var purchase_spending = 0
var sale_revenue = 0
var realized_trade_profit = 0
var scrap_revenue = 0
var scrapped_items = 0
var scrap_realized_loss = 0
var expansion_spending = 0

func _init(config: Dictionary) -> void:
	cash = int(config.economy.starting_cash)
	starting_cash = cash
	capacity = int(config.economy.initial_inventory_capacity)

func weekly_operating_cost(config: Dictionary, target_week: int) -> int:
	return int(config.economy.weekly_operating_cost.first_week + (target_week - 1) * config.economy.weekly_operating_cost.weekly_increase)
