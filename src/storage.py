import hashlib
import json
import os
import time

from .parser import canonical_config, normalize_config


# ============================================================
# Config expiration
# ============================================================

MAX_AGE_SECONDS = 5 * 60 * 60


# ============================================================
# Config ID
# ============================================================

def config_id(
    config: str,
) -> str:
    return hashlib.sha256(
        canonical_config(config).encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================
# Load state
# ============================================================

def load_state(
    path: str,
) -> dict:

    try:

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as f:

            state = json.load(f)

        if not isinstance(state, dict):
            raise ValueError(
                "State must be a JSON object."
            )

        state.setdefault(
            "telegram",
            {},
        )

        state.setdefault(
            "configs",
            {},
        )

        return state

    except Exception:

        return {
            "telegram": {},
            "configs": {},
        }


# ============================================================
# Save state safely
# ============================================================

def save_state(
    path: str,
    state: dict,
):
    """
    state.json را به صورت اتمیک ذخیره می‌کند.
    """

    directory = os.path.dirname(
        os.path.abspath(path)
    )

    os.makedirs(
        directory,
        exist_ok=True,
    )

    temp_path = (
        path + ".tmp"
    )

    try:

        with open(
            temp_path,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=2,
            )

            f.flush()
            os.fsync(
                f.fileno()
            )

        os.replace(
            temp_path,
            path,
        )

    except Exception:

        try:
            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )
        except Exception:
            pass

        raise


# ============================================================
# Add configs
# ============================================================

def add_configs(
    state: dict,
    configs: list[dict],
):
    database = state.setdefault(
        "configs",
        {},
    )

    now = int(
        time.time()
    )

    for item in configs:

        if not isinstance(
            item,
            dict,
        ):
            continue

        original = item.get(
            "config",
            "",
        )

        if not isinstance(
            original,
            str,
        ):
            continue

        original = original.strip()

        if not original:
            continue

        # ------------------------------------------------------
        # Canonical ID
        # ------------------------------------------------------

        cid = config_id(
            original
        )

        normalized = normalize_config(
            original
        )

        # ------------------------------------------------------
        # Existing config
        # ------------------------------------------------------

        if cid in database:

            entry = database[cid]

            # --------------------------------------------------
            # مهم:
            # مقدار config را هر بار از جدیدترین collector
            # جایگزین می‌کنیم تا output با state همگام بماند.
            # --------------------------------------------------

            entry["config"] = normalized

            # --------------------------------------------------
            # Source را فقط زمانی تغییر بده که مقدار جدید داریم
            # --------------------------------------------------

            source = item.get(
                "source"
            )

            if source:
                entry["source"] = source

            # --------------------------------------------------
            # created_at دست نمی‌خورد
            # چون عمر کانفیگ باید از زمان اولین ورود محاسبه شود.
            # --------------------------------------------------

            continue

        # ------------------------------------------------------
        # New config
        # ------------------------------------------------------

        database[cid] = {
            "config": normalized,
            "created_at": now,
            "source": item.get(
                "source",
                "",
            ),
        }


# ============================================================
# Remove expired configs
# ============================================================

def remove_expired(
    state: dict,
) -> int:

    database = state.setdefault(
        "configs",
        {},
    )

    now = int(
        time.time()
    )

    expired = []

    for cid, item in list(
        database.items()
    ):

        try:

            created_at = int(
                item.get(
                    "created_at",
                    now,
                )
            )

        except (
            TypeError,
            ValueError,
        ):

            created_at = now

        if (
            now - created_at
            >= MAX_AGE_SECONDS
        ):
            expired.append(
                cid
            )

    for cid in expired:
        del database[cid]

    return len(
        expired
    )


# ============================================================
# Get active configs
# ============================================================

def get_active_configs(
    state: dict,
) -> list[str]:

    database = state.get(
        "configs",
        {},
    )

    active = []

    for item in database.values():

        if not isinstance(
            item,
            dict,
        ):
            continue

        config = item.get(
            "config"
        )

        if (
            isinstance(config, str)
            and config.strip()
        ):
            active.append(
                config
            )

    return active
