"""Sanskrit Heritage Platform (INRIA) — sandhi analysis + morphological tools.
Blocked by Anubis bot protection. Uses Playwright to bypass."""

import logging
import re

from bs4 import BeautifulSoup

import browser
import db
from harvester import Harvester

log = logging.getLogger(__name__)

BASE = "https://sanskrit.inria.fr"
READER = f"{BASE}/DICO/reader.fr.html"
INDEX = f"{BASE}/DICO/index.fr.html"


class HeritageHarvester(Harvester):
    name = "heritage"
    url = BASE
    license = "unclear"
    source_type = "dictionary"
    pipeline_stage = 1

    def harvest(self) -> int:
        total = 0
        total += self._ingest_dictionary()
        return total

    def _ingest_dictionary(self) -> int:
        html = browser.fetch_page(INDEX, wait_ms=5000)
        soup = BeautifulSoup(html, "lxml")

        letter_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if len(text) == 1 or re.match(r"^[A-Za-z]{1,3}$", text):
                if "index" in href or "dico" in href.lower():
                    letter_links.append((text, BASE + "/DICO/" + href if not href.startswith("http") else href))

        if not letter_links:
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if text and ("index" in href.lower() or re.search(r"\b[a-z]\.html", href)):
                    letter_links.append((text, BASE + "/DICO/" + href if not href.startswith("http") else href))

        log.info("[heritage] found %d letter index pages", len(letter_links))
        if not letter_links:
            log.info("[heritage] trying direct dictionary scrape")
            return self._scrape_direct()

        rows = []
        for letter, url in letter_links:
            try:
                page_html = browser.fetch_page(url, wait_ms=3000)
                page_soup = BeautifulSoup(page_html, "lxml")
                entries = self._extract_entries(page_soup)
                rows.extend(entries)
                log.info("[heritage] '%s': %d entries", letter, len(entries))
            except Exception as e:
                log.warning("[heritage] skip letter '%s': %s", letter, e)

        return db.insert_dictionary_entries(rows)

    def _scrape_direct(self) -> int:
        rows = []
        html = browser.fetch_page(BASE, wait_ms=5000)
        soup = BeautifulSoup(html, "lxml")

        dict_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if "dico" in href.lower() or "dict" in href.lower() or "lexicon" in text.lower():
                dict_links.append((text, href if href.startswith("http") else BASE + "/" + href.lstrip("/")))

        for title, url in dict_links[:30]:
            try:
                page_html = browser.fetch_page(url, wait_ms=3000)
                page_soup = BeautifulSoup(page_html, "lxml")
                entries = self._extract_entries(page_soup)
                rows.extend(entries)
            except Exception:
                pass

        return db.insert_dictionary_entries(rows)

    def _extract_entries(self, soup) -> list:
        rows = []
        for tag in soup.find_all(["dt", "b", "strong", "span"]):
            headword = tag.get_text(strip=True)
            if not headword or len(headword) < 2 or len(headword) > 80:
                continue
            definition = ""
            sib = tag.find_next_sibling()
            if sib:
                definition = sib.get_text(strip=True)
            if not definition and tag.parent:
                parent_text = tag.parent.get_text(strip=True)
                if parent_text.startswith(headword):
                    definition = parent_text[len(headword):].strip(" :—-–")
            if definition and len(definition) > 5:
                rows.append((
                    self.source_id, headword, None, definition,
                    None, None, self.to_json({"source": "heritage"}),
                ))

        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    hw = tds[0].get_text(strip=True)
                    defn = tds[1].get_text(strip=True)
                    if hw and defn and len(defn) > 3:
                        rows.append((
                            self.source_id, hw, None, defn,
                            None, None, self.to_json({"source": "heritage"}),
                        ))
        return rows
