"""SuttaCentral — 927 Buddhist Sanskrit files + 35 English translations."""

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/suttacentral/sc-data.git"


class SuttaCentralHarvester(Harvester):
    name = "suttacentral"
    url = "https://github.com/suttacentral/sc-data"
    license = "CC0"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        total = 0

        sa_texts = []
        en_texts = {}

        for root_dir in [repo / "html_text", repo / "sc_bilara_data"]:
            if not root_dir.exists():
                continue
            for f in root_dir.rglob("*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(root_dir)).lower()
                if "/san/" in rel or "/sa/" in rel or "/sanskrit/" in rel:
                    if f.suffix in (".html", ".htm"):
                        sa_texts.append(("html", f))
                    elif f.suffix == ".json":
                        sa_texts.append(("json", f))
                    elif f.suffix == ".txt":
                        sa_texts.append(("txt", f))
                elif "/en/" in rel and ("/san/" in rel or "/sa/" in rel):
                    en_texts[f.stem] = f

        log.info("[suttacentral] found %d Sanskrit files, %d English files",
                 len(sa_texts), len(en_texts))

        rows = []
        for fmt, f in sa_texts:
            try:
                content = self._extract(fmt, f)
                if len(content) < 50:
                    continue
                rows.append((
                    self.source_id, f.stem, f.stem, content, "sa",
                    "devanagari" if self._is_devanagari(content) else "iast",
                    "buddhist", None, self.token_count(content),
                    self.to_json({"path": str(f.relative_to(repo))}),
                ))
            except Exception as e:
                log.warning("[suttacentral] skip %s: %s", f.name, e)
        total += db.insert_texts(rows)

        pair_rows = []
        for fmt, f in sa_texts:
            if f.stem in en_texts:
                try:
                    sa_content = self._extract(fmt, f)
                    en_f = en_texts[f.stem]
                    en_content = self._extract(
                        "html" if en_f.suffix in (".html", ".htm") else "txt", en_f
                    )
                    if sa_content and en_content:
                        pair_rows.append((
                            self.source_id, sa_content, en_content, "sa", "en",
                            "document", self.expansion_ratio(sa_content, en_content),
                            "translation", f.stem, self.to_json({}),
                        ))
                except Exception:
                    pass
        total += db.insert_parallel_pairs(pair_rows)
        return total

    def _extract(self, fmt, f) -> str:
        raw = f.read_text(encoding="utf-8", errors="replace")
        if fmt == "html":
            soup = BeautifulSoup(raw, "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            return soup.get_text("\n", strip=True)
        if fmt == "json":
            import json
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    return "\n".join(str(v) for v in data.values() if isinstance(v, str))
            except json.JSONDecodeError:
                pass
            return ""
        return raw.strip()

    @staticmethod
    def _is_devanagari(text):
        for ch in text[:200]:
            if "ऀ" <= ch <= "ॿ":
                return True
        return False
