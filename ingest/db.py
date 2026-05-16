import threading
import psycopg2
import psycopg2.extras
from config import DATABASE_URL, BATCH_SIZE

_local = threading.local()


def get_conn():
    if not hasattr(_local, "conn") or _local.conn.closed:
        _local.conn = psycopg2.connect(DATABASE_URL)
        _local.conn.autocommit = False
    return _local.conn


def register_source(name, url, license_, source_type, pipeline_stage):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO sources (name, url, license, source_type, pipeline_stage)
               VALUES (%s, %s, %s, %s, %s)
               ON CONFLICT (name) DO UPDATE
               SET url=EXCLUDED.url, license=EXCLUDED.license,
                   source_type=EXCLUDED.source_type, pipeline_stage=EXCLUDED.pipeline_stage
               RETURNING id""",
            (name, url, license_, source_type, pipeline_stage),
        )
        source_id = cur.fetchone()[0]
    conn.commit()
    return source_id


def set_status(source_id, status, items_count=None, error_msg=None):
    conn = get_conn()
    with conn.cursor() as cur:
        if status == "running":
            cur.execute(
                "UPDATE sources SET status=%s, started_at=now() WHERE id=%s",
                (status, source_id),
            )
        elif status == "done":
            cur.execute(
                "UPDATE sources SET status=%s, finished_at=now(), items_count=%s WHERE id=%s",
                (status, items_count or 0, source_id),
            )
        elif status == "error":
            cur.execute(
                "UPDATE sources SET status=%s, finished_at=now(), error_msg=%s WHERE id=%s",
                (status, error_msg, source_id),
            )
    conn.commit()


def insert_texts(rows):
    if not rows:
        return 0
    conn = get_conn()
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO texts
                   (source_id, external_id, title, content, language, script, tradition, genre, token_count, meta)
                   VALUES %s""",
                batch,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
            )
            total += len(batch)
        conn.commit()
    return total


def insert_parallel_pairs(rows):
    if not rows:
        return 0
    conn = get_conn()
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO parallel_pairs
                   (source_id, source_text, target_text, source_lang, target_lang,
                    alignment_type, expansion_ratio, pair_type, text_ref, meta)
                   VALUES %s""",
                batch,
                template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
            )
            total += len(batch)
        conn.commit()
    return total


def insert_dictionary_entries(rows):
    if not rows:
        return 0
    conn = get_conn()
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO dictionary_entries
                   (source_id, headword, headword_slp1, definition, pos, domain, meta)
                   VALUES %s""",
                batch,
                template="(%s, %s, %s, %s, %s, %s, %s::jsonb)",
            )
            total += len(batch)
        conn.commit()
    return total


def insert_morphological(rows):
    if not rows:
        return 0
    conn = get_conn()
    total = 0
    with conn.cursor() as cur:
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            psycopg2.extras.execute_values(
                cur,
                """INSERT INTO morphological
                   (source_id, form, lemma, unsandhied, pos, features, wordnet_id, text_ref)
                   VALUES %s""",
                batch,
                template="(%s, %s, %s, %s, %s, %s, %s, %s)",
            )
            total += len(batch)
        conn.commit()
    return total
