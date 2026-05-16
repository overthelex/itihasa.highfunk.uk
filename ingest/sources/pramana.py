"""Pramana-NLP — Sanskrit epistemology/logic texts for NLP (includes Buddhist)."""

import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/tylergneill/pramana-nlp.git"


class PramanaHarvester(Harvester):
    name = "pramana"
    url = "https://github.com/tylergneill/pramana-nlp"
    license = "Research use"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        rows = []
        for f in sorted(repo.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".txt", ".xml"):
                continue
            if "readme" in f.name.lower():
                continue
            if f.stat().st_size < 200:
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace").strip()
            except Exception:
                continue
            if len(content) < 100:
                continue
            title = f.stem
            fname = f.name.lower()
            is_buddhist = any(k in fname for k in (
                "dignaga", "dharmakirti", "ratnakirti", "pramana",
                "nyayabindu", "hetubindu", "santanantara", "vadanyaya",
            ))
            rows.append((
                self.source_id, f.name, title, content, "sa", "iast",
                "buddhist" if is_buddhist else None, "shastra",
                self.token_count(content),
                self.to_json({"path": str(f.relative_to(repo))}),
            ))
        log.info("[pramana] %d texts (%d buddhist)",
                 len(rows), sum(1 for r in rows if r[6] == "buddhist"))
        return db.insert_texts(rows)
