import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession

from .parser import extract_configs


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
        timeout=20,
        request_retries=2,
        connection_retries=2,
    )

    collected = []
    telegram_state = state.setdefault("telegram", {})

    try:
        print("[TELEGRAM] Connecting...", flush=True)

        await asyncio.wait_for(
            client.connect(),
            timeout=30
        )

        print("[TELEGRAM] Connected.", flush=True)

        authorized = await asyncio.wait_for(
            client.is_user_authorized(),
            timeout=30
        )

        if not authorized:
            raise RuntimeError("Telegram session is not authorized.")

        print("[TELEGRAM] Session authorized.", flush=True)

        for channel in channels:
            channel = channel.strip()

            if not channel:
                continue

            try:
                print(f"[TELEGRAM] Processing: {channel}", flush=True)

                entity = await asyncio.wait_for(
                    client.get_entity(channel),
                    timeout=30
                )

                key = str(entity.id)

                last_id = int(
                    telegram_state.get(key, 0)
                )

                newest_id = last_id

                print(
                    f"[TELEGRAM] {channel} | last_id={last_id}",
                    flush=True
                )

                async for message in client.iter_messages(
                    entity,
                    min_id=last_id,
                    reverse=True,
                    limit=500,
                ):
                    if not message.id:
                        continue

                    newest_id = max(
                        newest_id,
                        message.id
                    )

                    text = message.message or ""

                    for config in extract_configs(text):
                        collected.append({
                            "config": config,
                            "source": channel,
                            "message_id": message.id,
                        })

                telegram_state[key] = newest_id

                print(
                    f"[TELEGRAM] Finished: {channel} | newest_id={newest_id}",
                    flush=True
                )

            except Exception as exc:
                print(
                    f"[TELEGRAM ERROR] {channel}: {type(exc).__name__}: {exc}",
                    flush=True
                )

    finally:
        print("[TELEGRAM] Disconnecting...", flush=True)

        try:
            await asyncio.wait_for(
                client.disconnect(),
                timeout=10
            )
        except Exception as exc:
            print(
                f"[TELEGRAM] Disconnect error: {exc}",
                flush=True
            )

        print("[TELEGRAM] Disconnected.", flush=True)

    return collected
