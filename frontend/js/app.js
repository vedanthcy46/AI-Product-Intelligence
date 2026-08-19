"use strict";

/* UniHack frontend — reads the internal Product JSON produced by the
 * pipeline (frontend/data/products.json) and real metrics (metrics.json).
 * No hardcoded demonstration numbers anywhere. */

const DATA_URL = "data/products.json";
const METRICS_URL = "data/metrics.json";
const REVIEW_KEY = "unihack.reviews";

const state = {
  products: [],
  metrics: null,
  reviews: loadReviews(),
  filter: "",
  detailId: null,
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

function attrStatus(attr) {
  if (attr.needs_review) return '<span class="flag-warn">⚠ Needs Review</span>';
  if (attr.value == null) return '<span class="flag-ok">— empty (OK)</span>';
  const grounded = attr.source ? '<span class="flag-ok">✓ grounded</span>' : '<span class="flag-warn">no source</span>';
  const lov = attr.lov_matched ? '<span class="flag-ok">✓ LOV</span>' : '<span class="flag-bad">✗ LOV</span>';
  return `${grounded} ${lov}`;
}

/* ── Data loading ────────────────────────────────────────── */
async function loadData() {
  const [pRes, mRes] = await Promise.all([fetch(DATA_URL), fetch(METRICS_URL)]);
  if (!pRes.ok) throw new Error("products.json missing");
  state.products = await pRes.json();
  state.metrics = mRes.ok ? await mRes.json() : null;
}

/* ── Router ──────────────────────────────────────────────── */
function currentView() {
  const hash = location.hash.replace("#", "");
  if (hash.startsWith("product/")) return "detail";
  return ["dashboard", "products", "review", "metrics"].includes(hash) ? hash : "dashboard";
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
  const n = state.products.length;
  const needsReview = countNeedsReview();
  const high = m.high_confidence != null ? m.high_confidence : countHigh();
  const valFail = m.validation_failures != null ? m.validation_failures : 0;
  const ground = m.grounding_rate != null ? m.grounding_rate : avgGrounding();

  $("#view").innerHTML = `
    <div class="section">
      <h2>Processing Overview</h2>
      <p class="sub">Live pipeline results — refreshed from frontend/data/products.json</p>
      <div class="grid">
        <div class="stat"><div class="label">Products Processed</div><div class="value">${n}</div><div class="hint">rows in this snapshot</div></div>
        <div class="stat"><div class="label">High Confidence</div><div class="value ok">${high}</div><div class="hint">status HIGH (&gt;85%)</div></div>
        <div class="stat"><div class="label">Needs Review</div><div class="value warn">${needsReview}</div><div class="hint">manual triage required</div></div>
        <div class="stat"><div class="label">Validation Failures</div><div class="value bad">${valFail}</div><div class="hint">hard rule violations</div></div>
        <div class="stat"><div class="label">Grounding Rate</div><div class="value ok">${pct(ground)}</div><div class="hint">claims with source evidence</div></div>
      </div>
    </div>
    <div class="section">
      <h2>Recent Products</h2>
      <p class="sub">Click a row to open the product detail + evidence viewer</p>
      ${renderProductsTable(state.products.slice(0, 12), "row")}
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
  const list = filteredProducts();
  $("#view").innerHTML = `
    <div class="section">
      <h2>Products</h2>
      <p class="sub">${state.products.length} records · search by MPN, description, brand or classpath</p>
      <div class="toolbar">
        <input type="search" id="search" placeholder="Search products…" value="${esc(state.filter)}" />
        <button class="btn small" onclick="exportCsv()">Export CSV</button>
      </div>
      ${renderProductsTable(list, "row")}
    </div>`;
  $("#search").addEventListener("input", (e) => {
    state.filter = e.target.value;
    renderProducts();
  });
}

function renderProductsTable(products, kind) {
  if (!products.length) {
    return `<div class="empty">No products in this view.<br/>Run the pipeline and <span class="code">python frontend/generate_data.py</span> first.</div>`;
  }
  return `
    <table>
      <thead><tr>
        <th>MPN</th><th>Description</th><th>Brand</th><th>Manufacturer</th><th>Classpath</th><th>Confidence</th>
      </tr></thead>
      <tbody>
        ${products.map((p) => {
          return `<tr class="clickable" onclick="location.hash='#product/${encodeURIComponent(productKey(p))}'">
            <td class="mono">${esc(p.mfg_part_num || "—")}</td>
            <td>${esc(p.part_desc || "—")}</td>
            <td>${esc(p.brand_name || "—")}</td>
            <td>${esc(p.manufacturer_name || "—")}</td>
            <td class="mono">${esc(p.classpath || "—")}</td>
            <td>${confidencePill(p)}</td>
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
        <button class="btn warn" onclick="reviewAction('edit', '${esc(key)}')">Edit</button>
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
      <div class="flag-ok">${a.source ? "🔎" : ""}</div>
    </div>`;
}

function showEvidence(rowId, label) {
  const p = findProduct(rowId);
  if (!p) return;
  const a = (p.attributes || []).find((x) => x && x.label === label);
  const card = $("#modal-card");
  card.innerHTML = `
    <h4>Evidence — ${esc(label)}</h4>
    <p class="sub" style="color:var(--muted);margin-bottom:12px">Value: <strong>${esc(a ? a.value : "")}</strong> ${esc(a && a.uom ? a.uom : "")}</p>
    ${a && a.source ? `
      <div class="evidence">
        <div><span class="src">Source:</span> ${esc(a.source)}</div>
        ${a.source_page ? `<div>Page: ${esc(a.source_page)}</div>` : ""}
        ${a.raw_value ? `<div>Raw value: <span class="mono">${esc(a.raw_value)}</span></div>` : ""}
      </div>
      <p style="font-size:12px;color:var(--muted);margin-top:10px">
        Retrieved from manufacturer sources via RAG and normalized against the controlled vocabulary.
      </p>` : `
      <div class="evidence">No manufacturer source attached to this attribute — flag for review.</div>`}
    <div style="margin-top:16px;text-align:right"><button class="btn" onclick="closeModal()">Close</button></div>`;
  $("#modal").hidden = false;
}

/* ── Review (V11) ────────────────────────────────────────── */
function countNeedsReview() {
  return state.products.filter((p) =>
    state.reviews[productKey(p)] ||
    (p.confidence && p.confidence.needs_review) ||
    (p.attributes || []).some((a) => a && a.needs_review)
  ).length;
}

function toast(msg) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1800);
}

function renderReview() {
  const flagged = state.products.filter((p) =>
    (p.confidence && p.confidence.needs_review) ||
    (p.attributes || []).some((a) => a && a.needs_review)
  );
  $("#view").innerHTML = `
    <div class="section">
      <h2>Human Review Queue</h2>
      <p class="sub">${flagged.length} products flagged for manual triage. Accept / Edit / Reject — decisions are stored in your browser.</p>
      ${flagged.length ? `
      <table>
        <thead><tr><th>MPN</th><th>Description</th><th>Status</th><th>Review Reason</th><th></th></tr></thead>
        <tbody>
          ${flagged.map((p) => {
            const id = productKey(p);
            const reasons = (p.confidence && p.confidence.review_reasons || []).slice(0, 2);
            return `<tr>
              <td class="mono">${esc(p.mfg_part_num || "—")}</td>
              <td>${esc(p.part_desc || "—")}</td>
              <td>${confidencePill(p)}</td>
              <td style="font-size:12.5px;color:var(--muted)">${reasons.map((r) => `• ${esc(r)}`).join("<br/>") || "attribute needs review"}</td>
              <td><button class="btn small" onclick="location.hash='#product/${encodeURIComponent(id)}'">Review →</button></td>
            </tr>`;
          }).join("")}
        </tbody>
      </table>` : '<div class="empty">🎉 Nothing needs review — all products pass triage.</div>'}
    </div>`;
}

function reviewAction(decision, id) {
  // `id` is passed directly by the button; fall back to the current detail view.
  const key = id || String(state.products.find((p) => productKey(p) === String(state.detailId))?.row_id ?? state.detailId);
  state.reviews[key] = { decision, at: new Date().toISOString() };
  saveReviews();
  updateBadge();
  toast(`Marked as ${decision}`);
  renderDetail();
}

/* ── Metrics (V12) ───────────────────────────────────────── */
function renderMetrics() {
  const m = state.metrics || {};
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
                "classpath", "attributes", "descriptions", "confidence"];
  const rows = filteredProducts().map((p) => cols.map((c) => {
    if (c === "attributes") return (p.attributes || []).map((a) => `${a.label}:${a.value}${a.uom ? " " + a.uom : ""}`).join(" | ");
    if (c === "descriptions") return JSON.stringify(p.descriptions || {});
    if (c === "confidence") return (p.confidence && p.confidence.status) || "";
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
}

/* ── Rendering dispatch ──────────────────────────────────── */
function render(view) {
  if (view === "products") return renderProducts();
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
  try {
    await loadData();
    updateBadge();
    window.addEventListener("hashchange", route);
    route();
  } catch (e) {
    $("#view").innerHTML = `
      <div class="section">
        <h2>No data yet</h2>
        <div class="empty">
          The dashboard needs pipeline output to display.
          <br/><br/>
          <span class="code">python run_pipeline.py --input data/raw/input.csv --output data/processed/output.csv --internal-json data/processed/products.json</span>
          <br/><br/>
          then
          <br/><br/>
          <span class="code">python frontend/generate_data.py</span>
          <br/><br/>
          and reload this page. (Error: ${esc(e.message)})
        </div>
      </div>`;
  }
})();

window.addEventListener("click", (e) => {
  if (e.target.id === "modal") return closeModal();
  const evRow = e.target.closest("[data-evidence]");
  if (evRow) showEvidence(evRow.dataset.evidence, evRow.dataset.label);
});