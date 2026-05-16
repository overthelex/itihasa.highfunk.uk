# Exegetical Generation: Task Formalization

## 1. Task Definition

**Exegetical generation** is the task of producing an expansive target-language text $e$ from a tersely encoded source text $s$ such that $e$ recovers the implicit semantic content that $s$ presupposes but does not express.

Formally:

$$f: s \rightarrow e \quad \text{where} \quad |e| \gg |s| \quad \text{and} \quad \mathcal{I}(e) \supset \mathcal{I}(s)$$

where $\mathcal{I}(\cdot)$ denotes the information content of a text.

### Input
A source text $s$ in language $L_s$ (e.g., Sanskrit) characterized by:
- **High information density**: maximal semantic content per surface token
- **Convention-driven compression**: ellipsis of shared knowledge assumed by the tradition
- **Compositional opacity**: compound words (samāsa), sandhi, and unexpanded technical terms

### Output
An exegetical text $e$ in language $L_t$ (e.g., English) that:
1. **Preserves** all propositional content of $s$ (faithfulness)
2. **Recovers** implicit context, definitions, and logical connections elided in $s$ (completeness)
3. **Maintains** doctrinal coherence with the source tradition (tradition-coherence)
4. Exhibits an **expansion ratio** $R(s, e) = |e|_{tokens} / |s|_{tokens} \in [5, 20]$


## 2. Distinction from Related Tasks

| Property | Translation | Summarization | Exegetical Generation |
|----------|------------|---------------|----------------------|
| Direction | $L_s \rightarrow L_t$ | $L \rightarrow L$ | $L_s \rightarrow L_t$ |
| Length relation | $|e| \approx |s|$ | $|e| < |s|$ | $|e| \gg |s|$ |
| Information | $\mathcal{I}(e) \approx \mathcal{I}(s)$ | $\mathcal{I}(e) \subset \mathcal{I}(s)$ | $\mathcal{I}(e) \supset \mathcal{I}(s)$ |
| Expansion ratio | 1–3× | 0.1–0.5× | 5–20× |
| Knowledge required | Bilingual competence | Salience judgment | Domain expertise + abductive reasoning |
| Reasoning type | Transductive | Abstractive | Abductive |

**Key distinction**: translation is *information-preserving*, summarization is *information-reducing*, exegetical generation is *information-expanding*. The additional information in $e$ is not invented — it is *recovered* from the tradition's shared knowledge base $\mathcal{K}$ that $s$ implicitly references.

$$\mathcal{I}(e) = \mathcal{I}(s) \cup \mathcal{R}(s, \mathcal{K})$$

where $\mathcal{R}(s, \mathcal{K})$ is the set of recoverable implicit content given source $s$ and knowledge base $\mathcal{K}$.


## 3. Information Density

We define **information density** of a text as:

$$D(s) = \frac{|\mathcal{I}(s)|}{|s|_{tokens}}$$

Sanskrit Buddhist source texts exhibit extreme information density because:

1. **Morphological compression**: Sandhi merges word boundaries; compounds (samāsa) pack multiple concepts into single orthographic units. A 4-word Sanskrit compound may require a 15-word English phrase.

2. **Ellipsis by convention**: Sūtra style deliberately omits what the tradition considers shared knowledge. E.g., "śūnyatā" (emptiness) in a Madhyamaka text presupposes the entire apparatus of two truths, dependent origination, and the negation of svabhāva — none of which is stated.

3. **Technical term density**: Each term carries a tradition-specific semantic payload far exceeding its dictionary definition. "Prajñāpāramitā" is not just "perfection of wisdom" but indexes an entire corpus, practice tradition, and philosophical position.

**Empirical evidence** (from our corpus analysis of 1.33M open Sa-En pairs):
- Translation corpora average $R = 1\text{–}3\times$ expansion
- The same source texts prompted for exegesis yield $R = 45\text{–}52\times$ (zero-shot LLM baseline)
- Only 1.4% of open parallel data exhibits $R \geq 5\times$
- 98.6% of open data is translation, not exegesis → confirming the task is underserved


## 4. Taxonomy of Exegetical Operations

An exegetical text $e$ performs a combination of the following operations on source $s$:

### O1: Term Definition Unpacking
Expanding a technical term into its full semantic content.

> **Source**: "bodhicittam utpādayati"
> **Translation**: "generates the mind of awakening"
> **Exegesis**: "generates bodhicitta — the aspiration to attain complete and perfect buddhahood for the benefit of all sentient beings, which constitutes the entry point to the Mahāyāna path and is cultivated through both the aspiration (praṇidhāna) and engagement (prasthāna) aspects..."

Measured by: overlap with domain dictionary definitions (BHS, MW).

### O2: Implicit Context Restoration
Recovering the unstated philosophical or narrative background.

> **Source**: "pratītyasamutpādād"
> **Translation**: "from dependent origination"
> **Exegesis**: "because all phenomena arise in dependence upon causes and conditions — as the Buddha taught in the rice seedling sūtra (Śālistamba-sūtra), where he demonstrated that nothing arises from a single cause, from no cause, from a creator deity, or from itself..."

Measured by: count of referenced texts, doctrines, and premises not in source.

### O3: Logical Connection Bridging
Making explicit the inferential steps that the source leaves implicit.

> **Source**: "tasmāt śūnyatā eva rūpam" (therefore emptiness itself is form)
> **Translation**: "therefore emptiness is form"
> **Exegesis**: "the argument proceeds as follows: if form is empty of inherent existence (as established in the preceding verse), then emptiness cannot be a separate entity apart from form — for that would make emptiness itself an inherently existent thing, contradicting the very principle it establishes. Therefore emptiness and form are not two different things but..."

