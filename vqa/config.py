import yaml


class Cfg(dict):
    """dict with attribute access: cfg.solving.solvers"""

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(key)


def _wrap(obj):
    if isinstance(obj, dict):
        return Cfg({k: _wrap(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [_wrap(v) for v in obj]
    return obj


def load_config(path):
    with open(path, encoding="utf-8") as f:
        return _wrap(yaml.safe_load(f))
