from telethon.sync import TelegramClient
from telethon.sessions import StringSession

api_id = int(input("API ID: ").strip())
api_hash = input("API HASH: ").strip()

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("\nLogin successful.\n")
    print("TG_SESSION:")
    print(client.session.save())
    print("\nKeep this value private. Do NOT put it in GitHub files.")
