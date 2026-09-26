"""Local settings. The API key is read from the environment or a key file, never from chat."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "cloud_enabled": True,
    "cloud_model": "claude-sonnet-5",
    "monthly_token_budget": 3_000_000,
    "max_output_tokens": 700,
    "docs_dir": "",
    "aquarium_path": "",
    "docs_exclude_sheets": ["DATE COMANDĂ"],
}


def load_config(data_dir):
    config = dict(DEFAULTS)
    path = Path(data_dir) / "jarvis_config.json"
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            config.update({k: v for k, v in loaded.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    override = os.environ.get("JARVIS_CLOUD_MODEL")
    if override:
        config["cloud_model"] = override
    return config


def load_api_key(data_dir):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        try:
            key = (Path(data_dir) / "anthropic_key.txt").read_text(encoding="utf-8").strip()
        except OSError:
            key = ""
    return key
