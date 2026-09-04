import os
import re

CONFIG_DIR = os.path.join(os.path.dirname(__file__), "config")


def _parse_yaml(path):
    """Minimal flat-YAML reader. Good enough for our config files."""
    out = {}
    with open(path) as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith(" "):
                continue
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", line)
            if m and m.group(2):
                out[m.group(1)] = m.group(2).strip()
    return out


def _load_env_file(path):
    out = {}
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    return out


def load_settings(env=None):
    env = env or os.environ.get("APP_ENV", "production")

    settings = {}

    # 1. baked-in defaults have the LOWEST priority: they only fill in
    #    values that nothing else provides, so a bare container still boots.
    for key, value in _load_env_file(os.path.join(CONFIG_DIR, "defaults.env")).items():
        settings.setdefault(key.lower(), value)

    # 2. environment-specific yaml overrides the defaults
    settings.update(_parse_yaml(os.path.join(CONFIG_DIR, f"{env}.yaml")))

    # 3. real environment variables win
    for key in ("DATABASE_URL", "REDIS_URL", "LOG_LEVEL"):
        if key in os.environ:
            settings[key.lower()] = os.environ[key]

    return settings
