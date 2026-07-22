"""Pipeline CLI.

Kullanım:
    python -m vqa fetch|passages|generate|filter|solve|band|publish|all
        [--config config.yaml] [--limit N]

Her aşama data/ altına kendi JSONL'ini yazar; istediğin aşamadan devam edebilirsin.
"""
import argparse

from .band import run_band
from .config import load_config
from .fetch import run_fetch
from .filters import run_filters
from .generate import run_generate
from .passages import run_passages
from .publish import run_publish
from .solve import run_solve

STAGES = {
    "fetch": run_fetch,
    "passages": run_passages,
    "generate": run_generate,
    "filter": run_filters,
    "solve": run_solve,
    "band": run_band,
    "publish": run_publish,
}
PIPELINE = ["fetch", "passages", "generate", "filter", "solve", "band"]


def main():
    ap = argparse.ArgumentParser(prog="vqa", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=[*STAGES, "all"])
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--limit", type=int, default=None,
                    help="aşama girdisini ilk N kayıtla sınırla (smoke test)")
    args = ap.parse_args()

    cfg = load_config(args.config)
    stages = PIPELINE if args.stage == "all" else [args.stage]
    for name in stages:
        print(f"== {name} ==")
        STAGES[name](cfg, limit=args.limit)


if __name__ == "__main__":
    main()
