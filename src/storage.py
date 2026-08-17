import hashlib
import json
import time

from .parser import canonical_config, normalize_config


MAX_AGE_SECONDS = 2 * 60 * 60


def config_id(config: str) -> str:
    return hashlib.sha256(
        canonical_config(config).encode("utf-8")
    ).hexdigest()


def load_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return {
            "telegram": {},
            "configs": {},
        }


def save_state(path: str, state: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


def add_configs(
    state: dict,
    configs: list[dict],
):
    database = state.setdefault(
        "configs",
        {},
    )

    now = int(time.time())

    for item in configs:

        original = item.get("config", "")

        if not original:
            continue

        # ID بر اساس بخش اصلی کانفیگ
        cid = config_id(original)

        # ------------------------------------------------------
        # کانفیگ قبلاً وجود دارد
        # ------------------------------------------------------

        if cid in database:

            # Remark را همگام نگه می‌داریم
            database[cid]["config"] = normalize_config(
                original
            )

            # اگر اطلاعات منبع جدید وجود دارد
            if item.get("source"):
                database[cid]["source"] = item["source"]

            continue

        # ------------------------------------------------------
        # کانفیگ جدید
        # ------------------------------------------------------

        database[cid] = {
            "config": normalize_config(original),
            "created_at": now,
            "source": item.get("source", ""),
        }


def remove_expired(
    state: dict,
) -> int:

    database = state.setdefault(
        "configs",
        {},
    )

    now = int(time.time())

    expired = [
        cid
        for cid, item in database.items()
        if now - int(
            item.get(
                "created_at",
                now,
            )
        ) >= MAX_AGE_SECONDS
    ]

    for cid in expired:
        del database[cid]

    return len(expired)


def get_active_configs(
    state: dict,
) -> list[str]:

    return [
        item["config"]
        for item in state.get(
            "configs",
            {},
        ).values()
        if item.get("config")
    ]
