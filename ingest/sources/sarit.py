"""SARIT — Sanskrit TEI XML corpus with layered mūla-ṭīkā commentary structure."""

import logging
import re

from lxml import etree

import db
from harvester import Harvester

log = logging.getLogger(__name__)

REPO = "https://github.com/sarit/SARIT-corpus.git"

BUDDHIST_KEYWORDS = re.compile(
    r"bauddha|buddhis|pramāṇa|pramana|dignāga|dignaga|dharmakīrti|dharmakirti|"
    r"nyāya|nyaya|vāda|vada|madhyamaka|yogācāra|yogacara|abhidharma|"
    r"bodhicaryā|bodhicarya|śāntideva|santideva|nāgārjuna|nagarjuna|"
    r"vasubandhu|tattvasaṃgraha|tattvasamgraha|prajñāpāramitā",
    re.IGNORECASE,
)


class SaritHarvester(Harvester):
    name = "sarit"
    url = "https://sarit.indology.info/"
    license = "CC BY-SA 4.0"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        repo = self.clone_repo(REPO)
        xml_files = list(repo.rglob("*.xml"))
        log.info("[sarit] found %d XML files total", len(xml_files))

        rows = []
        for f in xml_files:
            raw = f.read_text(encoding="utf-8", errors="replace")
            fname = f.stem.lower()
            if not BUDDHIST_KEYWORDS.search(fname) and not BUDDHIST_KEYWORDS.search(raw[:2000]):
                continue
            title = f.stem
            content = self._extract_tei(raw)
            if len(content) < 100:
                continue
            tradition = "buddhist"
            genre = "commentary" if any(k in fname for k in ("tika", "bhasya", "vrtti")) else None
            rows.append((
                self.source_id, f.name, title, content, "sa", "iast",
                tradition, genre, self.token_count(content),
                self.to_json({"file": f.name}),
            ))
            log.info("[sarit] added %s (%d tokens)", f.name, self.token_count(content))

        all_rows = []
        for f in xml_files:
            if any(r[2] == f.stem for r in rows):
                continue
            raw = f.read_text(encoding="utf-8", errors="replace")
            content = self._extract_tei(raw)
            if len(content) < 100:
                continue
            all_rows.append((
                self.source_id, f.name, f.stem, content, "sa", "iast",
                None, None, self.token_count(content),
                self.to_json({"file": f.name}),
            ))

        total = db.insert_texts(rows)
        total += db.insert_texts(all_rows)
        return total

    def _extract_tei(self, xml_str) -> str:
        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except etree.XMLSyntaxError:
            root = etree.fromstring(
                xml_str.encode("utf-8"), parser=etree.XMLParser(recover=True)
            )
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        body = root.find(".//tei:body", ns) or root.find(".//body")
        if body is None:
            return re.sub(r"<[^>]+>", " ", xml_str)
        parts = []
        for elem in body.iter():
            if elem.text:
                parts.append(elem.text.strip())
            if elem.tail:
                parts.append(elem.tail.strip())
        return "\n".join(p for p in parts if p)
