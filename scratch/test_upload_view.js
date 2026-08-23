const fs = require("fs");
const vm = require("vm");

let viewHTML = "";
const modalHidden = { value: true };

global.window = global;
global.localStorage = { getItem: () => null, setItem: () => {} };
global.document = {
  querySelector: (sel) => {
    if (sel === "#view") {
      const el = {};
      Object.defineProperty(el, "innerHTML", { set: (v) => { viewHTML = v; }, get: () => viewHTML });
      return el;
    }
    if (sel === "#modal") return { hidden: modalHidden };
    if (sel === "#modal-card") return {};
    if (sel === "#review-badge") return { textContent: 0, classList: { toggle: () => {} } };
    return null;
  },
  querySelectorAll: () => [],
  createElement: () => ({ click: () => {}, className: "", textContent: "", remove: () => {} }),
  body: { appendChild: () => {} },
};
global.location = { hash: "#upload" };
global.addEventListener = () => {};
global.fetch = async (url) => {
  console.log("fetch called:", url);
  if (url === "/api/status") return { ok: true, json: async () => ({ ready: true, n_products: 3, master_ready: false, llm_ready: true }) };
  return { ok: false };
};

const src = fs.readFileSync("frontend/js/app.js", "utf8");
vm.runInThisContext(src);

console.log("currentView:", currentView());
try {
  route();
  console.log("route OK, viewHTML length:", viewHTML.length);
  console.log("has file input:", viewHTML.includes('id="file-input"'));
  console.log("has process btn:", viewHTML.includes("processUpload"));
} catch (e) {
  console.log("ROUTE ERROR:", e.message, "\n", e.stack);
}

// also test refreshEnv path
(async () => {
  try {
    await refreshEnv();
    console.log("refreshEnv OK");
  } catch (e) {
    console.log("refreshEnv ERROR:", e.message);
  }
})();