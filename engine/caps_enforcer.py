from engine.constants import HARD_CAPS, LOCKED_ABSOLUTE, LOCKED_CAPS, RELATIONAL_RULES


def _round5(v):
    return round(v / 5) * 5


def enforce_caps(tendencies):
    result = {}

    for name, value in tendencies.items():
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = 0

        # Round to nearest 5
        v = _round5(v)

        # Apply hard cap
        cap = HARD_CAPS.get(name, 100)
        v = min(v, cap)

        # Locked absolute
        if name in LOCKED_ABSOLUTE:
            v = min(v, LOCKED_ABSOLUTE[name])

        # Locked caps (upper bound)
        if name in LOCKED_CAPS:
            v = min(v, LOCKED_CAPS[name])

        # Floor at 0
        v = max(v, 0)

        result[name] = int(v)

    # Relational rules
    for (a, op, b) in RELATIONAL_RULES:
        if a in result and b in result:
            if op == "<=":
                result[a] = min(result[a], result[b])

    return result
