"""Cologne Digital Sanskrit Dictionaries — MW (286K entries) + BHS (17K entries)."""

import logging
import re

import db
from harvester import Harvester

log = logging.getLogger(__name__)

MW_URL = "https://raw.githubusercontent.com/sanskrit-lexicon/csl-orig/master/v02/mw/mw.txt"
BHS_URL = "https://raw.githubusercontent.com/sanskrit-lexicon/csl-orig/master/v02/bhs/bhs.txt"

ENTRY_RE = re.compile(r"^<L>(\S+)<pc>([^<]*)<k1>(\S+)<k2>([^<\n]*)")
END_RE = re.compile(r"^<LEND>")


class CologneHarvester(Harvester):
    name = "cologne"
    url = "https://www.sanskrit-lexicon.uni-koeln.de/"
    license = "CC BY-NC-SA 3.0"
    source_type = "dictionary"
    pipeline_stage = 1

    def harvest(self) -> int:
        total = 0
        total += self._ingest_dict(MW_URL, "mw", "general")
        total += self._ingest_dict(BHS_URL, "bhs", "buddhist")
        return total

    def _ingest_dict(self, url, dict_name, domain) -> int:
        path = self.download(url, f"{dict_name}.txt")
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        log.info("[cologne] parsing %s (%d lines)", dict_name, len(lines))

        rows = []
        current_hw = None
        current_slp1 = None
        current_lines = []

        for line in lines:
            m = ENTRY_RE.match(line)
            if m:
                if current_hw and current_lines:
                    defn = self._clean_definition("\n".join(current_lines))
                    if defn:
                        pos = self._extract_pos(defn)
                        rows.append((
                            self.source_id, current_hw, current_slp1, defn,
                            pos, domain,
                            self.to_json({"dict": dict_name}),
                        ))
                current_slp1 = m.group(3)
                current_hw = m.group(4) or current_slp1
                current_lines = []
                rest = ENTRY_RE.sub("", line).strip()
                if rest:
                    current_lines.append(rest)
            elif END_RE.match(line):
                if current_hw and current_lines:
                    defn = self._clean_definition("\n".join(current_lines))
                    if defn:
                        pos = self._extract_pos(defn)
                        rows.append((
                            self.source_id, current_hw, current_slp1, defn,
                            pos, domain,
                            self.to_json({"dict": dict_name}),
                        ))
                current_hw = None
                current_lines = []
            elif current_hw is not None:
                current_lines.append(line)

        count = db.insert_dictionary_entries(rows)
        log.info("[cologne] %s: %d entries loaded", dict_name, count)
        return count

    @staticmethod
    def _clean_definition(text):
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = text.lstrip("¦ ")
        return text if len(text) > 2 else ""

    @staticmethod
    def _extract_pos(text):
        m = re.search(r"<lex>([^<]+)</lex>", text)
        if m:
            return m.group(1).strip(". ")
        for tag in ("m.", "f.", "n.", "mfn.", "ind.", "adj.", "adv."):
            if text.startswith(tag) or f" {tag}" in text[:50]:
                return tag.rstrip(".")
        return None
