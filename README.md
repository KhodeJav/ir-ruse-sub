# IR-RUSE Subscription Collector

Collects supported VLESS/VMess/Trojan/SS links from configured Telegram channels and external subscription URLs.

Features:
- Incremental Telegram reading using the last processed message ID.
- Duplicate removal.
- Remark replacement with `T.me/iR_RUSE | کانال ما`.
- 48-hour lifetime for collected configs.
- Base64 subscription output.
- Automatic GitHub Actions execution every 30 minutes.
- No VPS/hosting required.

## Important
Only use channels and subscription sources you are allowed to access and republish.

Secrets required in GitHub:
- `TG_API_ID`
- `TG_API_HASH`
- `TG_SESSION`

Do not commit your Telegram session to the repository.
