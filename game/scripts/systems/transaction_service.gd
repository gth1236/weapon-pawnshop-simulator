class_name TransactionService
extends RefCounted

static func refuse(config: Dictionary, rng: RandomNumberGenerator, state: ShopState, guest: Dictionary) -> String:
	state.refused_purchases += 1
	var raw = config.reputation.failed_scam_delta if guest.trade_attitude == "SCAMMER" else float(Balance.weighted(rng, config.reputation.no_purchase_deltas))
	state.reputation += ProgressionService.apply_delta(config, state.reputation, raw)
	return "매입을 거절했습니다. 손님이 무기를 가지고 떠납니다."

static func purchase_issue(state: ShopState, offer: int) -> String:
	if state.inventory.size() >= state.capacity:
		return "재고가 가득 찼습니다. 매입을 거절한 뒤 재고를 확장하거나 고물상에 처분하세요."
	if offer <= 0 or state.cash < offer:
		return "제안할 자금이 부족합니다. 가격 반영을 조정하거나 매입을 거절하세요."
	return ""

# Commit the accepted player offer, never substitute the seller asking price.
static func buy(config: Dictionary, state: ShopState, item: WeaponData, market: Dictionary, offer: int) -> Dictionary:
	var issue = purchase_issue(state, offer)
	if not issue.is_empty():
		return {"success": false, "message": issue}
	var price = PriceCalculator.calculate(config, item, market)
	state.cash -= offer
	state.purchase_spending += offer
	item.final_purchase_price = offer
	item.current_appraised_price = price.true_appraised_price
	item.purchase_day = state.day
	state.inventory.append(item)
	state.seller_trades += 1
	state.trade_count += 1
	var raw = ProgressionService.purchase_delta(config, item.seller, float(offer) / price.true_appraised_price)
	state.reputation += ProgressionService.apply_delta(config, state.reputation, raw)
	return {"success": true, "message": "좋아, 그 가격에 팔겠어. 제안한 %d 골드에 매입했습니다." % offer}

static func buyer(config: Dictionary, rng: RandomNumberGenerator, state: ShopState, guest: Dictionary, market: Dictionary) -> Dictionary:
	var selected = BuyerFitService.choose(config, rng, guest, state.inventory)
	if not selected.failure.is_empty():
		return {"success": false, "message": "사용할 수 있는 무기가 없네요. 다음에 다시 올게요." if selected.failure == "NO_COMPATIBLE_ITEM" else "오늘은 마음에 드는 무기가 없네요. 다음에 다시 올게요."}
	var item = selected.item
	var fit = selected.fit
	var c = config.economy
	var current = PriceCalculator.calculate(config, item, market).true_appraised_price
	item.current_appraised_price = current
	var listing = Balance.money(current * (1 + c.listing_markup))
	var band = BuyerFitService.interest(config, fit.score)
	var ceiling = current * (band.price_multiplier + c.market_knowledge_price_adjustment[guest.market_knowledge])
	var offer = Balance.money(minf(listing * (1 - band.desired_discount), ceiling))
	var minimum = maxf(current, item.final_purchase_price * (1 + c.minimum_profit_over_cost))
	var details = "적합도 %.1f | 판매가 %d 골드 | 제안 %d 골드 | 흥정 %d회" % [fit.score, listing, offer, band.haggles]
	if offer < minimum:
		return {"success": false, "message": details + "\n가격이 맞지 않아 손님이 떠납니다."}
	state.cash += offer
	state.sale_revenue += offer
	state.realized_trade_profit += offer - item.final_purchase_price
	state.inventory.erase(item)
	state.buyer_trades += 1
	state.trade_count += 1
	state.reputation += ProgressionService.apply_delta(config, state.reputation, c.sale_reputation_by_haggles[str(int(band.haggles))])
	return {"success": true, "message": details + "\n%s을(를) %d 골드에 판매했습니다." % [TextCatalog.weapon(item.known.item_type), offer], "offer": offer}

static func expand(config: Dictionary, state: ShopState) -> bool:
	var c = config.economy
	if state.capacity >= c.maximum_inventory_capacity or state.cash < c.inventory_expansion_cost:
		return false
	state.cash -= int(c.inventory_expansion_cost)
	state.expansion_spending += int(c.inventory_expansion_cost)
	state.capacity += 1
	return true

static func scrap_quote(config: Dictionary, item: WeaponData) -> Dictionary:
	var revenue = Balance.money(item.final_purchase_price * config.economy.scrap_purchase_price_ratio)
	return {"purchase": item.final_purchase_price, "revenue": revenue, "loss": item.final_purchase_price - revenue}

static func scrap(config: Dictionary, state: ShopState, item: WeaponData) -> bool:
	if item not in state.inventory:
		return false
	var quote = scrap_quote(config, item)
	state.cash += quote.revenue
	state.scrap_revenue += quote.revenue
	state.scrap_realized_loss += quote.loss
	state.scrapped_items += 1
	state.inventory.erase(item)
	return true
