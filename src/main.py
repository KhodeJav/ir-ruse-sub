import asyncio
import base64
import os
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .telegram import collect_telegram
from .sources import collect_subscriptions
from .storage import (
    add_configs,
    get_active_configs,
    load_state,
    remove_expired,
    save_state,
)


# ============================================================
# Paths
# ============================================================

ROOT = Path(__file__).resolve().parent.parent

STATE_FILE = ROOT / "data" / "state.json"

OUTPUT_DIR = ROOT / "output"

SUBSCRIPTION_FILE = OUTPUT_DIR / "subscription.txt"
CONFIGS_FILE = OUTPUT_DIR / "configs.txt"


# ============================================================
# Sources
# ============================================================

def load_sources():
    path = ROOT / "config" / "sources.txt"

    telegram = []
    subscriptions = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            if line.startswith("#"):
                continue

            # Telegram channels
            if line.startswith(
                (
                    "@",
                    "https://t.me/",
                    "http://t.me/",
                )
            ):
                telegram.append(line)

            # Subscription URLs
            elif line.startswith(
                (
                    "http://",
                    "https://",
                )
            ):
                subscriptions.append(line)

    return telegram, subscriptions


# ============================================================
# Gregorian -> Jalali
# ============================================================

def gregorian_to_jalali(
    gy: int,
    gm: int,
    gd: int,
):
    g_days_in_month = [
        31, 28, 31, 30, 31, 30,
        31, 31, 30, 31, 30, 31,
    ]

    j_days_in_month = [
        31, 31, 31, 31, 31, 31,
        30, 30, 30, 30, 30, 29,
    ]

    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1

    g_day_no = (
        365 * gy2
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
    )

    for i in range(gm2):
        g_day_no += g_days_in_month[i]

    if gm > 2 and (
        gy % 4 == 0
        and (gy % 100 != 0 or gy % 400 == 0)
    ):
        g_day_no += 1

    g_day_no += gd2

    j_day_no = g_day_no - 79

    j_np = j_day_no // 12053
    j_day_no %= 12053

    jy = (
        979
        + 33 * j_np
        + 4 * (j_day_no // 1461)
    )

    j_day_no %= 1461

    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365

    i = 0

    while (
        i < 11
        and j_day_no >= j_days_in_month[i]
    ):
        j_day_no -= j_days_in_month[i]
        i += 1

    jm = i + 1
    jd = j_day_no + 1

    return jy, jm, jd


# ============================================================
# Tehran date/time
# ============================================================

def get_tehran_datetime():
    now = datetime.now(
        ZoneInfo("Asia/Tehran")
    )

    jy, jm, jd = gregorian_to_jalali(
        now.year,
        now.month,
        now.day,
    )

    date_text = (
        f"{jy:04d}/{jm:02d}/{jd:02d}"
    )

    time_text = now.strftime(
        "%H:%M"
    )

    return date_text, time_text


# ============================================================
# Remaining time until oldest config expires
# ============================================================

MAX_AGE_SECONDS = 4 * 60 * 60


def get_expiration_info(state: dict) -> str:
    """
    زمان باقی‌مانده تا حذف قدیمی‌ترین کانفیگ فعلی را نمایش می‌دهد.
    """

    database = state.get(
        "configs",
        {},
    )

    if not database:
        return "⏳ حذف کانفیگ‌های قدیمی: بدون کانفیگ"

    now = int(time.time())

    remaining_times = []

    for item in database.values():
        try:
            created_at = int(
                item.get(
                    "created_at",
                    now,
                )
            )

            remaining = (
                MAX_AGE_SECONDS
                - (now - created_at)
            )

            # اگر قبلاً از زمان انقضا گذشته باشد
            if remaining < 0:
                remaining = 0

            remaining_times.append(
                remaining
            )

        except (TypeError, ValueError):
            continue

    if not remaining_times:
        return (
            "⏳ حذف کانفیگ‌های قدیمی: "
            "نامشخص"
        )

    # کمترین زمان = قدیمی‌ترین کانفیگ
    remaining = min(
        remaining_times
    )

    hours = remaining // 3600
    minutes = (
        remaining % 3600
    ) // 60

    if hours > 0:
        if minutes > 0:
            return (
                "⏳ حذف کانفیگ‌های قدیمی: "
                f"{hours} ساعت و {minutes} دقیقه دیگر"
            )

        return (
            "⏳ حذف کانفیگ‌های قدیمی: "
            f"{hours} ساعت دیگر"
        )

    if minutes > 0:
        return (
            "⏳ حذف کانفیگ‌های قدیمی: "
            f"{minutes} دقیقه دیگر"
        )

    return (
        "⏳ حذف کانفیگ‌های قدیمی: "
        "کمتر از ۱ دقیقه دیگر"
    )


# ============================================================
# Generate outputs
# ============================================================

def generate_subscription(
    configs: list[str],
    state: dict,
):
    # --------------------------------------------------------
    # Clean empty configs
    # --------------------------------------------------------

    configs = [
        config.strip()
        for config in configs
        if config and config.strip()
    ]

    # --------------------------------------------------------
    # Subscription content
    #
    # IMPORTANT:
    # subscription.txt contains ONLY configs.
    # --------------------------------------------------------

    text = "\n".join(configs)

    encoded = base64.b64encode(
        text.encode("utf-8")
    ).decode("ascii")

    SUBSCRIPTION_FILE.write_text(
        encoded,
        encoding="utf-8",
    )

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    vless_count = sum(
        1
        for config in configs
        if config.lower().startswith(
            "vless://"
        )
    )

    trojan_count = sum(
        1
        for config in configs
        if config.lower().startswith(
            "trojan://"
        )
    )

    all_count = len(configs)

    # --------------------------------------------------------
    # Tehran date/time
    # --------------------------------------------------------

    date_text, time_text = (
        get_tehran_datetime()
    )

    # --------------------------------------------------------
    # Remaining expiration time
    # --------------------------------------------------------

    expiration_info = (
        get_expiration_info(state)
    )

    # --------------------------------------------------------
    # Human-readable output
    #
    # This file is NOT the subscription.
    # --------------------------------------------------------

    info = (
        f"ℹ️ VLESS: {vless_count} | "
        f"Trojan: {trojan_count} | "
        f"All: {all_count}\n\n"
        f"🕒 آخرین بروزرسانی: "
        f"{date_text} - {time_text}\n\n"
        f"{expiration_info}\n\n"
    )

    CONFIGS_FILE.write_text(
        info + text,
        encoding="utf-8",
    )


# ============================================================
# Main
# ============================================================

async def async_main():
    print("=" * 60)
    print("IR-RUSE Subscription Collector")
    print("=" * 60)

    # --------------------------------------------------------
    # Prepare directories
    # --------------------------------------------------------

    OUTPUT_DIR.mkdir(
        exist_ok=True
    )

    STATE_FILE.parent.mkdir(
        exist_ok=True
    )

    # --------------------------------------------------------
    # Load state
    # --------------------------------------------------------

    state = load_state(
        str(STATE_FILE)
    )

    # --------------------------------------------------------
    # Load sources
    # --------------------------------------------------------

    telegram_channels, subscription_urls = (
        load_sources()
    )

    print(
        f"[INFO] Telegram channels: "
        f"{len(telegram_channels)}",
        flush=True,
    )

    print(
        f"[INFO] Subscription URLs: "
        f"{len(subscription_urls)}",
        flush=True,
    )

    # --------------------------------------------------------
    # Telegram
    # --------------------------------------------------------

    telegram_configs = []

    api_id = os.getenv(
        "TG_API_ID"
    )

    api_hash = os.getenv(
        "TG_API_HASH"
    )

    session_string = os.getenv(
        "TG_SESSION"
    )

    if (
        telegram_channels
        and api_id
        and api_hash
        and session_string
    ):
        print(
            "[INFO] Starting Telegram collector...",
            flush=True,
        )

        telegram_configs = await collect_telegram(
            int(api_id),
            api_hash,
            session_string,
            telegram_channels,
            state,
        )

    elif telegram_channels:

        print(
            "[WARNING] Telegram sources exist "
            "but TG secrets are missing.",
            flush=True,
        )

    # --------------------------------------------------------
    # Subscription URLs
    # --------------------------------------------------------

    print(
        "[INFO] Starting subscription collector...",
        flush=True,
    )

    subscription_configs = (
        await collect_subscriptions(
            subscription_urls
        )
    )

    # --------------------------------------------------------
    # Collector statistics
    # --------------------------------------------------------

    print(
        f"[INFO] New Telegram configs: "
        f"{len(telegram_configs)}",
        flush=True,
    )

    print(
        f"[INFO] Subscription configs: "
        f"{len(subscription_configs)}",
        flush=True,
    )

    # --------------------------------------------------------
    # Add configs
    # --------------------------------------------------------

    before = len(
        state.get(
            "configs",
            {},
        )
    )

    add_configs(
        state,
        telegram_configs
        + subscription_configs,
    )

    after = len(
        state.get(
            "configs",
            {},
        )
    )

    print(
        f"[INFO] Added unique: "
        f"{after - before}",
        flush=True,
    )

    # --------------------------------------------------------
    # Remove expired configs
    # --------------------------------------------------------

    expired = remove_expired(
        state
    )

    print(
        f"[INFO] Removed expired: "
        f"{expired}",
        flush=True,
    )

    # --------------------------------------------------------
    # Active configs
    # --------------------------------------------------------

    active = get_active_configs(
        state
    )

    active.sort()

    # --------------------------------------------------------
    # Generate subscription + readable output
    # --------------------------------------------------------

    generate_subscription(
        active,
        state,
    )

    # --------------------------------------------------------
    # Save state
    # --------------------------------------------------------

    save_state(
        str(STATE_FILE),
        state,
    )

    # --------------------------------------------------------
    # Final statistics
    # --------------------------------------------------------

    vless_count = sum(
        1
        for config in active
        if config.lower().startswith(
            "vless://"
        )
    )

    trojan_count = sum(
        1
        for config in active
        if config.lower().startswith(
            "trojan://"
        )
    )

    date_text, time_text = (
        get_tehran_datetime()
    )

    expiration_info = (
        get_expiration_info(state)
    )

    print(
        f"[INFO] Active configs: "
        f"{len(active)}",
        flush=True,
    )

    print(
        f"[INFO] VLESS: "
        f"{vless_count}",
        flush=True,
    )

    print(
        f"[INFO] Trojan: "
        f"{trojan_count}",
        flush=True,
    )

    print(
        f"[INFO] All: "
        f"{len(active)}",
        flush=True,
    )

    print(
        f"[INFO] Tehran update: "
        f"{date_text} - {time_text}",
        flush=True,
    )

    print(
        f"[INFO] {expiration_info}",
        flush=True,
    )

    print(
        "[DONE]",
        flush=True,
    )


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    asyncio.run(
        async_main()
    )
