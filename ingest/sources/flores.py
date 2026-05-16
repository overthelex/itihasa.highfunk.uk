"""FLORES-200 — Sanskrit (san_Deva) eval benchmark.
Downloads from HuggingFace datasets API."""

import json
import logging

import db
from harvester import Harvester

log = logging.getLogger(__name__)

HF_API = "https://datasets-server.huggingface.co/rows"
DATASET = "openlanguagedata/flores_plus"


class FloresHarvester(Harvester):
    name = "flores"
    url = "https://huggingface.co/datasets/openlanguagedata/flores_plus"
    license = "CC BY-SA 4.0"
    source_type = "benchmark"
    pipeline_stage = 0

    def harvest(self) -> int:
        total = 0
        for split in ("dev", "devtest"):
            try:
                total += self._ingest_split(split)
            except Exception as e:
                log.warning("[flores] %s failed: %s", split, e)
        if total == 0:
            total = self._fallback_tinyurl()
        return total

    def _ingest_split(self, split) -> int:
        url = f"{HF_API}?dataset={DATASET}&config=san_Deva&split={split}&offset=0&length=2000"
        log.info("[flores] fetching %s from HF API", split)
        resp = self.client.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        rows_data = data.get("rows", [])
        if not rows_data:
            log.warning("[flores] no rows in %s response", split)
            return 0

        rows = []
        for item in rows_data:
            row = item.get("row", item)
            sa = row.get("sentence") or row.get("san_Deva") or row.get("text", "")
            en = row.get("eng_Latn", "")
            if not sa:
                continue
            if not en:
                for k, v in row.items():
                    if "eng" in k.lower() and isinstance(v, str) and len(v) > 5:
                        en = v
                        break
            if sa and en:
                rows.append((
                    self.source_id, sa, en, "sa", "en",
                    "sentence", self.expansion_ratio(sa, en),
                    "translation", f"flores:{split}:{len(rows)+1}",
                    self.to_json({"split": split}),
                ))
        count = db.insert_parallel_pairs(rows)
        log.info("[flores] %s: %d pairs", split, count)
        return count

    def _fallback_tinyurl(self) -> int:
        """Fallback: download the FLORES-200 tarball."""
        import subprocess
        import tarfile
        from pathlib import Path

        archive = self.work_dir / "flores200.tar.gz"
        if not archive.exists():
            log.info("[flores] downloading FLORES-200 tarball")
            try:
                subprocess.run(
                    ["curl", "-L", "-o", str(archive), "--max-time", "120",
                     "https://tinyurl.com/flores200dataset"],
                    check=True, capture_output=True, timeout=180,
                )
            except Exception as e:
                log.warning("[flores] tarball download failed: %s", e)
                return 0

        if not archive.exists() or archive.stat().st_size < 1000:
            return 0

        extract_dir = self.work_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        with tarfile.open(archive) as tf:
            tf.extractall(extract_dir)

        total = 0
        for split in ("dev", "devtest"):
            sa_file = self._find(extract_dir, f"san_Deva.{split}")
            en_file = self._find(extract_dir, f"eng_Latn.{split}")
            if sa_file and en_file:
                sa_lines = sa_file.read_text("utf-8").strip().splitlines()
                en_lines = en_file.read_text("utf-8").strip().splitlines()
                n = min(len(sa_lines), len(en_lines))
                rows = []
                for i in range(n):
                    sa, en = sa_lines[i].strip(), en_lines[i].strip()
                    if sa and en:
                        rows.append((
                            self.source_id, sa, en, "sa", "en",
                            "sentence", self.expansion_ratio(sa, en),
                            "translation", f"flores:{split}:{i+1}",
                            self.to_json({"split": split}),
                        ))
                total += db.insert_parallel_pairs(rows)
                log.info("[flores] fallback %s: %d pairs", split, len(rows))
        return total

    def _find(self, root: "Path", name: str):
        for f in root.rglob(name):
            return f
        return None
