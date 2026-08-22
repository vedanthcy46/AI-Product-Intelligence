"use strict";

/* UniHack frontend — reads the internal Product JSON produced by the
 * pipeline (frontend/data/products.json) and real metrics (metrics.json).
 * No hardcoded demonstration numbers anywhere. */

const DATA_URL = "data/products.json";
const METRICS_URL = "data/metrics.json";
const REVIEW_KEY = "unihack.reviews";

/* ── Backend connection ──────────────────────────────────── */
/* Environment-aware routing:
 *   - DEVELOPMENT  (page opened from the local Flask server: localhost /
 *     127.0.0.1)            -> ALWAYS the local server, relative paths
 *   - PRODUCTION   (page hosted anywhere else: Render itself, GitHub Pages,
 *     file:// preview)      -> window.UNIHACK_BACKEND_URL from index.html
 * The deployed backend must allow CORS (it does — see server.py). */
const CONFIGURED_BACKEND = String(window.UNIHACK_BACKEND_URL || "").replace(/\/+$/, "");
const DEV_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function backendBase() {
  const host = String(location.hostname || "").toLowerCase();
  if (!host || location.protocol === "file:") return CONFIGURED_BACKEND;
  if (DEV_HOSTNAMES.has(host)) return "";                 // dev -> local API
  try {
    if (CONFIGURED_BACKEND && new URL(CONFIGURED_BACKEND).origin === location.origin) {
      return "";                                          // prod ON the backend itself
    }
  } catch (e) { /* malformed config -> fall through */ }
  return CONFIGURED_BACKEND;
}

const api = (path) => backendBase() + path;

const state = {
  products: [],
  metrics: null,
  reviews: loadReviews(),
  filter: "",
  detailId: null,
  showRejected: false,
};

function loadReviews() {
  try {
    return JSON.parse(localStorage.getItem(REVIEW_KEY) || "{}");
  } catch (e) {
    return {};
  }
}

function saveReviews() {
  localStorage.setItem(REVIEW_KEY, JSON.stringify(state.reviews));
}

/* ── Helpers ─────────────────────────────────────────────── */
const $ = (sel) => document.querySelector(sel);
const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

function pct(v, digits = 1) {
  if (v == null) return "n/a";
  return (v * 100).toFixed(digits) + "%";
}

function confidencePill(product) {
  const c = product.confidence;
  if (!c) return '<span class="pill medium">n/a</span>';
  const cls = String(c.status || "MEDIUM").toLowerCase();
  return `<span class="pill ${cls}">${esc(c.status)}</span>`;
}

/* ── Human verdicts (accept / reject / edit) ─────────────── */
function decisionOf(p) {
  return (state.reviews[productKey(p)] || p.review || {}).decision || null;
}
function isApproved(p) { return decisionOf(p) === "accept"; }
function isRejected(p) { return decisionOf(p) === "reject"; }
/* Records that still count as catalogue output — rejected rows are out. */
function activeProducts() { return state.products.filter((p) => !isRejected(p)); }
function verdictBadge(p) {
  if (isApproved(p)) return ' <span class="flag-ok">✓ approved</span>';
  if (isRejected(p)) return ' <span class="flag-bad">✗ rejected</span>';
  return "";
}
function verdictBanner(p) {
  const r = state.reviews[productKey(p)] || p.review;
  if (!r || !r.decision) return "";
  const when = r.at ? ` on ${esc(String(r.at).slice(0, 10))}` : "";
  if (r.decision === "reject")
    return `<div class="banner-bad">✗ Rejected by human review${when} — excluded from the catalogue and CSV exports.</div>`;
  if (r.decision === "accept")
    return `<div class="banner-ok">✓ Approved by human review${when} — marked as commerce-ready.</div>`;
  return `<div class="banner-warn">✎ Edited${when} — corrections saved, still awaiting a final Accept/Reject decision.</div>`;
}

function isWebSource(src) {
  return /^https?:\/\//i.test(String(src || ""));
}

function attrStatus(attr) {
  if (attr.needs_review) return '<span class="flag-warn">⚠ Needs Review</span>';
  if (attr.value == null) return '<span class="flag-ok">— empty (OK)</span>';
  const src = String(attr.source || "");
  const grounded = isWebSource(src)
    ? '<span class="flag-ok">✓ grounded</span>'
    : src ? '<span class="flag-warn">desc only</span>'
          : '<span class="flag-warn">no source</span>';
  const lov = attr.lov_matched ? '<span class="flag-ok">✓ LOV</span>' : '<span class="flag-bad">✗ LOV</span>';
  return `${grounded} ${lov}`;
}

/* ── Data loading ────────────────────────────────────────── */
async function loadData() {
  const [pRes, mRes] = await Promise.all([fetch(api(DATA_URL)), fetch(api(METRICS_URL))]);
  if (!pRes.ok) throw new Error("products.json missing");
  state.products = await pRes.json();
  state.metrics = mRes.ok ? await mRes.json() : null;
  // Seed server-persisted reviews (written by POST /api/review) into local
  // state — local decisions always win over the server snapshot.
  for (const p of state.products) {
    const k = productKey(p);
    if (p.review && p.review.decision && !state.reviews[k]) state.reviews[k] = p.review;
  }
}

/* ── Router ──────────────────────────────────────────────── */
function currentView() {
  const hash = location.hash.replace("#", "");
  if (hash.startsWith("product/")) return "detail";
  return ["dashboard", "upload", "products", "rag", "review", "metrics"].includes(hash) ? hash : "dashboard";
}

