---
language:
  - sa
  - en
license: cc-by-4.0
task_categories:
  - translation
  - text-generation
tags:
  - sanskrit
  - buddhist
  - exegetical
  - parallel-corpus
  - morphological
  - dictionary
pretty_name: Sanskrit Exegetical Generation Corpus
size_categories:
  - 1M<n<10M
---

# Sanskrit Exegetical Generation Corpus

A comprehensive collection of Sanskrit-English parallel data, monolingual Sanskrit texts, dictionaries, and morphological annotations assembled for research on **exegetical generation** — producing expansive English commentary from terse Sanskrit Buddhist source texts.

## Dataset Summary

| Subset | Records | Description |
|--------|---------|-------------|
| **parallel_pairs** | ~1.3M | Sanskrit-English aligned sentence/verse pairs |
| **texts** | ~8K | Monolingual Sanskrit texts (Buddhist & general) |
| **dictionary** | ~304K | Sanskrit-English dictionary entries (MW + BHS) |
| **morphological** | ~6.5M | Morphological annotations (lemma, POS, features) |

## Sources

| Source | License | Type | Records |
|--------|---------|------|---------|
| MITRA-Parallel | CC-compatible | parallel | 917K |
| AI4Bharat BPCC | CC0 / CC BY 4.0 | parallel | 272K |
| Itihasa | Apache-2.0 | parallel | 93K |
| Polyglotta | Open Access | parallel | 24K+ |
| FLORES-200 | CC BY-SA 4.0 | parallel/benchmark | 2K |
| Samayik | Research use | parallel | 1.7K |
| DCS | CC BY 4.0 | morphological | 5.7M |
| BDRC | Apache 2.0 | morphological | 777K |
| Cologne MW+BHS | CC BY-NC-SA 3.0 | dictionary | 304K |
| SuttaCentral | CC0 | texts | 3.7K |
| DharmaNexus | Varies | texts | 3.2K |
| SARIT | CC BY-SA 4.0 | texts | 87 |
| Pramana-NLP | Research use | texts | 349 |
| GRETIL | CC BY-NC-SA 4.0 | texts | 20 |
| DSBC | Custom NC | texts | 20 |

## Subsets with License Restrictions

The following subsets carry **NonCommercial** restrictions:
- `dictionary/cologne.parquet` — CC BY-NC-SA 3.0
- `texts/gretil.parquet` — CC BY-NC-SA 4.0
- `texts/dsbc.parquet` — Custom NC (permission required from University of the West)

All other subsets are permissively licensed (CC0, CC BY, Apache-2.0, or Open Access).

## File Structure

```
parallel_pairs/
  mitra.parquet         # 917K Buddhist Sa-En pairs
  ai4bharat.parquet     # 272K Wikipedia/web-mined Sa-En
  itihasa.parquet       # 93K Hindu epic verse pairs
  polyglotta.parquet    # 24K+ Buddhist verse-aligned
  flores.parquet        # 2K eval benchmark
  samayik.parquet       # 1.7K contemporary pairs
texts/
  suttacentral.parquet  # 3.7K Buddhist Sanskrit texts
  dharmanexus.parquet   # 3.2K aggregated Buddhist texts
  dcs.parquet           # 605 annotated texts
  pramana.parquet       # 349 epistemology texts
  sarit.parquet         # 87 commentary texts (TEI)
  gretil.parquet        # 20 Buddhist Sanskrit texts [NC]
  dsbc.parquet          # 20 Buddhist canon texts [NC]
dictionary/
  cologne.parquet       # 304K MW + BHS entries [NC]
morphological/
  dcs.parquet           # 5.7M CoNLL-U annotations
  bdrc.parquet          # 777K stemming data
sources.parquet         # Source metadata
```

## Intended Use

This dataset is designed for three-stage training of Sanskrit-to-English exegetical generation models:

1. **Pre-training** (Stage 1): General Sa-En alignment using Itihasa, AI4Bharat, dictionaries
2. **Domain adaptation** (Stage 2): Buddhist-specific data from MITRA, Polyglotta, SuttaCentral
3. **Fine-tuning** (Stage 3): User's private 50K-page exegetical corpus (not included)

## Citation

If you use this dataset, please cite the original sources (see individual source URLs in `sources.parquet`).

## Collection Methodology

Data was collected programmatically using a multi-threaded Docker-based ingestion pipeline with Playwright for JavaScript-rendered sites. See [github.com/overthelex/exegeticalgen](https://github.com/overthelex/exegeticalgen) for the ingestion code.
