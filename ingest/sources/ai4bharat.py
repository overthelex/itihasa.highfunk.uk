"""AI4Bharat BPCC — Bharat Parallel Corpus Collection.
Sanskrit-English subset. Gated HF dataset, requires token."""

import csv
import io
import logging
import os
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

HF_TOKEN = os.environ.get("HUGGING_FACE_HUB_TOKEN", "")
DATASET = "ai4bharat/BPCC"
HF_RESOLVE = f"https://huggingface.co/datasets/{DATASET}/resolve/main"

KNOWN_FILES = [
    ("wiki/san_Deva.tsv", "wiki"),
    ("nllb_filtered/san_Deva.tsv", "nllb"),
    ("samanantar_v0.3_filtered/eng_Latn-san_Deva/train.san_Deva", "samanantar"),
]

PAIRED_DIRS = [
    "wiki/eng_Latn-san_Deva",
    "nllb_filtered/eng_Latn-san_Deva",
]


class AI4BharatHarvester(Harvester):
    name = "ai4bharat"
    url = "https://huggingface.co/datasets/ai4bharat/BPCC"
    license = "CC0 (mined) / CC BY 4.0 (human)"
    source_type = "parallel"
    pipeline_stage = 1

    def harvest(self) -> int:
        if not HF_TOKEN:
            log.warning("[ai4bharat] no HF token set, skipping")
            return 0

        self.client.headers["Authorization"] = f"Bearer {HF_TOKEN}"
        total = 0

        for rpath, subset in KNOWN_FILES:
            try:
                count = self._download_and_ingest_tsv(rpath, subset)
                total += count
            except Exception as e:
                log.warning("[ai4bharat] %s: %s", rpath, e)

        for dir_path in PAIRED_DIRS:
            try:
                count = self._ingest_paired_dir(dir_path)
                total += count
            except Exception as e:
                log.warning("[ai4bharat] dir %s: %s", dir_path, e)

        return total

    def _download_and_ingest_tsv(self, rpath, subset) -> int:
        url = f"{HF_RESOLVE}/{rpath}"
        safe_name = rpath.replace("/", "__")
        local = self.download(url, safe_name)
        text = local.read_text(encoding="utf-8", errors="replace")
        sep = "\t" if "\t" in text[:2000] else ","

        reader = csv.reader(io.StringIO(text), delimiter=sep)
        header = next(reader, None)

        sa_col, en_col = None, None
        if header:
            for i, h in enumerate(header):
                hl = h.lower().strip()
                if hl in ("san_deva", "san", "sa", "src", "source", "sanskrit"):
                    sa_col = i
                elif hl in ("eng_latn", "eng", "en", "tgt", "target", "english"):
                    en_col = i

        if sa_col is None or en_col is None:
            reader = csv.reader(io.StringIO(text), delimiter=sep)
            if header:
                next(reader)
            sa_col, en_col = 0, 1

        rows = []
        for line in reader:
            if len(line) <= max(sa_col, en_col):
                continue
            sa = line[sa_col].strip()
            en = line[en_col].strip()
            if not sa or not en or len(sa) < 3 or len(en) < 3:
                continue
            rows.append((
                self.source_id, sa, en, "sa", "en",
                "sentence", self.expansion_ratio(sa, en),
                "translation", f"bpcc:{subset}",
                self.to_json({"subset": subset, "file": rpath}),
            ))
            if len(rows) >= 5000:
                db.insert_parallel_pairs(rows)
                rows = []

        count = db.insert_parallel_pairs(rows)
        log.info("[ai4bharat] %s: %d pairs", rpath, count)
        return count

    def _ingest_paired_dir(self, dir_path) -> int:
        api_url = f"https://huggingface.co/api/datasets/{DATASET}/tree/main/{dir_path}"
        try:
            resp = self.client.get(api_url, timeout=30)
            resp.raise_for_status()
            items = resp.json()
        except Exception:
            return 0

        sa_files = {}
        en_files = {}
        for item in items:
            path = item.get("path", "")
            name = path.rsplit("/", 1)[-1].lower()
            if "san" in name or "sa" in name:
                sa_files[name.split(".")[0]] = path
            elif "eng" in name or "en" in name:
                en_files[name.split(".")[0]] = path

        total = 0
        for key in sa_files:
            if key in en_files:
                try:
                    sa_path = self.download(
                        f"{HF_RESOLVE}/{sa_files[key]}",
                        sa_files[key].replace("/", "__"),
                    )
                    en_path = self.download(
                        f"{HF_RESOLVE}/{en_files[key]}",
                        en_files[key].replace("/", "__"),
                    )
                    sa_lines = sa_path.read_text("utf-8", errors="replace").strip().splitlines()
                    en_lines = en_path.read_text("utf-8", errors="replace").strip().splitlines()
                    n = min(len(sa_lines), len(en_lines))
                    rows = []
                    for i in range(n):
                        sa, en = sa_lines[i].strip(), en_lines[i].strip()
                        if sa and en and len(sa) > 2 and len(en) > 2:
                            rows.append((
                                self.source_id, sa, en, "sa", "en",
                                "sentence", self.expansion_ratio(sa, en),
                                "translation", f"bpcc:{dir_path}:{key}",
                                self.to_json({"dir": dir_path}),
                            ))
                    total += db.insert_parallel_pairs(rows)
                    log.info("[ai4bharat] paired %s/%s: %d pairs", dir_path, key, len(rows))
                except Exception as e:
                    log.warning("[ai4bharat] paired %s/%s: %s", dir_path, key, e)
        return total