function route() {
  const view = currentView();
  document.querySelectorAll("#nav a").forEach((a) => {
    a.classList.toggle("active", a.dataset.view === view);
  });
  if (view === "detail") {
    state.detailId = decodeURIComponent(location.hash.replace("#product/", ""));
    renderDetail();
  } else {
    render(view);
  }
}

/* ── Dashboard (V8) ──────────────────────────────────────── */
function renderDashboard() {
  const m = state.metrics || {};
  const active = activeProducts();
  const n = active.length;
  const rejected = state.products.length - n;
  const approved = state.products.filter(isApproved).length;
  const needsReview = countNeedsReview();
  const high = m.high_confidence != null ? m.high_confidence : countHigh();
  const valFail = m.validation_failures != null ? m.validation_failures : 0;
  const ground = m.grounding_rate != null ? m.grounding_rate : avgGrounding();

  $("#view").innerHTML = `
    <div class="section">
      <h2>Processing Overview</h2>
      <p class="sub">Live pipeline results — refreshed from frontend/data/products.json, updated by your review decisions</p>
      <div class="grid">
        <div class="stat"><div class="label">Products in Catalogue</div><div class="value">${n}</div><div class="hint">${rejected ? rejected + " rejected row(s) excluded" : "no rows rejected yet"}</div></div>
        <div class="stat"><div class="label">High Confidence</div><div class="value ok">${high}</div><div class="hint">status HIGH (&gt;85%)</div></div>
        <div class="stat"><div class="label">Needs Review</div><div class="value warn">${needsReview}</div><div class="hint">still open in the queue</div></div>
        <div class="stat"><div class="label">Human Approved</div><div class="value ok">${approved}</div><div class="hint">accepted via review</div></div>
        <div class="stat"><div class="label">Rejected</div><div class="value bad">${rejected}</div><div class="hint">excluded from exports</div></div>
        <div class="stat"><div class="label">Validation Failures</div><div class="value bad">${valFail}</div><div class="hint">hard rule violations</div></div>
        <div class="stat"><div class="label">Grounding Rate</div><div class="value ok">${pct(ground)}</div><div class="hint">claims with source evidence</div></div>
      </div>
    </div>
    <div class="section">
      <h2>Recent Products</h2>
      <p class="sub">Click a row to open the product detail + evidence viewer · rejected rows are hidden</p>
      ${renderProductsTable(active.slice(0, 12), "row")}
    </div>`;
}

/* ── Products list (V9) ──────────────────────────────────── */
function filteredProducts() {
  const q = state.filter.trim().toLowerCase();
  if (!q) return state.products;
  return state.products.filter((p) =>
    ["mfg_part_num", "part_desc", "brand_name", "manufacturer_name", "classpath"]
      .map((k) => String(p[k] || "").toLowerCase())
      .some((v) => v.includes(q))
  );
}

function renderProducts() {
  const list = filteredProducts().filter((p) => state.showRejected || !isRejected(p));
  const rejectedCount = state.products.filter(isRejected).length;
  $("#view").innerHTML = `
    <div class="section">
      <h2>Products</h2>
      <p class="sub">${list.length} of ${state.products.length} records shown · search by MPN, description, brand or classpath</p>
      <div class="toolbar">
        <input type="search" id="search" placeholder="Search products…" value="${esc(state.filter)}" />
        <label class="toggle"><input type="checkbox" id="show-rejected" ${state.showRejected ? "checked" : ""} /> Show rejected (${rejectedCount})</label>
        <button class="btn small" onclick="exportCsv()">Export CSV</button>
      </div>
      ${renderProductsTable(list, "row")}
    </div>`;
  $("#search").addEventListener("input", (e) => {
    state.filter = e.target.value;
    renderProducts();
  });
  $("#show-rejected").addEventListener("change", (e) => {
    state.showRejected = e.target.checked;
    renderProducts();
  });
}

function renderProductsTable(products, kind) {
  if (!products.length) {
    return `<div class="empty">No products in this view.<br/>Upload a catalogue file from the <a href="#upload">Upload</a> page.</div>`;
  }
  return `
    <table>
      <thead><tr>
        <th>MPN</th><th>Description</th><th>Brand</th><th>Manufacturer</th><th>Classpath</th><th>Confidence</th>
      </tr></thead>
      <tbody>
        ${products.map((p) => {
          return `<tr class="clickable${isRejected(p) ? " row-rejected" : ""}" onclick="location.hash='#product/${encodeURIComponent(productKey(p))}'">
            <td class="mono">${esc(p.mfg_part_num || "—")}</td>
            <td>${esc(p.part_desc || "—")}</td>
            <td>${esc(p.brand_name || "—")}</td>
            <td>${esc(p.manufacturer_name || "—")}</td>
            <td class="mono">${esc(p.classpath || "—")}</td>
            <td>${confidencePill(p)}${verdictBadge(p)}</td>
          </tr>`;
        }).join("")}
      </tbody>
    </table>`;
}

/* ── Product key (single source of truth for review identity) ── */
function productKey(p) {
  return String(p.row_id ?? p.mfg_part_num ?? p.part_desc ?? "row");
}

/* ── Product detail + evidence viewer (V9, V10) ─────────── */
function findProduct(id) {
  return state.products.find((p) => productKey(p) === decodeURIComponent(id));
}

