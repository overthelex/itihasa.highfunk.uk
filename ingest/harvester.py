import json
import logging
import shutil
import subprocess
import time
from pathlib import Path

import httpx

import db
from config import CLONE_DEPTH, DATA_DIR, RATE_LIMIT_SLEEP, REQUEST_TIMEOUT

log = logging.getLogger(__name__)


class Harvester:
    name: str = ""
    url: str = ""
    license: str = ""
    source_type: str = "corpus"
    pipeline_stage: int = 1

    def __init__(self):
        self.work_dir = DATA_DIR / self.name
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.source_id = db.register_source(
            self.name, self.url, self.license, self.source_type, self.pipeline_stage
        )
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = httpx.Client(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "SanskritIngest/1.0 (academic research)"},
            )
        return self._client

    def run(self):
        db.set_status(self.source_id, "running")
        try:
            count = self.harvest()
            db.set_status(self.source_id, "done", items_count=count)
            log.info("[%s] done — %d items", self.name, count)
            return count
        except Exception as e:
            db.set_status(self.source_id, "error", error_msg=str(e)[:500])
            log.exception("[%s] failed", self.name)
            raise

    def harvest(self) -> int:
        raise NotImplementedError

    def clone_repo(self, repo_url, sparse_paths=None) -> Path:
        dest = self.work_dir / "repo"
        if dest.exists():
            shutil.rmtree(dest)
        cmd = ["git", "clone", "--depth", str(CLONE_DEPTH)]
        if sparse_paths:
            cmd += ["--filter=blob:none", "--sparse"]
        cmd += [repo_url, str(dest)]
        log.info("[%s] cloning %s", self.name, repo_url)
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        if sparse_paths:
            subprocess.run(
                ["git", "sparse-checkout", "set"] + sparse_paths,
                cwd=dest, check=True, capture_output=True,
            )
        return dest

    def download(self, url, filename=None) -> Path:
        filename = filename or url.rsplit("/", 1)[-1]
        dest = self.work_dir / filename
        if dest.exists():
            return dest
        log.info("[%s] downloading %s", self.name, url)
        with self.client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in r.iter_bytes(65536):
                    f.write(chunk)
        return dest

    def fetch(self, url) -> str:
        time.sleep(RATE_LIMIT_SLEEP)
        resp = self.client.get(url)
        resp.raise_for_status()
        return resp.text

    def fetch_bytes(self, url) -> bytes:
        time.sleep(RATE_LIMIT_SLEEP)
        resp = self.client.get(url)
        resp.raise_for_status()
        return resp.content

    @staticmethod
    def token_count(text):
        return len(text.split())

    @staticmethod
    def expansion_ratio(source, target):
        sl, tl = len(source.split()), len(target.split())
        return round(tl / sl, 2) if sl > 0 else 0.0

    @staticmethod
    def to_json(d):
        return json.dumps(d, ensure_ascii=False)
