# Team Implementation Plan — AI Product Intelligence Pipeline (UniHack)
### Team: Vedanth · Yashas · Tanush

> Merged and improved from `final-plan.md` + `FINAL_IMPLEMENTATION_PLAN.md`, restructured for 3 people working in parallel instead of sequentially. Core thesis unchanged: **PDF/Excel → structured, traceable, validated data → optional commerce enrichment.** Ship the core loop, then enrich.

---

## 0. Role Split (Equal Hours, Not Silos)

Work is balanced so each person carries **roughly the same total hours** across the core build (~5–8 hrs each on the 0–5 core, out of ~19 hrs total), rather than one person owning a disproportionately large or small track. Everyone still reviews everyone's PRs at each checkpoint, and the two highest-risk phases (Phase 1, Phase 5b) get a second person paired in for the first hour to de-risk them.

| Person | Owns | Core Hours (approx) |
|---|---|---|
| **Vedanth** | Phase 1 — PDF extraction (full ownership, highest-risk phase) | ~5 hrs |
| **Yashas** | Phase 2 — Excel extraction, Phase 3 — pipeline/storage, Phase 4 — validation/conflicts | ~6.5 hrs |
| **Tanush** | Phase 5a — FastAPI backend, Phase 5b — Review UI frontend | ~7.5 hrs |

Plus shared time: **Phase 0** (schema + samples + repo skeleton) is done together (~1–1.5 hrs, not counted above), and **Phase 6** (commerce enrichment) is split three ways at the end so nobody is left doing the differentiator solo — see Section 6. Once Phase 6 is included, total hours per person come out close to even.

**Pairing for risk, not just ownership:** even though one person owns each phase, pair up like this to keep hours balanced *and* de-risk the scary phases:
- Vedanth (Phase 1) gets Tanush for the first ~1 hr to sanity-check the extraction prompt/schema fit before Tanush moves to Phase 5a.
- Tanush (Phase 5b, the other high-risk phase) gets Vedanth back for ~1 hr once Phase 1 is stable, to help wire up the PDF source viewer.
- This keeps each person's *net* time close to the target above while ensuring no single point of failure on the two riskiest phases.

---

## 1. Guiding Principles (unchanged, still non-negotiable)

1. **Core-first, polish-last.** Phases 0–5 are mandatory. Commerce enrichment and pixel-level provenance are bonus layers.
2. **One category, one small schema (5–8 fields).**
3. **Traceability is the hero.** Every field: value, confidence, source, verified/unverified.
4. **No hallucinated values.** Missing → `null`. Enrichment → `unverified`.
5. **Time-box every phase** and enforce stop-conditions — don't let one person's slow phase silently eat the team's buffer. If a phase overruns its budget by 50%, the other two stop and help.

---

## 2. Architecture

```
[ Inputs: PDF / Excel / CSV ]
        │
        ▼
STAGE 1  Multi-Modal Ingestion        (Vedanth — PyMuPDF→images, pandas)
        │
        ▼
STAGE 2  Schema Mapping + Provenance  (Vedanth — Claude + instructor + Pydantic)
        │  → value + confidence + source (page/row) + optional bbox
        ▼
STAGE 3  Validation + Conflict Layer  (Yashas — reference rules, duplicate merge)
        │
        ▼
STAGE 4  Storage                      (Yashas — SQLite, unified schema, JSON payload)
        │
        ▼
STAGE 5  Review UI                    (Tanush frontend + Yashas backend — FastAPI + Next.js/Tailwind)
        │
        ▼
STAGE 6  Commerce Enrichment [DIFFERENTIATOR] — split 3 ways, provenance-labelled
        │
        ▼
STAGE 7  RAG Gap-Filling [OPTIONAL, only if 6 is done with time left]
```

---

## 3. Phase-by-Phase Plan with Owners & Time Budget

Total core budget: **~14–22 hrs**. Running in parallel across 3 people (not strictly sequential) should compress wall-clock time significantly if handled right — see the parallelization note after the table.

