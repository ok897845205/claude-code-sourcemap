/**
 * validate-architecture.mjs
 * Validates EventBus/GameState/Constants architecture for Three.js game.
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const rootDir = resolve(__dirname, '..');
const SRC_DIR = resolve(rootDir, 'src');

const violations = [];
const magicNumbers = [];

function walk(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, e.name);
    if (e.isDirectory()) walk(full);
    else if (e.isFile() && e.name.endsWith('.js')) checkFile(full);
  }
}

function checkFile(filePath) {
  const rel = filePath.replace(rootDir + '/', '');
  const src = readFileSync(filePath, 'utf-8');
  const isCoreFile = rel.includes('/core/');

  src.split('\n').forEach((line, i) => {
    if (isCoreFile) return;
    const stripped = line.replace(/\/\/.*/g, '').replace(/'[^']*'|"[^"]*"|`[^`]*`/g, '""');
    const matches = stripped.match(/\b([2-9]\d{1,4}|[1-9]\d{2,})\b/g);
    if (matches) {
      matches.forEach(n => {
        if (!stripped.includes('version')) magicNumbers.push(`${rel}:${i + 1} magic number ${n}`);
      });
    }
  });

  if (rel.includes('/entities/') && /from\s+['"]\.\.\/orchestrator\//.test(src)) {
    violations.push(`${rel}: entities must not import from orchestrator (use EventBus)`);
  }
}

const REQUIRED_CORE = ['EventBus.js', 'GameState.js', 'Constants.js'];
for (const f of REQUIRED_CORE) {
  try { statSync(join(SRC_DIR, 'core', f)); }
  catch { violations.push(`missing required core file: src/core/${f}`); }
}

walk(SRC_DIR);

const result = { success: violations.length === 0, violations, magic_numbers: magicNumbers };
console.log(JSON.stringify(result, null, 2));
process.exit(violations.length > 0 ? 1 : 0);
