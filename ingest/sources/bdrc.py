"""BDRC — Buddhist Digital Resource Center: sanskrit-stemming-data (128 MB morphological)."""

import logging
import re
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/buda-base/sanskrit-stemming-data.git"


class BDRCHarvester(Harvester):
    name = "bdrc"
    url = "https://github.com/buda-base/sanskrit-stemming-data"
    license = "Apache 2.0"
    source_type = "morphological"
    pipeline_stage = 1

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        rows = []
        total = 0

        for f in repo.rglob("*"):
            if not f.is_file() or f.suffix not in (".tsv", ".csv", ".txt"):
                continue
            if f.stat().st_size < 100:
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            sep = "\t" if f.suffix == ".tsv" or "\t" in text[:500] else ","
            for line in text.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(sep)
                if len(parts) < 2:
                    continue
                form = parts[0].strip()
                lemma = parts[1].strip() if len(parts) > 1 else form
                pos = parts[2].strip() if len(parts) > 2 else None
                if not form or not lemma:
                    continue
                rows.append((
                    self.source_id, form, lemma, None, pos, None, None, f.stem,
                ))
                if len(rows) >= 50000:
                    total += db.insert_morphological(rows)
                    log.info("[bdrc] flushed %d morph rows", total)
                    rows = []

        total += db.insert_morphological(rows)
        log.info("[bdrc] total: %d morph rows", total)
        return total
