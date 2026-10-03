from dataclasses import asdict, dataclass, field
from typing import Any
import json


@dataclass(frozen=True)
class Guest:
    trade_attitude: str
    adventurer_class: str
    adventurer_level: int
    adventurer_power: str
    equipment_tendency: str
    achievement_rank: str
    title_rank: str
    market_knowledge: str
    selling_purpose: str
    role: str = "SELL_TO_SHOP"
    preferred_weapon_type: str | None = None


@dataclass(frozen=True)
class StatLine:
    stat_id: str
    category: str
    internal_grade: str | None
    actual_value: float
    display_unit: str
    is_relevant: bool


@dataclass
class KnownField:
    knowledge_state: str = "UNKNOWN"
    known_exact_value: Any = None
    known_min_value: Any = None
    known_max_value: Any = None
    displayed_value: Any = None

    def player_view(self):
        return {"knowledge_state": self.knowledge_state, "displayed_value": self.displayed_value}


@dataclass
class WeaponKnownState:
    knows_item_type: bool = False
    item_type: str | None = None
    item_tier: KnownField = field(default_factory=KnownField)
    known_stat_lines: dict[str, KnownField] = field(default_factory=dict)
    reinforcement: KnownField = field(default_factory=KnownField)
    refining: KnownField = field(default_factory=KnownField)
    amplification: KnownField = field(default_factory=KnownField)
    stability: KnownField = field(default_factory=KnownField)
    unique_property: KnownField = field(default_factory=KnownField)

    def player_view(self):
        """JSON-ready player data. Never serialize WeaponTrueState for a player UI."""
        return {
            "tier": self.item_tier.player_view(),
            "concrete_stats": [line.player_view() for line in self.known_stat_lines.values()],
            "properties": {name: getattr(self, name).player_view() for name in (
                "reinforcement", "refining", "amplification", "stability", "unique_property")},
        }


@dataclass(frozen=True)
class WeaponTrueState:
    item_type: str
    required_class: str  # Market/stat origin, not an exclusive buyer restriction.
    seller_class_compatible: bool
    generation_mode: str
    tier: int
    normal_stat_grade: str
    high_stat_grade: str
    unique_stat_grade: str
    reinforcement_grade: str
    refining_level: int
    amplification_grade: str
    processing_load: int
    effective_processing_load: int
    stability: int
    stability_bracket: str
    stat_lines: tuple[StatLine, ...]
    amplification_lines: tuple[StatLine, ...]

    @property
    def target_class(self) -> str:
        """Backward-compatible alias for the specification's older name."""
        return self.required_class


@dataclass(frozen=True)
class PriceResult:
    base_price: int
    item_value_modifier: float
    effective_refining_value: float
    stability_multiplier: float
    appraised_price: int
    asking_price: int

    @property
    def true_appraised_price(self):
        return self.appraised_price


@dataclass(frozen=True)
class SimulationRecord:
    record_id: int
    guest: Guest
    weapon: WeaponTrueState
    known_state: WeaponKnownState
    class_balance: str
    class_popularity: str
    price: PriceResult

    def flat_dict(self) -> dict[str, Any]:
        row = {"record_id": self.record_id}
        row.update({f"guest_{k}": v for k, v in asdict(self.guest).items()})
        weapon = asdict(self.weapon)
        weapon["stat_lines"] = "|".join(format_stat_line(StatLine(**x)) for x in weapon["stat_lines"])
        weapon["amplification_lines"] = "|".join(format_stat_line(StatLine(**x)) for x in weapon["amplification_lines"])
        row.update({f"item_{k}": v for k, v in weapon.items()})
        row.update({
            "known_item_type": self.known_state.knows_item_type,
            "known_tier_state": self.known_state.item_tier.knowledge_state,
            "known_reinforcement_state": self.known_state.reinforcement.knowledge_state,
            "known_refining_state": self.known_state.refining.knowledge_state,
            "known_amplification_state": self.known_state.amplification.knowledge_state,
            "known_stability_state": self.known_state.stability.knowledge_state,
            "player_visible_json": json.dumps(self.known_state.player_view(), ensure_ascii=False),
        })
        row.update({"class_balance": self.class_balance, "class_popularity": self.class_popularity})
        row.update({f"price_{k}": v for k, v in asdict(self.price).items()})
        return row


def format_stat_line(line: StatLine) -> str:
    value = f"{line.actual_value:g}{'%' if line.display_unit == 'PERCENT' else ''}"
    return f"{line.stat_id} +{value}"
