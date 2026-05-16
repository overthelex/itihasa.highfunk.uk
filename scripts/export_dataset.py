"""Export Sanskrit ingestion DB to Parquet files for HuggingFace dataset."""

import os
import json
import psycopg2
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from collections import defaultdict

DB_URL = os.environ.get("DATABASE_URL", "postgresql://sanskrit:sanskrit@localhost:5434/sanskrit")
OUT = Path("data/export")

OPEN_LICENSE_SOURCES = {
    "itihasa", "dcs", "suttacentral", "sarit", "flores",
    "bdrc", "mitra", "ai4bharat", "polyglotta", "dharmanexus",
    "leipzig", "samayik", "pramana",
}

NC_SOURCES = {"gretil", "cologne", "dsbc"}
UNCLEAR_SOURCES = {"heritage"}


def connect():
    return psycopg2.connect(DB_URL)


def export_parallel_pairs(conn):
    out_dir = OUT / "parallel_pairs"
    out_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    cur.execute("""
        SELECT s.name, s.license, p.source_text, p.target_text,
               p.source_lang, p.target_lang, p.alignment_type,
               p.expansion_ratio, p.pair_type, p.text_ref, p.meta
        FROM parallel_pairs p
        JOIN sources s ON p.source_id = s.id
        ORDER BY s.name
    """)

    by_source = defaultdict(list)
    for row in cur:
        by_source[row[0]].append(row)

    for source, rows in by_source.items():
        table = pa.table({
            "source": [r[0] for r in rows],
            "license": [r[1] for r in rows],
            "source_text": [r[2] for r in rows],
            "target_text": [r[3] for r in rows],
            "source_lang": [r[4] for r in rows],
            "target_lang": [r[5] for r in rows],
            "alignment_type": [r[6] for r in rows],
            "expansion_ratio": [r[7] for r in rows],
            "pair_type": [r[8] for r in rows],
            "text_ref": [r[9] for r in rows],
            "meta": [json.dumps(r[10]) if r[10] else "{}" for r in rows],
        })
        pq.write_table(table, out_dir / f"{source}.parquet", compression="zstd")
        print(f"  parallel/{source}: {len(rows):,} pairs")

    cur.close()


def export_texts(conn):
    out_dir = OUT / "texts"
    out_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    cur.execute("""
        SELECT s.name, s.license, t.external_id, t.title, t.content,
               t.language, t.script, t.tradition, t.genre, t.token_count, t.meta
        FROM texts t
        JOIN sources s ON t.source_id = s.id
        ORDER BY s.name
    """)

    by_source = defaultdict(list)
    for row in cur:
        by_source[row[0]].append(row)

    for source, rows in by_source.items():
        table = pa.table({
            "source": [r[0] for r in rows],
            "license": [r[1] for r in rows],
            "external_id": [r[2] or "" for r in rows],
            "title": [r[3] or "" for r in rows],
            "content": [r[4] for r in rows],
            "language": [r[5] for r in rows],
            "script": [r[6] or "" for r in rows],
            "tradition": [r[7] or "" for r in rows],
            "genre": [r[8] or "" for r in rows],
            "token_count": [r[9] or 0 for r in rows],
            "meta": [json.dumps(r[10]) if r[10] else "{}" for r in rows],
        })
        pq.write_table(table, out_dir / f"{source}.parquet", compression="zstd")
        print(f"  texts/{source}: {len(rows):,} texts")

    cur.close()


def export_dictionary(conn):
    out_dir = OUT / "dictionary"
    out_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor()
    cur.execute("""
        SELECT s.name, s.license, d.headword, d.headword_slp1,
               d.definition, d.pos, d.domain, d.meta
        FROM dictionary_entries d
        JOIN sources s ON d.source_id = s.id
        ORDER BY s.name
    """)

    by_source = defaultdict(list)
    for row in cur:
        by_source[row[0]].append(row)

    for source, rows in by_source.items():
        table = pa.table({
            "source": [r[0] for r in rows],
            "license": [r[1] for r in rows],
            "headword": [r[2] for r in rows],
            "headword_slp1": [r[3] or "" for r in rows],
            "definition": [r[4] for r in rows],
            "pos": [r[5] or "" for r in rows],
            "domain": [r[6] or "" for r in rows],
            "meta": [json.dumps(r[7]) if r[7] else "{}" for r in rows],
        })
        pq.write_table(table, out_dir / f"{source}.parquet", compression="zstd")
        print(f"  dictionary/{source}: {len(rows):,} entries")

    cur.close()


def export_morphological(conn):
    out_dir = OUT / "morphological"
    out_dir.mkdir(parents=True, exist_ok=True)

    cur = conn.cursor("morph_cursor")
    cur.execute("""
        SELECT s.name, m.form, m.lemma, m.unsandhied, m.pos,
               m.features, m.wordnet_id, m.text_ref
        FROM morphological m
        JOIN sources s ON m.source_id = s.id
        ORDER BY s.name
    """)

    batch_size = 500000
    by_source = defaultdict(list)
    total = 0

    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        for row in rows:
            by_source[row[0]].append(row)
        total += len(rows)
        print(f"  morphological: fetched {total:,}...")

    for source, rows in by_source.items():
        table = pa.table({
            "source": [r[0] for r in rows],
            "form": [r[1] for r in rows],
            "lemma": [r[2] for r in rows],
            "unsandhied": [r[3] or "" for r in rows],
            "pos": [r[4] or "" for r in rows],
            "features": [r[5] or "" for r in rows],
            "wordnet_id": [r[6] or "" for r in rows],
            "text_ref": [r[7] or "" for r in rows],
        })
        pq.write_table(table, out_dir / f"{source}.parquet", compression="zstd")
        print(f"  morphological/{source}: {len(rows):,} entries")

    cur.close()


def export_sources_meta(conn):
    cur = conn.cursor()
    cur.execute("SELECT name, url, license, source_type, pipeline_stage, items_count FROM sources ORDER BY id")
    rows = cur.fetchall()
    table = pa.table({
        "name": [r[0] for r in rows],
        "url": [r[1] or "" for r in rows],
        "license": [r[2] or "" for r in rows],
        "source_type": [r[3] or "" for r in rows],
        "pipeline_stage": [r[4] or 0 for r in rows],
        "items_count": [r[5] or 0 for r in rows],
    })
    pq.write_table(table, OUT / "sources.parquet", compression="zstd")
    print(f"  sources: {len(rows)} entries")
    cur.close()


def main():
    conn = connect()
    print("Exporting dataset to", OUT)

    export_sources_meta(conn)
    export_parallel_pairs(conn)
    export_texts(conn)
    export_dictionary(conn)
    export_morphological(conn)

    conn.close()

    total_size = sum(f.stat().st_size for f in OUT.rglob("*.parquet"))
    print(f"\nDone. Total: {total_size / 1024 / 1024:.1f} MB in {sum(1 for _ in OUT.rglob('*.parquet'))} files")


if __name__ == "__main__":
    main()
