"""GRETIL — Göttingen Register of Electronic Texts in Indian Languages.
Buddhist Sanskrit subset: ~357 files, 5-7M tokens, TEI XML + plain text."""

import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup
from lxml import etree

import db
from harvester import Harvester

log = logging.getLogger(__name__)

BASE = "http://gretil.sub.uni-goettingen.de"
INDEX = f"{BASE}/gretil.html"

BUDDHIST_KEYWORDS = re.compile(
    r"bauddha|buddhis|mahāyāna|mahayana|sūtra|sutra|abhidharma|yogācāra|yogacara|"
    r"madhyamaka|vajrayāna|vajrayana|prajñāpāramitā|prajnaparamita|"
    r"laṅkāvatāra|lankavat|lalitavistara|saddharmapuṇḍarīka|saddharma|"
    r"bodhicaryāvatāra|bodhicary|nāgārjuna|nagarjuna|vasubandhu|asaṅga|"
    r"dignāga|dharmakīrti|śāntideva|santideva|mūlamadhyamaka|mulamadhy|"
    r"avadāna|avadana|jātaka|divyāvadāna|divyavad|vinaya|milinda|"
    r"aṣṭasāhasrikā|astasahasri|vajracchedikā|vajracchedi",
    re.IGNORECASE,
)


class GretilHarvester(Harvester):
    name = "gretil"
    url = INDEX
    license = "CC BY-NC-SA 4.0"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        links = self._discover_buddhist_links()
        log.info("[gretil] found %d Buddhist file links", len(links))
        rows = []
        for i, (title, href) in enumerate(links):
            try:
                content = self._fetch_and_extract(href)
                if not content or len(content) < 50:
                    continue
                rows.append((
                    self.source_id, href, title, content, "sa", "iast",
                    "buddhist", self._guess_genre(title),
                    self.token_count(content),
                    self.to_json({"url": href}),
                ))
            except Exception as e:
                log.warning("[gretil] skip %s: %s", href, e)
            if (i + 1) % 50 == 0:
                log.info("[gretil] progress: %d/%d", i + 1, len(links))
        return db.insert_texts(rows)

    def _discover_buddhist_links(self) -> list:
        html = self.fetch(INDEX)
        soup = BeautifulSoup(html, "lxml")
        links = []
        seen = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            full_text = text
            parent = a.parent
            if parent:
                full_text += " " + parent.get_text(strip=True)
            if not BUDDHIST_KEYWORDS.search(full_text):
                continue
            if not href.startswith("http"):
                href = BASE + "/" + href.lstrip("/")
            if href in seen:
                continue
            if not any(href.endswith(ext) for ext in (".htm", ".html", ".xml", ".txt")):
                continue
            seen.add(href)
            links.append((text, href))

        if len(links) < 20:
            self._discover_from_corpustei(links, seen)
        return links

    def _discover_from_corpustei(self, links, seen):
        try:
            html = self.fetch(f"{BASE}/gretil/corpustei/")
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("sa_") and href.endswith(".xml"):
                    if BUDDHIST_KEYWORDS.search(href):
                        full = f"{BASE}/gretil/corpustei/{href}"
                        if full not in seen:
                            seen.add(full)
                            links.append((href.replace(".xml", ""), full))
        except Exception as e:
            log.warning("[gretil] corpustei scan failed: %s", e)

    def _fetch_and_extract(self, url) -> str:
        raw = self.fetch(url)
        if url.endswith(".xml"):
            return self._extract_tei(raw)
        return self._extract_html(raw)

    def _extract_tei(self, xml_str) -> str:
        try:
            root = etree.fromstring(xml_str.encode("utf-8"))
        except etree.XMLSyntaxError:
            root = etree.fromstring(xml_str.encode("utf-8"), parser=etree.XMLParser(recover=True))
        ns = {"tei": "http://www.tei-c.org/ns/1.0"}
        body = root.find(".//tei:body", ns)
        if body is None:
            body = root.find(".//body")
        if body is None:
            return re.sub(r"<[^>]+>", " ", xml_str)
        parts = []
        for elem in body.iter():
            if elem.text:
                parts.append(elem.text.strip())
            if elem.tail:
                parts.append(elem.tail.strip())
        return "\n".join(p for p in parts if p)

    def _extract_html(self, html) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "head", "nav", "footer"]):
            tag.decompose()
        text = soup.get_text("\n", strip=True)
        lines = text.splitlines()
        start = 0
        for i, line in enumerate(lines):
            if line.startswith("# Text") or line.startswith("## Text") or re.match(r"^[|]?\s*namo\b", line, re.I):
                start = i
                break
        return "\n".join(lines[start:])

    @staticmethod
    def _guess_genre(title):
        t = title.lower()
        if any(k in t for k in ("sūtra", "sutra", "sutta")):
            return "sutra"
        if any(k in t for k in ("śāstra", "sastra", "kārikā", "karika")):
            return "shastra"
        if any(k in t for k in ("avadāna", "avadana", "jātaka")):
            return "narrative"
        if any(k in t for k in ("ṭīkā", "tika", "bhāṣya", "bhasya", "vṛtti", "vrtti")):
            return "commentary"
        if any(k in t for k in ("tantra", "vajra")):
            return "tantra"
        return None
