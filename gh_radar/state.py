"""De-dup memory: which repos we've already sent, with timestamps. Tolerates a
corrupt/hand-edited file and writes atomically so a crash can't leave it broken."""
import json
import time

from . import config


def load_seen():
    try:
        data = json.loads(config.SEEN_PATH.read_text())
        if not isinstance(data, dict):
            return {}
        return {k: v for k, v in data.items() if isinstance(v, (int, float))}
    except Exception:  # noqa: BLE001
        return {}


def save_seen(seen):
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - config.SEEN_TTL_DAYS * 86400
    seen = {k: v for k, v in seen.items() if isinstance(v, (int, float)) and v > cutoff}
    tmp = config.SEEN_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(seen))
    tmp.replace(config.SEEN_PATH)        # atomic — never leaves a half-written file
