"""Config-driven customer progression interpolation and analysis helpers."""


def interpolated_weights(progression, value):
    anchors = progression["anchors"]
    if value <= anchors[0]["value"]:
        return dict(anchors[0]["weights"])
    if value >= anchors[-1]["value"]:
        return dict(anchors[-1]["weights"])
    lower, upper = next(
        (a, b) for a, b in zip(anchors, anchors[1:])
        if a["value"] <= value <= b["value"]
    )
    fraction = (value - lower["value"]) / (upper["value"] - lower["value"])
    weights = {
        key: lower["weights"][key] + fraction * (upper["weights"][key] - lower["weights"][key])
        for key in lower["weights"]
    }
    total = sum(weights.values())
    return {key: max(0.0, weight) / total for key, weight in weights.items()}


def customer_progression_distributions(config, reputation, trade_count):
    progression = config["progression"]
    result = {}
    for name, table in progression["reputation"].items():
        result[name] = interpolated_weights(table, reputation)
    for name, table in progression["trade_count"].items():
        result[name] = interpolated_weights(table, trade_count)
    return result
