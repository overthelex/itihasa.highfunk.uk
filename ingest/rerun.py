"""Re-run specific harvesters by name."""

import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.logging import RichHandler

import db
from config import MAX_WORKERS
from sources import ALL_HARVESTERS

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)

names = set(sys.argv[1:])
to_run = [cls for cls in ALL_HARVESTERS if cls.name in names]
if not to_run:
    console.print("[red]Usage: python rerun.py itihasa flores ...[/red]")
    sys.exit(1)

console.print(f"Re-running: {[c.name for c in to_run]}")

def run(cls):
    h = cls()
    return h.name, h.run()

with ThreadPoolExecutor(max_workers=len(to_run)) as pool:
    futures = {pool.submit(run, cls): cls.name for cls in to_run}
    for f in as_completed(futures):
        try:
            name, count = f.result()
            console.print(f"  [green]✓[/green] {name}: {count:,}")
        except Exception as e:
            console.print(f"  [red]✗[/red] {futures[f]}: {e}")

conn = db.get_conn()
with conn.cursor() as cur:
    for tbl in ("texts", "parallel_pairs", "dictionary_entries", "morphological"):
        cur.execute(f"SELECT count(*) FROM {tbl}")
        console.print(f"  {tbl}: {cur.fetchone()[0]:,}")
