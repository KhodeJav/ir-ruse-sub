from telethon import TelegramClient
from telethon.sessions import StringSession

from .parser import extract_configs


# ------------------------------------------------------------
# تنظیمات
# ------------------------------------------------------------

INITIAL_MESSAGES = 20


async def collect_telegram(
    api_id: int,
    api_hash: str,
    session_string: str,
    channels: list[str],
    state: dict,
):
    """
    جمع‌آوری کانفیگ از کانال‌های Telegram.

    منطق:

    اولین اجرا:
        فقط 20 پیام آخر کانال بررسی می‌شود.

    اجراهای بعدی:
        فقط آخرین پیام کانال دریافت می‌شود.
        اگر message_id جدید باشد، فقط همان پیام استخراج می‌شود.
    """

    print("[TG] Creating Telegram client...", flush=True)

    client = TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
        timeout=20,
        connection_retries=2,
        request_retries=2,
        retry_delay=2,
    )

    collected: list[dict] = []

    # state.telegram
    telegram_state = state.setdefault(
        "telegram",
        {}
    )

    try:
        # --------------------------------------------------------
        # اتصال
        # --------------------------------------------------------

        print("[TG] Connecting...", flush=True)

        await client.connect()

        print("[TG] Connected.", flush=True)

        # --------------------------------------------------------
        # بررسی Session
        # --------------------------------------------------------

        authorized = await client.is_user_authorized()

        print(
            f"[TG] Authorized: {authorized}",
            flush=True,
        )

        if not authorized:
            raise RuntimeError(
                "Telegram session is not authorized."
            )

        # --------------------------------------------------------
        # کانال‌ها
        # --------------------------------------------------------

        for channel in channels:

            channel = channel.strip()

            if not channel:
                continue

            try:
                print(
                    f"[TG] Processing channel: {channel}",
                    flush=True,
                )

                # ------------------------------------------------
                # دریافت Entity
                # ------------------------------------------------

                entity = await client.get_entity(channel)

                print(
                    f"[TG] Entity resolved: {channel}",
                    flush=True,
                )

                # ID یکتای کانال
                channel_key = str(entity.id)

                # آخرین message_id ذخیره‌شده
                saved_last_id = telegram_state.get(
                    channel_key
                )

                # ====================================================
                # FIRST RUN
                # فقط 20 پیام آخر
                # ====================================================

                if saved_last_id is None:

                    print(
                        f"[TG] FIRST RUN -> "
                        f"last {INITIAL_MESSAGES} messages",
                        flush=True,
                    )

                    messages = await client.get_messages(
                        entity,
                        limit=INITIAL_MESSAGES,
                    )

                    newest_id = 0
                    found_configs = 0
                    processed_messages = 0

                    for message in messages:

                        if not message:
                            continue

                        if not message.id:
                            continue

                        processed_messages += 1

                        newest_id = max(
                            newest_id,
                            message.id,
                        )

                        # --------------------------------------------
                        # متن کامل پیام
                        # --------------------------------------------

                        text = get_full_message_text(
                            message
                        )

                        if not text:
                            continue

                        # --------------------------------------------
                        # استخراج
                        # --------------------------------------------

                        configs = extract_configs(
                            text
                        )

                        found_configs += len(configs)

                        for config in configs:

                            collected.append(
                                {
                                    "config": config,
                                    "source": channel,
                                    "message_id": message.id,
                                }
                            )

                    # --------------------------------------------
                    # ذخیره آخرین پیام
                    # --------------------------------------------

                    if newest_id:
                        telegram_state[channel_key] = (
                            newest_id
                        )

                    print(
                        f"[TG] FIRST RUN DONE | "
                        f"channel={channel} | "
                        f"messages={processed_messages} | "
                        f"last_id={newest_id} | "
                        f"configs={found_configs}",
                        flush=True,
                    )

                    continue

                # ====================================================
                # NEXT RUN
                # فقط آخرین پیام
                # ====================================================

                last_id = int(
                    saved_last_id
                )

                print(
                    f"[TG] Checking latest message | "
                    f"channel={channel} | "
                    f"last_id={last_id}",
                    flush=True,
                )

                # ------------------------------------------------
                # فقط آخرین پیام کانال
                # ------------------------------------------------

                latest_messages = await client.get_messages(
                    entity,
                    limit=1,
                )

                if not latest_messages:

                    print(
                        f"[TG] No messages: {channel}",
                        flush=True,
                    )

                    continue

                message = latest_messages[0]

                if not message:
                    continue

                if not message.id:
                    continue

                latest_id = message.id

                print(
                    f"[TG] Latest message ID: {latest_id}",
                    flush=True,
                )

                # ------------------------------------------------
                # پیام جدیدی وجود ندارد
                # ------------------------------------------------

                if latest_id <= last_id:

                    print(
                        f"[TG] No new message | "
                        f"channel={channel}",
                        flush=True,
                    )

                    continue

                # ====================================================
                # پیام جدید است
                # فقط همین پیام پردازش می‌شود
                # ====================================================

                print(
                    f"[TG] NEW MESSAGE | "
                    f"{last_id} -> {latest_id}",
                    flush=True,
                )

                text = get_full_message_text(
                    message
                )

                found_configs = 0

                if text:

                    configs = extract_configs(
                        text
                    )

                    found_configs = len(
                        configs
                    )

                    for config in configs:

                        collected.append(
                            {
                                "config": config,
                                "source": channel,
                                "message_id": message.id,
                            }
                        )

                # ------------------------------------------------
                # مهم:
                # حتی اگر پیام کانفیگ نداشته باشد،
                # message_id جدید ثبت می‌شود.
                # ------------------------------------------------

                telegram_state[channel_key] = (
                    latest_id
                )

                print(
                    f"[TG] NEW MESSAGE PROCESSED | "
                    f"channel={channel} | "
                    f"message_id={latest_id} | "
                    f"configs={found_configs}",
                    flush=True,
                )

            except Exception as exc:

                print(
                    f"[TG ERROR] {channel}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

    finally:

        print(
            "[TG] Disconnecting...",
            flush=True,
        )

        try:
            await client.disconnect()

        except Exception as exc:

            print(
                f"[TG] Disconnect error: {exc}",
                flush=True,
            )

        print(
            "[TG] Disconnected.",
            flush=True,
        )

    return collected


# ================================================================
# استخراج تمام محتوای قابل دسترسی پیام Telegram
# ================================================================

def get_full_message_text(message) -> str:

    parts: list[str] = []

    # ------------------------------------------------------------
    # متن اصلی پیام / Caption
    # ------------------------------------------------------------

    text = getattr(
        message,
        "message",
        None,
    )

    if text:
        parts.append(
            str(text)
        )

    # ------------------------------------------------------------
    # Telegram entities
    #
    # شامل:
    # TextUrl
    # URL
    # Code
    # Pre
    # و ...
    # ------------------------------------------------------------

    entities = getattr(
        message,
        "entities",
        None,
    ) or []

    for entity in entities:

        try:

            # Text URL
            url = getattr(
                entity,
                "url",
                None,
            )

            if url:
                parts.append(
                    str(url)
                )

            # متن Entity
            offset = getattr(
                entity,
                "offset",
                None,
            )

            length = getattr(
                entity,
                "length",
                None,
            )

            if (
                offset is not None
                and length is not None
                and text
            ):

                value = text[
                    offset:
                    offset + length
                ]

                if value:
                    parts.append(
                        str(value)
                    )

        except Exception:

            continue

    # ------------------------------------------------------------
    # Media caption
    # ------------------------------------------------------------

    media = getattr(
        message,
        "media",
        None,
    )

    if media:

        caption = getattr(
            media,
            "caption",
            None,
        )

        if caption:
            parts.append(
                str(caption)
            )

    # ------------------------------------------------------------
    # حذف بخش‌های کاملاً تکراری
    # بدون تغییر محتوای واقعی
    # ------------------------------------------------------------

    result: list[str] = []
    seen: set[str] = set()

    for item in parts:

        item = item.strip()

        if not item:
            continue

        if item in seen:
            continue

        seen.add(item)

        result.append(item)

    return "\n".join(result)
