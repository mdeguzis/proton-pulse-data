// Test helper: load ES module source(s) into a vm context by stripping the
// import/export syntax and concatenating, the same approach used in
// adminAuth.test.js and appRenderCallers.test.js. Jest here has no ESM
// transform, so this lets tests exercise js/shared and js/* modules.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

function stripModuleSyntax(src) {
  return src
    .replace(/^(import|export\s+\{[^}]*\}\s+from|export\s+default)\s.*$/gm, '')
    .replace(/^export\s+(async\s+)?(function|class|const|let|var)\s/gm, '$1$2 ')
    // drop self-referential window bridges (const X = window.X) that collide in
    // the flattened vm scope
    .replace(/^(?:const|let|var)\s+(\w+)\s*=\s*window\.\1\s*;?\s*$/gm, '')
    // top-level const/let do not become vm-context properties; var does, so the
    // caller can read exported objects/values off the returned context
    .replace(/^(?:const|let)\s/gm, 'var ');
}

// files: array of paths relative to repo root. ctx: extra globals for the vm.
// Returns the contextified object (all top-level declarations are properties).
function loadEsm(files, ctx = {}) {
  const ROOT = path.join(__dirname, '..');
  vm.createContext(ctx);
  for (const f of files) {
    const src = stripModuleSyntax(fs.readFileSync(path.join(ROOT, f), 'utf8'));
    vm.runInContext(src, ctx, { filename: f });
  }
  return ctx;
}

module.exports = { loadEsm, stripModuleSyntax };
