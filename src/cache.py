# =================================================================================================
#                                           Written by Ramin F.
#                                           Senior AI Engineer
#                            Ferdos.ramin@gmail.com | simplyramin.github.io
# =================================================================================================
import hashlib
import json
import os
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _key(model: str, temperature: float, prompt: str) -> str:
    raw = f"{model}|{float(temperature)}|{prompt}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get(model: str, temperature: float, prompt: str) -> dict | None:
    key = _key(model, temperature, prompt)
    path = CACHE_DIR / f"{key}.json"

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def set(model: str, temperature: float, prompt: str, value: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    key = _key(model, temperature, prompt)
    path = CACHE_DIR / f"{key}.json"
    tmp_path = path.with_suffix(".tmp")

    tmp_path.write_text(json.dumps(value))
    os.replace(tmp_path, path)
