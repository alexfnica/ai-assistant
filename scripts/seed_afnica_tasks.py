"""One-off import of the AFNICA daily-planning backlog into Jarvis's task store.

Run once from the project root (same Python that runs Jarvis):
    python scripts/seed_afnica_tasks.py

Populates three modules: game (Aplicație Simulator), shop (Shopify) and
assistant (A.I Assistant) — Jarvis's own backlog.

Safe to re-run: it skips any (module, title) pair that already exists, open or done.
Uses the same default data dir and database file as `jarvis/__main__.py`
(<project>/data/jarvis.sqlite3), or pass --data-dir to match a custom install.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jarvis.storage import Store  # noqa: E402

GAME_TASKS = [
    "Prototype one realistic sprite: guppy, male + female (~2-3h)",
    "Redesign the remaining fish sprites as real silhouettes (not CSS shapes)",
    "Give each species real color morphs matching AFNICA stock",
    "Make fry/juvenile/adult/mature stages visually distinct",
    "Give every species its own swim behavior, not just cory/anc",
    "Add new species from AFNICA's real catalog (plecos, shrimp)",
    "Extend breeding mechanics beyond Corydoras to all species",
    "Deepen water-quality simulation (filtration, nitrogen cycle, temperature)",
    "Add more disease types and treatments",
    "Design a dedicated Shop scene (replace the abstract Fish Market list)",
    "Add customer NPCs who walk into the shop",
    "Build the buy interaction: customer evaluates and purchases a fish",
    "Give customers personality: patience, budget, species preference",
    # No app-store/Google Play packaging tasks yet — design and mechanics come first.
]

SHOP_TASKS = [
    "Restock or hide: Guppy Metal Head Blue SnakeSkin (0 stock, still active)",
    "Restock or hide: Hypancistrus L-236 SW (0 stock, still active)",
    "Stock or unpublish 5 empty Shopify collections",
    "Merge duplicate 'Aquarium Gear' / 'Shop' collections",
    "Turn Forum / Join Club / Contact Us into real pages",
    "Write a real description for Red Cherry Shrimp",
    "Write a description for Christmas Moss",
    "Add SEO titles/descriptions to top products & collections",
    "Run a first marketing push — store has 0 orders to date",
]

ASSISTANT_TASKS = [
    "Read live Shopify data instead of a manual snapshot",
    "Surface the game backlog % in the morning briefing",
    "Add a Shopify line to the morning briefing",
    'Auto-promote 2 backlog items per project into "due today" each morning',
    "Add tests for the daily planner once it exists",
]


def seed(store):
    added = 0
    for module, titles in (("game", GAME_TASKS), ("shop", SHOP_TASKS), ("assistant", ASSISTANT_TASKS)):
        existing = {t["title"] for t in store.tasks(module, include_done=True)}
        for title in titles:
            if title in existing:
                continue
            store.add_task(module, title)
            added += 1
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parent.parent / "data")
    args = parser.parse_args()
    store = Store(args.data_dir / "jarvis.sqlite3")
    added = seed(store)
    print(f"Added {added} task(s). Say \"task-uri\" in the game, shop or assistant context "
          f"(or /game task-uri, /shop task-uri, /assistant task-uri) to see them.")


if __name__ == "__main__":
    main()
