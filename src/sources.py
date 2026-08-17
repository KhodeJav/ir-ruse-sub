import base64
import re


# ============================================================
# Supported protocols
# ============================================================

PROTOCOLS = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "socks://",
    "socks5://",
)


URI_PATTERN = re.compile(
    r"""
    (?:
        vless|vmess|trojan|ss|ssr|socks|socks5
    )
    ://
    [^\s<>"'`\]\[(){}]+
    """,
    re.IGNORECASE | re.VERBOSE,
)

BASE64_PATTERN = re.compile(
    r"\b[A-Za-z0-9+/=_-]{40,}\b"
)


# ============================================================
# Text cleaning
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Telegram invisible characters
    for char in (
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
    ):
        text = text.replace(char, "")

    return text


# ============================================================
# Config extraction
# ============================================================

def extract_configs(text: str) -> list[str]:
    if not text:
        return []

    text = clean_text(text)

    configs = []

    # --------------------------------------------------------
    # Direct URIs
    # --------------------------------------------------------

    for match in URI_PATTERN.finditer(text):
        config = match.group(0)

        config = config.rstrip(
            ".,;:!?)]}>\"'`"
        )

        if config:
            configs.append(config)

    # --------------------------------------------------------
    # Base64 payloads
    # --------------------------------------------------------

    for match in BASE64_PATTERN.finditer(text):
        token = match.group(0)

        decoded = decode_possible_base64(token)

        if not decoded:
            continue

        # VMess JSON
        if looks_like_vmess_json(decoded):
            configs.append(
                "vmess://" + normalize_base64_token(token)
            )

        # Base64 containing URI
        for uri_match in URI_PATTERN.finditer(decoded):
            config = uri_match.group(0).rstrip(
                ".,;:!?)]}>\"'`"
            )

            if config:
                configs.append(config)

    # --------------------------------------------------------
    # Deduplicate
    # --------------------------------------------------------

    result = []
    seen = set()

    for config in configs:
        config = config.strip()

        if not config:
            continue

        if config in seen:
            continue

        seen.add(config)
        result.append(config)

    return result


# ============================================================
# VMess detection
# ============================================================

def looks_like_vmess_json(text: str) -> bool:
    if not text:
        return False

    value = text.lower()

    return (
        "add" in value
        and "port" in value
        and (
            "id" in value
            or "ps" in value
            or "net" in value
        )
    )


# ============================================================
# Base64
# ============================================================

def normalize_base64_token(value: str) -> str:
    value = value.strip()

    value = value.replace("-", "+")
    value = value.replace("_", "/")

    value = "".join(value.split())

    padding = len(value) % 4

    if padding:
        value += "=" * (4 - padding)

    return value


def decode_base64(value: str) -> str | None:
    if not value:
        return None

    try:
        normalized = normalize_base64_token(value)

        raw = base64.b64decode(
            normalized,
            validate=False,
        )

        decoded = raw.decode(
            "utf-8",
            errors="ignore",
        ).strip()

        return decoded or None

    except Exception:
        return None


def decode_possible_base64(value: str) -> str | None:
    return decode_base64(value)


# ============================================================
# IMPORTANT
# Canonical config
# ============================================================

def canonical_config(config: str) -> str:
    """
    برای Deduplication.

    هیچ بخشی از URI بازسازی نمی‌شود.
    """

    if not config:
        return ""

    return str(config).strip()


# ============================================================
# IMPORTANT
# Normalize config
# ============================================================

def normalize_config(config: str) -> str:
    """
    فقط Remark بعد از # را تغییر می‌دهد.

    قسمت قبل از # کاملاً دست‌نخورده باقی می‌ماند.

    خروجی:
        ...#Telegram%20%40iR_RUSE
    """

    if not config:
        return ""

    config = str(config).strip()

    # فقط whitespace اطراف
    config = config.strip()

    # --------------------------------------------------------
    # پیدا کردن اولین #
    # --------------------------------------------------------

    hash_index = config.find("#")

    # اگر remark وجود ندارد:
    # فقط remark جدید اضافه کن
    if hash_index == -1:
        return config + "#Telegram%20%40iR_RUSE"

    # --------------------------------------------------------
    # قسمت اصلی کانفیگ
    # هیچ تغییری نمی‌کند
    # --------------------------------------------------------

    base = config[:hash_index]

    # --------------------------------------------------------
    # فقط Remark را عوض می‌کنیم
    # ASCII + URL encoded
    # --------------------------------------------------------

    remark = "Telegram @iR_RUSE"

    encoded_remark = quote_remark(remark)

    return base + "#" + encoded_remark


# ============================================================
# Remark encoder
# ============================================================

def quote_remark(value: str) -> str:
    """
    فقط کاراکترهای لازم برای Fragment را percent-encode می‌کند.
    """

    result = []

    for char in value:
        code = ord(char)

        # A-Z
        if 65 <= code <= 90:
            result.append(char)

        # a-z
        elif 97 <= code <= 122:
            result.append(char)

        # 0-9
        elif 48 <= code <= 57:
            result.append(char)

        # safe characters
        elif char in "-._~":
            result.append(char)

        else:
            # UTF-8 percent encoding
            for byte in char.encode("utf-8"):
                result.append(
                    f"%{byte:02X}"
                )

    return "".join(result)
