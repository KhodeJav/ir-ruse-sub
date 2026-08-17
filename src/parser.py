import base64
import json
import re
from urllib.parse import quote, urlsplit, urlunsplit

PROTOCOLS = ("vless://", "vmess://", "trojan://", "ss://")
REMARK = "T.me/iR_RUSE | کانال ما"

def extract_raw_configs(text: str) -> list[str]:
    if not text:
        return []
    pattern = re.compile(r"(?:vless|vmess|trojan|ss)://[^\s<>'\"`]+", re.IGNORECASE)
    results = []
    for value in pattern.findall(text):
        results.append(value.strip().rstrip(".,;)]}>"))
    return results

def decode_possible_base64(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    try:
        padding = "=" * (-len(text) % 4)
        decoded = base64.b64decode(text + padding, validate=False)
        result = decoded.decode("utf-8", errors="ignore")
        if any(proto in result.lower() for proto in PROTOCOLS):
            return result
    except Exception:
        pass
    return ""

def extract_configs(text: str) -> list[str]:
    configs = extract_raw_configs(text)
    if configs:
        return configs
    decoded = decode_possible_base64(text)
    return extract_raw_configs(decoded) if decoded else []

def normalize_vmess(config: str) -> str:
    try:
        payload = config[len("vmess://"):]
        padding = "=" * (-len(payload) % 4)
        raw = base64.b64decode(payload + padding).decode("utf-8", errors="ignore")
        data = json.loads(raw)
        if not isinstance(data, dict):
            return config
        data["ps"] = REMARK
        encoded = base64.b64encode(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).decode()
        return "vmess://" + encoded
    except Exception:
        return config

def normalize_uri_remark(config: str) -> str:
    try:
        parts = urlsplit(config)
        if not parts.scheme:
            return config
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, quote(REMARK, safe="")))
    except Exception:
        return config

def normalize_config(config: str) -> str:
    config = config.strip()
    low = config.lower()
    if low.startswith("vmess://"):
        return normalize_vmess(config)
    if low.startswith(("vless://", "trojan://", "ss://")):
        return normalize_uri_remark(config)
    return config

def canonical_config(config: str) -> str:
    """Canonical representation used for duplicate detection; ignores the remark."""
    config = config.strip()
    try:
        parts = urlsplit(config)
        if parts.scheme.lower() == "vmess":
            payload = config[len("vmess://"):]
            padding = "=" * (-len(payload) % 4)
            raw = base64.b64decode(payload + padding).decode("utf-8", errors="ignore")
            data = json.loads(raw)
            if isinstance(data, dict):
                data.pop("ps", None)
                return json.dumps(data, sort_keys=True, separators=(",", ":"))
        return urlunsplit((parts.scheme.lower(), parts.netloc, parts.path, parts.query, "")).lower()
    except Exception:
        return config.lower()
