"use client";

import { useEffect, useState, useMemo, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

interface Pair { s: string; sa: string; en: string; r: number; ref: string }
interface Bucket { b: string; n: number; sa: number; en: number }
interface Section { name: string; count: number; avg_r: number; min_r: number; max_r: number }
interface Overview { buckets: Bucket[]; sections: Section[]; total: number }
interface Meta { total: number; chunks: number; per_page: number }

const BUCKET_COLORS: Record<string, string> = {
  "<1x": "bg-gray-200", "1-2x": "bg-blue-100", "2-3x": "bg-blue-200",
  "3-5x": "bg-blue-300", "5-10x": "bg-amber-300", "10-20x": "bg-red-300", "20x+": "bg-red-500",
};

const BUCKET_RANGES: Record<string, [string, string]> = {
  "<1x": ["0", "1"], "1-2x": ["1", "2"], "2-3x": ["2", "3"],
  "3-5x": ["3", "5"], "5-10x": ["5", "10"], "10-20x": ["10", "20"], "20x+": ["20", "999"],
};

function Browser() {
  const router = useRouter();
  const sp = useSearchParams();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [loading, setLoading] = useState(false);

  const view = sp.get("view") || "overview";
  const page = parseInt(sp.get("page") || "0", 10);
  const minR = parseFloat(sp.get("min_r") || "0");
  const maxR = parseFloat(sp.get("max_r") || "999");
  const perPage = 50;

  useEffect(() => {
    fetch("/data/overview.json").then((r) => r.json()).then(setOverview);
    fetch("/data/meta.json").then((r) => r.json()).then(setMeta);
  }, []);

  useEffect(() => {
    if (view !== "browse") return;
    setLoading(true);
    fetch(`/data/page_${page}.json`)
      .then((r) => r.json())
      .then((d) => { setPairs(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [page, view]);

  const filtered = useMemo(
    () => pairs.filter((p) => p.r >= minR && p.r <= maxR),
    [pairs, minR, maxR]
  );

  function nav(params: Record<string, string>) {
    const next = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(params)) next.set(k, v);
    router.push(`?${next}`);
  }

  function badge(ratio: number) {
    if (ratio >= 10) return <span className="bg-red-600 text-white text-[11px] px-2 py-0.5 rounded-full font-medium">exegetical</span>;
    if (ratio >= 5) return <span className="bg-amber-500 text-white text-[11px] px-2 py-0.5 rounded-full font-medium">commentary</span>;
    if (ratio >= 1) return <span className="bg-gray-400 text-white text-[11px] px-2 py-0.5 rounded-full font-medium">translation</span>;
    return <span className="bg-gray-300 text-[11px] px-2 py-0.5 rounded-full">noise</span>;
  }

  const totalPages = meta?.chunks || 0;

  // ─── OVERVIEW ───
  if (view === "overview" && overview) {
    const maxBucket = Math.max(...overview.buckets.map((b) => b.n));
    return (
      <div className="max-w-6xl mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-1">Itihasa Sanskrit-English Corpus</h1>
        <p className="text-gray-500 mb-8">
          {overview.total.toLocaleString()} parallel verse pairs from Ramayana &amp; Mahabharata
          <span className="mx-2">|</span>
          <a href="https://github.com/overthelex/exegeticalgen" className="text-indigo-600 hover:underline">GitHub</a>
        </p>

        {/* Expansion ratio histogram */}
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Expansion Ratio Distribution</h2>
          <div className="space-y-2">
            {overview.buckets.map((b) => {
              const pct = (b.n / maxBucket) * 100;
              const range = BUCKET_RANGES[b.b];
              return (
                <button
                  key={b.b}
                  onClick={() => nav({ view: "browse", page: "0", min_r: range[0], max_r: range[1] })}
                  className="w-full flex items-center gap-3 group hover:bg-gray-50 rounded-lg p-1.5 transition text-left"
                >
                  <span className="w-16 text-sm font-mono text-right font-medium text-gray-700">{b.b}</span>
                  <div className="flex-1 h-8 bg-gray-100 rounded-md overflow-hidden relative">
                    <div
                      className={`h-full ${BUCKET_COLORS[b.b]} rounded-md transition-all group-hover:opacity-80`}
                      style={{ width: `${Math.max(pct, 1)}%` }}
                    />
                    <span className="absolute inset-y-0 left-2 flex items-center text-xs font-medium text-gray-700">
                      {b.n.toLocaleString()} pairs
                    </span>
                  </div>
                  <span className="w-24 text-xs text-gray-400 text-right">
                    avg {b.sa}→{b.en} chars
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Splits */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {overview.sections.map((s) => (
            <div key={s.name} className="bg-white border rounded-xl p-5">
              <div className="text-xs text-gray-400 uppercase tracking-wide mb-1">{s.name}</div>
              <div className="text-2xl font-bold">{s.count.toLocaleString()}</div>
              <div className="text-sm text-gray-500 mt-1">
                avg ratio {s.avg_r}x
                <span className="text-gray-300 mx-1">|</span>
                range {s.min_r}–{s.max_r}x
              </div>
            </div>
          ))}
        </div>

        {/* Quick access */}
        <div className="bg-white border rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-3">Browse by Type</h2>
          <div className="flex flex-wrap gap-3">
            {[
              { label: "All pairs", min: "0", max: "999", desc: "93K pairs", color: "bg-indigo-600" },
              { label: "Standard translation (1-3x)", min: "1", max: "3", desc: "58K pairs", color: "bg-blue-500" },
              { label: "Expanded translation (3-5x)", min: "3", max: "5", desc: "30K pairs", color: "bg-blue-600" },
              { label: "Commentary-like (5-10x)", min: "5", max: "10", desc: "4.4K pairs", color: "bg-amber-500" },
              { label: "Exegetical (10x+)", min: "10", max: "999", desc: "269 pairs", color: "bg-red-600" },
            ].map((b) => (
              <button
                key={b.label}
                onClick={() => nav({ view: "browse", page: "0", min_r: b.min, max_r: b.max })}
                className={`${b.color} text-white px-4 py-2.5 rounded-lg text-sm font-medium hover:opacity-90 transition`}
              >
                {b.label}
                <span className="block text-xs opacity-75 mt-0.5">{b.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* About */}
        <div className="bg-gray-50 border rounded-xl p-6 text-sm text-gray-600 leading-relaxed">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">About</h2>
          <p className="mb-2">
            This dataset contains <strong>93,030</strong> verse-aligned Sanskrit-English pairs from the
            <strong> Itihasa</strong> corpus (Ramayana &amp; Mahabharata). The data is part of research on
            <strong> exegetical generation</strong> — a new NLP task for producing expansive commentary
            from terse source texts.
          </p>
          <p>
            <strong>Expansion ratio</strong> measures |English| / |Sanskrit| in tokens. Translation
            typically gives 1-3x; exegetical commentary 5-20x. This corpus is primarily translational,
            serving as a baseline for comparison with exegetical data.
          </p>
          <p className="mt-2 text-xs text-gray-400">
            License: Apache-2.0 | Source: <a href="https://github.com/rahular/itihasa" className="text-indigo-500">github.com/rahular/itihasa</a>
          </p>
        </div>
      </div>
    );
  }

  // ─── BROWSE ───
  return (
    <div className="max-w-6xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => nav({ view: "overview" })}
          className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
        >
          ← Overview
        </button>
        <h1 className="text-xl font-bold">Browse Pairs</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 items-center mb-5 bg-white p-3 rounded-lg border sticky top-0 z-10">
        <div className="flex gap-1">
          {[
            { label: "All", min: "0", max: "999" },
            { label: "1-2x", min: "1", max: "2" },
            { label: "2-3x", min: "2", max: "3" },
            { label: "3-5x", min: "3", max: "5" },
            { label: "5-10x", min: "5", max: "10" },
            { label: "10x+", min: "10", max: "999" },
          ].map((p) => (
            <button
              key={p.label}
              onClick={() => nav({ min_r: p.min, max_r: p.max, page: "0" })}
              className={`text-xs px-3 py-1.5 rounded-full border transition font-medium ${
                String(minR) === p.min && String(maxR) === p.max
                  ? "bg-indigo-600 text-white border-indigo-600"
                  : "hover:bg-gray-100 text-gray-600"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>

        <span className="text-sm text-gray-400 ml-auto">
          {filtered.length} shown
          <span className="text-gray-300 mx-1">|</span>
          page {page + 1} of {totalPages}
        </span>

        {/* Page jump */}
        <div className="flex items-center gap-1">
          <button
            disabled={page === 0}
            onClick={() => nav({ page: "0" })}
            className="w-7 h-7 text-xs border rounded disabled:opacity-20 hover:bg-gray-100"
            title="First page"
          >
            1
          </button>
          <button
            disabled={page === 0}
            onClick={() => nav({ page: String(Math.max(0, page - 1)) })}
            className="w-7 h-7 text-xs border rounded disabled:opacity-20 hover:bg-gray-100"
          >
            &lt;
          </button>
          <input
            type="number"
            min={1}
            max={totalPages}
            defaultValue={page + 1}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                const v = parseInt((e.target as HTMLInputElement).value, 10) - 1;
                if (v >= 0 && v < totalPages) nav({ page: String(v) });
              }
            }}
            className="w-14 text-center text-xs border rounded py-1"
          />
          <button
            disabled={page >= totalPages - 1}
            onClick={() => nav({ page: String(page + 1) })}
            className="w-7 h-7 text-xs border rounded disabled:opacity-20 hover:bg-gray-100"
          >
            &gt;
          </button>
          <button
            disabled={page >= totalPages - 1}
            onClick={() => nav({ page: String(totalPages - 1) })}
            className="w-7 h-7 text-xs border rounded disabled:opacity-20 hover:bg-gray-100"
            title="Last page"
          >
            {totalPages}
          </button>
        </div>
      </div>

      {loading && <div className="text-center py-16 text-gray-400">Loading...</div>}

      {/* Cards */}
      <div className="space-y-2.5">
        {filtered.map((p, i) => (
          <div key={i} className="bg-white border rounded-lg p-4 hover:shadow-sm transition">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[11px] text-gray-400 font-mono">{p.ref}</span>
              <div className="flex items-center gap-2">
                {badge(p.r)}
                <span className="font-mono text-sm font-bold text-gray-700">{p.r}x</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-5">
              <div>
                <div
                  className="text-gray-800"
                  style={{ fontFamily: "'Noto Serif Devanagari', serif", fontSize: "15px", lineHeight: "2" }}
                >
                  {p.sa}
                </div>
              </div>
              <div className="text-[13px] leading-relaxed text-gray-600 border-l pl-5">
                {p.en}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom pagination */}
      <div className="flex items-center justify-center gap-2 mt-6 mb-12">
        <button
          disabled={page === 0}
          onClick={() => nav({ page: String(page - 1) })}
          className="px-3 py-1.5 border rounded text-sm disabled:opacity-20 hover:bg-gray-100"
        >
          Prev
        </button>
        {Array.from({ length: Math.min(9, totalPages) }, (_, i) => {
          let p: number;
          if (totalPages <= 9) p = i;
          else if (page <= 4) p = i;
          else if (page >= totalPages - 5) p = totalPages - 9 + i;
          else p = page - 4 + i;
          if (p < 0 || p >= totalPages) return null;
          return (
            <button
              key={p}
              onClick={() => nav({ page: String(p) })}
              className={`w-8 h-8 text-xs rounded transition ${
                p === page ? "bg-indigo-600 text-white font-bold" : "hover:bg-gray-100 text-gray-600"
              }`}
            >
              {p + 1}
            </button>
          );
        })}
        <button
          disabled={page >= totalPages - 1}
          onClick={() => nav({ page: String(page + 1) })}
          className="px-3 py-1.5 border rounded text-sm disabled:opacity-20 hover:bg-gray-100"
        >
          Next
        </button>
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-gray-400">Loading...</div>}>
      <Browser />
    </Suspense>
  );
}
