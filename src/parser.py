import base64
import hashlib
import re
from urllib.parse import unquote


# پروتکل‌های قابل استخراج
PROTOCOLS = (
    "vless://",
    "vmess://",
    "trojan://",
    "ss://",
    "ssr://",
    "socks://",
    "socks5://",
    "http://",
    "https://",
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

# برای پیدا کردن رشته‌های Base64 نسبتاً بلند
BASE64_PATTERN = re.compile(
    r"\b[A-Za-z0-9+/=_-]{40,}\b"
)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)

    # یکسان‌سازی newline
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # حذف کاراکترهای نامرئی
    invisible = (
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
    )

    for char in invisible:
        text = text.replace(char, "")

    # Decode کردن URL encoding
    try:
        decoded = unquote(text)

        if decoded != text:
            text = text + "\n" + decoded

    except Exception:
        pass

    return text


def extract_configs(text: str) -> list[str]:
    """
    استخراج کانفیگ از متن Telegram.

    پشتیبانی از:
    - vless://
    - vmess://
    - trojan://
    - ss://
    - ssr://
    - socks://
    - socks5://
    - URIهای URL-encoded
    - VMess Base64
    - Base64 شامل URI
    - متن quote/code/monospace
    """

    if not text:
        return []

    text = clean_text(text)

    configs = []

    # ==========================================================
    # 1. URI مستقیم
    # ==========================================================

    for match in URI_PATTERN.finditer(text):
        config = match.group(0)

        config = config.rstrip(
            ".,;:!?)]}>\"'`"
        )

        if config:
            configs.append(config)

    # ==========================================================
    # 2. VMess Base64
    # ==========================================================

    for match in BASE64_PATTERN.finditer(text):
        token = match.group(0)

        decoded = decode_possible_base64(token)

        if not decoded:
            continue

        decoded_clean = decoded.strip()

        # VMess JSON
        if looks_like_vmess_json(decoded_clean):
            configs.append(
                "vmess://" + normalize_base64_token(token)
            )

        # Base64 شامل URI
        for uri_match in URI_PATTERN.finditer(decoded_clean):
            config = uri_match.group(0).rstrip(
                ".,;:!?)]}>\"'`"
            )

            if config:
                configs.append(config)

    # ==========================================================
    # 3. VMess هایی که از قبل vmess:// دارند
    # ==========================================================

    vmess_pattern = re.compile(
        r"vmess://([A-Za-z0-9+/=_-]+)",
        re.IGNORECASE,
    )

    for match in vmess_pattern.finditer(text):
        payload = match.group(1).rstrip(
            ".,;:!?)]}>\"'`"
        )

        if payload:
            configs.append(
                "vmess://" + payload
            )

    # ==========================================================
    # 4. نرمال‌سازی خروجی بدون خراب کردن محتوا
    # ==========================================================

    result = []
    seen = set()

    for config in configs:
        config = config.strip()

        if not config:
            continue

        # فقط حذف newline/space اطراف
        # محتوای واقعی URI را تغییر نمی‌دهیم.
        key = config

        if key in seen:
            continue

        seen.add(key)
        result.append(config)

    return result


def looks_like_vmess_json(text: str) -> bool:
    if not text:
        return False

    lower = text.lower()

    # VMess JSON معمولاً این فیلدها را دارد
    return (
        "add" in lower
        and "port" in lower
        and (
            "id" in lower
            or "ps" in lower
            or "net" in lower
        )
    )


def normalize_base64_token(value: str) -> str:
    """
    Base64 را فقط از نظر فاصله و padding مرتب می‌کند.
    """
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

        if not decoded:
            return None

        return decoded

    except Exception:
        return None


def decode_possible_base64(value: str) -> str | None:
    """
    برای سازگاری با sources.py.
    """
    return decode_base64(value)


def canonical_config(config: str) -> str:
    """
    نسخه canonical برای deduplication.

    URI را تا حد امکان بدون تغییر نگه می‌دارد.
    فقط whitespace اطراف حذف می‌شود.
    """

    if not config:
        return ""

    value = str(config).strip()

    # newline و فاصله‌های ابتدا/انتها
    value = value.strip()

    return value


def normalize_config(config: str) -> str:
    """
    خروجی نهایی برای ذخیره در subscription.

    عمداً URI را خراب یا decode نمی‌کنیم.
    """

    if not config:
        return ""

    value = str(config).strip()

    # newline داخلی در یک کانفیگ معمولاً نباید وجود داشته باشد
    value = value.replace("\r", "")
    value = value.replace("\n", "")

    return value


def config_hash(config: str) -> str:
    """
    Hash اختیاری برای استفاده‌های آینده.
    """

    canonical = canonical_config(config)

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
