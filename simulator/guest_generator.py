from .config import weighted_choice
from .models import Guest
from .progression import interpolated_weights


def generate_guest(rng, config, shop_reputation=0.0, shop_trade_count=0, visitor_number=None) -> Guest:
    cfg = config["guest"]
    progression = config["progression"]
    bracket = weighted_choice(rng, interpolated_weights(progression["reputation"]["guest_level"], shop_reputation))
    low, high = map(int, bracket.split("-"))
    role = "SELL_TO_SHOP" if visitor_number is None or visitor_number <= config["economy"]["forced_initial_seller_visits"] else weighted_choice(rng, config["economy"]["visitor_roles"])
    guest_class = rng.choice(cfg["classes"])
    return Guest(
        kindness=weighted_choice(rng, interpolated_weights(progression["reputation"]["guest_kindness"], shop_reputation)),
        guest_class=guest_class,
        level=rng.randint(low, high),
        power=weighted_choice(rng, interpolated_weights(progression["reputation"]["guest_power"], shop_reputation)),
        tendency=rng.choice(cfg["tendencies"]),
        achievement=weighted_choice(rng, interpolated_weights(progression["trade_count"]["guest_achievement"], shop_trade_count)),
        title=weighted_choice(rng, interpolated_weights(progression["trade_count"]["guest_title"], shop_trade_count)),
        knowledge=rng.choice(cfg["knowledge"]),
        purpose=rng.choice(cfg["purposes"]),
        role=role,
        preferred_weapon_type=rng.choice(config["weapon"]["class_weapon_pools"][guest_class]) if role == "BUY_FROM_SHOP" else None,
    )
