"""Sanitized, typed Git failures. Never infer lease ownership from transport output."""
import re

OPERATIONS = {"fetch", "push", "commit", "merge", "reset", "add", "diff", "rev-list", "rev-parse", "status", "ls-remote"}
PATTERNS = {
    "protected_branch": r"GH006|GH013|protected branch|repository rule violations|changes must be made through a pull request",
    "authentication_or_permission": r"authentication failed|could not read (?:username|password)|permission denied \((?:publickey|password)|write access .*not granted|permission to .* denied to|invalid username or (?:password|token)|http basic: access denied|access denied|repository access denied",
    "stale_ref": r"\[rejected\].*(?:non-fast-forward|fetch first|stale info)|non-fast-forward|updates were rejected because|cannot lock ref .*is at .*expected|stale (?:ref|info)|not possible to fast-forward|would be overwritten by merge",
    "transport": r"could not resolve (?:host|proxy)|failed to connect|connection (?:refused|reset|timed out|closed)|operation timed out|network is unreachable|broken pipe|SSL (?:certificate|connect)|TLS|proxy connect|RPC failed|remote end hung up|HTTP [45]\d\d",
    "remote_hook_rejected": r"pre-receive hook declined|hook declined|\[remote rejected\]",
}
CODES = {"protected_branch":"GIT_PROTECTED_BRANCH", "authentication_or_permission":"GIT_AUTH_OR_PERMISSION",
         "stale_ref":"GIT_STALE_REF", "transport":"GIT_TRANSPORT", "remote_hook_rejected":"GIT_HOOK_REJECTED",
         "unknown":"GIT_FAILED", "execution":"GIT_EXECUTION", "sync_required":"GIT_SYNC_REQUIRED"}


def text(value):
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else str(value or "")


def sanitize(value):
    """Keep relevant Git diagnostics; omit arbitrary remote-hook/private text.

    All URLs are removed (including credential-free URLs). Known token/header and
    credential assignment forms are scrubbed before filtering and truncation.
    Nothing in this function reads campaign context or credential configuration.
    """
    value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text(value))
    value = re.sub(r"(?i)(?:proxy-)?authorization\s*:[^\r\n]*", "[redacted authorization]", value)
    value = re.sub(r"(?i)\b(?:https?|ssh|git|file)://[^\s<>\"']+", "[redacted-url]", value)
    value = re.sub(r"(?i)\b[^\s<>\"']+@[^\s<>\"':]+:[^\s<>\"']+", "[redacted-url]", value)
    value = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|sk-(?:proj-)?[A-Za-z0-9_-]+)\b", "[redacted-token]", value)
    value = re.sub(r"(?i)\b(password|passwd|token|access_token|oauth_token|client_secret|credential|secret)\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)", r"\1=[redacted]", value)
    value = "".join(c for c in value if c in "\n\t" or ord(c) >= 32)
    kept, omitted = [], False
    # Hook output is untrusted. Preserve known reasons, not arbitrary appended prose.
    reasons = [
        r"(?:fatal:\s*)?could not read (?:Username|Password) for ['\"]\[redacted-url\]['\"]:\s*(?:No such device or address|terminal prompts disabled)",
        r"(?:fatal:\s*)?Authentication failed(?: for ['\"]\[redacted-url\]['\"])?",
        r"Permission denied \((?:publickey|password)[^)]*\)",
        r"Write access to repository not granted",
        r"Invalid username or (?:password|token)",
        r"HTTP Basic: Access denied",
        r"GH006:\s*Protected branch update failed",
        r"GH013:\s*Repository rule violations found",
        r"protected branch(?: hook declined| update failed)?",
        r"Changes must be made through a pull request",
        r"non-fast-forward|fetch first|stale info|updates were rejected because",
        r"not possible to fast-forward|would be overwritten by merge",
        r"cannot lock ref",
        r"Could not resolve (?:host|proxy)",
        r"Failed to connect",
        r"(?:Connection refused|Connection reset(?: by peer)?|Connection timed out|Operation timed out|Network is unreachable|Broken pipe)",
        r"SSL certificate problem|SSL connect error|TLS (?:handshake failed|connection was non-properly terminated|connect error)|RPC failed|remote end hung up unexpectedly|HTTP [45]\d\d",
        r"pre-receive hook declined|hook declined|\[remote rejected\]",
        r"failed to push some refs to ['\"]\[redacted-url\]['\"]",
    ]
    for line in value.splitlines():
        if re.search(r"(?i)permission to .* denied to", line):
            kept.append("Permission to [repository] denied to [identity].")
            continue
        matches = []
        for pattern in reasons:
            found = re.search(pattern, line, re.I)
            if found:
                matches.append(found.group(0))
                break
        if matches:
            kept.append(matches[0][:500])
        elif line.strip():
            omitted = True
    if omitted:
        kept.append("[unrecognized Git/server output omitted]")
    return "\n".join(kept)[:4000]


def diagnostic(operation, exit_code, stderr="", stdout="", *, timed_out=False, execution=False):
    raw = text(stderr)+"\n"+text(stdout)
    category = "transport" if timed_out else "execution" if execution else "unknown"
    if not timed_out and not execution:
        for name, pattern in PATTERNS.items():
            if re.search(pattern, raw, re.I):
                category = name
                break
    # A generic HTTP 403/404 is not proof of repository permissions or a lease race.
    rejected = category in ("protected_branch", "authentication_or_permission", "stale_ref", "remote_hook_rejected")
    return {"operation": operation, "exit_code": exit_code, "classification": category,
            "stderr": sanitize(stderr), "stdout": sanitize(stdout), "timed_out": timed_out,
            "remote_outcome": "rejected" if rejected else "unknown"}


class GitFailure(RuntimeError):
    def __init__(self, details):
        self.details = details
        self.code = CODES.get(details["classification"], "GIT_FAILED")
        super().__init__(f"{self.code}: Git {details['operation']} failed (exit {details['exit_code']}); no competing lease holder is implied")

    def as_dict(self):
        return {"error": {"code": self.code, "message": str(self), "git": self.details}}
