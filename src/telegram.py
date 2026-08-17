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

    collected = []
    telegram_state = state.setdefault("telegram", {})

    try:
        print("[TG] Connecting...", flush=True)

        await client.connect()

        print("[TG] Connected.", flush=True)

        if not await client.is_user_authorized():
            raise RuntimeError("Telegram session is not authorized.")

        print("[TG] Authorized: True", flush=True)

        for channel in channels:
            channel = channel.strip()

            if not channel:
                continue

            try:
                print(
                    f"[TG] Processing channel: {channel}",
                    flush=True,
                )

                entity = await client.get_entity(channel)

                print(
                    f"[TG] Entity resolved: {channel}",
                    flush=True,
                )

                key = str(entity.id)

                saved_last_id = telegram_state.get(key)

                # ==================================================
                # FIRST RUN
                # فقط 20 پیام آخر
                # ==================================================

                if saved_last_id is None:

                    print(
                        f"[TG] FIRST RUN -> scanning only last "
                        f"{INITIAL_MESSAGES} messages",
                        flush=True,
                    )

                    messages = await client.get_messages(
                        entity,
                        limit=INITIAL_MESSAGES,
                    )

                    newest_id = 0
                    found_configs = 0

                    for message in messages:
                        if not message or not message.id:
                            continue

                        newest_id = max(
                            newest_id,
                            message.id,
                        )

                        text = get_full_message_text(message)

                        if not text:
                            continue

                        configs = extract_configs(text)

                        found_configs += len(configs)

                        for config in configs:
                            collected.append({
                                "config": config,
                                "source": channel,
                                "message_id": message.id,
                            })

                    if newest_id:
                        telegram_state[key] = newest_id

                    print(
                        f"[TG] FIRST RUN DONE | "
                        f"channel={channel} | "
                        f"last_id={newest_id} | "
                        f"configs={found_configs}",
                        flush=True,
                    )

                    continue

                # ==================================================
                # NEXT RUN
                # فقط پیام های جدید
                # ==================================================

                last_id = int(saved_last_id)

                print(
                    f"[TG] Checking new messages | "
                    f"channel={channel} | "
                    f"last_id={last_id}",
                    flush=True,
                )

                # --------------------------------------------------
                # فقط آخرین پیام کانال را می‌گیریم
                # --------------------------------------------------

                latest = await client.get_messages(
                    entity,
                    limit=1,
                )

                if not latest:
                    print(
                        f"[TG] Channel empty: {channel}",
                        flush=True,
                    )
                    continue

                latest_message = latest[0]

                if not latest_message or not latest_message.id:
                    continue

                latest_id = latest_message.id

                print(
                    f"[TG] Latest message ID: {latest_id}",
                    flush=True,
                )

                # --------------------------------------------------
                # هیچ پیام جدیدی نداریم
                # --------------------------------------------------

                if latest_id <= last_id:
                    print(
                        f"[TG] No new message: {channel}",
                        flush=True,
                    )
                    continue

                # --------------------------------------------------
                # پیام جدید داریم
                #
                # همه پیام‌های جدید بین last_id و latest_id
                # استخراج می‌شوند.
                #
                # اما هرگز تاریخچه قبل از last_id خوانده نمی‌شود.
                # --------------------------------------------------

                print(
                    f"[TG] NEW MESSAGES: "
                    f"{last_id + 1} -> {latest_id}",
                    flush=True,
                )

                messages = await client.get_messages(
                    entity,
                    min_id=last_id,
                    max_id=latest_id + 1,
                    reverse=True,
                )

                newest_processed_id = last_id
                found_configs = 0
                found_messages = 0

                for message in messages:
                    if not message or not message.id:
                        continue

                    if message.id <= last_id:
                        continue

                    if message.id > latest_id:
                        continue

                    found_messages += 1

                    newest_processed_id = max(
                        newest_processed_id,
                        message.id,
                    )

                    text = get_full_message_text(message)

                    if not text:
                        continue

                    configs = extract_configs(text)

                    found_configs += len(configs)

                    for config in configs:
                        collected.append({
                            "config": config,
                            "source": channel,
                            "message_id": message.id,
                        })

                # --------------------------------------------------
                # آخرین پیام پردازش‌شده ذخیره می‌شود
                # --------------------------------------------------

                telegram_state[key] = max(
                    newest_processed_id,
                    latest_id,
                )

                print(
                    f"[TG] UPDATE DONE | "
                    f"channel={channel} | "
                    f"messages={found_messages} | "
                    f"configs={found_configs} | "
                    f"last_id={telegram_state[key]}",
                    flush=True,
                )

            except Exception as exc:
                print(
                    f"[TG ERROR] {channel}: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )

    finally:
        print("[TG] Disconnecting...", flush=True)

        try:
            await client.disconnect()
        except Exception as exc:
            print(
                f"[TG] Disconnect error: {exc}",
                flush=True,
            )

        print("[TG] Disconnected.", flush=True)

    return collected


def get_full_message_text(message) -> str:
    parts = []

    # متن اصلی / caption
    text = getattr(message, "message", None)

    if text:
        parts.append(str(text))

    # Telegram entities
    entities = getattr(message, "entities", None) or []

    for entity in entities:
        try:
            url = getattr(entity, "url", None)

            if url:
                parts.append(str(url))

            offset = getattr(entity, "offset", None)
            length = getattr(entity, "length", None)

            if (
                offset is not None
                and length is not None
                and text
            ):
                value = text[
                    offset:offset + length
                ]

                if value:
                    parts.append(str(value))

        except Exception:
            continue

    # media caption
    media = getattr(message, "media", None)

    if media:
        caption = getattr(
            media,
            "caption",
            None,
        )

        if caption:
            parts.append(str(caption))

    # حذف تکراری‌ها
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
