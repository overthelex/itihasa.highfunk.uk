"""Dharmamitra MITRA-Parallel — 1.74M Buddhist parallel sentences.
Sanskrit/Pali/Chinese/Tibetan ↔ English. THE most valuable new source."""

import json
import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/dharmamitra/mitra-parallel.git"


class MitraHarvester(Harvester):
    name = "mitra"
    url = "https://github.com/dharmamitra/mitra-parallel"
    license = "CC-compatible (open)"
    source_type = "parallel"
    pipeline_stage = 2

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        total = 0

        for f in sorted(repo.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix in (".json", ".jsonl"):
                total += self._ingest_json(f)
            elif f.suffix in (".tsv", ".csv"):
                total += self._ingest_tsv(f)
            elif f.suffix == ".txt" and self._is_parallel_txt(f):
                total += self._ingest_parallel_txt(f)
        return total

    def _ingest_json(self, f: Path) -> int:
        rows = []
        text = f.read_text(encoding="utf-8", errors="replace")
        if f.suffix == ".jsonl":
            items = []
            for line in text.splitlines():
                line = line.strip()
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        else:
            try:
                data = json.loads(text)
                items = data if isinstance(data, list) else [data]
            except json.JSONDecodeError:
                return 0

        for item in items:
            sa, en = self._extract_pair(item)
            if sa and en and len(sa) > 3 and len(en) > 3:
                rows.append((
                    self.source_id, sa, en, "sa", "en",
                    "sentence", self.expansion_ratio(sa, en),
                    "translation", f.stem,
                    self.to_json({"file": f.name}),
                ))
            if len(rows) >= 5000:
                db.insert_parallel_pairs(rows)
                rows = []

        count = db.insert_parallel_pairs(rows)
        if count:
            log.info("[mitra] %s: %d pairs", f.name, count)
        return count

    def _ingest_tsv(self, f: Path) -> int:
        rows = []
        text = f.read_text(encoding="utf-8", errors="replace")
        sep = "\t" if "\t" in text[:1000] else ","
        for line in text.splitlines():
            parts = line.split(sep)
            if len(parts) < 2:
                continue
            sa, en = self._find_sa_en_cols(parts)
            if sa and en:
                rows.append((
                    self.source_id, sa, en, "sa", "en",
                    "sentence", self.expansion_ratio(sa, en),
                    "translation", f.stem,
                    self.to_json({"file": f.name}),
                ))
            if len(rows) >= 5000:
                db.insert_parallel_pairs(rows)
                rows = []
        return db.insert_parallel_pairs(rows)

    def _ingest_parallel_txt(self, f: Path) -> int:
        rows = []
        lines = f.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        pair_file = None
        stem = f.stem
        parent = f.parent
        for suffix in (".en", ".eng", "_en", "_eng"):
            candidate = parent / f"{stem.rsplit('.', 1)[0]}{suffix}.txt"
            if candidate.exists():
                pair_file = candidate
                break
        if not pair_file:
            return 0
        en_lines = pair_file.read_text("utf-8", errors="replace").strip().splitlines()
        n = min(len(lines), len(en_lines))
        for i in range(n):
            sa, en = lines[i].strip(), en_lines[i].strip()
            if sa and en:
                rows.append((
                    self.source_id, sa, en, "sa", "en",
                    "sentence", self.expansion_ratio(sa, en),
                    "translation", f.stem,
                    self.to_json({"file": f.name}),
                ))
        return db.insert_parallel_pairs(rows)

    def _extract_pair(self, item):
        if not isinstance(item, dict):
            return None, None
        sa = (item.get("sanskrit") or item.get("sa") or item.get("source")
              or item.get("src") or item.get("input") or "")
        en = (item.get("english") or item.get("en") or item.get("target")
              or item.get("tgt") or item.get("output") or item.get("translation") or "")
        if not sa:
            for k, v in item.items():
                if isinstance(v, str) and self._has_sa_chars(v):
                    sa = v
                    break
        if not en:
            for k, v in item.items():
                if isinstance(v, str) and k != sa and v.isascii():
                    en = v
                    break
        return sa.strip(), en.strip()

    def _find_sa_en_cols(self, parts):
        sa, en = None, None
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if self._has_sa_chars(p) and not sa:
                sa = p
            elif p.isascii() and len(p) > 3 and not en:
                en = p
        return sa, en

    @staticmethod
    def _has_sa_chars(text):
        return any("ऀ" <= c <= "ॿ" or c in "āīūṛṝḷṃḥśṣṭḍṇñ" for c in text[:100])

    @staticmethod
    def _is_parallel_txt(f: Path):
        stem = f.stem.lower()
        return any(k in stem for k in ("sa", "skt", "san", "sanskrit"))
