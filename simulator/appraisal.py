"""Player knowledge is separate from immutable item truth and from pricing."""
import random

from .models import KnownField, WeaponKnownState


PROPERTY_FIELDS = {
    "reinforcement": "reinforcement_grade",
    "refining": "refining_level",
    "amplification": "amplification_grade",
    "stability": "stability",
    "special_property": "special_stat_grade",
    "unique_property": "unique_stat_grade",
}


def property_domain(config, name):
    """Use the existing price/generation domains; never invent an enum or level."""
    tables = {"reinforcement": "reinforce_values", "amplification": "amplification_values",
              "special_property": "special_values", "unique_property": "unique_values"}
    if name in tables:
        return tuple(config["price"][tables[name]])
    if name == "refining":
        return tuple(sorted(int(value) for value in config["price"]["refining_values"]))
    if name == "stability":
        values = set()
        for table in config["weapon"]["stability_by_processing_load"].values():
            for bounds in table:
                low, high = map(int, bounds.split("-"))
                values.update(range(low, high + 1))
        return tuple(sorted(values))
    raise ValueError(f"Unknown appraisal property: {name}")


def exact_field(value):
    return KnownField(knowledge_state="EXACT", known_exact_value=value, displayed_value=value)


def isolated_appraisal_rng(generation_rng):
    """Derive a knowledge RNG without consuming guest/weapon/trade randomness."""
    clone = random.Random(0)
    clone.setstate(generation_rng.getstate())
    return random.Random(f"appraisal:{clone.getrandbits(128)}")


def create_player_knowledge(config, weapon, rng):
    known = WeaponKnownState(item_tier=exact_field(weapon.tier))
    # All generated concrete numbers are public, including unique/amplification
    # numeric lines. Their internal grade/source metadata is not player data.
    for group in ("stat_lines", "amplification_lines"):
        for index, line in enumerate(getattr(weapon, group)):
            visible = {"stat_id": line.stat_id, "actual_value": line.actual_value, "display_unit": line.display_unit}
            known.known_stat_lines[f"{group}:{index}"] = exact_field(visible)
    for name, attribute in PROPERTY_FIELDS.items():
        true_value = getattr(weapon, attribute)
        domain = property_domain(config, name)
        if true_value not in domain:
            raise ValueError(f"{name}: true value outside configured domain")
        if rng.random() < config["appraisal"]["unassisted_correct_probability"]:
            displayed = true_value
        else:
            alternatives = [value for value in domain if value != true_value]
            if not alternatives:
                raise ValueError(f"{name}: an incorrect guess needs an alternative value")
            displayed = rng.choice(alternatives)
        # Correct guesses remain guesses: the UI must not leak correctness.
        setattr(known, name, KnownField(knowledge_state="UNAPPRAISED_GUESS", displayed_value=displayed))
    return known


def apply_appraisal_tool(config, weapon, known, property_name, owned_tools):
    """Explicit player action. Possession alone does not reveal a property."""
    if property_name not in PROPERTY_FIELDS:
        raise ValueError(f"Unknown appraisal property: {property_name}")
    tool = config["appraisal"]["property_tools"][property_name]
    if tool not in owned_tools:
        raise PermissionError(f"Required appraisal tool not owned: {tool}")
    field = exact_field(getattr(weapon, PROPERTY_FIELDS[property_name]))
    setattr(known, property_name, field)
    return field
