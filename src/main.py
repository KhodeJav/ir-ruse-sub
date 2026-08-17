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
        return "حذف کانفیگ‌های قدیمی: بدون کانفیگ"

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
            "حذف کانفیگ‌های قدیمی: "
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
                "حذف کانفیگ‌های قدیمی: "
                f"{hours} ساعت و {minutes} دقیقه دیگر"
            )

        return (
            "حذف کانفیگ‌های قدیمی: "
            f"{hours} ساعت دیگر"
        )

    if minutes > 0:
        return (
            "حذف کانفیگ‌های قدیمی: "
            f"{minutes} دقیقه دیگر"
        )

    return (
        "حذف کانفیگ‌های قدیمی: "
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
    # Fake SOCKS5 display config
    #
    # IMPORTANT:
    # This is ONLY for configs.txt.
    # It is NOT added to subscription.txt.
    # --------------------------------------------------------

    fake_socks5_remark = (
        f"IR-RUSE | "
        f"VLESS: {vless_count} | "
        f"Trojan: {trojan_count} | "
        f"All: {all_count} | "
        f"Update: {date_text} - {time_text} | "
        f"{expiration_info}"
    )

    fake_socks5 = (
        "socks5://127.0.0.1:1080"
        f"#{fake_socks5_remark}"
    )

    # --------------------------------------------------------
    # Human-readable output
    #
    # This file is NOT the subscription.
    # --------------------------------------------------------

    CONFIGS_FILE.write_text(
        fake_socks5
        + "\n\n"
        + text,
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

    try:
        state = load_state(
            str(STATE_FILE)
        )

        if not isinstance(state, dict):
            print(
                "[WARNING] Invalid state format. "
                "Creating a new state.",
                flush=True,
            )

            state = {
                "configs": {}
            }

    except Exception as e:
        print(
            f"[WARNING] Failed to load state: {e}",
            flush=True,
        )

        state = {
            "configs": {}
        }

    # --------------------------------------------------------
    # Load sources
    # --------------------------------------------------------

    try:
        telegram_channels, subscription_urls = (
            load_sources()
        )

    except Exception as e:
        print(
            f"[ERROR] Failed to load sources.txt: {e}",
            flush=True,
        )

        return

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

        try:
            telegram_configs = await asyncio.wait_for(
                collect_telegram(
                    int(api_id),
                    api_hash,
                    session_string,
                    telegram_channels,
                    state,
                ),
                timeout=120,
            )

            if not telegram_configs:
                telegram_configs = []

        except asyncio.TimeoutError:

            print(
                "[ERROR] Telegram collector timeout "
                "(120 seconds). Continuing...",
                flush=True,
            )

            telegram_configs = []

        except Exception as e:

            print(
                f"[ERROR] Telegram collector failed: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )

            telegram_configs = []

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

    subscription_configs = []

    try:
        subscription_configs = await asyncio.wait_for(
            collect_subscriptions(
                subscription_urls
            ),
            timeout=180,
        )

        if not subscription_configs:
            subscription_configs = []

    except asyncio.TimeoutError:

        print(
            "[ERROR] Subscription collector timeout "
            "(180 seconds). Continuing...",
            flush=True,
        )

        subscription_configs = []

    except Exception as e:

        print(
            f"[ERROR] Subscription collector failed: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        subscription_configs = []

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

    try:

        add_configs(
            state,
            telegram_configs
            + subscription_configs,
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to add configs: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

    after = len(
        state.get(
            "configs",
            {}),
        )

    print(
        f"[INFO] Added unique: "
        f"{after - before}",
        flush=True,
    )

    # --------------------------------------------------------
    # Remove expired configs
    # --------------------------------------------------------

    try:

        expired = remove_expired(
            state
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to remove expired configs: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        expired = 0

    print(
        f"[INFO] Removed expired: "
        f"{expired}",
        flush=True,
    )

    # --------------------------------------------------------
    # Active configs
    # --------------------------------------------------------

    try:

        active = get_active_configs(
            state
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to get active configs: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        active = []

    active.sort()

    # --------------------------------------------------------
    # Generate subscription + readable output
    # --------------------------------------------------------

    try:

        generate_subscription(
            active,
            state,
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to generate outputs: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        return

    # --------------------------------------------------------
    # Save state
    # --------------------------------------------------------

    try:

        save_state(
            str(STATE_FILE),
            state,
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to save state: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        return

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
