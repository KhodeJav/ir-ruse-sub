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
# Collector Retry Settings
# ============================================================

# حداکثر تعداد تلاش برای هر Source
MAX_RETRIES = 3

# فاصله بین تلاش‌ها
RETRY_DELAYS = (
    3,
    7,
)


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
# Safe output writer
# ============================================================

def safe_write_text(
    path: Path,
    content: str,
):
    """
    فایل خروجی را به صورت اتمیک می‌نویسد.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    try:
        with open(
            temp_path,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:

            f.write(content)

            # اطمینان از flush شدن اطلاعات
            f.flush()

            try:
                os.fsync(
                    f.fileno()
                )
            except OSError:
                # در بعضی محیط‌ها fsync ممکن است در دسترس نباشد
                pass

        os.replace(
            temp_path,
            path,
        )

    except Exception:

        try:
            if temp_path.exists():
                temp_path.unlink()
        except Exception:
            pass

        raise


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


def get_expiration_info(
    state: dict,
) -> str:
    """
    زمان باقی‌مانده تا حذف قدیمی‌ترین کانفیگ فعلی را نمایش می‌دهد.
    """

    database = state.get(
        "configs",
        {},
    )

    if not database:
        return "حذف کانفیگ‌های قدیمی: بدون کانفیگ"

    now = int(
        time.time()
    )

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

            if remaining < 0:
                remaining = 0

            remaining_times.append(
                remaining
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

    if not remaining_times:
        return (
            "حذف کانفیگ‌های قدیمی: "
            "نامشخص"
        )

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
# Generic retry helper
# ============================================================

async def retry_async(
    operation,
    source_name: str,
    timeout: int,
    max_retries: int = MAX_RETRIES,
):
    """
    اجرای یک Source با حداکثر 3 تلاش.

    نتیجه:

        ("success", result)
        ("empty", [])
        ("failed", [])

    Empty به معنی خطا نیست.
    یعنی Source سالم بوده ولی کانفیگ جدیدی نداشته است.
    """

    last_error = None

    for attempt in range(
        1,
        max_retries + 1,
    ):

        try:

            print(
                f"[INFO] {source_name} "
                f"attempt {attempt}/{max_retries}",
                flush=True,
            )

            result = await asyncio.wait_for(
                operation(),
                timeout=timeout,
            )

            # ------------------------------------------------
            # Source سالم است ولی کانفیگ جدید ندارد
            # ------------------------------------------------

            if not result:

                print(
                    f"[INFO] {source_name} "
                    "returned no new configs -> skipped",
                    flush=True,
                )

                return (
                    "empty",
                    [],
                )

            # ------------------------------------------------
            # Success
            # ------------------------------------------------

            print(
                f"[INFO] {source_name} "
                f"success -> {len(result)} configs",
                flush=True,
            )

            return (
                "success",
                result,
            )

        except asyncio.TimeoutError as e:

            last_error = e

            print(
                f"[WARNING] {source_name} "
                f"timeout on attempt "
                f"{attempt}/{max_retries}",
                flush=True,
            )

        except Exception as e:

            last_error = e

            print(
                f"[WARNING] {source_name} "
                f"failed on attempt "
                f"{attempt}/{max_retries}: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )

        # ----------------------------------------------------
        # Retry delay
        # ----------------------------------------------------

        if attempt < max_retries:

            delay_index = min(
                attempt - 1,
                len(RETRY_DELAYS) - 1,
            )

            delay = RETRY_DELAYS[
                delay_index
            ]

            print(
                f"[INFO] Retrying {source_name} "
                f"in {delay} seconds...",
                flush=True,
            )

            await asyncio.sleep(
                delay
            )

    # --------------------------------------------------------
    # All attempts failed
    # --------------------------------------------------------

    if last_error is not None:

        print(
            f"[WARNING] {source_name} "
            f"failed after {max_retries} attempts -> skipped",
            flush=True,
        )

    return (
        "failed",
        [],
    )


# ============================================================
# Telegram fail-safe collector
# ============================================================

async def collect_telegram_safe(
    telegram_channels,
    api_id,
    api_hash,
    session_string,
    state,
):
    """
    ابتدا رفتار اصلی Batch Collector را حفظ می‌کند.

    اگر Batch موفق شود:
        همان نتیجه استفاده می‌شود.

    اگر Batch خطا/Timeout شود:
        هر Channel جداگانه بررسی می‌شود
        و برای هر Channel حداکثر 3 Retry انجام می‌شود.
    """

    if not telegram_channels:
        return []

    # --------------------------------------------------------
    # Existing batch behavior
    # --------------------------------------------------------

    async def batch_operation():

        return await collect_telegram(
            int(api_id),
            api_hash,
            session_string,
            telegram_channels,
            state,
        )

    batch_status, batch_result = (
        await retry_async(
            operation=batch_operation,
            source_name=(
                "Telegram batch collector"
            ),
            timeout=120,
            max_retries=MAX_RETRIES,
        )
    )

    # --------------------------------------------------------
    # Batch success
    # --------------------------------------------------------

    if batch_status == "success":

        return batch_result

    # --------------------------------------------------------
    # Batch empty
    # --------------------------------------------------------

    if batch_status == "empty":

        return []

    # --------------------------------------------------------
    # Batch failed
    # -> fallback to per-channel
    # --------------------------------------------------------

    print(
        "[INFO] Telegram batch collector failed. "
        "Switching to per-channel mode...",
        flush=True,
    )

    collected = []

    for channel in telegram_channels:

        async def channel_operation(
            channel=channel,
        ):

            return await collect_telegram(
                int(api_id),
                api_hash,
                session_string,
                [channel],
                state,
            )

        status, result = (
            await retry_async(
                operation=channel_operation,
                source_name=(
                    f"Telegram source {channel}"
                ),
                timeout=120,
                max_retries=MAX_RETRIES,
            )
        )

        if status == "success":

            collected.extend(
                result
            )

        elif status == "empty":

            continue

        else:

            continue

    return collected


# ============================================================
# Subscription fail-safe collector
# ============================================================

async def collect_subscriptions_safe(
    subscription_urls,
):
    """
    ابتدا رفتار اصلی Batch Collector را حفظ می‌کند.

    اگر Batch خطا/Timeout شود:
        هر URL جداگانه بررسی می‌شود
        و برای هر URL حداکثر 3 Retry انجام می‌شود.
    """

    if not subscription_urls:
        return []

    # --------------------------------------------------------
    # Existing batch behavior
    # --------------------------------------------------------

    async def batch_operation():

        return await collect_subscriptions(
            subscription_urls
        )

    batch_status, batch_result = (
        await retry_async(
            operation=batch_operation,
            source_name=(
                "Subscription batch collector"
            ),
            timeout=180,
            max_retries=MAX_RETRIES,
        )
    )

    # --------------------------------------------------------
    # Batch success
    # --------------------------------------------------------

    if batch_status == "success":

        return batch_result

    # --------------------------------------------------------
    # Batch empty
    # --------------------------------------------------------

    if batch_status == "empty":

        return []

    # --------------------------------------------------------
    # Batch failed
    # -> fallback per URL
    # --------------------------------------------------------

    print(
        "[INFO] Subscription batch collector failed. "
        "Switching to per-source mode...",
        flush=True,
    )

    collected = []

    for url in subscription_urls:

        async def source_operation(
            url=url,
        ):

            return await collect_subscriptions(
                [url]
            )

        status, result = (
            await retry_async(
                operation=source_operation,
                source_name=(
                    f"Subscription source {url}"
                ),
                timeout=60,
                max_retries=MAX_RETRIES,
            )
        )

        if status == "success":

            collected.extend(
                result
            )

        elif status == "empty":

            continue

        else:

            continue

    return collected


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
        if isinstance(config, str)
        and config.strip()
    ]

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

    all_count = len(
        configs
    )

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
        get_expiration_info(
            state
        )
    )

    expiration_text = (
        expiration_info.replace(
            "حذف کانفیگ‌های قدیمی: ",
            "",
        )
    )

    # --------------------------------------------------------
    # Fake SOCKS5 information configs
    #
    # قابلیت قبلی دست‌نخورده باقی مانده
    # --------------------------------------------------------

    info_configs = [

        # ----------------------------------------------------
        # Statistics
        # ----------------------------------------------------

        (
            "socks5://127.0.0.1:1080"
            f"#📊 VLESS: {vless_count} | "
            f"🟣 Trojan: {trojan_count} | "
            f"📦 All: {all_count}"
        ),

        # ----------------------------------------------------
        # Last update
        # ----------------------------------------------------

        (
            "socks5://127.0.0.1:1081"
            f"#🗓️ تاریخ بروزرسانی: "
            f"{date_text} | "
            f"⏰ ساعت: {time_text}"
        ),

        # ----------------------------------------------------
        # Expiration
        # ----------------------------------------------------

        (
            "socks5://127.0.0.1:1082"
            f"#⏳ زمان تقریبی حذف شدن کانفیگ‌ها: "
            f"{expiration_text}"
        ),
    ]

    # --------------------------------------------------------
    # Build subscription
    # --------------------------------------------------------

    subscription_configs = (
        info_configs
        + configs
    )

    subscription_text = "\n".join(
        subscription_configs
    )

    # --------------------------------------------------------
    # Encode subscription
    # --------------------------------------------------------

    encoded = base64.b64encode(
        subscription_text.encode(
            "utf-8"
        )
    ).decode(
        "ascii"
    )

    # --------------------------------------------------------
    # Write subscription safely
    # --------------------------------------------------------

    safe_write_text(
        SUBSCRIPTION_FILE,
        encoded,
    )

    # --------------------------------------------------------
    # Human-readable output
    # --------------------------------------------------------

    safe_write_text(
        CONFIGS_FILE,
        subscription_text,
    )

    # --------------------------------------------------------
    # Verify output files
    # --------------------------------------------------------

    if not SUBSCRIPTION_FILE.exists():
        raise RuntimeError(
            "subscription.txt was not created."
        )

    if not CONFIGS_FILE.exists():
        raise RuntimeError(
            "configs.txt was not created."
        )

    print(
        "[INFO] Output files updated successfully.",
        flush=True,
    )

    print(
        f"[INFO] subscription.txt size: "
        f"{SUBSCRIPTION_FILE.stat().st_size} bytes",
        flush=True,
    )

    print(
        f"[INFO] configs.txt size: "
        f"{CONFIGS_FILE.stat().st_size} bytes",
        flush=True,
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

        if not isinstance(
            state,
            dict,
        ):

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

            telegram_configs = (
                await collect_telegram_safe(
                    telegram_channels,
                    api_id,
                    api_hash,
                    session_string,
                    state,
                )
            )

        except Exception as e:

            print(
                f"[ERROR] Telegram safe collector failed: "
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

        subscription_configs = (
            await collect_subscriptions_safe(
                subscription_urls
            )
        )

    except Exception as e:

        print(
            f"[ERROR] Subscription safe collector failed: "
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
    # SAVE STATE BEFORE OUTPUT
    #
    # مهم:
    # state نهایی همین اجرای فعلی ابتدا ذخیره می‌شود.
    # سپس output دقیقاً از همین state ساخته می‌شود.
    # --------------------------------------------------------

    try:

        save_state(
            str(STATE_FILE),
            state,
        )

        print(
            "[INFO] state.json saved successfully.",
            flush=True,
        )

    except Exception as e:

        print(
            f"[ERROR] Failed to save state: "
            f"{type(e).__name__}: {e}",
            flush=True,
        )

        return

    # --------------------------------------------------------
    # ALWAYS generate output from current state
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
        get_expiration_info(
            state
        )
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
