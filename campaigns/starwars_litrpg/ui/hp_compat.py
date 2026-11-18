"""Read-only compatibility for accepted legacy HP events. New writes still require delta."""

def hp_delta(details):
    # Presence, not truthiness: delta=0 is authoritative; invalid modern fields do not
    # fall back to amount. Never guess a sign from prose or interpret unsigned damage.
    value = details.get("delta") if "delta" in details else details.get("amount", 0)
    return value if type(value) is int else 0
