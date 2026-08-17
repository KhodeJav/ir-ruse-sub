import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from .parser import extract_configs


INITIAL_MESSAGES = 20
PAGE_SIZE = 100


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

        await asyncio.wait_for(
            client.connect(),
            timeout=30,
        )

        print("[TG] Connected.", flush=True)

        authorized = await asyncio.wait_for(
            client.is_user_authorized(),
            timeout=30,
        )

        print(
            f"[TG] Authorized: {authorized}",
            flush=True,
        )

        if not authorized:
            raise RuntimeError(
                "Telegram session is not authorized."
            )

        for channel in channels:
            channel = channel.strip()

            if not channel:
                continue

            print(
                f"[TG] Processing channel: {channel}",
                flush=True,
            )

            try:
                entity = await asyncio.wait_for(
                    client.get_entity(channel),
                    timeout=30,
                )

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
                        f"[TG] First scan -> last {INITIAL_MESSAGES}: {channel}",
                        flush=True,
                    )

                    messages = await asyncio.wait_for(
                        client.get_messages(
                            entity,
                            limit=INITIAL_MESSAGES,
                        ),
                        timeout=60,
                    )

                    newest_id = 0

                    # get_messages از جدید به قدیم برمی‌گرداند
                    # ولی همه همان 20 پیام آخر هستند.
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

                        for config in configs:
                            collected.append({
                                "config": config,
                                "source": channel,
                                "message_id": message.id,
                            })

                    if newest_id:
                        telegram_state[key] = newest_id

                    print(
                        f"[TG] First scan done: {channel} | "
                        f"last_id={newest_id} | "
                        f"configs={len(collected)}",
                        flush=True,
                    )

                # ==================================================
                # NEXT RUN
                # فقط پیام های جدید
                # ==================================================
                else:

                    last_id = int(saved_last_id)
                    newest_id = last_id

                    print(
                        f"[TG] Incremental scan: {channel} | "
                        f"{last_id} -> new messages",
                        flush=True,
                    )

                    total_messages = 0
                    page = 0

                    # ------------------------------------------------
                    # هر بار فقط 100 پیام
                    # ------------------------------------------------
                    while True:
                        page += 1

                        print(
                            f"[TG] Fetching page {page} "
                            f"after message {newest_id}...",
                            flush=True,
                        )

                        messages = await asyncio.wait_for(
                            client.get_messages(
                                entity,
                                min_id=newest_id,
                                limit=PAGE_SIZE,
                                reverse=True,
                            ),
                            timeout=60,
                        )

                        if not messages:
                            break

                        page_new_messages = 0

                        for message in messages:
                            if not message or not message.id:
                                continue

                            if message.id <= newest_id:
                                continue

                            page_new_messages += 1
                            total_messages += 1

                            newest_id = max(
                                newest_id,
                                message.id,
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

                        print(
                            f"[TG] Page {page} done | "
                            f"messages={page_new_messages} | "
                            f"last_id={newest_id}",
                            flush=True,
                        )

                        # اگر کمتر از PAGE_SIZE برگشت،
                        # یعنی احتمالاً به آخرین پیام‌ها رسیده‌ایم.
                        if len(messages) < PAGE_SIZE:
                            break

                        # جلوگیری از loop بی‌نهایت
                        if page_new_messages == 0:
                            break

                    telegram_state[key] = newest_id

                    print(
                        f"[TG] Incremental scan done: {channel} | "
                        f"new_messages={total_messages} | "
                        f"newest_id={newest_id}",
                        flush=True,
                    )

            except asyncio.TimeoutError:
                print(
                    f"[TG TIMEOUT] {channel}",
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
            await asyncio.wait_for(
                client.disconnect(),
                timeout=10,
            )
        except Exception as exc:
            print(
                f"[TG] Disconnect error: {exc}",
                flush=True,
            )

        print("[TG] Disconnected.", flush=True)

    return collected


def get_full_message_text(message) -> str:
    parts = []

    text = getattr(message, "message", None)

    if text:
        parts.append(str(text))

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

    media = getattr(message, "media", None)

    if media:
        caption = getattr(
            media,
            "caption",
            None,
        )

        if caption:
            parts.append(str(caption))

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