| Phase | Deliverable | Owner | Supports | Budget | Risk |
|---|---|---|---|---|---|
| **0** | Category + `schema.py` + samples + API key + repo skeleton | **All 3 (30–45 min sync)** | — | 1–1.5 hrs | Low |
| **1** | `extract_pdf(path) -> Product` w/ confidence + source_page | **Vedanth** | Tanush (1st hr pairing) | 4–6 hrs | **High** |
| **2** | `extract_excel(path) -> list[Product]` (hardcoded column map) | **Yashas** | — | 2–3 hrs | Medium |
| **3** | Unified dispatcher + SQLite storage (**CONVERGENCE CHECKPOINT**) | **Yashas** | Vedanth (field name reconciliation) | 1–2 hrs | Low |
| **4** | Validation rules + conflict detection + `flags[]` | **Yashas** | — | 2–3 hrs | Low |
| **5a** | FastAPI backend: `/records`, `/records/{id}`, `/review` | **Tanush** | Yashas (schema contract) | 2–3 hrs | Medium |
| **5b** | Review UI: list, detail, accept/edit/reject, source labels | **Tanush** | Vedanth (2nd-half pairing) | 4–6 hrs | **High** |
| **6** | Commerce enrichment (SEO/copy/compliance tags + provenance) | **Vedanth (SEO+copy agent), Yashas (compliance agent + provenance schema), Tanush (UI badges)** | remainder | Optional |
| **7** | RAG gap-filling → `suggested_unverified` values | **Whoever's free** | — | remainder | Optional |

**Per-person core totals (Phases 1–5, midpoint of ranges):** Vedanth ≈ 5 hrs · Yashas ≈ 6.5 hrs · Tanush ≈ 7.5 hrs. This is close enough to even given estimate ranges (±1–2 hrs each), and Phase 6 below is split evenly to true it up further — whoever finished their core phase(s) fastest starts Phase 6 first and pulls the others in.

### Parallelization note (this is the key improvement over the original single-track plan)
Instead of everyone waiting for Phase 1 to finish before Phase 3 starts, run it like this:

- **Hour 0–1.5:** All three together — Phase 0 (schema, sample data, repo skeleton, agree on API contracts for SQLite row shape and REST endpoints *before* anyone codes against them).
- **Hour 1.5–2.5:** Vedanth starts Phase 1 (PDF), with Tanush pairing for the first hour to stress-test the extraction prompt against the schema. Yashas starts Phase 2 (Excel) solo — it's low-risk and doesn't depend on Phase 1.
- **Hour 2.5 onward:** Tanush peels off to start Phase 5a (FastAPI backend) against the agreed schema, using mock data — doesn't need real extraction output yet. Yashas moves from Phase 2 into Phase 3 (pipeline/storage) once Excel extraction is solid.
- **Convergence checkpoint (~hour 5–6):** Vedanth's real PDF extractor output and Yashas's real Excel extractor output both plug into Yashas's Phase 3 pipeline. This is the true 3-way merge point.
- **Hour 6 onward:** Yashas moves into Phase 4 (validation/conflicts) with real data. Tanush finishes Phase 5a and moves into Phase 5b (frontend), pulling Vedanth in for the second half once Phase 1 is stable and stops needing active attention.
- **Remaining time:** Phase 6, split 3 ways as above — start it as soon as `GET /records/{id}` works, whoever's free first.

This should get the *effective* core-loop demo working well before the 14–22 hr sequential estimate, leaving more real time for Phase 6/7 polish.

---

## 4. Schema (Phase 0 — lock this first, as a team)

```python
class Product(BaseModel):
    product_name: str | None
    size: str | None              # e.g., "2 inch", "DN50"
    material: str | None          # e.g., "Carbon Steel", "316SS"
    pressure_rating: str | None   # e.g., "200 WOG", "PN16"
    thread_type: str | None       # e.g., "NPT", "BSPP", "Metric"
    temperature_range: str | None # e.g., "-20°C to 200°C"
    # provenance fields (auto-populated)
    confidence: dict[str, Literal["high", "medium", "low"]]
    source: dict[str, str]        # "page 2" or "row 5 of valves.xlsx"
    flags: list[str] = []
```

**Category:** Industrial Valves or Pipe Fittings (well-structured tables, clear specs, public catalogs available). Need 3+ public PDFs, 2+ Excel/CSV exports.

**Explicitly cut:** knowledge graphs, arbitrary categories, multi-user auth, real-time collab, custom OCR training, image-only photos.

---

## 5. Phase Details

