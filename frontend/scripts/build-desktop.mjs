import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const tauriDir = path.join(frontendDir, "src-tauri");
const tauriConfigPath = path.join(tauriDir, "tauri.conf.json");

function runOrThrow(command, args, cwd) {
  const result = spawnSync(command, args, {
    cwd,
    stdio: "inherit",
    shell: false,
    env: process.env,
  });
  if (result.error) {
    throw result.error;
  }
  if ((result.status ?? 1) !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}`);
  }
}

function cleanupMountedDmgDevices() {
  const list = spawnSync("bash", ["-lc", "hdiutil info | awk '/\\/Volumes\\/dmg\\./ {print $1}'"], {
    stdio: ["ignore", "pipe", "ignore"],
    shell: false,
    env: process.env,
  });
  const devices = (list.stdout?.toString("utf8") ?? "")
    .split("\n")
    .map((value) => value.trim())
    .filter(Boolean);

  for (const device of devices) {
    spawnSync("hdiutil", ["detach", device, "-force"], {
      stdio: "ignore",
      shell: false,
      env: process.env,
    });
  }
}

function getArchTag() {
  if (process.arch === "arm64") {
    return "aarch64";
  }
  if (process.arch === "x64") {
    return "x64";
  }
  return process.arch;
}

function buildMacDmg() {
  const config = JSON.parse(fs.readFileSync(tauriConfigPath, "utf8"));
  const productName = config.productName ?? "Pallet Manager";
  const version = config.version ?? "0.0.0";
  const arch = getArchTag();
  const dmgName = `${productName}_${version}_${arch}.dmg`;

  const appPath = path.join(tauriDir, "target", "release", "bundle", "macos", `${productName}.app`);
  const dmgDir = path.join(tauriDir, "target", "release", "bundle", "dmg");
  const dmgPath = path.join(dmgDir, dmgName);
  const dmgScript = path.join(dmgDir, "bundle_dmg.sh");

  if (!fs.existsSync(appPath)) {
    throw new Error(`Expected app bundle not found: ${appPath}`);
  }
  if (!fs.existsSync(dmgScript)) {
    throw new Error(`Expected DMG script not found: ${dmgScript}`);
  }
  if (fs.existsSync(dmgPath)) {
    fs.rmSync(dmgPath);
  }

  cleanupMountedDmgDevices();
  let lastError = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const result = spawnSync("bash", [dmgScript, dmgName, appPath], {
      cwd: dmgDir,
      stdio: "inherit",
      shell: false,
      env: process.env,
    });
    if (!result.error && (result.status ?? 1) === 0) {
      return;
    }
    lastError = result.error ?? new Error(`DMG build attempt ${attempt + 1} failed with status ${result.status}`);
    cleanupMountedDmgDevices();
  }
  throw lastError ?? new Error("DMG build failed");
}

function main() {
  runOrThrow("npx", ["tauri", "build", "--bundles", "app"], frontendDir);

  if (process.platform === "darwin") {
    buildMacDmg();
  }

  runOrThrow("node", ["scripts/copy-tauri-bundles.mjs"], frontendDir);
}

main();
