from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Guest:
    kindness: str
    guest_class: str
    level: int
    power: str
    tendency: str
    achievement: str
    title: str
    knowledge: str
    purpose: str
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


@dataclass(frozen=True)
class WeaponTrueState:
    item_type: str
    item_class: str
    compatible: bool
    generation_mode: str
    tier: int
    normal_stat_grade: str
    high_stat_grade: str
    special_stat_grade: str
    unique_stat_grade: str
    reinforcement_grade: str
    refining_level: int
    amplification_grade: str
    processing_load: int
    popularity_load: int
    class_power_load: int
    effective_processing_load: int
    stability: int
    stability_bracket: str
    stat_lines: tuple[StatLine, ...]
    amplification_lines: tuple[StatLine, ...]

    @property
    def target_class(self) -> str:
        """Backward-compatible alias for the specification's older name."""
        return self.item_class


@dataclass(frozen=True)
class PriceResult:
    base_price: int
    item_value_modifier: float
    effective_refining_value: float
    stability_multiplier: float
    appraised_price: int
    asking_price: int


@dataclass(frozen=True)
class SimulationRecord:
    record_id: int
    guest: Guest
    weapon: WeaponTrueState
    known_state: WeaponKnownState
    class_power: str
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
        })
        row.update({"class_power": self.class_power, "class_popularity": self.class_popularity})
        row.update({f"price_{k}": v for k, v in asdict(self.price).items()})
        return row


def format_stat_line(line: StatLine) -> str:
    value = f"{line.actual_value:g}{'%' if line.display_unit == 'PERCENT' else ''}"
    return f"{line.stat_id} +{value}"
