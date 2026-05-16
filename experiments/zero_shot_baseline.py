"""Zero-shot exegetical generation baseline using Claude API.
Tests: can an LLM produce exegetical commentary from Sanskrit source text?"""

import json
import os
import time
import psycopg2
import anthropic

DB = os.environ.get("DATABASE_URL", "postgresql://sanskrit:sanskrit@localhost:5434/sanskrit")
MODEL = os.environ.get("MODEL", "claude-sonnet-4-6")

SYSTEM_PROMPT = """You are a scholar of Sanskrit Buddhist philosophy with deep expertise in
Madhyamaka, Yogācāra, Abhidharma, and Prajñāpāramitā traditions.

You will be given a terse Sanskrit verse or passage from a Buddhist text.
Your task is to produce an EXEGETICAL COMMENTARY — not a translation.

An exegetical commentary:
- Unpacks implicit philosophical context that the original assumes the reader knows
- Defines technical terms (e.g., dharma, śūnyatā, prajñā, upāya)
- Restores logical connections that are elided in the compressed Sanskrit
- Explains the doctrinal significance within the relevant tradition
- Draws connections to related concepts and texts
- Is typically 5-20x longer than the source text

Do NOT just translate. EXPLAIN and UNPACK the meaning."""

TRANSLATION_PROMPT = """Translate the following Sanskrit Buddhist text into English.
Produce a faithful, literal translation only. Do not add commentary or explanation."""


def get_test_verses(n=10):
    """Get diverse Sanskrit verses from DB for testing."""
    conn = psycopg2.connect(DB)
    cur = conn.cursor()

    verses = []

    # Clean Itihasa verses (known good Sa-En pairs for comparison)
    cur.execute("""
        SELECT source_text, target_text, expansion_ratio, text_ref
        FROM parallel_pairs p JOIN sources s ON p.source_id = s.id
        WHERE s.name = 'itihasa'
          AND length(source_text) BETWEEN 50 AND 300
          AND length(target_text) BETWEEN 30 AND 500
          AND expansion_ratio BETWEEN 1.5 AND 5
        ORDER BY random() LIMIT %s
    """, (n // 2,))
    for src, tgt, ratio, ref in cur.fetchall():
        verses.append({
            "source": src, "reference_translation": tgt,
            "ref_ratio": float(ratio), "origin": "itihasa", "ref": ref,
        })

    # Buddhist texts from GRETIL/SuttaCentral (monolingual, no reference)
    cur.execute("""
        SELECT left(content, 300), title
        FROM texts t JOIN sources s ON t.source_id = s.id
        WHERE s.name IN ('gretil', 'suttacentral')
          AND tradition = 'buddhist'
          AND length(content) > 100
        ORDER BY random() LIMIT %s
    """, (n // 2,))
    for content, title in cur.fetchall():
        lines = [l.strip() for l in content.split('\n') if l.strip() and len(l.strip()) > 30]
        if lines:
            verse = lines[0][:300]
            verses.append({
                "source": verse, "reference_translation": None,
                "ref_ratio": None, "origin": "buddhist_text", "ref": title,
            })

    cur.close()
    conn.close()
    return verses


def generate(client, source_text, mode="exegesis"):
    prompt = SYSTEM_PROMPT if mode == "exegesis" else TRANSLATION_PROMPT
    msg = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=prompt,
        messages=[{"role": "user", "content": f"Sanskrit text:\n\n{source_text}"}],
    )
    return msg.content[0].text


def analyze_output(source, output):
    src_words = len(source.split())
    out_words = len(output.split())
    ratio = out_words / max(src_words, 1)
    return {
        "src_words": src_words,
        "out_words": out_words,
        "expansion_ratio": round(ratio, 2),
        "out_length": len(output),
    }


def run():
    client = anthropic.AnthropicBedrock(aws_region="eu-central-1")
    verses = get_test_verses(10)
    print(f"Testing {len(verses)} verses\n")

    results = []
    for i, v in enumerate(verses):
        print(f"--- Verse {i+1}/{len(verses)} [{v['origin']}] ---")
        print(f"Source ({len(v['source'])} chars): {v['source'][:100]}...")
        if v["reference_translation"]:
            print(f"Ref translation (ratio {v['ref_ratio']}x): {v['reference_translation'][:100]}...")

        # Generate exegetical commentary
        print("\nGenerating exegesis...")
        t0 = time.time()
        exegesis = generate(client, v["source"], mode="exegesis")
        exeg_time = time.time() - t0
        exeg_stats = analyze_output(v["source"], exegesis)

        # Generate translation for comparison
        print("Generating translation...")
        translation = generate(client, v["source"], mode="translation")
        trans_stats = analyze_output(v["source"], translation)

        print(f"\nTranslation ({trans_stats['expansion_ratio']}x): {translation[:150]}...")
        print(f"Exegesis ({exeg_stats['expansion_ratio']}x): {exegesis[:150]}...")

        result = {
            "source": v["source"],
            "origin": v["origin"],
            "ref": v["ref"],
            "reference_translation": v["reference_translation"],
            "ref_expansion_ratio": v["ref_ratio"],
            "generated_translation": translation,
            "translation_ratio": trans_stats["expansion_ratio"],
            "generated_exegesis": exegesis,
            "exegesis_ratio": exeg_stats["expansion_ratio"],
            "exeg_time_s": round(exeg_time, 1),
        }
        results.append(result)
        print(f"  Translation ratio: {trans_stats['expansion_ratio']}x")
        print(f"  Exegesis ratio: {exeg_stats['expansion_ratio']}x")
        print(f"  Ratio difference: {exeg_stats['expansion_ratio'] - trans_stats['expansion_ratio']:.1f}x\n")
        time.sleep(1)

    # Summary
    print("=" * 70)
    print("SUMMARY: Zero-Shot Baseline")
    print("=" * 70)
    trans_ratios = [r["translation_ratio"] for r in results]
    exeg_ratios = [r["exegesis_ratio"] for r in results]
    ref_ratios = [r["ref_expansion_ratio"] for r in results if r["ref_expansion_ratio"]]

    print(f"\n  {'Metric':<30} {'Translation':>12} {'Exegesis':>12} {'Ref (human)':>12}")
    print(f"  {'-'*66}")
    print(f"  {'Avg expansion ratio':<30} {sum(trans_ratios)/len(trans_ratios):>12.2f} {sum(exeg_ratios)/len(exeg_ratios):>12.2f} {sum(ref_ratios)/len(ref_ratios) if ref_ratios else 'N/A':>12}")
    print(f"  {'Min ratio':<30} {min(trans_ratios):>12.2f} {min(exeg_ratios):>12.2f}")
    print(f"  {'Max ratio':<30} {max(trans_ratios):>12.2f} {max(exeg_ratios):>12.2f}")

    outfile = f"experiments/zero_shot_{MODEL.replace('.', '_').replace(':', '_')}.json"
    with open(outfile, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nFull results saved to {outfile}")


if __name__ == "__main__":
    run()
