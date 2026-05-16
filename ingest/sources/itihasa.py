"""Itihasa — 93K Sanskrit-English verse-aligned pairs from Hindu epics."""

import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/rahular/itihasa.git"
SPLITS = ["train", "dev", "test"]


class ItihasaHarvester(Harvester):
    name = "itihasa"
    url = "https://github.com/rahular/itihasa"
    license = "Apache-2.0"
    source_type = "parallel"
    pipeline_stage = 1

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        data_dir = repo / "data"
        if not data_dir.exists():
            data_dir = repo

        rows = []
        for split in SPLITS:
            sn_file = data_dir / f"{split}.sn"
            en_file = data_dir / f"{split}.en"
            if not sn_file.exists() or not en_file.exists():
                log.warning("[itihasa] missing %s split", split)
                continue
            sn_lines = sn_file.read_text(encoding="utf-8").strip().splitlines()
            en_lines = en_file.read_text(encoding="utf-8").strip().splitlines()
            n = min(len(sn_lines), len(en_lines))
            log.info("[itihasa] %s: %d pairs", split, n)
            for i in range(n):
                sn = sn_lines[i].strip()
                en = en_lines[i].strip()
                if not sn or not en:
                    continue
                rows.append((
                    self.source_id, sn, en, "sa", "en",
                    "verse", self.expansion_ratio(sn, en),
                    "translation", f"itihasa:{split}:{i+1}",
                    self.to_json({"split": split}),
                ))
        return db.insert_parallel_pairs(rows)
