"""Samayik — ~53K English-Sanskrit parallel sentence pairs."""

import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/ayushbits/Saamayik.git"


class SamayikHarvester(Harvester):
    name = "samayik"
    url = "https://github.com/ayushbits/Saamayik"
    license = "Research use"
    source_type = "parallel"
    pipeline_stage = 1

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        rows = []

        for f in repo.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix not in (".tsv", ".csv", ".txt"):
                continue
            if f.stat().st_size < 100:
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            sep = "\t" if "\t" in text[:500] else ","
            lines = text.strip().splitlines()

            header = lines[0].lower() if lines else ""
            start = 1 if ("english" in header or "sanskrit" in header or "src" in header) else 0
            en_col, sa_col = 0, 1
            if "sanskrit" in header.split(sep)[0].lower() if sep in header else False:
                sa_col, en_col = 0, 1

            for line in lines[start:]:
                parts = line.split(sep)
                if len(parts) < 2:
                    continue
                en = parts[en_col].strip().strip('"')
                sa = parts[sa_col].strip().strip('"')
                if not sa or not en or len(sa) < 3 or len(en) < 3:
                    continue
                rows.append((
                    self.source_id, sa, en, "sa", "en",
                    "sentence", self.expansion_ratio(sa, en),
                    "translation", f"samayik:{f.stem}",
                    self.to_json({"split": f.stem}),
                ))

        log.info("[samayik] parsed %d pairs", len(rows))
        return db.insert_parallel_pairs(rows)
