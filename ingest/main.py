"""Sanskrit data ingestion orchestrator.
Runs all harvesters in parallel via ThreadPoolExecutor."""

import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

import browser
import db
from config import MAX_WORKERS
from sources import ALL_HARVESTERS

console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
log = logging.getLogger("ingest")


def run_harvester(cls):
    h = cls()
    return h.name, h.run()


def print_summary():
    conn = db.get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT name, status, items_count, error_msg, "
            "EXTRACT(EPOCH FROM (COALESCE(finished_at, now()) - started_at))::int AS secs "
            "FROM sources ORDER BY id"
        )
        rows = cur.fetchall()

    table = Table(title="Ingestion Summary")
    table.add_column("Source", style="bold")
    table.add_column("Status")
    table.add_column("Items", justify="right")
    table.add_column("Time", justify="right")
    table.add_column("Error")

    for name, status, count, err, secs in rows:
        color = {"done": "green", "error": "red", "running": "yellow"}.get(status, "dim")
        table.add_row(
            name,
            f"[{color}]{status}[/{color}]",
            str(count or 0),
            f"{secs or 0}s",
            (err or "")[:60],
        )

    console.print(table)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM texts")
        n_texts = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM parallel_pairs")
        n_pairs = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM dictionary_entries")
        n_dict = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM morphological")
        n_morph = cur.fetchone()[0]

    console.print(f"\n[bold]DB totals:[/bold] "
                  f"texts={n_texts:,}  pairs={n_pairs:,}  "
                  f"dict={n_dict:,}  morph={n_morph:,}")


def main():
    console.print("[bold cyan]Sanskrit Data Ingestion[/bold cyan]")
    console.print(f"Workers: {MAX_WORKERS}, Sources: {len(ALL_HARVESTERS)}\n")

    t0 = time.time()
    results = {}
    errors = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(run_harvester, cls): cls.name for cls in ALL_HARVESTERS}
        for future in as_completed(futures):
            name = futures[future]
            try:
                src_name, count = future.result()
                results[src_name] = count
                console.print(f"  [green]✓[/green] {src_name}: {count:,} items")
            except Exception as e:
                errors[name] = str(e)
                console.print(f"  [red]✗[/red] {name}: {e}")

    elapsed = time.time() - t0
    console.print(f"\nCompleted in {elapsed:.0f}s")
    print_summary()

    browser.shutdown()

    if errors:
        console.print(f"\n[yellow]{len(errors)} source(s) had errors[/yellow]")
        sys.exit(1)


if __name__ == "__main__":
    main()
