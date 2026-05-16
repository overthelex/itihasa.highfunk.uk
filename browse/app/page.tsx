"use client";

import { useEffect, useState, useMemo, useCallback, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

/* ── types ── */
interface Pair { s: string; sa: string; en: string; r: number; ref: string }
interface Bucket { b: string; n: number; sa: number; en: number }
interface Section { name: string; count: number; avg_r: number; min_r: number; max_r: number }
interface Overview { buckets: Bucket[]; sections: Section[]; total: number }
interface Meta { total: number; chunks: number; per_page: number }
interface BucketIdx { first_page: number; last_page: number; pages: number }
interface PageIndex { pages: { p: number; min: number; max: number; n: number }[]; buckets: Record<string, BucketIdx> }

/* ── constants ── */
const IDX_KEY: Record<string, string> = {
  "<1x": "lt1", "1-2x": "1_2", "2-3x": "2_3", "3-5x": "3_5",
  "5-10x": "5_10", "10-20x": "10_20", "20x+": "20p",
};

const RANGE: Record<string, [string, string]> = {
  "<1x": ["0","1"], "1-2x": ["1","2"], "2-3x": ["2","3"], "3-5x": ["3","5"],
  "5-10x": ["5","10"], "10-20x": ["10","20"], "20x+": ["20","999"],
};

const BAR_COLOR: Record<string, string> = {
  "<1x": "bg-stone-300", "1-2x": "bg-stone-400/60", "2-3x": "bg-indigo-200",
  "3-5x": "bg-indigo-300", "5-10x": "bg-amber-300", "10-20x": "bg-rose-400", "20x+": "bg-rose-600",
};

const BUCKET_HINT: Record<string, string> = {
  "<1x": "Noise or metadata — target shorter than source",
  "1-2x": "Literal, close translation",
  "2-3x": "Standard verse-to-prose translation",
  "3-5x": "Expanded translation with added context",
  "5-10x": "Commentary-like — begins to add interpretive content",
  "10-20x": "Exegetical — significant implicit knowledge recovered",
  "20x+": "Extreme expansion — rare in open data",
};

const FILTERS = [
  { label: "All", min: "0", max: "999", idx: "all", hint: "Show all pairs regardless of expansion" },
  { label: "1–3x", min: "1", max: "3", idx: "1_2", hint: "Standard translation range" },
  { label: "3–5x", min: "3", max: "5", idx: "3_5", hint: "Expanded translation with context" },
  { label: "5–10x", min: "5", max: "10", idx: "5_10", hint: "Commentary-like expansion" },
  { label: "10x+", min: "10", max: "999", idx: "10_20", hint: "Exegetical — adds doctrinal & logical content" },
];

const BROWSE_BY = [
  { label: "All pairs", min: "0", max: "999", idx: "all", desc: "Complete corpus" },
  { label: "Translation", min: "1", max: "3", idx: "1_2", desc: "Standard 1–3x expansion" },
  { label: "Expanded", min: "3", max: "5", idx: "3_5", desc: "Contextual 3–5x expansion" },
  { label: "Commentary", min: "5", max: "10", idx: "5_10", desc: "Interpretive 5–10x" },
  { label: "Exegetical", min: "10", max: "999", idx: "10_20", desc: "10x+ with doctrine & reasoning" },
];

/* ── helpers ── */
function Badge({ ratio }: { ratio: number }) {
  if (ratio >= 10)
    return <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-rose-600/10 text-rose-700 ring-1 ring-rose-600/20">exegetical</span>;
  if (ratio >= 5)
    return <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-amber-500/10 text-amber-700 ring-1 ring-amber-500/20">commentary</span>;
  if (ratio >= 1)
    return <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-stone-500/10 text-stone-600 ring-1 ring-stone-400/30">translation</span>;
  return <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded bg-stone-200 text-stone-400">noise</span>;
}

function Hint({ text }: { text: string }) {
  return (
    <span className="hint cursor-help text-stone-400 hover:text-stone-600 transition" data-hint={text}>
      <svg className="inline w-3.5 h-3.5 -mt-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M12 18h.01" />
      </svg>
    </span>
  );
}

const API_URL = "https://exegen-api.highfunk.uk:8443";

interface LLMResult {
  translation?: string; exegesis?: string;
  translation_ratio?: number; exegesis_ratio?: number;
  info_gain?: { new_terms: number; cross_refs: number; reasoning: number; definitions: number; doctrinal: number; raw_gain: number };
  model?: string; time_s?: number;
}

function ExegesisLab({ initialText }: { initialText?: string }) {
  const [text, setText] = useState(initialText || "");
  const [result, setResult] = useState<LLMResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(!!initialText);
  const [fast, setFast] = useState(true);

  useEffect(() => { if (initialText) { setText(initialText); setOpen(true); } }, [initialText]);

  const [transText, setTransText] = useState("");
  const [exegText, setExegText] = useState("");
  const [phase, setPhase] = useState("");

  async function run() {
    if (!text.trim() || text.length < 5) return;
    setLoading(true); setError(""); setResult(null);
    setTransText(""); setExegText(""); setPhase("translation");

    try {
      const res = await fetch(`${API_URL}/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, mode: "both", fast }),
      });
      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let finalResult: LLMResult = {};

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const evt = JSON.parse(line.slice(6));
            if (evt.phase === "translation" && evt.delta) {
              setTransText(prev => prev + evt.delta);
            } else if (evt.phase === "translation" && evt.status === "done") {
              finalResult.translation_ratio = evt.ratio;
              setPhase("exegesis");
            } else if (evt.phase === "exegesis" && evt.delta) {
              setExegText(prev => prev + evt.delta);
            } else if (evt.phase === "exegesis" && evt.status === "done") {
              finalResult.exegesis_ratio = evt.ratio;
            } else if (evt.phase === "complete") {
              finalResult.info_gain = evt.info_gain;
              finalResult.model = evt.model;
              finalResult.time_s = evt.time_s;
              setResult(finalResult);
              setPhase("");
            }
          } catch {}
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to connect to API");
    }
    setLoading(false);
  }

  return (
    <div className="border border-indigo-200 rounded-lg bg-indigo-50/30 overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between px-4 py-3 hover:bg-indigo-50/50 transition">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold bg-indigo-600 text-white px-2 py-0.5 rounded">LIVE</span>
          <span className="text-sm font-medium text-stone-800">Try Exegesis — Compare translation vs. commentary</span>
        </div>
        <svg className={`w-4 h-4 text-stone-400 transition ${open ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" /></svg>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-indigo-100">
          <p className="text-[11px] text-stone-400 mt-3 mb-2">Enter a Sanskrit verse to see how translation and exegetical commentary differ. Powered by Claude via AWS Bedrock.</p>
          <div className="flex gap-2 mb-3">
            <div className="flex items-center gap-2 self-end mb-0.5">
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" checked={fast} onChange={e => setFast(e.target.checked)} className="rounded border-stone-300" />
                <span className="text-[10px] text-stone-500">Fast <span className="text-stone-400">(Haiku ~15s)</span></span>
              </label>
            </div>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Paste Sanskrit text (Devanagari or IAST)..."
              rows={2}
              className="flex-1 text-sm p-2 border border-stone-200 rounded-md bg-white focus:ring-1 focus:ring-indigo-400 focus:outline-none resize-none sa-text"
            />
            <button
              onClick={run}
              disabled={loading || text.length < 5}
              className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-md hover:bg-indigo-700 disabled:opacity-40 transition shrink-0 self-end"
            >
              {loading ? "Generating..." : "Generate"}
            </button>
          </div>

          {error && <div className="text-xs text-rose-600 mb-2">{error}</div>}

          {/* Streaming output */}
          {(transText || exegText || result) && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-white border border-stone-200 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">Translation</span>
                      {phase === "translation" && <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />}
                    </div>
                    {result?.translation_ratio && <span className="text-xs font-mono font-bold text-stone-500">{result.translation_ratio}x</span>}
                  </div>
                  <div className="text-[13px] leading-relaxed text-stone-600 max-h-64 overflow-y-auto">{transText || "..."}</div>
                </div>
                <div className="bg-white border border-indigo-200 rounded-lg p-3 ring-1 ring-indigo-100">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-semibold uppercase tracking-wide text-indigo-600">Exegetical Commentary</span>
                      {phase === "exegesis" && <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />}
                    </div>
                    {result?.exegesis_ratio && <span className="text-xs font-mono font-bold text-indigo-600">{result.exegesis_ratio}x</span>}
                  </div>
                  <div className="text-[13px] leading-relaxed text-stone-700 max-h-64 overflow-y-auto whitespace-pre-wrap">
                    {exegText || (phase === "translation" ? <span className="text-stone-300">Waiting for translation to complete...</span> : "...")}
                  </div>
                </div>
              </div>

              {/* Info Gain — only after complete */}
              {result?.info_gain && (
                <div className="bg-white border border-stone-200 rounded-lg p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-stone-400">Information Gain</span>
                    <Hint text="Measures how much NEW information the exegesis adds beyond translation: technical terms, cross-references, reasoning steps, definitions, and doctrinal content." />
                  </div>
                  <div className="grid grid-cols-6 gap-2 text-center">
                    {[
                      { label: "New terms", v: result.info_gain.new_terms },
                      { label: "Cross-refs", v: result.info_gain.cross_refs },
                      { label: "Reasoning", v: result.info_gain.reasoning },
                      { label: "Definitions", v: result.info_gain.definitions },
                      { label: "Doctrinal", v: result.info_gain.doctrinal },
                      { label: "Total gain", v: result.info_gain.raw_gain },
                    ].map(m => (
                      <div key={m.label}>
                        <div className="text-lg font-bold tabular-nums text-indigo-700">{m.v}</div>
                        <div className="text-[9px] text-stone-400 uppercase">{m.label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result?.time_s && (
                <div className="text-[10px] text-stone-300 text-right">
                  {result.model} &middot; {result.time_s}s
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── main component ── */
function Browser() {
  const router = useRouter();
  const sp = useSearchParams();

  const [overview, setOverview] = useState<Overview | null>(null);
  const [meta, setMeta] = useState<Meta | null>(null);
  const [pageIndex, setPageIndex] = useState<PageIndex | null>(null);
  const [pairs, setPairs] = useState<Pair[]>([]);
  const [loading, setLoading] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [labText, setLabText] = useState("");

  const view = sp.get("view") || "overview";
  const page = parseInt(sp.get("page") || "0", 10);
  const minR = parseFloat(sp.get("min_r") || "0");
  const maxR = parseFloat(sp.get("max_r") || "999");

  useEffect(() => { setMounted(true); }, []);

  useEffect(() => {
    fetch("/data/overview.json").then(r => r.json()).then(setOverview);
    fetch("/data/meta.json").then(r => r.json()).then(setMeta);
    fetch("/data/page_index.json").then(r => r.json()).then(setPageIndex);
  }, []);

  useEffect(() => {
    if (view !== "browse") return;
    setLoading(true);
    fetch(`/data/page_${page}.json`)
      .then(r => r.json())
      .then(d => { setPairs(d); setLoading(false); })
      .catch(() => setLoading(false));
  }, [page, view]);

  const filtered = useMemo(
    () => pairs.filter(p => p.r >= minR && p.r <= maxR),
    [pairs, minR, maxR],
  );

  const nav = useCallback((params: Record<string, string>) => {
    const next = new URLSearchParams(sp.toString());
    for (const [k, v] of Object.entries(params)) next.set(k, v);
    router.push(`?${next}`);
  }, [sp, router]);

  useEffect(() => {
    if (view !== "browse") return;
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement) return;
      const tp = meta?.chunks || 0;
      if (e.key === "ArrowLeft" && page > 0) nav({ page: String(page - 1) });
      if (e.key === "ArrowRight" && page < tp - 1) nav({ page: String(page + 1) });
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [view, page, meta, nav]);

  const totalPages = meta?.chunks || 0;

  /* ═══════════════════ OVERVIEW ═══════════════════ */
  if (view === "overview") {
    if (!overview) return <div className="flex items-center justify-center h-64 text-stone-400 text-sm">Loading corpus data...</div>;
    const maxN = Math.max(...overview.buckets.map(b => b.n));

    return (
      <div className={`max-w-4xl mx-auto px-6 py-12 transition-opacity duration-500 ${mounted ? "opacity-100" : "opacity-0"}`}>
        {/* Header */}
        <header className="mb-12">
          <p className="text-[11px] font-semibold tracking-[0.2em] uppercase text-indigo-600 mb-3">Research Dataset</p>
          <h1 className="text-3xl font-bold tracking-tight text-stone-900 mb-2">
            Itihasa Sanskrit–English Corpus
          </h1>
          <p className="text-stone-500 text-[15px] leading-relaxed max-w-2xl">
            {overview.total.toLocaleString()} verse-aligned parallel pairs from the Rāmāyaṇa and Mahābhārata.
            Part of research on <strong className="text-stone-700">exegetical generation</strong> — a new NLP task
            for producing expansive commentary from terse source texts.
          </p>
        </header>

        {/* Distribution */}
        <section className="mb-10">
          <div className="flex items-baseline gap-2 mb-1">
            <h2 className="text-sm font-semibold text-stone-900 uppercase tracking-wide">Expansion Ratio Distribution</h2>
            <Hint text="Expansion ratio = |English tokens| ÷ |Sanskrit tokens|. Translation is typically 1–3x. Exegetical commentary is 5–20x — it adds definitions, context, and reasoning not in the source." />
          </div>
          <p className="text-xs text-stone-400 mb-5">Click any bar to browse pairs in that range</p>

          <div className="space-y-1.5">
            {overview.buckets.map((b, i) => {
              const pct = (b.n / maxN) * 100;
              const r = RANGE[b.b];
              const startPage = pageIndex?.buckets[IDX_KEY[b.b]]?.first_page ?? 0;
              return (
                <button
                  key={b.b}
                  onClick={() => nav({ view: "browse", page: String(startPage), min_r: r[0], max_r: r[1] })}
                  className="w-full flex items-center gap-2 group rounded-lg py-1 px-1 -mx-1 hover:bg-stone-100/80 transition text-left"
                  style={{ animationDelay: `${i * 60}ms` }}
                >
                  <span className="w-12 text-xs font-mono text-right text-stone-500 shrink-0">{b.b}</span>
                  <div className="flex-1 h-7 bg-stone-100 rounded overflow-hidden relative">
                    <div
                      className={`bar-fill h-full rounded ${BAR_COLOR[b.b]} group-hover:brightness-95`}
                      style={{ width: `${Math.max(pct, 0.5)}%` }}
                    />
                  </div>
                  <span className="w-20 text-right text-xs tabular-nums text-stone-600 shrink-0">{b.n.toLocaleString()}</span>
                  <span className="hint w-4 shrink-0" data-hint={BUCKET_HINT[b.b]}>
                    <svg className="w-3.5 h-3.5 text-stone-300 group-hover:text-stone-500 transition" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                    </svg>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Splits */}
        <section className="mb-10">
          <h2 className="text-[11px] font-bold tracking-[0.12em] uppercase text-stone-400 mb-4">Dataset Splits</h2>

          {/* Stacked proportion bar */}
          {(() => {
            const total = overview.total;
            const colors = ["bg-stone-700", "bg-indigo-400", "bg-stone-300"];
            return (
              <div className="mb-5">
                <div className="flex h-2 rounded-full overflow-hidden gap-px">
                  {overview.sections.map((s, i) => (
                    <div
                      key={s.name}
                      className={`${colors[i]} transition-all duration-700`}
                      style={{ width: `${(s.count / total) * 100}%` }}
                      title={`${s.name}: ${((s.count / total) * 100).toFixed(1)}%`}
                    />
                  ))}
                </div>
                <div className="flex mt-1.5 gap-px">
                  {overview.sections.map((s, i) => (
                    <div
                      key={s.name}
                      style={{ width: `${(s.count / total) * 100}%` }}
                      className="overflow-hidden"
                    >
                      <span className={`text-[9px] font-semibold uppercase tracking-wide ${i === 1 ? "text-indigo-500" : "text-stone-400"} whitespace-nowrap`}>
                        {((s.count / total) * 100).toFixed(0)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}

          {/* Split rows */}
          <div className="divide-y divide-stone-100">
            {overview.sections.map((s, i) => {
              const pct = ((s.count / overview.total) * 100).toFixed(1);
              const dotColors = ["bg-stone-700", "bg-indigo-400", "bg-stone-300"];
              return (
                <div key={s.name} className="flex items-baseline gap-3 py-2.5">
                  <span className={`w-1.5 h-1.5 rounded-full shrink-0 mt-0.5 self-center ${dotColors[i]}`} />
                  <span className="text-[11px] font-semibold text-stone-500 uppercase tracking-wide w-24 shrink-0">{s.name}</span>
                  <span className="text-sm font-bold tabular-nums text-stone-800 w-20 shrink-0">{s.count.toLocaleString()}</span>
                  <span className="text-[11px] tabular-nums text-stone-400 w-10 shrink-0">{pct}%</span>
                  <span className="text-[11px] text-stone-300 hidden sm:block">avg {s.avg_r}x &middot; range {s.min_r}–{s.max_r}x</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Browse by type */}
        <section className="mb-10">
          <div className="flex items-baseline gap-2 mb-5">
            <h2 className="text-[11px] font-bold tracking-[0.12em] uppercase text-stone-400">Browse by Type</h2>
            <Hint text="Pairs are pre-sorted by expansion ratio (highest first). Each category jumps to the page where that ratio range begins." />
          </div>

          {/* Spectrum track */}
          <div className="relative">
            {/* Axis label */}
            <div className="flex justify-between text-[9px] uppercase tracking-widest text-stone-300 mb-2 font-semibold">
              <span>literal</span>
              <span>expansive</span>
            </div>

            {/* Connected segments */}
            <div className="flex gap-px">
              {BROWSE_BY.map((b, i) => {
                const n = pageIndex?.buckets[b.idx]?.pages ?? 0;
                const start = pageIndex?.buckets[b.idx]?.first_page ?? 0;
                // Spectrum: stone → indigo → amber → rose, widths reflect corpus weight
                const trackColors = [
                  "bg-stone-200 hover:bg-stone-300",
                  "bg-stone-300 hover:bg-stone-400",
                  "bg-indigo-200 hover:bg-indigo-300",
                  "bg-indigo-400 hover:bg-indigo-500",
                  "bg-rose-400 hover:bg-rose-500",
                ];
                const labelColors = ["text-stone-600", "text-stone-700", "text-indigo-700", "text-indigo-800", "text-rose-700"];
                const isFirst = i === 0;
                const isLast = i === BROWSE_BY.length - 1;
                return (
                  <button
                    key={b.label}
                    onClick={() => nav({ view: "browse", page: String(start), min_r: b.min, max_r: b.max })}
                    className={`group flex-1 text-left pt-0 transition-all duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500`}
                  >
                    {/* Track segment */}
                    <div className={`h-1.5 w-full transition-all duration-150 ${trackColors[i]} ${isFirst ? "rounded-l-full" : ""} ${isLast ? "rounded-r-full" : ""}`} />
                    {/* Label block */}
                    <div className="pt-3 pr-1">
                      <div className={`text-[12px] font-semibold leading-tight ${labelColors[i]} group-hover:underline underline-offset-2 decoration-1`}>
                        {b.label}
                      </div>
                      <div className="text-[10px] text-stone-400 mt-0.5 leading-tight">{b.desc}</div>
                      <div className="text-[10px] tabular-nums text-stone-300 mt-1.5">
                        {n > 0 ? `${n} ${n === 1 ? "page" : "pages"}` : "—"}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>

        {/* Try Exegesis */}
        <section className="mb-10">
          <ExegesisLab initialText="" />
        </section>

        {/* About */}
        <section className="border-t border-stone-200 pt-8">
          <div className="grid grid-cols-[1fr_1fr] gap-8 text-xs text-stone-500 leading-relaxed">
            <div>
              <h3 className="font-semibold text-stone-700 mb-1">About this dataset</h3>
              <p>93,030 verse-aligned Sanskrit–English pairs from the <em>Itihasa</em> corpus (Rāmāyaṇa &amp; Mahābhārata). Used as a <strong>translation baseline</strong> for exegetical generation research — demonstrating that standard parallel corpora are translational (1–3x), not exegetical (5–20x).</p>
            </div>
            <div>
              <h3 className="font-semibold text-stone-700 mb-1">What is exegetical generation?</h3>
              <p>An NLP task where the model produces expansive commentary from terse source text, recovering implicit definitions, logical connections, and tradition-specific knowledge. Unlike translation (information-preserving), exegesis is <strong>information-expanding</strong>.</p>
            </div>
          </div>
          <div className="mt-6 pt-4 border-t border-stone-100 flex items-center gap-4 text-[10px] text-stone-400">
            <span>License: Apache-2.0</span>
            <span>&middot;</span>
            <a href="https://github.com/rahular/itihasa" className="hover:text-indigo-600 transition">Source: github.com/rahular/itihasa</a>
            <span>&middot;</span>
            <a href="https://github.com/overthelex/exegeticalgen" className="hover:text-indigo-600 transition">Research: github.com/overthelex/exegeticalgen</a>
          </div>
        </section>
      </div>
    );
  }

  /* ═══════════════════ BROWSE ═══════════════════ */
  return (
    <div className={`max-w-5xl mx-auto px-6 py-6 transition-opacity duration-300 ${mounted ? "opacity-100" : "opacity-0"}`}>
      {/* Nav */}
      <div className="flex items-center gap-4 mb-5">
        <button
          onClick={() => nav({ view: "overview" })}
          className="text-xs text-stone-400 hover:text-indigo-600 transition font-medium flex items-center gap-1"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
          Overview
        </button>
        <div className="h-4 w-px bg-stone-200" />
        <h1 className="text-sm font-semibold text-stone-800">Browse Pairs</h1>
      </div>

      {/* Sticky filter bar */}
      <div className="sticky top-0 z-20 -mx-6 px-6 py-3 bg-[#fafaf9]/95 backdrop-blur-sm border-b border-stone-200/60 mb-4">
        <div className="flex items-center gap-3">
          {/* Filter pills */}
          <div className="flex gap-1">
            {FILTERS.map(f => {
              const active = String(minR) === f.min && String(maxR) === f.max;
              const start = pageIndex?.buckets[f.idx]?.first_page ?? 0;
              return (
                <button
                  key={f.label}
                  onClick={() => nav({ min_r: f.min, max_r: f.max, page: String(start) })}
                  className={`hint text-[11px] px-3 py-1 rounded-full font-medium transition ${
                    active
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-stone-500 hover:text-stone-800 hover:bg-stone-200/60"
                  }`}
                  data-hint={f.hint}
                >
                  {f.label}
                </button>
              );
            })}
          </div>

          {/* Meta */}
          <div className="ml-auto flex items-center gap-3 text-[11px] text-stone-400">
            <span className="tabular-nums">{filtered.length} shown</span>
            <div className="h-3 w-px bg-stone-200" />

            {/* Pagination inline */}
            <div className="flex items-center gap-0.5">
              <button
                disabled={page === 0}
                onClick={() => nav({ page: String(page - 1) })}
                className="w-6 h-6 flex items-center justify-center rounded hover:bg-stone-200/60 disabled:opacity-20 transition"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" /></svg>
              </button>
              <input
                type="number"
                key={page}
                min={1}
                max={totalPages}
                defaultValue={page + 1}
                onKeyDown={e => {
                  if (e.key === "Enter") {
                    const v = parseInt((e.target as HTMLInputElement).value, 10) - 1;
                    if (v >= 0 && v < totalPages) nav({ page: String(v) });
                  }
                }}
                className="w-10 text-center text-[11px] font-medium text-stone-600 bg-stone-100 rounded py-0.5 border-0 focus:ring-1 focus:ring-indigo-400 focus:outline-none"
              />
              <span className="text-stone-300 mx-0.5">/</span>
              <span className="tabular-nums text-stone-400">{totalPages}</span>
              <button
                disabled={page >= totalPages - 1}
                onClick={() => nav({ page: String(page + 1) })}
                className="w-6 h-6 flex items-center justify-center rounded hover:bg-stone-200/60 disabled:opacity-20 transition"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Exegesis Lab */}
      {labText && (
        <div className="mb-4">
          <ExegesisLab initialText={labText} />
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-20 text-stone-400 text-sm gap-2">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
          Loading pairs...
        </div>
      )}

      {/* Empty state */}
      {!loading && filtered.length === 0 && pairs.length > 0 && (
        <div className="text-center py-16 text-stone-400 text-sm">
          No pairs match this filter on the current page.
          <br />
          <span className="text-xs">Try a different ratio range or navigate to another page.</span>
        </div>
      )}

      {/* Cards */}
      <div className="space-y-2">
        {filtered.map((p, i) => (
          <div key={i} className="pair-card bg-white border border-stone-200 rounded-lg overflow-hidden">
            {/* Card header */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-stone-100 bg-stone-50/50">
              <span className="text-[10px] font-mono text-stone-400 tracking-wide">{p.ref}</span>
              <div className="flex items-center gap-2">
                <Badge ratio={p.r} />
                <span className="text-xs font-mono font-bold text-stone-500 tabular-nums">{p.r}x</span>
              </div>
            </div>
            {/* Card body */}
            <div className="grid grid-cols-[1fr_1px_1fr]">
              <div className="p-4">
                <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-stone-300 mb-2">Sanskrit</div>
                <div className="sa-text text-stone-800">{p.sa}</div>
              </div>
              <div className="bg-stone-100" />
              <div className="p-4">
                <div className="text-[10px] font-semibold tracking-[0.15em] uppercase text-stone-300 mb-2">English</div>
                <div className="text-[13px] leading-[1.7] text-stone-600">{p.en}</div>
              </div>
            </div>
            {/* Card footer */}
            <div className="px-4 py-1.5 border-t border-stone-100 bg-stone-50/30 flex justify-end">
              <button
                onClick={() => { setLabText(p.sa); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                className="text-[10px] text-indigo-500 hover:text-indigo-700 font-medium transition"
              >
                Try exegesis on this verse →
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Bottom pagination */}
      {filtered.length > 0 && (
        <div className="flex items-center justify-center gap-1 mt-8 mb-6">
          <button
            disabled={page === 0}
            onClick={() => nav({ page: String(page - 1) })}
            className="px-3 py-1.5 text-xs font-medium text-stone-500 rounded hover:bg-stone-200/60 disabled:opacity-20 transition"
          >
            Prev
          </button>
          {(() => {
            const pages: number[] = [];
            const win = 3;
            let start = Math.max(0, page - win);
            let end = Math.min(totalPages - 1, page + win);
            if (end - start < win * 2) {
              if (start === 0) end = Math.min(totalPages - 1, win * 2);
              else start = Math.max(0, totalPages - 1 - win * 2);
            }
            for (let i = start; i <= end; i++) pages.push(i);
            return pages.map(p => (
              <button
                key={p}
                onClick={() => nav({ page: String(p) })}
                className={`w-7 h-7 text-[11px] rounded transition tabular-nums ${
                  p === page
                    ? "bg-indigo-600 text-white font-bold"
                    : "text-stone-400 hover:bg-stone-200/60 hover:text-stone-700"
                }`}
              >
                {p + 1}
              </button>
            ));
          })()}
          <button
            disabled={page >= totalPages - 1}
            onClick={() => nav({ page: String(page + 1) })}
            className="px-3 py-1.5 text-xs font-medium text-stone-500 rounded hover:bg-stone-200/60 disabled:opacity-20 transition"
          >
            Next
          </button>
        </div>
      )}

      {/* Keyboard hint */}
      <div className="text-center text-[10px] text-stone-300 mb-10">
        Use <kbd className="px-1 py-0.5 bg-stone-100 rounded text-stone-400 font-mono">←</kbd> <kbd className="px-1 py-0.5 bg-stone-100 rounded text-stone-400 font-mono">→</kbd> arrow keys to navigate pages
      </div>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen text-stone-400 text-sm">Loading...</div>
    }>
      <Browser />
    </Suspense>
  );
}
