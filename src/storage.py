import hashlib
import json
import time
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
)

from .parser import (
    canonical_config,
    normalize_config,
)


# ============================================================
# Config expiration
# ============================================================

MAX_AGE_SECONDS = 5 * 60 * 60


# ============================================================
# Strong Anti-Duplicate fingerprint
# ============================================================

def strong_canonical_config(
    config: str,
) -> str:
    """
    فقط برای تشخیص Duplicate استفاده می‌شود.

    متن واقعی کانفیگ برای کاربر تغییر نمی‌کند.

    موارد نادیده گرفته‌شده:
    - #remark
    - حروف بزرگ/کوچک scheme
    - حروف بزرگ/کوچک hostname
    - ترتیب Query Parameters

    سایر اطلاعات کانفیگ حفظ می‌شوند.
    """

    if not isinstance(
        config,
        str,
    ):
        return ""

    value = config.strip()

    if not value:
        return ""

    # --------------------------------------------------------
    # ابتدا canonical موجود پروژه امتحان می‌شود.
    # --------------------------------------------------------

    try:

        base = canonical_config(
            value
        )

        if base:
            value = base

    except Exception:
        pass

    # --------------------------------------------------------
    # URI parsing
    # --------------------------------------------------------

    try:

        parts = urlsplit(
            value
        )

    except Exception:

        return " ".join(
            value.split()
        )

    if not parts.scheme:

        return " ".join(
            value.split()
        )

    scheme = parts.scheme.lower()

    # --------------------------------------------------------
    # Host
    # --------------------------------------------------------

    try:
        hostname = parts.hostname
    except Exception:
        hostname = None

    host = (
        hostname.lower()
        if hostname
        else ""
    )

    # --------------------------------------------------------
    # Port
    # --------------------------------------------------------

    port = ""

    try:

        if parts.port is not None:
            port = f":{parts.port}"

    except ValueError:

        port = ""

    # --------------------------------------------------------
    # Username
    # --------------------------------------------------------

    username = (
        parts.username
        if parts.username is not None
        else ""
    )

    # --------------------------------------------------------
    # Password
    # --------------------------------------------------------

    password = (
        parts.password
        if parts.password is not None
        else ""
    )

    authority = ""

    if username:

        authority += username

        if parts.password is not None:
            authority += (
                ":"
                + password
            )

        authority += "@"

    # --------------------------------------------------------
    # IPv6
    # --------------------------------------------------------

    if ":" in host:
        host = f"[{host}]"

    authority += (
        host
        + port
    )

    # --------------------------------------------------------
    # Path
    # --------------------------------------------------------

    path = parts.path or ""

    # --------------------------------------------------------
    # Query
    # --------------------------------------------------------

    query = ""

    if parts.query:

        try:

            query_items = parse_qsl(
                parts.query,
                keep_blank_values=True,
            )

            # ترتیب Query روی fingerprint اثر نگذارد
            query_items.sort(
                key=lambda item: (
                    item[0],
                    item[1],
                )
            )

            query = urlencode(
                query_items,
                doseq=True,
            )

        except Exception:

            query = parts.query

    # --------------------------------------------------------
    # Fragment / Remark intentionally removed
    # --------------------------------------------------------

    result = (
        scheme
        + "://"
        + authority
        + path
    )

    if query:
        result += (
            "?"
            + query
        )

    return result


# ============================================================
# Config ID
# ============================================================

def config_id(
    config: str,
) -> str:

    fingerprint = (
        strong_canonical_config(
            config
        )
    )

    return hashlib.sha256(
        fingerprint.encode(
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

        if not isinstance(
            state,
            dict,
        ):
            raise ValueError(
                "Invalid state format"
            )

        state.setdefault(
            "telegram",
            {},
        )

        state.setdefault(
            "configs",
            {},
        )

        # ----------------------------------------------------
        # Deduplicate old state
        # ----------------------------------------------------

        deduplicate_state(
            state
        )

        return state

    except Exception:

        return {
            "telegram": {},
            "configs": {},
        }


# ============================================================
# Save state
# ============================================================

def save_state(
    path: str,
    state: dict,
):
    with open(
        path,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# Deduplicate existing state
# ============================================================

def deduplicate_state(
    state: dict,
):
    """
    Duplicateهای قدیمی موجود در state.json را ادغام می‌کند.

    این تابع متن کانفیگ را برای کاربر تغییر نمی‌دهد.
    فقط رکوردهای Duplicate را به یک رکورد تبدیل می‌کند.
    """

    database = state.setdefault(
        "configs",
        {},
    )

    new_database = {}

    for _, item in list(
        database.items()
    ):

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

        cid = config_id(
            original
        )

        # ----------------------------------------------------
        # متن اصلی همچنان با normalize_config ذخیره می‌شود
        # ----------------------------------------------------

        try:

            normalized = normalize_config(
                original
            )

        except Exception:

            normalized = original

        # ----------------------------------------------------
        # First occurrence
        # ----------------------------------------------------

        if cid not in new_database:

            new_database[cid] = {
                "config": normalized,
                "created_at": item.get(
                    "created_at",
                    int(time.time()),
                ),
                "source": item.get(
                    "source",
                    "",
                ),
            }

            continue

        # ----------------------------------------------------
        # Duplicate occurrence
        # ----------------------------------------------------

        existing = new_database[cid]

        # قدیمی‌ترین زمان حفظ می‌شود
        try:

            existing_created_at = int(
                existing.get(
                    "created_at",
                    int(time.time()),
                )
            )

            duplicate_created_at = int(
                item.get(
                    "created_at",
                    existing_created_at,
                )
            )

            existing["created_at"] = min(
                existing_created_at,
                duplicate_created_at,
            )

        except (
            TypeError,
            ValueError,
        ):
            pass

        # Source غیرخالی حفظ شود
        source = item.get(
            "source",
            "",
        )

        if source:
            existing["source"] = source


    state["configs"] = new_database


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

        # ----------------------------------------------------
        # Strong Duplicate ID
        # ----------------------------------------------------

        cid = config_id(
            original
        )

        # ----------------------------------------------------
        # Normalize only the stored/display config
        # ----------------------------------------------------

        try:

            normalized = normalize_config(
                original
            )

        except Exception:

            normalized = original

        # ----------------------------------------------------
        # Existing config
        # ----------------------------------------------------

        if cid in database:

            database[cid]["config"] = (
                normalized
            )

            source = item.get(
                "source",
                "",
            )

            if source:
                database[cid]["source"] = (
                    source
                )

            # created_at تغییر نمی‌کند
            continue

        # ----------------------------------------------------
        # New config
        # ----------------------------------------------------

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

    return len(
        expired
    )


# ============================================================
# Get active configs
# ============================================================

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
