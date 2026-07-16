from pathlib import Path

import yaml


def load_machine_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as config_file:
        return yaml.safe_load(config_file)
