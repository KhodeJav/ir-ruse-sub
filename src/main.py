import asyncio
import base64
import os
from pathlib import Path

from .telegram import collect_telegram
from .sources import collect_subscriptions
from .storage import add_configs, get_active_configs, load_state, remove_expired, save_state

ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = ROOT / "data" / "state.json"
OUTPUT_DIR = ROOT / "output"
SUBSCRIPTION_FILE = OUTPUT_DIR / "subscription.txt"
CONFIGS_FILE = OUTPUT_DIR / "configs.txt"

def load_sources():
    path = ROOT / "config" / "sources.txt"
    telegram, subscriptions = [], []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(("@", "https://t.me/", "http://t.me/")):
                telegram.append(line)
            elif line.startswith(("http://", "https://")):
                subscriptions.append(line)
    return telegram, subscriptions

def generate_subscription(configs: list[str]):
    text = "\n".join(configs)
    encoded = base64.b64encode(text.encode("utf-8")).decode("ascii")
    SUBSCRIPTION_FILE.write_text(encoded, encoding="utf-8")
    CONFIGS_FILE.write_text(text, encoding="utf-8")

async def async_main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    STATE_FILE.parent.mkdir(exist_ok=True)
    state = load_state(str(STATE_FILE))
    telegram_channels, subscription_urls = load_sources()

    print(f"[INFO] Telegram channels: {len(telegram_channels)}")
    print(f"[INFO] Subscription URLs: {len(subscription_urls)}")

    telegram_configs = []
    api_id, api_hash, session_string = os.getenv("TG_API_ID"), os.getenv("TG_API_HASH"), os.getenv("TG_SESSION")

    if telegram_channels and api_id and api_hash and session_string:
        telegram_configs = await collect_telegram(
            int(api_id), api_hash, session_string, telegram_channels, state
        )
    elif telegram_channels:
        print("[WARNING] Telegram sources exist but TG secrets are missing.")

    subscription_configs = await collect_subscriptions(subscription_urls)

    print(f"[INFO] New Telegram configs: {len(telegram_configs)}")
    print(f"[INFO] Subscription configs: {len(subscription_configs)}")

    before = len(state.get("configs", {}))
    add_configs(state, telegram_configs + subscription_configs)
    after = len(state.get("configs", {}))
    print(f"[INFO] Added unique: {after - before}")

    expired = remove_expired(state)
    print(f"[INFO] Removed expired: {expired}")

    active = get_active_configs(state)
    active.sort()
    generate_subscription(active)
    save_state(str(STATE_FILE), state)

    print(f"[INFO] Active configs: {len(active)}")
    print("[DONE]")

if __name__ == "__main__":
    asyncio.run(async_main())
