from telethon import TelegramClient
from telethon.sessions import StringSession
from .parser import extract_configs

async def collect_telegram(api_id: int, api_hash: str, session_string: str, channels: list[str], state: dict):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise RuntimeError("Telegram session is not authorized.")

    collected = []
    telegram_state = state.setdefault("telegram", {})

    for channel in channels:
        channel = channel.strip()
        if not channel:
            continue
        try:
            entity = await client.get_entity(channel)
            key = str(entity.id)
            last_id = int(telegram_state.get(key, 0))
            newest_id = last_id

            async for message in client.iter_messages(entity, min_id=last_id, reverse=True):
                if not message.id:
                    continue
                newest_id = max(newest_id, message.id)
                text = message.message or ""
                for config in extract_configs(text):
                    collected.append({
                        "config": config,
                        "source": channel,
                        "message_id": message.id,
                    })
            telegram_state[key] = newest_id
        except Exception as exc:
            print(f"[TELEGRAM ERROR] {channel}: {exc}")

    await client.disconnect()
    return collected
