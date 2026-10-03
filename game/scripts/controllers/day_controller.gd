class_name DayController
extends RefCounted

signal changed
signal completed

const GUEST_COUNT = 8
const DEFAULT_SEED = 12352
var config: Dictionary
var state: ShopState
var market: Dictionary = {}
var sequence: Array = []
var guest_number = 0
var guest: Dictionary = {}
var item: WeaponData
var negotiation: SellerNegotiation
var phase = "BETWEEN"
var message = "첫날 영업을 시작합니다. 재고를 정리하거나 손님을 맞이하세요."
var seed_value = DEFAULT_SEED
var rng = RandomNumberGenerator.new()

func _init(seed_input = DEFAULT_SEED) -> void:
	config = Balance.load_config()
	state = ShopState.new(config)
	seed_value = seed_input
	var arrivals = RandomNumberGenerator.new()
	arrivals.seed = seed_value
	sequence = ["SELL_TO_SHOP", "SELL_TO_SHOP", "SELL_TO_SHOP", "SELL_TO_SHOP", "BUY_FROM_SHOP", "BUY_FROM_SHOP", "BUY_FROM_SHOP"]
	sequence.append("SELL_TO_SHOP" if arrivals.randf() < 0.5 else "BUY_FROM_SHOP")
	var market_rng = RandomNumberGenerator.new()
	market_rng.seed = seed_value ^ 59321
	for guest_class in config.guest.classes:
		market[guest_class] = [Balance.pick(market_rng, config.price.market_power_values.keys()), Balance.pick(market_rng, config.price.market_popularity_values.keys())]

func next_guest() -> void:
	if phase != "BETWEEN" or guest_number >= GUEST_COUNT:
		return
	guest_number += 1
	rng.seed = seed_value + guest_number * 104729
	guest = CustomerController.generate(config, rng, state, sequence[guest_number - 1], guest_number)
	item = null
	negotiation = null
	if guest.role == "SELL_TO_SHOP":
		item = WeaponGenerator.generate(config, rng, guest, market)
		negotiation = SellerNegotiation.new(config, guest, PriceCalculator.calculate(config, item, market).asking_price)
		phase = "SELLER"
		message = "이 무기를 팔고 싶어요. 테이블 위의 물건을 살펴보시겠어요?"
	else:
		phase = "BUYER"
		message = "%s 종류를 찾고 있어요. 가지고 계신 무기를 보여주세요." % TextCatalog.weapon(guest.preferred_weapon_type)
	changed.emit()

func buy() -> void:
	if phase != "SELLER":
		return
	var offer = PriceCalculator.estimate(config, item.known.player_view(), item.judgement)
	var issue = TransactionService.purchase_issue(state, offer)
	if not issue.is_empty():
		message = issue
		changed.emit()
		return
	var outcome = negotiation.evaluate(config, guest, offer)
	if outcome == "ACCEPTED":
		message = TransactionService.buy(config, state, item, market, offer).message
		finish_visit()
	elif outcome == "FAILED":
		TransactionService.refuse(config, rng, state, guest)
		message = "그 가격에는 팔 수 없어. 이번 거래는 여기까지 하자.\n흥정 횟수를 모두 사용하여 거래가 결렬되었습니다."
		finish_visit()
	else:
		message = "그 가격은 너무 낮아. %d골드는 받아야겠어.\n판단과 가격 반영을 조정해서 다시 제안해 주세요." % negotiation.current_asking
		changed.emit()

func refuse() -> void:
	if phase != "SELLER":
		return
	message = TransactionService.refuse(config, rng, state, guest)
	finish_visit()

func resolve_buyer() -> void:
	if phase != "BUYER":
		return
	message = TransactionService.buyer(config, rng, state, guest, market).message
	finish_visit()

func finish_visit() -> void:
	item = null
	phase = "COMPLETE" if guest_number == GUEST_COUNT else "BETWEEN"
	changed.emit()
	if phase == "COMPLETE":
		completed.emit()

func expand() -> bool:
	if phase != "BETWEEN":
		return false
	var result = TransactionService.expand(config, state)
	changed.emit()
	return result

func scrap(owned: WeaponData) -> bool:
	if phase != "BETWEEN":
		return false
	var result = TransactionService.scrap(config, state, owned)
	changed.emit()
	return result
