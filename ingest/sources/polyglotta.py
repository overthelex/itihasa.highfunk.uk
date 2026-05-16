"""Bibliotheca Polyglotta — verse-aligned Sa-En Buddhist translations.
Ranked #1 in audit. Uses Playwright to bypass access restrictions."""

import logging
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin

from bs4 import BeautifulSoup

import browser
import db
from harvester import Harvester

PARALLEL_BROWSERS = 5

log = logging.getLogger(__name__)

BASE = "https://www2.hf.uio.no/polyglotta"
CATALOG = f"{BASE}/index.php?page=library&bid=2"


class PolyglottaHarvester(Harvester):
    name = "polyglotta"
    url = BASE
    license = "Open Access"
    source_type = "parallel"
    pipeline_stage = 2

    def harvest(self) -> int:
        text_links = self._discover_texts()
        log.info("[polyglotta] discovered %d text entries, scraping with %d browsers",
                 len(text_links), PARALLEL_BROWSERS)
        total = 0
        lock = threading.Lock()

        def process_text(args):
            i, title, url = args
            try:
                pairs = self._scrape_text(title, url)
                if pairs:
                    count = db.insert_parallel_pairs(pairs)
                    log.info("[polyglotta] '%s': %d pairs", title[:40], count)
                    return count
            except Exception as e:
                log.warning("[polyglotta] skip '%s': %s", title[:40], e)
            return 0

        work = [(i, t, u) for i, (t, u) in enumerate(text_links)]
        with ThreadPoolExecutor(max_workers=PARALLEL_BROWSERS) as pool:
            futures = {pool.submit(process_text, w): w[1] for w in work}
            done_count = 0
            for future in as_completed(futures):
                count = future.result()
                total += count
                done_count += 1
                if done_count % 10 == 0:
                    log.info("[polyglotta] progress: %d/%d texts, %d pairs total",
                             done_count, len(text_links), total)
        return total

    def _discover_texts(self) -> list:
        html = browser.fetch_page(CATALOG, wait_selector="a", wait_ms=4000)
        soup = BeautifulSoup(html, "lxml")
        results = []
        seen = set()

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if not text or len(text) < 2:
                continue
            if "page=volume" in href or "vid=" in href:
                full = urljoin(BASE + "/", href)
                if full not in seen:
                    seen.add(full)
                    results.append((text, full))

        if len(results) < 5:
            log.info("[polyglotta] few direct links, exploring sub-libraries")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                text = a.get_text(strip=True)
                if "bid=" in href and text and len(text) > 2:
                    sub_url = urljoin(BASE + "/", href)
                    sub_html = browser.fetch_page(sub_url, wait_ms=3000)
                    sub_soup = BeautifulSoup(sub_html, "lxml")
                    for sa in sub_soup.find_all("a", href=True):
                        sh = sa["href"]
                        st = sa.get_text(strip=True)
                        if ("page=volume" in sh or "vid=" in sh) and st:
                            full = urljoin(BASE + "/", sh)
                            if full not in seen:
                                seen.add(full)
                                results.append((st, full))

        return results

    def _scrape_text(self, title, url) -> list:
        html = browser.fetch_page(url, wait_ms=3000)
        soup = BeautifulSoup(html, "lxml")

        chapter_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if ("page=fulltext" in href or "cid=" in href) and text:
                chapter_links.append((text, urljoin(BASE + "/", href)))

        if not chapter_links:
            return self._extract_from_page(soup, url, title)

        all_pairs = []
        for ch_title, ch_url in chapter_links:
            ch_html = browser.fetch_page(ch_url, wait_ms=3000)
            ch_soup = BeautifulSoup(ch_html, "lxml")
            pairs = self._extract_from_page(ch_soup, ch_url, f"{title}/{ch_title}")
            all_pairs.extend(pairs)
        return all_pairs

    def _extract_from_page(self, soup, url, text_ref) -> list:
        rows = []

        # Strategy 1: tables with multiple columns (verse-aligned)
        for table in soup.find_all("table"):
            for tr in table.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) < 2:
                    continue
                cell_texts = [td.get_text(strip=True) for td in tds]
                sa, en = self._identify_pair(cell_texts)
                if sa and en:
                    rows.append(self._make_row(sa, en, url, text_ref))

        # Strategy 2: parallel div blocks
        if not rows:
            all_divs = soup.find_all("div")
            sa_buf, en_buf = [], []
            for div in all_divs:
                cls = " ".join(div.get("class", []))
                lang = div.get("lang", "") or div.get("xml:lang", "")
                text = div.get_text(strip=True)
                if not text or len(text) < 3:
                    continue
                if "sa" in lang or "sanskrit" in cls.lower() or self._looks_sa(text):
                    sa_buf.append(text)
                elif "en" in lang or "english" in cls.lower() or self._looks_en(text):
                    en_buf.append(text)
            for sa, en in zip(sa_buf, en_buf):
                if len(sa) > 5 and len(en) > 5:
                    rows.append(self._make_row(sa, en, url, text_ref))

        # Strategy 3: spans with lang attributes
        if not rows:
            sa_spans = soup.find_all("span", attrs={"lang": re.compile(r"sa|san")})
            en_spans = soup.find_all("span", attrs={"lang": re.compile(r"en|eng")})
            for sa_s, en_s in zip(sa_spans, en_spans):
                sa = sa_s.get_text(strip=True)
                en = en_s.get_text(strip=True)
                if len(sa) > 5 and len(en) > 5:
                    rows.append(self._make_row(sa, en, url, text_ref))

        # Strategy 4: numbered paragraphs / verse blocks
        if not rows:
            paragraphs = soup.find_all(["p", "div", "span"])
            texts = [p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 10]
            sa_texts = [t for t in texts if self._looks_sa(t)]
            en_texts = [t for t in texts if self._looks_en(t)]
            for sa, en in zip(sa_texts, en_texts):
                rows.append(self._make_row(sa, en, url, text_ref))

        return rows

    def _make_row(self, sa, en, url, text_ref):
        return (
            self.source_id, sa, en, "sa", "en",
            "verse", self.expansion_ratio(sa, en),
            "translation", text_ref,
            self.to_json({"url": url}),
        )

    def _identify_pair(self, texts):
        sa, en = None, None
        for t in texts:
            if not t or len(t) < 3:
                continue
            if self._looks_sa(t) and not sa:
                sa = t
            elif self._looks_en(t) and not en:
                en = t
        return sa, en

    @staticmethod
    def _looks_sa(text):
        deva = sum(1 for c in text[:300] if "ऀ" <= c <= "ॿ")
        iast = sum(1 for c in text[:300] if c in "āīūṛṝḷḹṃḥśṣṭḍṇñṅĀĪŪṚṜḶḸṂḤŚṢṬḌṆÑṄ")
        return (deva + iast) > max(3, len(text[:300]) * 0.08)

    @staticmethod
    def _looks_en(text):
        ascii_a = sum(1 for c in text[:300] if c.isascii() and c.isalpha())
        return ascii_a > len(text[:300]) * 0.5
