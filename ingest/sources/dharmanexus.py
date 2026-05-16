"""DharmaNexus Sanskrit — aggregated cleaned Sanskrit corpus from multiple sources."""

import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/dharmamitra/sanskrit-english-identification.git"


class DharmaNexusHarvester(Harvester):
    name = "dharmanexus"
    url = "https://github.com/dharmamitra/dharmanexus-sanskrit"
    license = "Varies (aggregation is open)"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        rows = []
        for f in sorted(repo.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix not in (".txt", ".xml", ".html", ".json"):
                continue
            if "readme" in f.name.lower() or "license" in f.name.lower():
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
            tradition = "buddhist"
            rows.append((
                self.source_id, f.name, title, content, "sa", "iast",
                tradition, None, self.token_count(content),
                self.to_json({"path": str(f.relative_to(repo))}),
            ))
        log.info("[dharmanexus] %d texts", len(rows))
        return db.insert_texts(rows)
