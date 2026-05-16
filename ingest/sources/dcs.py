"""DCS — Digital Corpus of Sanskrit: CoNLL-U morphological data + dictionary."""

import json
import logging
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/OliverHellwig/sanskrit.git"


class DCSHarvester(Harvester):
    name = "dcs"
    url = "https://github.com/OliverHellwig/sanskrit"
    license = "CC BY 4.0"
    source_type = "morphological"
    pipeline_stage = 1

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        total = 0
        total += self._ingest_conllu(repo)
        total += self._ingest_dictionary(repo)
        total += self._ingest_texts(repo)
        return total

    def _ingest_conllu(self, repo: Path) -> int:
        conllu_dir = None
        for candidate in [
            repo / "dcs" / "data" / "conllu",
            repo / "data" / "conllu",
        ]:
            if candidate.exists():
                conllu_dir = candidate
                break
        if not conllu_dir:
            for p in repo.rglob("*.conllu"):
                conllu_dir = p.parent
                break
        if not conllu_dir:
            log.warning("[dcs] no CoNLL-U directory found")
            return 0

        rows = []
        files = list(conllu_dir.rglob("*.conllu"))
        log.info("[dcs] parsing %d CoNLL-U files", len(files))
        for f in files:
            text_ref = f.stem
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) < 10:
                    continue
                try:
                    int(parts[0])
                except ValueError:
                    continue
                form = parts[1]
                lemma = parts[2]
                pos = parts[3]
                features = parts[5] if parts[5] != "_" else None
                misc = parts[9] if len(parts) > 9 else ""
                unsandhied = None
                wordnet_id = None
                if misc and misc != "_":
                    for kv in misc.split("|"):
                        if "=" in kv:
                            k, v = kv.split("=", 1)
                            if k == "Unsandhied":
                                unsandhied = v
                            elif k in ("WordNetId", "LId"):
                                wordnet_id = v
                rows.append((
                    self.source_id, form, lemma, unsandhied, pos,
                    features, wordnet_id, text_ref,
                ))
            if len(rows) >= 50000:
                db.insert_morphological(rows)
                log.info("[dcs] flushed %d morph rows", len(rows))
                rows = []
        count = db.insert_morphological(rows)
        log.info("[dcs] total morph rows loaded")
        return count

    def _ingest_dictionary(self, repo: Path) -> int:
        dict_dir = None
        for candidate in [
            repo / "dcs" / "data" / "dictionary",
            repo / "data" / "dictionary",
        ]:
            if candidate.exists():
                dict_dir = candidate
                break
        if not dict_dir:
            for p in repo.rglob("*dictionary*"):
                if p.is_dir():
                    dict_dir = p
                    break
        if not dict_dir:
            log.warning("[dcs] no dictionary directory found")
            return 0

        rows = []
        for f in dict_dir.rglob("*"):
            if not f.is_file():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8", errors="replace"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(data, dict):
                entries = [data]
            elif isinstance(data, list):
                entries = data
            else:
                continue
            for entry in entries:
                hw = entry.get("word") or entry.get("headword") or entry.get("lemma", "")
                defn = entry.get("meaning") or entry.get("definition") or entry.get("gloss", "")
                if not hw or not defn:
                    if isinstance(defn, list):
                        defn = "; ".join(str(d) for d in defn)
                    if not defn:
                        continue
                if isinstance(defn, list):
                    defn = "; ".join(str(d) for d in defn)
                rows.append((
                    self.source_id, str(hw), None, str(defn),
                    entry.get("pos"), None, self.to_json({"source_file": f.name}),
                ))
        return db.insert_dictionary_entries(rows)

    def _ingest_texts(self, repo: Path) -> int:
        rows = []
        for f in repo.rglob("*.txt"):
            if "readme" in f.name.lower() or "license" in f.name.lower():
                continue
            text = f.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) < 100:
                continue
            rows.append((
                self.source_id, f.stem, f.stem, text, "sa", "iast",
                None, None, self.token_count(text),
                self.to_json({"path": str(f.relative_to(repo))}),
            ))
        return db.insert_texts(rows)