function renderDetail() {
  const p = findProduct(state.detailId);
  const back = '<a class="btn small" href="#products">← Back to products</a>';
  if (!p) {
    $("#view").innerHTML = `<div class="section">${back}<div class="empty">Product not found in this snapshot.</div></div>`;
    return;
  }

  const attrs = (p.attributes || []).filter((a) => a && a.label);
  const descriptions = p.descriptions || {};
  const features = p.features || [];
  const key = productKey(p);
  const review = state.reviews[key] || {};
  const conf = p.confidence || {};

  $("#view").innerHTML = `
    <div class="section">
      ${back}
      ${verdictBanner(p)}
      <div class="detail-head" style="margin-top:12px">
        <div>
          <h3>${esc(p.brand_name || "Unbranded")} ${esc(p.mfg_part_num || "")}</h3>
          <p class="sub">${esc(p.part_desc || "")}</p>
        </div>
        <div style="text-align:right">
          ${confidencePill(p)}
          ${review.decision ? `<div class="review-note">Reviewed by you: <span class="user">${esc(review.decision)}</span></div>` : ""}
        </div>
      </div>

      <div class="meta-grid">
        <div class="meta"><div class="k">Manufacturer</div><div class="v">${esc(p.manufacturer_name || "—")}</div></div>
        <div class="meta"><div class="k">Brand</div><div class="v">${esc(p.brand_name || "—")}</div></div>
        <div class="meta"><div class="k">MPN</div><div class="v mono">${esc(p.mfg_part_num || "—")}</div></div>
        <div class="meta"><div class="k">Classpath</div><div class="v mono" style="font-size:12px">${esc(p.classpath || "—")}</div></div>
        <div class="meta"><div class="k">Overall Confidence</div><div class="v">${conf.overall_confidence != null ? pct(conf.overall_confidence) : "—"}</div></div>
      </div>

      <h2 style="font-size:15px;margin:6px 0 10px">Attributes — click a row to see its evidence</h2>
      ${attrs.length ? attrs.map((a) => renderAttrRow(p, a)).join("") : '<div class="empty">No attributes extracted for this product.</div>'}

      <div style="margin-top:18px">
        <h2 style="font-size:15px;margin-bottom:10px">Descriptions</h2>
        <table>
          <tbody>
            ${Object.entries(descriptions).map(([k, v]) =>
              `<tr><td class="mono" style="width:220px">${esc(k)}</td><td>${esc(v || "")}</td></tr>`
            ).join("")}
          </tbody>
        </table>
      </div>

      ${features.length ? `
      <div style="margin-top:18px">
        <h2 style="font-size:15px;margin-bottom:10px">Features</h2>
        <ul style="padding-left:20px">${features.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
      </div>` : ""}

      <div class="action-strip" id="review-actions">
        <button class="btn ok" onclick="reviewAction('accept', '${esc(key)}')">Accept</button>
        <button class="btn warn" onclick="openEditModal('${esc(key)}')">Edit</button>
        <button class="btn bad" onclick="reviewAction('reject', '${esc(key)}')">Reject</button>
      </div>
    </div>`;
}

function renderAttrRow(p, a) {
  const id = productKey(p);
  const review = state.reviews[id] || {};
  let badge = "";
  if (review.attr && review.attr[a.label]) {
    const d = review.attr[a.label];
    badge = d === "rejected" ? '<span class="flag-bad">rejected</span>'
            : d === "edited" ? '<span class="flag-warn">edited</span>'
            : '<span class="flag-ok">accepted</span>';
  }
  const uom = a.uom ? `<span class="uom">${esc(a.uom)}</span>` : "";
  return `
    <div class="attr-row" data-evidence="${esc(id)}" data-label="${esc(a.label)}">
      <div class="name">${esc(a.label)}</div>
      <div class="val">${esc(a.value ?? "")} ${uom}</div>
      <div class="status">${badge || attrStatus(a)}</div>
      <div class="flag-ok">${isWebSource(a.source) ? "🔎" : ""}</div>
    </div>`;
}

function showEvidence(rowId, label) {
  const p = findProduct(rowId);
  if (!p) return;
  const a = (p.attributes || []).find((x) => x && x.label === label);
  const chunks = (p.rag && p.rag.evidence) || [];
  // Best match: same source URL (+page when given), else same URL only.
  let chunk = null;
  if (a && a.source) {
    chunk =
      chunks.find((c) => c.url === a.source && String(c.page) === String(a.source_page ?? "")) ||
      chunks.find((c) => c.url === a.source) ||
      null;
  }
  const terms = [a && a.value, a && a.raw_value].filter(Boolean);
  const webSrc = isWebSource(a && a.source);
  const card = $("#modal-card");
  card.innerHTML = `
    <h4>Evidence — ${esc(label)}</h4>
    <p class="sub" style="color:var(--muted);margin-bottom:12px">Value: <strong>${esc(a ? a.value : "")}</strong> ${esc(a && a.uom ? a.uom : "")}</p>
    ${a && a.source ? `
      <div class="evidence">
        <div><span class="src">Source:</span> ${webSrc
          ? `<a href="${esc(a.source)}" target="_blank" rel="noopener noreferrer" style="color:#93c5fd">${esc(a.source)}</a>`
          : esc(a.source)}</div>
        ${webSrc && a.source_page ? `<div>Page: ${esc(a.source_page)}</div>` : ""}
        ${a.raw_value ? `<div>Raw value: <span class="mono">${esc(a.raw_value)}</span></div>` : ""}
      </div>
      ${chunk ? `
        <div class="ev-item modal-ev">
          <div class="ev-meta">
            <span class="chip mono">${esc(docTypeLabel(chunk.document_type))}</span>
            ${chunk.page != null ? `<span>chunk ${esc(chunk.page)}</span>` : ""}
            <span class="ev-score">BM25 ${esc(String(chunk.score ?? "—"))}</span>
          </div>
          <div class="ev-text">${highlightTerms(chunk.snippet, terms)}</div>
        </div>` : chunks.length ? `
        <div class="rag-warn" style="margin-top:8px">This source page was not among the retrieved chunks — the value may come from description parsing rather than web evidence.</div>` : `
        <div class="rag-warn" style="margin-top:8px">Source recorded, but no document text was retrieved for this row.</div>`}
      <p style="font-size:12px;color:var(--muted);margin-top:10px">
        Retrieved from manufacturer sources via RAG and normalized against the controlled vocabulary.
      </p>` : `
      <div class="evidence">No manufacturer web source — this value was parsed from the part description (or is empty) and is routed through human review before it can be trusted.</div>`}
    <div style="margin-top:16px;text-align:right"><button class="btn" onclick="closeModal()">Close</button></div>`;
  $("#modal").hidden = false;
}

/* ── RAG Evidence viewer (V10 deep-dive) ─────────────────── */
const DOC_TYPE_LABELS = {
  product_page: "Product Page",
  specification_sheet: "Spec Sheet",
  installation_manual: "Manual",
  catalogue: "Catalogue",
  technical_doc: "Tech Doc",
};

function docTypeLabel(t) {
  return DOC_TYPE_LABELS[t] || (t ? String(t).replace(/_/g, " ") : "Source");
}

function docStatusPill(status) {
  if (status === "fetched") return '<span class="pill high">fetched</span>';
  if (status === "pdf_skipped") return '<span class="pill medium">pdf skipped</span>';
  return '<span class="pill low">failed</span>';
}

/* Escape-first highlighting: split() on a safe regex keeps matches at odd
 * indices, so only escaped text ever becomes markup. */
function highlightTerms(text, terms) {
  const raw = String(text == null ? "" : text);
  const clean = [...new Set(
    (terms || [])
      .map((t) => String(t).trim())
      .filter((t) => t.length > 1)
      .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
  )];
  if (!clean.length) return esc(raw);
  try {
    const re = new RegExp("(" + clean.join("|") + ")", "gi");
    return raw
      .split(re)
      .map((part, i) => (i % 2 === 1 ? "<mark>" + esc(part) + "</mark>" : esc(part)))
      .join("");
  } catch (e) {
    return esc(raw);
  }
}

function ragTermsFor(p) {
  const terms = [p.mfg_part_num, p.manufacturer_name, p.brand_name];
  for (const q of (p.rag && p.rag.queries) || []) terms.push(...q.split(/\s+/));
  return terms;
}

function ragStats(products) {
  const s = { sources: 0, fetched: 0, fetchFails: 0, chunks: 0, evidence: 0,
              queries: 0, groundedAttrs: 0, totalAttrs: 0 };
  for (const p of products) {
    const attrs = (p.attributes || []).filter((a) => a && a.label);
    s.totalAttrs += attrs.length;
    s.groundedAttrs += attrs.filter((a) => a.source).length;
    const r = p.rag;
    if (!r) continue;
    s.queries += (r.queries || []).length;
    s.sources += (r.sources || []).length;
    for (const d of r.documents || []) d.status === "fetched" ? s.fetched++ : s.fetchFails++;
    s.chunks += r.chunks_indexed || 0;
    s.evidence += (r.evidence || []).length;
  }
  return s;
}

function shortUrl(u) {
  return String(u || "").replace(/^https?:\/\//, "").replace(/\/$/, "");
}

function ragCard(p, maxScore) {
  const r = p.rag || {};
  const docs = r.documents || [];
  const ev = r.evidence || [];
  const key = encodeURIComponent(productKey(p));
  const terms = ragTermsFor(p);
  const fetchedCount = docs.filter((d) => d.status === "fetched").length;

  return `
  <details class="rag-card">
    <summary>
      <span class="mono rc-mpn">${esc(p.mfg_part_num || "—")}</span>
      <span class="rc-brand">${esc(p.brand_name || "")}</span>
      <span class="rc-counts">
        <span>${(r.queries || []).length} queries</span>
        <span>${(r.sources || []).length} sources</span>
        <span class="${fetchedCount ? "ok-text" : ""}">${fetchedCount}/${docs.length} docs</span>
        <span>${r.chunks_indexed || 0} chunks</span>
        <span class="${ev.length ? "ok-text" : "warn-text"}">${ev.length} evidence</span>
      </span>
      <a class="btn small" href="#product/${key}" onclick="event.stopPropagation()">Product →</a>
    </summary>
    <div class="rag-body">
      ${(r.queries || []).length ? `
        <div class="rag-h">Retrieval queries</div>
        <div class="chips">${r.queries.map((q) => `<span class="chip mono">${esc(q)}</span>`).join("")}</div>` : ""}
      <div class="rag-h">Discovered manufacturer documents</div>
      ${docs.length ? `
        <table class="docs-table">
          <thead><tr><th>Document</th><th>Type</th><th>Status</th><th class="num">Chars parsed</th></tr></thead>
          <tbody>
            ${docs.map((d) => `<tr>
              <td class="mono"><a href="${esc(d.url)}" target="_blank" rel="noopener noreferrer">${esc(shortUrl(d.url))}</a>${d.error ? `<div class="doc-err">${esc(d.error)}</div>` : ""}</td>
              <td>${docTypeLabel(d.document_type)}</td>
              <td>${docStatusPill(d.status)}</td>
              <td class="mono num">${d.chars != null ? d.chars.toLocaleString() : "—"}</td>
            </tr>`).join("")}
          </tbody>
        </table>` : '<div class="empty-inline">No manufacturer sources were discovered for this row.</div>'}
      <div class="rag-h">Retrieved evidence (BM25-ranked)</div>
      ${ev.length ? ev.map((e) => `
        <div class="ev-item">
          <div class="ev-meta">
            <span class="chip mono">${docTypeLabel(e.document_type)}</span>
            <span>page/chunk ${esc(e.page ?? "?")}</span>
            <span class="score-bar"><span style="width:${Math.round(((Number(e.score) || 0) / maxScore) * 100)}%"></span></span>
            <span class="score-val mono">${esc(e.score ?? "—")}</span>
          </div>
          <p class="ev-text mono">${highlightTerms((e.snippet || "").slice(0, 320), terms)}${(e.snippet || "").length > 320 ? "…" : ""}</p>
        </div>`).join("") : '<div class="empty-inline">No evidence retrieved — attribute extraction fell back to description-only parsing for this row.</div>'}
    </div>
  </details>`;
}

function renderRag() {
  const products = activeProducts();
  const traced = products.filter((p) => p.rag);
  const s = ragStats(products);
  const maxScore = Math.max(
    1,
    ...traced.flatMap((p) => ((p.rag && p.rag.evidence) || []).map((e) => Number(e.score) || 0))
  );

  $("#view").innerHTML = `
    <div class="section">
      <h2>RAG Evidence</h2>
      <p class="sub">How every extracted attribute is grounded in real manufacturer documents —
      expand a product to see its full retrieval trace.</p>

      <div class="rag-flow">
        ${[
          ["Queries", "MPN + manufacturer + type"],
          ["Discover", "official URLs only · marketplaces blocked"],
          ["Fetch & parse", "HTML → clean text"],
          ["Chunk", "500-word windows, 50 overlap"],
          ["Retrieve", "BM25 top-k per query"],
          ["Extract", "LLM cites URL + page"],
        ].map(([t, d]) =>
          `<div class="flow-step"><div class="fs-t">${t}</div><div class="fs-d">${d}</div></div>`
        ).join('<div class="flow-arrow" aria-hidden="true">→</div>')}
      </div>

      <div class="grid" style="margin-top:14px">
        <div class="stat"><div class="label">Retrieval Queries</div><div class="value">${s.queries}</div><div class="hint">generated across all products</div></div>
        <div class="stat"><div class="label">Sources Discovered</div><div class="value">${s.sources}</div><div class="hint">official manufacturer URLs</div></div>
        <div class="stat"><div class="label">Documents Fetched</div><div class="value ok">${s.fetched}</div><div class="hint">${s.fetchFails} failed or pdf-skipped</div></div>
        <div class="stat"><div class="label">Chunks Indexed</div><div class="value">${s.chunks}</div><div class="hint">searchable text windows</div></div>
        <div class="stat"><div class="label">Evidence Retrieved</div><div class="value ok">${s.evidence}</div><div class="hint">top BM25 matches passed to extraction</div></div>
        <div class="stat"><div class="label">Grounded Attributes</div><div class="value ok">${s.groundedAttrs}/${s.totalAttrs}</div><div class="hint">attributes citing a source document</div></div>
      </div>
    </div>
    ${traced.length ? traced.map((p) => ragCard(p, maxScore)).join("") : `
    <div class="section">
      <div class="empty">
        No RAG traces in this snapshot.<br/>
        Run the pipeline on a catalogue file from the <a href="#upload">Upload</a> page — every processed row records its full retrieval trace here.
      </div>
    </div>`}`;
}

/* ── Review (V11) ────────────────────────────────────────── */
function isFlagged(p) {
  return (
    (p.confidence && p.confidence.needs_review) ||
    (p.attributes || []).some((a) => a && a.needs_review)
  );
}

/* accept / reject close the loop; edit keeps the item open until a final
 * accept/reject decision is made. */
function isResolved(p) {
  const r = state.reviews[productKey(p)] || p.review;
  return !!r && (r.decision === "accept" || r.decision === "reject");
}

function countNeedsReview() {
  return state.products.filter((p) => isFlagged(p) && !isResolved(p)).length;
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1800);
}

function renderReview() {
  const open = state.products.filter((p) => isFlagged(p) && !isResolved(p));
  const resolved = state.products.filter((p) => isFlagged(p) && isResolved(p));
  $("#view").innerHTML = `
    <div class="section">
      <h2>Human Review Queue</h2>
      <p class="sub">${open.length} open · ${resolved.length} resolved — Accept/Reject clear the queue, Edit corrects values and keeps the item open. Rejected rows are excluded from the catalogue and exports; decisions persist to the backend.</p>
      ${open.length ? `
      <table>
        <thead><tr><th>MPN</th><th>Description</th><th>Status</th><th>Review Reason</th><th></th></tr></thead>
        <tbody>
          ${open.map((p) => {
            const id = productKey(p);
            const draft = state.reviews[id] || p.review || {};
            const reasons = (p.confidence && p.confidence.review_reasons || []).slice(0, 2);
            return `<tr>
              <td class="mono">${esc(p.mfg_part_num || "—")}</td>
              <td>${esc(p.part_desc || "—")}</td>
              <td>${confidencePill(p)}${draft.decision === "edit" ? ' <span class="flag-warn">edited, awaiting decision</span>' : ""}</td>
              <td style="font-size:12.5px;color:var(--muted)">${reasons.map((r) => `• ${esc(r)}`).join("<br/>") || "attribute needs review"}</td>
              <td><button class="btn small" onclick="location.hash='#product/${encodeURIComponent(id)}'">Review →</button></td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>` : '<div class="empty">🎉 Nothing needs review — all flagged products have a final decision.</div>'}
    </div>`;
}

function reviewAction(decision, id) {
  // `id` is passed directly by the button; fall back to the current detail view.
  const key = id || String(state.detailId);
  if (!key) return;
  state.reviews[key] = { decision, at: new Date().toISOString() };
  saveReviews();
  updateBadge();
  toast(`Marked as ${decision}`);
  syncReview(key, decision);
  renderDetail();
}

/* Push a decision (and optional edited fields) to the backend so it lands in
 * products.json — survives browsers/devices. Local state is already saved;
 * this is best-effort. */
async function syncReview(key, decision, edited) {
  try {
    const body = { key, decision, at: new Date().toISOString() };
    if (edited) body.product = edited;
    const res = await fetch(api("/api/review"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
  } catch (e) {
    toast("Saved locally — backend unreachable");
  }
}

/* ── Edit modal — correct attribute values / descriptions ── */
function openEditModal(key) {
  const p = state.products.find((x) => productKey(x) === key);
  if (!p) return;
  const attrs = (p.attributes || []).filter((a) => a && a.label);
  const descriptions = p.descriptions || {};
  const card = $("#modal-card");
  card.innerHTML = `
    <h4>Edit — ${esc(p.brand_name || "Unbranded")} ${esc(p.mfg_part_num || "")}</h4>
    <p class="sub" style="margin-bottom:12px">Correct values below. Edits are saved, but the item stays in the queue until you Accept or Reject it.</p>
    ${attrs.length ? `
      <div class="edit-h">Attributes</div>
      ${attrs.map((a, i) => `
        <div class="edit-row">
          <div class="edit-label">${esc(a.label)}${a.needs_review ? ' <span class="flag-warn">⚠</span>' : ""}</div>
          <input type="text" data-edit-attr="${i}" value="${esc(a.value ?? "")}" placeholder="value" />
          <input type="text" data-edit-uom="${i}" value="${esc(a.uom ?? "")}" placeholder="uom" style="width:84px;flex:0 0 84px" />
        </div>`).join("")}` : ""}
    ${Object.keys(descriptions).length ? `
      <div class="edit-h">Descriptions</div>
      ${Object.entries(descriptions).map(([k, v], i) => `
        <div class="edit-row col">
          <div class="edit-label">${esc(k)}</div>
          <textarea data-edit-desc="${i}" rows="2">${esc(v || "")}</textarea>
        </div>`).join("")}` : ""}
    <div style="margin-top:16px;text-align:right">
      <button class="btn" onclick="closeModal()">Cancel</button>
      <button class="btn ok" onclick="saveEdits('${esc(key)}')">Save edits</button>
    </div>`;
  $("#modal").hidden = false;
}

function saveEdits(key) {
  const p = state.products.find((x) => productKey(x) === key);
  if (!p) return;
  const attrs = (p.attributes || []).filter((a) => a && a.label);
  let changed = 0;
  document.querySelectorAll("[data-edit-attr]").forEach((inp) => {
    const i = Number(inp.dataset.editAttr);
    if (!attrs[i]) return;
    const uomInput = document.querySelector(`[data-edit-uom="${i}"]`);
    const newValue = inp.value;
    const newUom = uomInput ? uomInput.value.trim() : attrs[i].uom;
    if (newValue !== String(attrs[i].value ?? "") || newUom !== String(attrs[i].uom ?? "")) {
      attrs[i].value = newValue;
      attrs[i].uom = newUom || null;
      attrs[i].edited = true;
      changed++;
    }
  });
  const descKeys = Object.keys(p.descriptions || {});
  document.querySelectorAll("[data-edit-desc]").forEach((ta) => {
    const k = descKeys[Number(ta.dataset.editDesc)];
    if (k == null) return;
    if (ta.value !== String(p.descriptions[k] ?? "")) {
      p.descriptions[k] = ta.value;
      changed++;
    }
  });
  state.reviews[key] = { decision: "edit", at: new Date().toISOString(), changes: changed };
  saveReviews();
  updateBadge();
  closeModal();
  toast(changed ? `Saved ${changed} edit(s)` : "No changes");
  syncReview(key, "edit", { attributes: p.attributes, descriptions: p.descriptions });
  renderDetail();
}

/* ── Metrics (V12) ───────────────────────────────────────── */
function renderMetrics() {
  const m = state.metrics || {};
  const flagged = state.products.filter(isFlagged).length;
  const resolved = state.products.filter((p) => isFlagged(p) && isResolved(p)).length;
  const approved = state.products.filter(isApproved).length;
  const rejected = state.products.filter(isRejected).length;
  const open = countNeedsReview();
  const reviewBands = [
    ["Human Approved", approved, "accepted via the review queue"],
    ["Rejected", rejected, "excluded from catalogue + exports"],
    ["Open Queue", open, "still waiting for a decision"],
    ["Triage Progress", flagged ? pct(resolved / flagged) : "—", `${resolved} of ${flagged} flagged products decided`],
  ];
  const bands = [
    ["Field Accuracy", m.field_accuracy != null ? pct(m.field_accuracy) : "—", "requires 200-row labelled eval (scripts/evaluate_200.py)"],
    ["LOV Compliance", pct(m.lov_compliance_rate), "% of values matched to the approved list of values"],
    ["UOM Compliance", pct(m.uom_compliance_rate), "% of units present in the approved UOM master"],
    ["Grounding Rate", pct(m.grounding_rate), "% of factual claims with manufacturer source evidence"],
    ["Review Rate", pct(m.needs_review != null ? m.needs_review / Math.max(m.n_products || 1, 1) : null), "rows routed to human review"],
    ["Avg Confidence", m.avg_confidence != null ? pct(m.avg_confidence) : "—", "weighted manufacturer/classification/LOV/UOM/grounding score"],
  ];
  $("#view").innerHTML = `
    <div class="section">
      <h2>Evaluation Metrics</h2>
      <p class="sub">Measured on ${m.n_products != null ? m.n_products + " product(s)" : "—"} from the real pipeline output — never hardcoded</p>

      <h3 style="font-size:15px;margin:4px 0 10px">Human Review — live from your decisions</h3>
      <div class="metric-band">
        ${reviewBands.map(([label, value, detail]) => `
          <div class="metric-card">
            <div class="m-label">${label}</div>
            <div class="m-value">${value}</div>
            <div class="m-detail">${detail}</div>
          </div>`).join("")}
      </div>

      <h3 style="font-size:15px;margin:18px 0 10px">Pipeline Quality — last processing run</h3>
      <div class="metric-band">
        ${bands.map(([label, value, detail]) => `
          <div class="metric-card">
            <div class="m-label">${label}</div>
            <div class="m-value">${value}</div>
            <div class="m-detail">${detail}</div>
          </div>`).join("")}
      </div>
    </div>`;
}

/* ── Export (V17 DoD) ────────────────────────────────────── */
function exportCsv() {
  const cols = ["row_id", "mfg_part_num", "part_desc", "brand_name", "manufacturer_name",
                "classpath", "attributes", "descriptions", "confidence", "review"];
  // Rejected records never leave the system as catalogue rows.
  const all = filteredProducts();
  const included = all.filter((p) => !isRejected(p));
  const excluded = all.length - included.length;
  const rows = included.map((p) => cols.map((c) => {
    if (c === "attributes") return (p.attributes || []).map((a) => `${a.label}:${a.value}${a.uom ? " " + a.uom : ""}`).join(" | ");
    if (c === "descriptions") return JSON.stringify(p.descriptions || {});
    if (c === "confidence") return (p.confidence && p.confidence.status) || "";
    if (c === "review") return (state.reviews[productKey(p)] || p.review || {}).decision || "";
    const v = p[c];
    return typeof v === "string" ? v.replace(/,/g, ";") : (v == null ? "" : String(v));
  }).join(",")).join("\n");
  const csv = cols.join(",") + "\n" + rows;
  const blob = new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "products_export.csv";
  a.click();
  URL.revokeObjectURL(a.href);
  toast(excluded ? `Exported ${included.length} rows — ${excluded} rejected row(s) excluded` : `Exported ${included.length} rows`);
}

/* ── Upload → live pipeline run ──────────────────────────── */
function renderUpload() {
  $("#view").innerHTML = `
    <div class="section">
      <h2>Process a catalogue file</h2>
      <p class="sub">Upload a CSV or XLSX of raw product rows — the full AI pipeline runs on it and every
      view below updates with the enriched output.</p>

      <div class="upload-box" id="upload-box">
        <input type="file" id="file-input" accept=".csv,.xlsx,.xls" />
        <label class="opt">Rows to process
          <input type="number" id="limit-input" min="1" placeholder="all rows" style="width:110px" />
        </label>
        <button class="btn ok" id="process-btn" onclick="processUpload()">Run pipeline</button>
      </div>
      <p class="sub" id="upload-status" style="min-height:20px"></p>

      <div class="meta-grid" style="margin-top:16px" id="env-grid"></div>

      <div class="howto">
        <h3>What happens on upload</h3>
        <ol>
          <li>The file is parsed and validated (CSV or Excel). Headers are auto-detected — common names like "Part Number", "Description", "Brand" or "Manufacturer" are mapped automatically.</li>
          <li>Every row runs the 11-stage pipeline: understanding &rarr; classification &rarr; entity resolution &rarr; source discovery &rarr; RAG extraction &rarr; normalization &rarr; content generation.</li>
          <li>Validation + confidence scoring flag anything a human should check.</li>
          <li>The dashboard, products, review queue and metrics views reload with the fresh output.</li>
        </ol>
      </div>
    </div>`;
  refreshEnv();
}

async function refreshEnv() {
  const grid = $("#env-grid");
  if (!grid) return;
  try {
    const r = await fetch(api("/api/status"));
    const s = await r.json();
    const item = (ok, label) =>
      `<div class="meta"><div class="k">${label}</div><div class="v ${ok ? "ok-text" : "warn-text"}">${ok ? "Ready" : "Not available"}</div></div>`;
    grid.innerHTML =
      item(s.master_ready, "Manufacturer master") +
      item(s.llm_ready, "LLM enrichment (GROQ)") +
      // Detects an older server build still running from before code changes.
      item(s.flexible_headers === true, "Flexible header mapping") +
      `<div class="meta"><div class="k">Backend</div><div class="v mono" style="font-size:12px">${esc(backendBase() || location.origin || "same origin")}</div></div>` +
      `<div class="meta"><div class="k">Current snapshot</div><div class="v">${s.ready ? s.n_products + " products" : "empty"}</div></div>`;
  } catch (e) {
    grid.innerHTML = '<div class="meta"><div class="k">Backend</div><div class="v warn-text">API unreachable</div></div>';
  }
}

async function processUpload() {
  const fileInput = $("#file-input");
  const status = $("#upload-status");
  const btn = $("#process-btn");
  const limit = $("#limit-input") ? $("#limit-input").value : "";

  if (!fileInput.files.length) {
    status.textContent = "Choose a .csv or .xlsx file first.";
    return;
  }

  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  if (limit) fd.append("limit", limit);

  btn.disabled = true;
  fileInput.disabled = true;

  let poll = null;
  const finishUi = () => { clearInterval(poll); btn.disabled = false; fileInput.disabled = false; };

  // Kick off processing. The backend ACCEPTS the upload and returns
  // immediately; the pipeline runs in a background thread (long synchronous
  // responses were killed by hosting proxies mid-flight -> "Failed to fetch").
  try {
    const res = await fetch(api("/api/process"), { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      status.textContent = data.error || "Processing failed.";
      finishUi();
      return;
    }
  } catch (e) {
    status.innerHTML =
      "Could not reach the backend. On a free tier the service may be asleep — " +
      "the first request can take ~1 minute to wake it. Wait a moment and retry." +
      `<br/><span class="warn-text">${esc(e.message)}</span>`;
    finishUi();
    return;
  }

  status.innerHTML =
    'Upload accepted — the AI pipeline is running in the background…' +
    '<div class="progress"><span id="progress-fill"></span></div>';

  // Drive everything from /api/progress: live rows, then done | error.
  poll = setInterval(async () => {
    let p;
    try {
      p = await (await fetch(api("/api/progress"))).json();
    } catch (e) { return; /* transient network blip — next tick retries */ }

    if (p.status === "error") {
      finishUi();
      status.innerHTML = `<span class="warn-text">Processing failed:</span> ${esc(p.error || "unknown error")}`;
      return;
    }
    if (p.status === "done") {
      finishUi();
      const r = p.result || {};
      const m = r.metrics || {};
      const cm = r.column_map;
      const mapLine = cm && Object.keys(cm.mapped || {}).length
        ? `<div class="map-line">Headers matched: ${
            Object.entries(cm.mapped).map(([c, o]) => `${esc(o)} &rarr; <strong>${esc(c)}</strong>`).join(" &middot; ")
          }${cm.missing && cm.missing.length
            ? ` &middot; <span class="warn-text">no match for ${cm.missing.map(esc).join(", ")} (treated as empty)</span>`
            : ""}</div>`
        : "";
      status.innerHTML =
        `<strong>Done:</strong> ${r.n_rows} products enriched in ${r.elapsed_s}s` +
        ` · high confidence ${m.high_confidence ?? 0} · needs review ${m.needs_review ?? 0}` +
        ` · avg confidence ${m.avg_confidence != null ? pct(m.avg_confidence) : "n/a"}` +
        mapLine;

      // Refresh the dashboard from the fresh snapshot. Retry a few times —
      // right after a run the file can take a moment to become reachable
      // through proxies/caches. Never fail silently again.
      let loaded = false;
      let lastErr = null;
      for (let attempt = 1; attempt <= 4 && !loaded; attempt++) {
        try {
          await loadData();
          loaded = true;
        } catch (e) {
          lastErr = e;
          console.warn(`Snapshot load failed (attempt ${attempt}/4):`, e.message);
          if (attempt < 4) await new Promise((res) => setTimeout(res, 1500));
        }
      }
      if (loaded) {
        updateBadge();
        toast(`Loaded ${state.products.length} product(s)`);
        location.hash = "#dashboard";
        route();
      } else {
        status.innerHTML +=
          `<div class="warn-text" style="margin-top:8px">Processing finished, but refreshing the views failed: ${esc(lastErr ? lastErr.message : "unknown")}.` +
          ` The data IS saved — open <a href="#products">Products</a> or reload the page.</div>`;
      }
      return;
    }

    const total = p.total || 0;
    const label = total
      ? `Processing row ${p.done}/${total} — ${p.elapsed_s}s elapsed.`
      : `Processing — ${p.elapsed_s}s elapsed.`;
    status.innerHTML =
      `${label} Each row makes several LLM + web calls; Groq rate limits pace the run.` +
      '<div class="progress"><span id="progress-fill"></span></div>';
    const fill = $("#progress-fill");
    if (fill && total) fill.style.width = Math.min(100, (p.done / total) * 100) + "%";
  }, 2000);
}

/* ── Rendering dispatch ──────────────────────────────────── */
function render(view) {
  if (view === "upload") return renderUpload();
  if (view === "products") return renderProducts();
  if (view === "rag") return renderRag();
  if (view === "review") return renderReview();
  if (view === "metrics") return renderMetrics();
  return renderDashboard();
}

function updateBadge() {
  const badge = $("#review-badge");
  const n = countNeedsReview();
  badge.textContent = n;
  badge.classList.toggle("zero", n === 0);
}

function closeModal() {
  $("#modal").hidden = true;
}

/* ── Boot ────────────────────────────────────────────────── */
(async function boot() {
  $("#view").innerHTML = '<div class="loading">Loading data…</div>';
  window.addEventListener("hashchange", route);
  try {
    await loadData();
    updateBadge();
    route();
  } catch (e) {
    // No snapshot yet — the Upload view is the way in.
    location.hash = "#upload";
    updateBadge();
    route();
  }
})();

window.addEventListener("click", (e) => {
  if (e.target.id === "modal") return closeModal();
  const evRow = e.target.closest("[data-evidence]");
  if (evRow) showEvidence(evRow.dataset.evidence, evRow.dataset.label);
});