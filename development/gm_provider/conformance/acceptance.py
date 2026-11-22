"""Independent evidence checks for staging acceptance. No gateway access."""
import hashlib
import json
import re


def cursor(receipt):
    public = receipt.get("public", {})
    value = public.get("cursor", {})
    fields = tuple(value.get(key) for key in ("campaign_id", "revision", "ledger_head", "public_sha256"))
    if (not isinstance(fields[0], str) or not fields[0]
            or type(fields[1]) is not int or fields[1] < 0
            or not isinstance(fields[2], str) or not fields[2]
            or not isinstance(fields[3], str) or not re.fullmatch(r"[0-9a-f]{64}", fields[3])):
        raise ValueError("Incomplete authoritative cursor")
    return fields


def check_refresh_pair(gpt, gemini):
    """Validate redacted tool response evidence, not a model's prose summary."""
    if (gpt.get("connection_provider"), gemini.get("connection_provider")) != ("gpt-session", "gemini-session"):
        raise ValueError("Distinct bound GPT and Gemini identities are required")
    for receipt in (gpt, gemini):
        if receipt.get("audience") != "player":
            raise ValueError("A player-audience refresh receipt is required")
        if receipt.get("storage_recovery_required") is not False:
            raise ValueError("Storage recovery is unresolved")
        if receipt.get("recovery", {}).get("record_mid_write") is not False:
            raise ValueError("Authoritative record is not stable")
    if cursor(gpt) != cursor(gemini):
        raise ValueError("Provider cursor mismatch")
    return cursor(gpt)


def digest(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def check_recovered_rolls(previous, recovered):
    """Compare already accepted fixture receipts, including result and request hash."""
    for key, accepted in previous.items():
        restored = recovered.get(key)
        if (not isinstance(accepted.get("request_hash"), str) or not accepted["request_hash"]
                or not isinstance(accepted.get("result", {}).get("roll_id"), str)
                or not accepted["result"]["roll_id"]):
            raise ValueError("Incomplete accepted receipt")
        if not isinstance(restored, dict) or digest(restored) != digest(accepted):
            raise ValueError("Accepted receipt changed or disappeared")
    ids = [entry["result"]["roll_id"] for entry in recovered.values()]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate accepted receipt ID")
    return len(previous)


def diagnose_scope(*, request_includes_gm=None, issued_includes_gm=None, session_includes_gm=False):
    """Consume operator-supplied booleans for one matched authorization exchange."""
    if any(value is not None and type(value) is not bool
           for value in (request_includes_gm, issued_includes_gm, session_includes_gm)):
        raise ValueError("Supply only redacted boolean diagnostics")
    if session_includes_gm is True:
        return "SESSION_HAS_GM"
    if issued_includes_gm is True and session_includes_gm is False:
        return "SESSION_DOES_NOT_REFLECT_ISSUED_GRANT"
    if request_includes_gm is False:
        return "CLIENT_OMITTED_GM"
    if request_includes_gm is True and issued_includes_gm is False:
        return "ISSUER_DID_NOT_GRANT_GM"
    return "REQUEST_OR_GRANT_EVIDENCE_MISSING"
