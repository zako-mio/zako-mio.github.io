import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export interface GateEntry {
  script: string;
  reads: string;
  selftest?: boolean;
}

export interface CapabilityUse {
  key: string;
  artifact: string;
  note: string;
}

export interface GateManifest {
  schema_version: number;
  note: string;
  gates: GateEntry[];
  capability_uses: CapabilityUse[];
}

const MANIFEST_PATH = 'scripts/gate-manifest.json';

/**
 * 门控与能力层取用的声明式清单（构建期读取）。
 *
 * ★ 为什么 fail-closed（⛔ 不给兜底默认值）：本文件**在仓库内**，
 *   它缺失或损坏意味着「本站做法」的声明面已经不可信；
 *   与本仓库其它 loader（`site.config.json` → `DEFAULTS`）不同，
 *   那里的默认值等价于"按约定配置"，这里的默认值会变成**第二真相源**。
 * ★ 一致性由 `scripts/gate_ia_division.py` 的 `A7`/`A8` 机检：
 *   声明的脚本必须存在、声明 `selftest: true` 的必须真的支持 `--selftest`、
 *   且 `scripts/` 下符合命名约定的门控必须都已在清单中（漏登记即 FAIL）。
 */
export function loadGateManifest(): GateManifest {
  const raw = readFileSync(resolve(process.cwd(), MANIFEST_PATH), 'utf8');
  const parsed = JSON.parse(raw) as GateManifest;
  if (!Array.isArray(parsed.gates) || !Array.isArray(parsed.capability_uses)) {
    throw new Error(`${MANIFEST_PATH}: gates / capability_uses 必须为数组`);
  }
  return parsed;
}
