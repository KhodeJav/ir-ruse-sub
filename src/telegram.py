from telethon import TelegramClient
from telethon.sessions import StringSession

from .parser import extract_configs


INITIAL_MESSAGES = 20


async def collect_telegram(
    api_id: int,
    api_hash: str,
    session_string: str,
    channels: list[str],
    state: dict,
):
    client = TelegramClient(
        StringSession(session_string),
        api_id,
        api_hash,
    )

    collected = []
    telegram_state = state.setdefault("telegram", {})

    await client.connect()

    try:
        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session is not authorized.")

        for channel in channels:
            channel = channel.strip()

            if not channel:
                continue

            try:
                entity = await client.get_entity(channel)
                key = str(entity.id)

                # آخرین پیام پردازش‌شده
                saved_last_id = telegram_state.get(key)

                # --------------------------------------------------
                # اولین اجرا:
                # فقط 20 پیام آخر
                # --------------------------------------------------
                if saved_last_id is None:
                    messages = client.iter_messages(
                        entity,
                        limit=INITIAL_MESSAGES,
                    )

                    newest_id = 0

                    async for message in messages:
                        if not message or not message.id:
                            continue

                        newest_id = max(
                            newest_id,
                            message.id
                        )

                        text = get_full_message_text(message)

                        if not text:
                            continue

                        configs = extract_configs(text)

                        for config in configs:
                            collected.append({
                                "config": config,
                                "source": channel,
                                "message_id": message.id,
                            })

                    if newest_id:
                        telegram_state[key] = newest_id

                    print(
                        f"[TELEGRAM] Initial scan: "
                        f"{channel} | last={newest_id} | "
                        f"configs={len(collected)}",
                        flush=True,
                    )

                # --------------------------------------------------
                # اجراهای بعدی:
                # فقط پیام‌های جدید
                # --------------------------------------------------
                else:
                    last_id = int(saved_last_id)
                    newest_id = last_id

                    async for message in client.iter_messages(
                        entity,
                        min_id=last_id,
                        reverse=True,
                    ):
                        if not message or not message.id:
                            continue

                        newest_id = max(
                            newest_id,
                            message.id
                        )

                        text = get_full_message_text(message)

                        if not text:
                            continue

                        configs = extract_configs(text)

                        for config in configs:
                            collected.append({
                                "config": config,
                                "source": channel,
                                "message_id": message.id,
                            })

                    telegram_state[key] = newest_id

                    print(
                        f"[TELEGRAM] New messages: "
                        f"{channel} | "
                        f"{last_id} -> {newest_id}",
                        flush=True,
                    )

            except Exception as exc:
                print(
                    f"[TELEGRAM ERROR] {channel}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

    finally:
        await client.disconnect()

    return collected


def get_full_message_text(message) -> str:
    """
    تمام محتوای متنی قابل دسترس پیام Telegram را جمع می‌کند.

    شامل:
    - متن عادی
    - متن code/pre
    - quote
    - URL های داخل entity
    - text_url
    - متن caption
    """

    parts = []

    # متن اصلی / caption
    text = getattr(message, "message", None)

    if text:
        parts.append(str(text))

    # --------------------------------------------------
    # Message entities
    # --------------------------------------------------

    entities = getattr(message, "entities", None) or []

    for entity in entities:
        try:
            # TextUrl
            url = getattr(entity, "url", None)

            if url:
                parts.append(str(url))

            # URL
            offset = getattr(entity, "offset", None)
            length = getattr(entity, "length", None)

            if (
                offset is not None
                and length is not None
                and text
            ):
                value = text[offset:offset + length]

                if value:
                    parts.append(str(value))

        except Exception:
            continue

    # --------------------------------------------------
    # Message media caption
    # --------------------------------------------------

    media = getattr(message, "media", None)

    if media:
        caption = getattr(media, "caption", None)

        if caption:
            parts.append(str(caption))

    # --------------------------------------------------
    # حذف تکراری‌ها بدون تغییر محتوا
    # --------------------------------------------------

    result = []
    seen = set()

    for item in parts:
        item = item.strip()

        if not item:
            continue

        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return "\n".join(result)
