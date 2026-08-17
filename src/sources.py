import aiohttp

from .parser import (
    extract_configs,
    decode_possible_base64,
)


async def fetch_subscription(
    session,
    url: str,
) -> list[str]:
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=20),
            headers={
                "User-Agent": "Mozilla/5.0 (IR-RUSE-Subscription/1.0)"
            },
        ) as response:

            if response.status != 200:
                print(
                    f"[SOURCE] HTTP {response.status}: {url}",
                    flush=True,
                )
                return []

            data = await response.text(
                errors="ignore"
            )

            # اول استخراج مستقیم
            configs = extract_configs(data)

            if configs:
                return configs

            # اگر کل محتوا Base64 بود
            decoded = decode_possible_base64(data)

            if decoded:
                return extract_configs(decoded)

            return []

    except Exception as exc:
        print(
            f"[SOURCE ERROR] {url}: {type(exc).__name__}: {exc}",
            flush=True,
        )
        return []


async def collect_subscriptions(
    urls: list[str],
) -> list[dict]:
    results = []

    connector = aiohttp.TCPConnector(
        limit=20,
        ssl=False,
    )

    async with aiohttp.ClientSession(
        connector=connector
    ) as session:

        for url in urls:
            print(
                f"[SOURCE] Checking: {url}",
                flush=True,
            )

            configs = await fetch_subscription(
                session,
                url,
            )

            print(
                f"[SOURCE] Extracted: {len(configs)}",
                flush=True,
            )

            for config in configs:
                results.append(
                    {
                        "config": config,
                        "source": url,
                        "message_id": 0,
                    }
                )

    return results
