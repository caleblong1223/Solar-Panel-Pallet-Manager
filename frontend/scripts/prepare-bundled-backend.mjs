import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendDir, "..");
const backendDir = path.join(repoRoot, "backend");

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

function resolvePythonCommand() {
  if (process.platform === "win32") {
    const pyProbe = spawnSync("py", ["-3.11", "--version"], {
      stdio: "ignore",
      shell: false,
      env: process.env,
    });
    if ((pyProbe.status ?? 1) === 0) {
      return { command: "py", args: ["-3.11"] };
    }
  }
  return { command: "python", args: [] };
}

function resolveBundledPython() {
  const candidates = process.platform === "win32"
    ? [path.join(backendDir, ".venv", "Scripts", "python.exe")]
    : [
        path.join(backendDir, ".venv", "bin", "python3"),
        path.join(backendDir, ".venv", "bin", "python"),
      ];
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function ensureBackendVenv() {
  const bundledPython = resolveBundledPython();
  if (!bundledPython) {
    const python = resolvePythonCommand();
    runOrThrow(python.command, [...python.args, "-m", "venv", ".venv"], backendDir);
  }

  const pythonPath = resolveBundledPython();
  if (!pythonPath) {
    throw new Error("Bundled backend virtualenv was not created successfully.");
  }

  runOrThrow(pythonPath, ["-m", "pip", "install", "--upgrade", "pip"], backendDir);
  runOrThrow(pythonPath, ["-m", "pip", "install", "-e", "."], backendDir);
}

ensureBackendVenv();
