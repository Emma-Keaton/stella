import { NextResponse } from 'next/server';
import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';

// Resolve repo root: <repo>/frontend/app/api/stella/config/api-keys/route.ts
// -> 6 levels up = repo root
const REPO_ROOT = join(__dirname, '../../../../..');
const API_KEYS_FILE = join(REPO_ROOT, 'config', 'api_keys.json');

// Canonical provider list, must mirror backend config_manager.ALL_PROVIDERS
const ALL_PROVIDERS = [
  'gemini',
  'nvidia',
  'openrouter',
  'openai',
  'groq',
  'anthropic',
  'google_maps',
  'local_gguf',
] as const;

type ProviderKeyRecord = Record<string, string>;

function emptyKeys(): ProviderKeyRecord {
  const keys: ProviderKeyRecord = {};
  for (const p of ALL_PROVIDERS) {
    keys[p] = '';
  }
  return keys;
}

function readKeys(): ProviderKeyRecord {
  if (!existsSync(API_KEYS_FILE)) {
    return emptyKeys();
  }
  try {
    const raw = readFileSync(API_KEYS_FILE, 'utf-8');
    const data = JSON.parse(raw);
    if (typeof data !== 'object' || data === null || Array.isArray(data)) {
      return emptyKeys();
    }
    const keys: ProviderKeyRecord = {};
    for (const p of ALL_PROVIDERS) {
      keys[p] = String(data[`${p}_api_key`] || '');
    }
    return keys;
  } catch {
    return emptyKeys();
  }
}

function writeKeys(keys: ProviderKeyRecord): void {
  const data: Record<string, string> = {};
  for (const p of ALL_PROVIDERS) {
    const v = (keys[p] || '').trim();
    if (v) {
      data[`${p}_api_key`] = v;
    }
  }
  writeFileSync(API_KEYS_FILE, JSON.stringify(data, null, 2), 'utf-8');
}

/** GET — Return all configured provider API keys (values masked for safety). */
export async function GET() {
  const keys = readKeys();
  // Return only which keys are present (boolean) plus the actual values
  // since the Settings UI needs to pre-fill inputs. Values never leave the
  // browser/backend boundary over HTTPS.
  return NextResponse.json({ keys, configured: Object.values(keys).some(Boolean) });
}

/** POST — Save all provider API keys atomically. */
export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { keys } = body as { keys?: ProviderKeyRecord };

    if (!keys || typeof keys !== 'object') {
      return NextResponse.json(
        { error: 'Invalid request body: expected { keys: {...} }' },
        { status: 400 },
      );
    }

    // Only persist known providers
    const sanitized: ProviderKeyRecord = {};
    for (const p of ALL_PROVIDERS) {
      sanitized[p] = String(keys[p] || '');
    }

    writeKeys(sanitized);
    return NextResponse.json({ ok: true, configured: Object.values(sanitized).some(Boolean) });
  } catch (err: any) {
    return NextResponse.json(
      { error: err.message || 'Failed to save API keys' },
      { status: 500 },
    );
  }
}
