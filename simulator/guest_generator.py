from .config import weighted_choice
from .models import Guest
from .progression import interpolated_weights


def generate_guest(rng, config, shop_reputation=0.0, shop_trade_count=0, visitor_number=None) -> Guest:
    cfg = config["guest"]
    progression = config["progression"]
    bracket = weighted_choice(rng, interpolated_weights(progression["reputation"]["adventurer_level"], shop_reputation))
    low, high = map(int, bracket.split("-"))
    role = "SELL_TO_SHOP" if visitor_number is None or visitor_number <= config["economy"]["forced_initial_seller_visits"] else weighted_choice(rng, config["economy"]["visitor_roles"])
    adventurer_class = rng.choice(cfg["classes"])
    return Guest(
        trade_attitude=weighted_choice(rng, interpolated_weights(progression["reputation"]["trade_attitude"], shop_reputation)),
        adventurer_class=adventurer_class,
        adventurer_level=rng.randint(low, high),
        adventurer_power=weighted_choice(rng, interpolated_weights(progression["reputation"]["adventurer_power"], shop_reputation)),
        equipment_tendency=rng.choice(cfg["tendencies"]),
        achievement_rank=weighted_choice(rng, interpolated_weights(progression["trade_count"]["achievement_rank"], shop_trade_count)),
        title_rank=weighted_choice(rng, interpolated_weights(progression["trade_count"]["title_rank"], shop_trade_count)),
        market_knowledge=rng.choice(cfg["market_knowledge"]),
        selling_purpose=rng.choice(cfg["purposes"]),
        role=role,
        preferred_weapon_type=rng.choice(config["weapon"]["class_weapon_pools"][adventurer_class]) if role == "BUY_FROM_SHOP" else None,
    )
