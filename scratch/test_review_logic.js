const fs = require("fs");
const vm = require("vm");

// Minimal DOM / browser stubs
let viewHTML = "";
const modalHidden = { value: true };
const reviews = {};

global.window = global;
global.localStorage = {
  getItem: () => null,
  setItem: (k, v) => { reviews[k] = v; },
};
global.document = {
  querySelector: (sel) => {
    if (sel === "#view") {
      const el = {};
      Object.defineProperty(el, "innerHTML", { set: (v) => { viewHTML = v; }, get: () => viewHTML });
      return el;
    }
    if (sel === "#modal") return { hidden: modalHidden };
    if (sel === "#modal-card") return { innerHTML: () => {} };
    if (sel === "#review-badge") return { textContent: 0, classList: { toggle: () => {} } };
    return null;
  },
  querySelectorAll: () => [{ dataset: { view: "detail" }, classList: { toggle: () => {} } }],
  createElement: () => ({ click: () => {}, href: "", className: "", textContent: "", remove: () => {} }),
  body: { appendChild: () => {} },
};
global.location = { hash: "#product/1" };
global.addEventListener = () => {};
global.fetch = async () => ({ ok: false });
global.URL = { createObjectURL: () => "", revokeObjectURL: () => {} };
global.Blob = function () {};
global.decodeURIComponent = decodeURIComponent;
global.encodeURIComponent = encodeURIComponent;

const src = fs.readFileSync("frontend/js/app.js", "utf8");
vm.runInThisContext(src);

// Simulate loaded data
state.products = [
  {
    row_id: "1",
    mfg_part_num: "PDSH4816AF",
    part_desc: "Dishwasher",
    brand_name: "FRIGIDAIRE®",
    manufacturer_name: "Rheem Manufacturing",
    classpath: "Appliances>Kitchen>Dishwashers",
    confidence: { status: "HIGH", needs_review: false, overall_confidence: 0.97, review_reasons: [] },
    attributes: [
      { label: "Material", value: "Stainless Steel", source: "spec.pdf", source_page: 3, needs_review: true, lov_matched: true, uom: null },
    ],
    descriptions: { INVOICE_DESC: "DISHWASHER" },
    features: [],
  },
];

console.log("--- clicking Accept ---");
try {
  reviewAction("accept");
  console.log("reviews after accept:", reviews["unihack.reviews"]);
  console.log("view re-rendered:", viewHTML.includes("Reviewed by you") ? "YES" : "NO");
} catch (e) {
  console.log("ERROR:", e.message, "\n", e.stack);
}

console.log("\n--- simulate full boot (route sets detailId) ---");
try {
  viewHTML = "";
  route();
  console.log("detailId after route:", state.detailId, "type:", typeof state.detailId);
  console.log("viewHTML after route (len):", viewHTML.length);
  console.log("--- calling renderDetail() directly ---");
  viewHTML = "";
  renderDetail();
  console.log("viewHTML after renderDetail (len):", viewHTML.length);
  console.log("snippet:", JSON.stringify(viewHTML.slice(0, 120)));
  viewHTML = "";
  reviewAction("reject");
  console.log("reviews after reject:", reviews["unihack.reviews"]);
  console.log("viewHTML after reject (len):", viewHTML.length);
  console.log("view shows Reviewed by you:", viewHTML.includes("Reviewed by you") ? "YES" : "NO");
} catch (e) {
  console.log("ERROR:", e.message, "\n", e.stack);
}