"""Publish sanitized n8n exports without modifying private originals (stdlib only)."""

import argparse
import copy
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "workflows"
PUBLIC = ROOT / "published-workflows"
REDACTED = "REDACTED"
SENSITIVE = {
    "password", "passwd", "secret", "clientsecret", "token", "accesstoken",
    "refreshtoken", "bottoken", "apikey", "authorization", "proxyauthorization",
    "cookie", "setcookie", "privatekey", "encryptionkey", "xapikey",
    "xgoogapikey", "geminiapikey", "googleapikey",
}
PATTERNS = [
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), REDACTED),
    (re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----.*?"
                r"-----END (?:[A-Z0-9]+ )*PRIVATE KEY-----", re.S), REDACTED),
    (re.compile(r"\b\d{6,15}:[A-Za-z0-9_-]{30,}\b"), REDACTED),
    (re.compile(r"\b(?:sk-|ghp_|github_pat_|AKIA)[A-Za-z0-9_-]{16,}\b"), REDACTED),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), REDACTED),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
     "user@example.invalid"),
    (re.compile(r"(?i)[A-Z]:[\\/]+Users[\\/]+[^\s\"'<>]+"), "/LOCAL_PATH"),
    (re.compile(r"/(?:home|Users)/[^/\s\"'<>]+"), "/home/USER"),
    (re.compile(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@"), r"\1REDACTED@"),
    (re.compile(r"(?i)([?&](?:key|api[_-]?key|token|access_token|secret|password)=)"
                r"[^&#\s\"']+"), r"\1REDACTED"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"), "Bearer REDACTED"),
    (re.compile(r"(?i)(\b(?:api[_-]?key|bot[_-]?token|password|client[_-]?secret)"
                r"\s*[:=]\s*)([\"'])([^\"'\r\n]+)([\"'])"),
     r"\1\2REDACTED\4"),
]


def normalized(key):
    return re.sub(r"[^a-z0-9]", "", key.lower())


def scrub(value):
    if isinstance(value, str):
        for pattern, replacement in PATTERNS:
            value = pattern.sub(replacement, value)
        return value
    if isinstance(value, list):
        return [scrub(item) for item in value]
    if isinstance(value, dict):
        result = {}
        # Handles header/query entries like {"name": "Authorization", "value": ...}.
        named_secret = any(
            isinstance(value.get(key), str)
            and normalized(value[key]) in SENSITIVE
            for key in ("name", "key")
        )
        for key, item in value.items():
            norm = normalized(key)
            if norm in {"credentials", "webhookid"}:
                continue
            if norm == "chatid":
                result[key] = "YOUR_TELEGRAM_CHAT_ID"
            elif norm in SENSITIVE or (named_secret and norm == "value"):
                result[key] = REDACTED
            else:
                result[key] = scrub(item)
        return result
    return value


def anonymize(workflow):
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        raise ValueError("Expected an n8n workflow object with a nodes array")
    workflow = copy.deepcopy(workflow)
    for key in ("id", "versionId", "activeVersionId", "meta", "staticData",
                "shared", "createdAt", "updatedAt", "triggerCount"):
        workflow.pop(key, None)
    workflow["pinData"] = {}
    workflow["tags"] = []
    workflow["active"] = False
    for node in workflow["nodes"]:
        node.pop("notes", None)
        node.pop("notesInFlow", None)
        if node.get("type") == "n8n-nodes-base.stickyNote":
            node["parameters"] = {
                **node.get("parameters", {}),
                "content": "Private notes omitted from the published export.",
            }
    return scrub(workflow)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Fail if published exports are missing, stale or unexpected; write nothing")
    args = parser.parse_args()
    try:
        sources = sorted(PRIVATE.rglob("*.json"))
        if not sources:
            raise ValueError("No private workflow JSON files found in workflows/")
        # Prepare every export before writing anything; an invalid input fails the run.
        exports = {}
        for source in sources:
            if source.is_symlink():
                raise ValueError("Symlinked workflow inputs are not supported")
            document = json.loads(source.read_text(encoding="utf-8-sig"))
            relative = source.relative_to(PRIVATE)
            # Filenames themselves are not anonymized; use generic export names.
            exports[relative] = json.dumps(anonymize(document), ensure_ascii=False, indent=2) + "\n"
        existing = {p.relative_to(PUBLIC) for p in PUBLIC.rglob("*.json")}
        if existing - exports.keys():
            raise ValueError("Unexpected published JSON files; review/remove stale exports before continuing")
        if args.check:
            for relative, content in exports.items():
                target = PUBLIC / relative
                if not target.is_file() or target.read_text(encoding="utf-8") != content:
                    raise ValueError("Published exports are missing or stale; run the script without --check")
            print(f"OK: {len(exports)} published workflow(s) match sanitized private exports.")
        else:
            for relative, content in exports.items():
                target = PUBLIC / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.is_symlink():
                    raise ValueError("Refusing to overwrite a symlinked output")
                target.write_text(content, encoding="utf-8", newline="\n")
            print(f"Wrote {len(exports)} sanitized workflow(s) to published-workflows/. Originals unchanged.")
        return 0
    except (OSError, ValueError):
        # Do not echo input or parser errors: they can contain the secret itself.
        print("Export failed: invalid/unreadable workflow, stale output, or unsafe path. "
              "Check inputs and published files locally.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
