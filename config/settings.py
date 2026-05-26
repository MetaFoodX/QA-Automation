"""Config loader for QA-Automation.

Reads the ENV var (default: 'staging'), loads matching YAML files under
config/, merges them, applies env-var overrides, resolves ${VAR}
placeholders, and exposes a single `settings` object the rest of the
project imports.

Usage:
    from config.settings import settings

    settings.name                  # 'staging' or 'prod'
    settings.base_url              # final URL (after BASE_URL override)
    settings.allow_destructive
    settings.browser.engine        # 'chromium' | 'firefox' | 'webkit'
    settings.browser.headless
    settings.browser.viewport.width
    settings.timeouts.navigation
    settings.timeouts.short

Runtime env-var overrides:
    ENV=staging|prod               which environment YAML to load
    BASE_URL=https://...           overrides base_url from the YAML
    HEADED=1                       forces visible browser (overrides headless)
    SLOW_MO=200                    ms delay between Playwright actions
    BROWSER=chromium|firefox|webkit  overrides browser.engine
"""

import os
import re
from pathlib import Path
from types import SimpleNamespace

import yaml


CONFIG_DIR = Path(__file__).parent
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
VALID_ENVIRONMENTS = {"staging", "prod"}


# ---------- Helpers ----------

def _load_yaml(path: Path) -> dict:
    """Read a YAML file. Empty files return {}. Missing files raise."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


def _resolve_env_vars(value):
    """Recursively replace ${VAR} placeholders with os.environ[VAR].

    Missing env vars become '${VAR:UNSET}' so the failure is obvious
    when the value is finally used (instead of silently being empty).
    """
    if isinstance(value, str):
        def replace(match):
            var_name = match.group(1)
            env_value = os.environ.get(var_name)
            return env_value if env_value is not None else f"${{{var_name}:UNSET}}"
        return ENV_VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def _to_namespace(data):
    """Convert nested dicts to SimpleNamespace for dot access."""
    if isinstance(data, dict):
        return SimpleNamespace(**{k: _to_namespace(v) for k, v in data.items()})
    if isinstance(data, list):
        return [_to_namespace(item) for item in data]
    return data


def _apply_runtime_overrides(env_data: dict, browsers_data: dict) -> None:
    """Apply env-var overrides on top of YAML defaults. Mutates dicts in place."""
    # Base URL override (the big one — used to point at any prod URL)
    if base_url := os.getenv("BASE_URL"):
        env_data["base_url"] = base_url

    # Visible browser for local debugging
    if os.getenv("HEADED", "").lower() in {"1", "true", "yes"}:
        browsers_data["headless"] = False

    # Slow-motion delay between actions
    if slow_mo := os.getenv("SLOW_MO"):
        try:
            browsers_data["slow_mo"] = int(slow_mo)
        except ValueError:
            raise ValueError(f"SLOW_MO must be an integer, got: {slow_mo!r}")

    # Browser engine override
    if browser_engine := os.getenv("BROWSER"):
        browsers_data["engine"] = browser_engine.lower()


# ---------- The main build function ----------

def _build_settings():
    # 1. Pick the environment
    env_name = os.getenv("ENV", "staging").lower()
    if env_name not in VALID_ENVIRONMENTS:
        raise ValueError(
            f"ENV={env_name!r} is invalid. Must be one of: {sorted(VALID_ENVIRONMENTS)}"
        )

    # 2. Load YAML files
    env_data = _load_yaml(CONFIG_DIR / "environments" / f"{env_name}.yaml")
    browsers_data = _load_yaml(CONFIG_DIR / "browsers.yaml")
    timeouts_data = _load_yaml(CONFIG_DIR / "timeouts.yaml")

    # 3. Sanity check: env YAML's name field must match the ENV var
    #    (catches the "I copied staging.yaml to prod.yaml and forgot to edit" mistake)
    if env_data.get("name") != env_name:
        raise ValueError(
            f"environments/{env_name}.yaml has name={env_data.get('name')!r}, "
            f"but ENV={env_name!r}. Fix the YAML file."
        )

    # 4. Apply runtime overrides
    _apply_runtime_overrides(env_data, browsers_data)

    # 5. Merge into one config tree
    merged = {
        **env_data,                    # name, base_url, allow_destructive
        "browser": browsers_data,      # engine, headless, viewport, ...
        "timeouts": timeouts_data,     # navigation, default, short, ...
    }

    # 6. Resolve ${VAR} placeholders (used by users.yaml later)
    merged = _resolve_env_vars(merged)

    # 7. Convert to dot-access object
    return _to_namespace(merged)


# Built once at import time. All consumers import this `settings` object.
settings = _build_settings()