### Phase 1 — PDF Extraction (Vedanth) ⚠️ Highest risk
- PyMuPDF (fitz) → 150 DPI PNG per page
- Instructor + Anthropic for structured output enforcement
- Prompt must say: "Return null if absent. Include confidence (high/medium/low) and source page per field."
- **Hallucination test:** run against a PDF deliberately missing a field, confirm `null` is returned, not a guess.
- Stretch: bounding box coordinates from the vision model for pixel-level provenance (defer to Phase 6 if it's slow).

### Phase 2 — Excel/CSV Extraction (Yashas)
- Start with a hardcoded column map (fast, reliable):
```python
COLUMN_MAP = {
    "Size (in)": "size",
    "Material": "material",
    "Pressure (WOG)": "pressure_rating",
    "Thread": "thread_type",
    "Temp Range": "temperature_range",
}
```
- Normalize units (in→mm, °F→°C) in plain Python — never ask the LLM to do unit math.
- Only upgrade to LLM-assisted column mapping if time permits and the hardcoded map is fragile across files.

### Phase 3 — Unified Pipeline + SQLite (Yashas) ✅ Checkpoint
```python
def extract(path: Path) -> Product | list[Product]:
    if path.suffix == ".pdf": return extract_pdf(path)
    if path.suffix in (".xlsx", ".csv"): return extract_excel(path)
```
- One SQLite row per product, JSON blob for full record + provenance.
- Reconcile field names now: PDF's `source_page` and Excel's `source_row` → unify to a single `source: str`.
- **Demoable at this point:** `python -m pipeline /data/samples/` → query SQLite → consistent records from both sources.

### Phase 4 — Validation + Conflict Detection (Yashas)
Reference data (`reference_data.json`):
```json
{
  "valid_materials": ["Carbon Steel", "316SS", "304SS", "Brass", "Bronze"],
  "valid_threads": ["NPT", "BSPP", "Metric", "UNF"],
  "pressure_max_wog": 6000,
  "size_range_mm": [6, 600]
}
```
- Range checks (pressure, size), enum checks (material, thread).
- **Conflict detection:** same `product_name` from PDF + Excel with differing values → keep both, add a `CONFLICT:` flag. Never silently merge.
- Keep it to ~10 hardcoded checks — no generic rules DSL, this is a hackathon.

### Phase 5 — Review UI (Tanush, backend then frontend, with Vedanth pairing on frontend) ⚠️ Second highest risk
**Backend (FastAPI, Tanush):**
- `GET /records` — list with flag counts
- `GET /records/{id}` — full field breakdown: value, confidence, source
- `POST /records/{id}/review` — accept/edit/reject per field

**Frontend (Next.js + Tailwind, Tanush, joined by Vedanth once Phase 1 is stable):**
| View | Key UX |
|---|---|
| List | Table: Product \| Flags \| Source Count \| Actions |
| Detail | Field cards: Value \| Confidence badge \| Source link \| [Accept] [Edit] [Reject] |
| PDF Source | `react-pdf` render page, highlight relevant text region (stretch: bounding box) |
| Excel Source | Show row data in a small table |

**Scope cut if behind:** skip bounding-box highlighting; "Source: Page 2" text label is enough for MVP.

### Phase 6 — Commerce Enrichment (all three, split by agent) 🚀
Only starts once `GET /records/{id}` works end-to-end. Split so it lands fast:

- **Vedanth** — SEO Agent (`seo_title`, `meta_description`, `url_slug`) + Copywriting Agent (`marketing_bullets`, `long_description`)
- **Yashas** — Compliance Agent (`inferred_tags`, e.g. "RoHS Compliant", "Requires Thermal PPE", "Corrosion Risk") + the provenance schema for enrichment fields
- **Tanush** — UI: yellow "AI-Generated" badge + reasoning-on-hover for every enrichment field

Provenance shape for enrichment fields:
```json
"inferred_tags": {
  "value": "Corrosion Risk",
  "source_type": "ai_enrichment",
  "explanation": "Carbon steel lacks chromium oxide layer; flagged for non-treated water/oil apps."
}
```

### Phase 7 — RAG Gap-Filling (optional, whoever's free)
- Only if Phase 6 is fully done and 3–4+ hrs remain.
- Never auto-fill silently — always mark `suggested_unverified` and show a distinct "guess" badge (yellow) in the UI.
- A broken RAG feature hurts the demo more than a missing one — cut it without hesitation if it's flaky near the deadline.

---

## 6. Demo Strategy (3 moves, one per person if possible)

1. **Messy-input → clean output** (Vedanth narrates): real PDF + real Excel through the pipeline end-to-end, converging into identical structured records.
2. **Traceability** (Tanush drives the UI): hover any field → confidence + source page/row. If bbox landed, show the cropped region the AI read from.
3. **Validation in action** (Yashas narrates): feed an out-of-range value and a conflicting PDF-vs-Excel value → both flagged, both sources preserved, nothing silently merged.

### Demo script
1. Upload a messy industrial valve catalog PDF + Excel spec sheet
2. Click "Process" → briefly show terminal logs
3. Review Dashboard → 2 records, one with ⚠️ 2 flags (conflict + range)
4. Click Record A → field-by-field: value, confidence, "Source: Page 3" link
5. Click Source Link → PDF opens to exact page, relevant text highlighted
6. Edit the wrong field → Accept → flag count drops
7. *(If Phase 6 done)* Toggle "Show Commerce Assets" → SEO title, marketing bullets, compliance tags with AI reasoning on hover
8. Export → download commerce-ready JSON

---

## 7. Key Risk Mitigations

| Risk | Mitigation | Owner |
|---|---|---|
| Phase 1 hallucination | Test null-on-absence explicitly; keep schema small; Instructor retry | Vedanth |
| Context bloat on multi-page PDFs | Process page-by-page, not whole doc at once | Vedanth |
| Schema drift between PDF/Excel field names | Reconcile at Phase 3, before UI depends on them | Yashas |
| Bounding-box time sink | Ship page-level sourcing first; bbox only as Phase 6 stretch | Vedanth + Tanush |
| Phase 5 UI time sink | List view first, detail view second, bbox highlighting last/skip | Tanush |
| One track finishes early / late vs. the others | Whoever finishes their phase first joins the next-busiest person instead of starting Phase 6 alone, to keep hours roughly even | All 3 |
| RAG flop | Never auto-fill; always `suggested_unverified` + yellow badge; cut entirely if flaky | Whoever owns Phase 7 |
| Scope creep (Phase 6 starting early) | **Hard rule:** Phase 6 does not start until `GET /records/{id}` works end-to-end | All 3 |
| One person's phase overruns and blocks the team | 50%-over-budget rule: other two stop and jump in to help | All 3 |

---

## 8. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | Python | Fast prototyping, rich ecosystem |
| Vision LLM | Claude (via Instructor) | Best structured output + vision |
| Validation | Pydantic | Schema enforcement, type safety |
| Database | SQLite | Zero config, file-based, portable |
| Backend API | FastAPI | Async, auto-docs, fast |
| Frontend | Next.js 14 + Tailwind | React, great DX, easy deployment |
| PDF Render | react-pdf | Client-side PDF display |
| Embeddings (Phase 7) | Voyage AI or OpenAI | Only if RAG attempted |

---

## 9. Repo Structure

```
/data/samples/           # 3 PDFs, 2 Excel files
/extraction/
  pdf_extractor.py       # Phase 1 — Vedanth
  excel_extractor.py     # Phase 2 — Yashas
  pipeline.py            # Phase 3 dispatcher — Yashas
/validation/
  rules.py               # Phase 4 — Yashas
  conflict.py            # Phase 4 — Yashas
/api/
  main.py                # FastAPI — Tanush
  models.py              # Pydantic request/response models — Tanush
/frontend/
  app/                   # Next.js 14 app router — Tanush (+ Vedanth on pairing)
  components/            # RecordList, RecordDetail, FieldCard, PdfViewer — Tanush
/schema.py                # Single source of truth: Product model — agreed by all in Phase 0
/reference_data.json      # Validation enums/ranges — Yashas
requirements.txt
.env.example
README.md
```

---

## 10. Definition of Done

**Core demo:**
- [ ] Schema defined, samples collected, API key working (all)
- [ ] PDF → Product extraction correct on all 3 sample PDFs, nulls where appropriate (Vedanth)
- [ ] Excel → Product extraction correct on all 2 sample files (Yashas)
- [ ] Unified pipeline → SQLite with consistent shape (Yashas)
- [ ] Validation flags on out-of-range / enum violations (Yashas)
- [ ] Conflict detection flags same product from two sources (Yashas)
- [ ] Review UI: list → detail → source link → edit → accept works (Tanush, Vedanth pairing)
- [ ] Export produces clean JSON/CSV (Tanush)

**Stretch:**
- [ ] Commerce assets generated for at least one product (Vedanth + Yashas)
- [ ] Enrichment provenance shown in UI — yellow badge + reasoning (Tanush)
- [ ] Pixel-level bounding box highlight on PDF, if vision model supports it (Vedanth + Tanush)

---

## 11. Final Recommendation

Run **Phase 0 together, then the rest in parallel** across Vedanth (Phase 1), Yashas (Phases 2–4), and Tanush (Phase 5) rather than strictly sequentially — this keeps hours roughly even (~5–7.5 hrs each on the core) instead of stacking most of the work on one or two people, and it should buy back several hours for Phase 6. Use the pairing moments in Section 0 to de-risk Phase 1 and Phase 5b without unbalancing anyone's total load.

**Do not start Phase 6 until Phase 5's detail view works end-to-end.** The traceability + conflict/flag + human review loop is what judges remember — it proves "product intelligence," not just extraction. Phase 6 is the differentiator that wins if delivered, but a broken Phase 6 loses more points than a missing one gains.

**Ship the core loop. Then enrich.**
