import base64
import re
from urllib.parse import unquote


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


def clean_text(text: str) -> str:
    if not text:
        return ""

    # Telegram markdown / quote / code formatting
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Unicode های نامرئی
    invisible = (
        "\u200b",
        "\u200c",
        "\u200d",
        "\u2060",
        "\ufeff",
    )

    for char in invisible:
        text = text.replace(char, "")

    # URL encode مثل %3A%2F%2F
    try:
        decoded = unquote(text)

        if decoded != text:
            text += "\n" + decoded
    except Exception:
        pass

    return text


def extract_configs(text: str) -> list[str]:
    """
    استخراج مستقیم کانفیگ‌ها از متن.

    فرمت‌های Telegram Markdown / Quote / Code
    اهمیتی ندارند؛ چون در نهایت متن خام بررسی می‌شود.
    """

    if not text:
        return []

    text = clean_text(text)

    configs = []

    # --------------------------------------------------
    # استخراج مستقیم URI
    # --------------------------------------------------

    for match in URI_PATTERN.finditer(text):
        config = match.group(0)

        # کاراکترهای انتهایی که جزو URI نیستند
        config = config.rstrip(
            ".,;:!?)]}>\"'`"
        )

        if config:
            configs.append(config)

    # --------------------------------------------------
    # استخراج VMess Base64
    # --------------------------------------------------

    for token in re.findall(
        r"(?:vmess://)?([A-Za-z0-9+/=_-]{40,})",
        text,
    ):
        decoded = decode_base64(token)

        if not decoded:
            continue

        if (
            "v" in decoded
            and (
                "add" in decoded
                or "host" in decoded
                or "port" in decoded
            )
        ):
            configs.append(
                "vmess://" + token
            )

    # --------------------------------------------------
    # استخراج Base64 عمومی که داخلش URI وجود دارد
    # --------------------------------------------------

    for token in re.findall(
        r"\b[A-Za-z0-9+/=_-]{50,}\b",
        text,
    ):
        decoded = decode_base64(token)

        if not decoded:
            continue

        for match in URI_PATTERN.finditer(decoded):
            config = match.group(0).rstrip(
                ".,;:!?)]}>\"'`"
            )

            if config:
                configs.append(config)

    # --------------------------------------------------
    # پاکسازی و Deduplicate
    # --------------------------------------------------

    result = []
    seen = set()

    for config in configs:
        config = config.strip()

        if not config:
            continue

        # Telegram ممکن است % encoding داشته باشد.
        # اما خود config را دستکاری نمی‌کنیم.
        key = config

        if key in seen:
            continue

        seen.add(key)
        result.append(config)

    return result


def decode_base64(value: str) -> str | None:
    try:
        value = value.strip()

        # URL-safe Base64
        value = value.replace("-", "+")
        value = value.replace("_", "/")

        padding = len(value) % 4

        if padding:
            value += "=" * (4 - padding)

        raw = base64.b64decode(
            value,
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
    تلاش برای Decode کردن Base64.
    اگر ورودی Base64 معتبر نباشد، None برمی‌گرداند.
    """

    if not value:
        return None

    value = value.strip()

    try:
        # Base64 معمولی و URL-safe
        normalized = value.replace("-", "+").replace("_", "/")

        # حذف فاصله‌های احتمالی
        normalized = "".join(normalized.split())

        # Padding
        padding = len(normalized) % 4

        if padding:
            normalized += "=" * (4 - padding)

        decoded = base64.b64decode(
            normalized,
            validate=False,
        )

        return decoded.decode(
            "utf-8",
            errors="ignore",
        ).strip()

    except Exception:
        return None
