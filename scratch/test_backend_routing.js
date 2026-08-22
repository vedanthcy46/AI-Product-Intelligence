// Sanity-check backendBase() routing logic across environments.
const CONFIGURED_BACKEND = "https://ai-product-intelligence-6xfq.onrender.com".replace(/\/+$/, "");
const DEV_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);
function backendBase(location) {
  const host = String(location.hostname || "").toLowerCase();
  if (!host || location.protocol === "file:") return CONFIGURED_BACKEND;
  if (DEV_HOSTNAMES.has(host)) return "";
  try {
    if (CONFIGURED_BACKEND && new URL(CONFIGURED_BACKEND).origin === location.origin) return "";
  } catch (e) {}
  return CONFIGURED_BACKEND;
}

const cases = [
  ["dev local server",    { hostname: "localhost", protocol: "http:", origin: "http://localhost:8000" }, ""],
  ["dev via 127.0.0.1",   { hostname: "127.0.0.1", protocol: "http:", origin: "http://127.0.0.1:8000" }, ""],
  ["prod on render",      { hostname: "ai-product-intelligence-6xfq.onrender.com", protocol: "https:", origin: "https://ai-product-intelligence-6xfq.onrender.com" }, ""],
  ["github pages",        { hostname: "team.github.io", protocol: "https:", origin: "https://team.github.io" }, CONFIGURED_BACKEND],
  ["file preview",        { hostname: "", protocol: "file:", origin: "null" }, CONFIGURED_BACKEND],
];

for (const [name, loc, expected] of cases) {
  const got = backendBase(loc);
  assertEqual(name, got, expected);
}
function assertEqual(name, got, exp) {
  if (got !== exp) { console.error(`FAIL ${name}: got "${got}" want "${exp}"`); process.exit(1); }
  console.log(`OK ${name} -> "${got || "(relative/local)"}"`);
}
console.log("ALL ROUTING CASES PASS");
