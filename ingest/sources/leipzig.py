"""Leipzig Corpora — Sanskrit Wikipedia corpus: 200K sentences."""

import logging
import tarfile
from pathlib import Path

import db
from harvester import Harvester

log = logging.getLogger(__name__)

URLS = [
    "https://downloads.wortschatz-leipzig.de/corpora/san_wikipedia_2021.tar.gz",
    "https://downloads.wortschatz-leipzig.de/corpora/san-wik_wikipedia_2021.tar.gz",
    "https://downloads.wortschatz-leipzig.de/corpora/san_wikipedia_2016.tar.gz",
]


class LeipzigHarvester(Harvester):
    name = "leipzig"
    url = "https://wortschatz.uni-leipzig.de/en/download/Sanskrit"
    license = "CC BY"
    source_type = "corpus"
    pipeline_stage = 1

    def harvest(self) -> int:
        archive = None
        for url in URLS:
            try:
                archive = self.download(url, url.rsplit("/", 1)[-1])
                break
            except Exception as e:
                log.warning("[leipzig] %s: %s", url, e)

        if not archive:
            log.warning("[leipzig] no download URL worked, trying API")
            return self._try_api()

        extract_dir = self.work_dir / "extracted"
        extract_dir.mkdir(exist_ok=True)
        with tarfile.open(archive) as tf:
            tf.extractall(extract_dir)

        return self._ingest_dir(extract_dir)

    def _try_api(self) -> int:
        try:
            resp = self.client.get(
                "https://corpora.uni-leipzig.de/en",
                params={"corpusId": "san_wikipedia_2021"},
            )
            if resp.status_code != 200:
                log.warning("[leipzig] API unavailable")
                return 0
        except Exception:
            return 0
        return 0

    def _ingest_dir(self, extract_dir) -> int:
        sentences_file = None
        for f in extract_dir.rglob("*sentences*"):
            sentences_file = f
            break
        if not sentences_file:
            txt_files = list(extract_dir.rglob("*.txt"))
            if txt_files:
                sentences_file = max(txt_files, key=lambda f: f.stat().st_size)

        if not sentences_file:
            log.warning("[leipzig] no sentence file found in archive")
            return 0

        rows = []
        text = sentences_file.read_text(encoding="utf-8", errors="replace")
        for line in text.strip().splitlines():
            parts = line.split("\t", 1)
            sentence = parts[-1].strip()
            if not sentence or len(sentence) < 10:
                continue
            rows.append((
                self.source_id, None, None, sentence, "sa", "devanagari",
                None, None, self.token_count(sentence),
                self.to_json({"source": "wikipedia"}),
            ))

        log.info("[leipzig] %d sentences", len(rows))
        return db.insert_texts(rows)
