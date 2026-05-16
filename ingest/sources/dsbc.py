"""DSBC — Digital Sanskrit Buddhist Canon. ~486 texts.
Uses Playwright to handle JS-rendered pages."""

import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import browser
import db
from harvester import Harvester

log = logging.getLogger(__name__)

BASE = "https://www.dsbcproject.org"


class DSBCHarvester(Harvester):
    name = "dsbc"
    url = BASE
    license = "Custom (NC, permission required)"
    source_type = "corpus"
    pipeline_stage = 2

    def harvest(self) -> int:
        text_links = self._discover_texts()
        log.info("[dsbc] discovered %d text links", len(text_links))
        rows = []
        for i, (title, url) in enumerate(text_links):
            try:
                content = self._scrape_text(url)
                if not content or len(content) < 100:
                    continue
                rows.append((
                    self.source_id, url, title, content, "sa", "iast",
                    "buddhist", self._guess_genre(title),
                    self.token_count(content),
                    self.to_json({"url": url}),
                ))
            except Exception as e:
                log.warning("[dsbc] skip '%s': %s", title[:40], e)
            if (i + 1) % 20 == 0:
                log.info("[dsbc] progress: %d/%d, %d texts collected",
                         i + 1, len(text_links), len(rows))
        return db.insert_texts(rows)

    def _discover_texts(self) -> list:
        results = []
        for path in ["/canon-text/list", "/canon-text", "/canon/text", "/"]:
            try:
                html = browser.fetch_page(
                    BASE + path,
                    wait_selector="a",
                    wait_ms=5000,
                )
                soup = BeautifulSoup(html, "lxml")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    text = a.get_text(strip=True)
                    if not text or len(text) < 3:
                        continue
                    if "canon-text/content" in href or re.search(r"/\d+/\d+", href):
                        full = urljoin(BASE, href)
                        results.append((text, full))
                if results:
                    break
            except Exception as e:
                log.warning("[dsbc] catalog %s: %s", path, e)

        if not results:
            results = self._crawl_catalog()

        return results

    def _crawl_catalog(self) -> list:
        results = []
        html = browser.fetch_page(BASE, wait_ms=5000)
        soup = BeautifulSoup(html, "lxml")
        cat_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if "/canon" in href and text and len(text) > 3:
                cat_links.append(urljoin(BASE, href))

        for cat_url in cat_links[:20]:
            try:
                sub_html = browser.fetch_page(cat_url, wait_ms=3000)
                sub_soup = BeautifulSoup(sub_html, "lxml")
                for a in sub_soup.find_all("a", href=True):
                    href = a["href"]
                    text = a.get_text(strip=True)
                    if "content" in href and text:
                        results.append((text, urljoin(BASE, href)))
            except Exception:
                pass
            if len(results) > 500:
                break
        return results

    def _scrape_text(self, url) -> str:
        html = browser.fetch_page(url, wait_ms=4000)
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        content_div = (
            soup.find("div", class_=re.compile(r"content|text|body|canon"))
            or soup.find("article")
            or soup.find("main")
        )
        if content_div:
            text = content_div.get_text("\n", strip=True)
        else:
            text = soup.get_text("\n", strip=True)

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        lines = [l for l in lines
                 if not re.match(r"^(Home|Menu|Search|Copyright|©|Nav|Log)", l)]
        return "\n".join(lines)

    @staticmethod
    def _guess_genre(title):
        t = title.lower()
        if any(k in t for k in ("sūtra", "sutra", "sutta")):
            return "sutra"
        if any(k in t for k in ("vinaya",)):
            return "vinaya"
        if any(k in t for k in ("avadāna", "avadana")):
            return "narrative"
        if any(k in t for k in ("śāstra", "sastra", "abhidharma")):
            return "shastra"
        return None
