/**
 * validate-architecture.mjs
 * Validates that the game follows EventBus/GameState/Constants architecture.
 * Usage: node scripts/validate-architecture.mjs [--src=src]
 */
import { readdirSync, readFileSync, statSync } from 'fs';
import { join, resolve } from 'path';
import { fileURLToPath } from 'url';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const rootDir = resolve(__dirname, '..');

const args = Object.fromEntries(
  process.argv.slice(2).map(a => {
    const [k, v] = a.replace(/^--/, '').split('=');
    return [k, v ?? true];
  })
);

const SRC_DIR = resolve(rootDir, args.src ?? 'src');

const violations = [];
const magicNumbers = [];

function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = join(dir, e.name);
    if (e.isDirectory()) {
      walk(full);
    } else if (e.isFile() && e.name.endsWith('.js')) {
      checkFile(full);
    }
  }
}

function checkFile(filePath) {
  const rel = filePath.replace(rootDir + '/', '');
  const src = readFileSync(filePath, 'utf-8');
  const lines = src.split('\n');

  const isCoreFile = rel.includes('/core/');

  // Check for magic numbers (bare numeric literals > 1 in non-constant context)
  lines.forEach((line, i) => {
    if (isCoreFile) return;
    const stripped = line.replace(/\/\/.*/g, '').replace(/'[^']*'|"[^"]*"|`[^`]*`/g, '""');
    const matches = stripped.match(/\b([2-9]\d{1,4}|[1-9]\d{2,})\b/g);
    if (matches) {
      matches.forEach(n => {
        // Ignore version numbers and common patterns
        if (!stripped.includes('version') && !stripped.includes('0x')) {
          magicNumbers.push(`${rel}:${i + 1} magic number ${n}`);
        }
      });
    }
  });

  // Scenes must not import directly from other scenes
  if (rel.includes('/scenes/')) {
    if (/from\s+['"]\.\.\/scenes\//.test(src)) {
      violations.push(`${rel}: scenes must not import directly from other scenes (use EventBus)`);
    }
  }

  // Entities must not import from scenes
  if (rel.includes('/entities/')) {
    if (/from\s+['"]\.\.\/scenes\//.test(src)) {
      violations.push(`${rel}: entities must not import from scenes`);
    }
  }
}

// Check required core files exist
const REQUIRED_CORE = ['EventBus.js', 'GameState.js', 'Constants.js'];
for (const f of REQUIRED_CORE) {
  try {
    statSync(join(SRC_DIR, 'core', f));
  } catch {
    violations.push(`missing required core file: src/core/${f}`);
  }
}

walk(SRC_DIR);

const result = {
  success: violations.length === 0,
  violations,
  magic_numbers: magicNumbers,
};

console.log(JSON.stringify(result, null, 2));
process.exit(violations.length > 0 ? 1 : 0);