Measured by: count of explicit inferential connectives (because, therefore, it follows) absent in source.

### O4: Doctrinal Elaboration
Situating the passage within the broader doctrinal framework.

> **Source**: "pañcaskandha" (five aggregates)
> **Translation**: "five aggregates"
> **Exegesis**: "the five aggregates (skandha) — form (rūpa), feeling (vedanā), perception (saṃjñā), volitional formations (saṃskāra), and consciousness (vijñāna) — which together constitute the Buddhist analysis of personal experience. The Abhidharma tradition further subdivides these into 75 (Sarvāstivāda) or 82 (Yogācāra) dharmas..."

Measured by: depth of taxonomic/doctrinal expansion.

### O5: Cross-Reference Linking
Connecting the passage to related texts, commentaries, and traditions.

Measured by: count of explicit cross-references not present in source.


## 5. Formal Metrics

### 5.1 Expansion Ratio (R)
$$R(s, e) = \frac{|e|_{tokens}}{|s|_{tokens}}$$

Baseline: translation $R \in [1, 3]$; exegesis $R \in [5, 20]$.

### 5.2 Faithfulness (F)
Does $e$ preserve all propositional content of $s$?

$$F(s, e) = \frac{|\mathcal{P}(s) \cap \mathcal{P}(e)|}{|\mathcal{P}(s)|}$$

where $\mathcal{P}(\cdot)$ is the set of propositions. $F = 1$ means no source content is lost or contradicted.

### 5.3 Information Gain (G)
How much implicit content does $e$ recover?

$$G(s, e) = |\mathcal{I}(e) \setminus \mathcal{I}(s)|$$

Operationalized as: count of (definitions + premises + cross-references + doctrinal facts) in $e$ not present in $s$.

### 5.4 Completeness (C)
What fraction of the recoverable implicit content is actually recovered?

$$C(s, e, \mathcal{K}) = \frac{|\mathcal{R}(s, \mathcal{K}) \cap \mathcal{I}(e)|}{|\mathcal{R}(s, \mathcal{K})|}$$

Requires a gold-standard exegetical reference. The private 50K corpus provides this.

### 5.5 Tradition-Coherence (T)
Is the generated commentary doctrinally accurate?

Binary expert judgment per exegetical claim. Aggregate: fraction of claims judged as tradition-coherent by domain expert.

### 5.6 Composite ExeScore

$$\text{ExeScore}(s, e) = F^{\alpha} \cdot G^{\beta} \cdot C^{\gamma} \cdot T^{\delta}$$

where $\alpha, \beta, \gamma, \delta$ are weights determined by the relative importance of each dimension. Proposed default: $\alpha = \gamma = \delta = 1, \beta = 0.5$ (faithfulness, completeness, and tradition-coherence are hard constraints; information gain is a soft objective).


## 6. Empirical Evidence for the Task

### 6.1 The Translation-Exegesis Gap

Analysis of 1.33M open Sanskrit-English parallel pairs from 17 sources:

| Expansion bucket | Pairs | % of total |
|------------------|-------|-----------|
| < 1× (noise) | 1,066,958 | 79.3% |
| 1–3× (translation) | 215,637 | 16.0% |
| 3–5× (expanded translation) | 40,183 | 3.0% |
| 5–10× (commentary-like) | 14,031 | 1.0% |
| 10–20× (exegetical) | 4,704 | 0.4% |
| 20×+ (extreme) | 3,289 | 0.2% |

**Finding**: 98.6% of open parallel data has $R < 5$. Only 1.4% exhibits exegetical-range expansion, and this subset (from Bibliotheca Polyglotta) is multilingual noise (Tibetan, French mixed in), not clean Sa→En exegesis.

**Conclusion**: No large-scale Sa→En exegetical parallel corpus exists in open data. The task is not only underserved — it is *unserved*.

### 6.2 Zero-Shot LLM Baseline

Claude Sonnet 4.6 and Haiku 4.5 tested on Sanskrit Buddhist verses:

| Model | Translation R | Exegesis R | Cost (per M tokens) |
|-------|--------------|------------|---------------------|
| Sonnet 4.6 | 2.4× | 51.5× | $3 / $15 |
| Haiku 4.5 | 4.2× | 45.6× | $0.80 / $4 |

**Finding**: LLMs *can* produce exegetical-range expansion when explicitly prompted. The same model produces translation-range output (2–4×) with a translation prompt. This confirms:
1. The task is *distinct* from translation — different prompts yield categorically different outputs
2. LLMs have *some* relevant knowledge but quality is unvalidated
3. A supervised model trained on genuine exegetical pairs could outperform zero-shot

### 6.3 Dictionary as Micro-Exegesis

Buddhist Hybrid Sanskrit dictionary (Edgerton): 17,839 entries with average character expansion of 33×. Each entry is a micro-exegetical act: a terse headword → multi-sentence definition unpacking its full semantic payload. This validates O1 (Term Definition Unpacking) as a core exegetical operation.


## 7. Research Questions

1. **RQ1**: Can exegetical generation be formalized as a learnable task with measurable metrics?
2. **RQ2**: Does a supervised model trained on exegetical pairs outperform zero-shot LLM baselines?
3. **RQ3**: Which exegetical operations (O1–O5) are hardest for current models?
4. **RQ4**: Does the task transfer across traditions (Buddhist → Talmudic, Scholastic)?
