// Sanity-check backendBase() routing logic across environments.
const REMOTE_BACKENDS = [
  "https://ai-product-intelligence-6xfq.onrender.com",
  "https://ai-product-intelligence-i5em.onrender.com",
].map((url) => url.replace(/\/+$/, ""));

const DEV_HOSTNAMES = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

function backendBase(location, configuredBackend) {
  const host = String(location.hostname || "").toLowerCase();
  if (!host || location.protocol === "file:") return configuredBackend || REMOTE_BACKENDS[0];
  if (DEV_HOSTNAMES.has(host)) return "";
  try {
    if (configuredBackend && new URL(configuredBackend).origin === location.origin) return "";
  } catch (e) {}
  return configuredBackend || REMOTE_BACKENDS[0];
}

const cases = [
  // No configured backend
  ["no-config: dev local server",    { hostname: "localhost", protocol: "http:", origin: "http://localhost:8000" }, "", ""],
  ["no-config: dev via 127.0.0.1",   { hostname: "127.0.0.1", protocol: "http:", origin: "http://127.0.0.1:8000" }, "", ""],
  ["no-config: prod on render",      { hostname: "ai-product-intelligence-6xfq.onrender.com", protocol: "https:", origin: "https://ai-product-intelligence-6xfq.onrender.com" }, "", REMOTE_BACKENDS[0]],
  ["no-config: github pages",        { hostname: "team.github.io", protocol: "https:", origin: "https://team.github.io" }, REMOTE_BACKENDS[0], REMOTE_BACKENDS[0]],
  ["no-config: file preview",        { hostname: "", protocol: "file:", origin: "null" }, REMOTE_BACKENDS[0], REMOTE_BACKENDS[0]],
  // Configured backend
  ["config: dev local server",       { hostname: "localhost", protocol: "http:", origin: "http://localhost:8000" }, "https://ai-product-intelligence-6xfq.onrender.com", ""],
  ["config: github pages",           { hostname: "team.github.io", protocol: "https:", origin: "https://team.github.io" }, "https://ai-product-intelligence-6xfq.onrender.com", "https://ai-product-intelligence-6xfq.onrender.com"],
  ["config: prod on render",         { hostname: "ai-product-intelligence-6xfq.onrender.com", protocol: "https:", origin: "https://ai-product-intelligence-6xfq.onrender.com" }, "https://ai-product-intelligence-6xfq.onrender.com", ""],
  ["config: file preview",           { hostname: "", protocol: "file:", origin: "null" }, "https://ai-product-intelligence-6xfq.onrender.com", "https://ai-product-intelligence-6xfq.onrender.com"],
];

for (const [name, loc, configuredBackend, expected] of cases) {
  const got = backendBase(loc, configuredBackend);
  assertEqual(name, got, expected);
}
function assertEqual(name, got, exp) {
  if (got !== exp) { console.error(`FAIL ${name}: got "${got}" want "${exp}"`); process.exit(1); }
  console.log(`OK ${name} -> "${got || "(relative/local)"}"`);
}
console.log("ALL ROUTING CASES PASS");
