"""Simple browser for parallel pairs from the DB."""

import html
import psycopg2
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

DB = "postgresql://sanskrit:sanskrit@localhost:5434/sanskrit"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        source = params.get("source", [""])[0]
        min_r = float(params.get("min_r", ["0"])[0])
        max_r = float(params.get("max_r", ["999"])[0])
        offset = int(params.get("offset", ["0"])[0])
        limit = int(params.get("limit", ["50"])[0])

        conn = psycopg2.connect(DB)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sources ORDER BY name")
        sources = [r[0] for r in cur.fetchall()]

        en_only = params.get("en", ["1"])[0] == "1"

        where = "WHERE 1=1"
        qparams = []
        if en_only:
            where += """ AND p.target_text ~ '[a-zA-Z]{20}'
                         AND length(p.target_text) > 50
                         AND length(p.source_text) > 20
                         AND p.source_text !~ '^[A-Z][0-9]'
                         AND p.target_text NOT LIKE 'Choose language%%'
                         AND p.target_text NOT LIKE 'You are here%%'
                         AND p.target_text NOT LIKE 'Go to the full%%'
                         AND p.source_text NOT LIKE '%%·%%·%%·%%·%%·%%'"""
        if source:
            where += " AND s.name = %s"
            qparams.append(source)
        if min_r > 0:
            where += " AND p.expansion_ratio >= %s"
            qparams.append(min_r)
        if max_r < 999:
            where += " AND p.expansion_ratio <= %s"
            qparams.append(max_r)

        cur.execute(f"SELECT count(*) FROM parallel_pairs p JOIN sources s ON p.source_id=s.id {where}", qparams)
        total = cur.fetchone()[0]

        cur.execute(f"""
            SELECT s.name, p.source_text, p.target_text,
                   round(p.expansion_ratio::numeric, 2), p.text_ref, p.pair_type
            FROM parallel_pairs p JOIN sources s ON p.source_id=s.id
            {where}
            ORDER BY p.expansion_ratio DESC
            LIMIT %s OFFSET %s
        """, qparams + [limit, offset])
        rows = cur.fetchall()
        cur.close()
        conn.close()

        opts = "".join(f'<option value="{s}" {"selected" if s==source else ""}>{s}</option>' for s in sources)
        prev_off = max(0, offset - limit)
        next_off = offset + limit

        cards = ""
        for name, src, tgt, ratio, ref, ptype in rows:
            s = html.escape(src[:500])
            t = html.escape(tgt[:1000])
            r = html.escape(ref or "")
            badge = ""
            if ratio and float(ratio) >= 10:
                badge = '<span style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">exegetical</span>'
            elif ratio and float(ratio) >= 5:
                badge = '<span style="background:#f59e0b;color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">commentary</span>'
            elif ratio and float(ratio) >= 1:
                badge = '<span style="background:#6b7280;color:#fff;padding:2px 8px;border-radius:12px;font-size:12px">translation</span>'
            cards += f"""
            <div style="border:1px solid #e5e7eb;border-radius:8px;padding:16px;margin-bottom:12px;background:#fff">
              <div style="display:flex;justify-content:space-between;margin-bottom:8px">
                <span style="font-weight:600;color:#4f46e5">{html.escape(name)}</span>
                <span>{badge} <b>{ratio}x</b></span>
              </div>
              <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
                <div>
                  <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">Sanskrit source</div>
                  <div class="sa-text">{s}</div>
                </div>
                <div>
                  <div style="font-size:11px;color:#9ca3af;margin-bottom:4px">English target</div>
                  <div class="en-text">{t}</div>
                </div>
              </div>
              <div style="font-size:11px;color:#9ca3af;margin-top:8px">{r}</div>
            </div>"""

        body = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ExeGen Pairs Browser</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;600&family=Noto+Serif+Devanagari:wght@400;600&display=swap" rel="stylesheet">
<style>
body{{font-family:system-ui;background:#f9fafb;margin:0;padding:20px}}
a{{color:#4f46e5}}
.sa-text{{font-family:'Noto Serif Devanagari','Noto Sans Devanagari',serif;font-size:16px;line-height:1.8;color:#1f2937}}
.en-text{{font-size:14px;line-height:1.7;color:#374151}}
</style></head>
<body>
<h1 style="margin:0 0 16px">ExeGen Pairs Browser</h1>
<form style="display:flex;gap:12px;align-items:center;margin-bottom:20px;flex-wrap:wrap">
  <select name="source" style="padding:6px 12px;border:1px solid #d1d5db;border-radius:6px">
    <option value="">All sources</option>{opts}
  </select>
  <label>Min R: <input name="min_r" type="number" step="0.5" value="{min_r}" style="width:60px;padding:6px;border:1px solid #d1d5db;border-radius:6px"></label>
  <label>Max R: <input name="max_r" type="number" step="0.5" value="{max_r}" style="width:60px;padding:6px;border:1px solid #d1d5db;border-radius:6px"></label>
  <label style="display:flex;align-items:center;gap:4px"><input type="checkbox" name="en" value="1" {"checked" if en_only else ""}> English only</label>
  <button type="submit" style="padding:6px 16px;background:#4f46e5;color:#fff;border:none;border-radius:6px;cursor:pointer">Filter</button>
  <span style="color:#6b7280">{total:,} pairs</span>
</form>
<div>{cards}</div>
<div style="display:flex;gap:12px;margin-top:16px">
  <a href="?source={source}&min_r={min_r}&max_r={max_r}&offset={prev_off}&limit={limit}">← Prev</a>
  <span style="color:#9ca3af">{offset+1}–{min(offset+limit, total)} of {total:,}</span>
  <a href="?source={source}&min_r={min_r}&max_r={max_r}&offset={next_off}&limit={limit}">Next →</a>
</div>
</body></html>"""

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    port = 8899
    print(f"http://localhost:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
