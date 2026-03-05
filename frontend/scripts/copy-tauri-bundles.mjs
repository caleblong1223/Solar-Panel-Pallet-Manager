import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendDir = path.resolve(__dirname, "..");
const bundleDir = path.join(frontendDir, "src-tauri", "target", "release", "bundle");
const outputDir = path.join(frontendDir, "dist", "installers");

async function copyInstallers() {
  await fs.mkdir(outputDir, { recursive: true });

  const candidates = [];
  const installerDirs = ["nsis", "msi", "dmg"];
  const installerExtensions = [".exe", ".msi", ".dmg"];

  for (const subDir of installerDirs) {
    const directory = path.join(bundleDir, subDir);
    try {
      const entries = await fs.readdir(directory, { withFileTypes: true });
      for (const entry of entries) {
        if (!entry.isFile()) {
          continue;
        }
        const fileName = entry.name.toLowerCase();
        if (installerExtensions.some((ext) => fileName.endsWith(ext))) {
          candidates.push(path.join(directory, entry.name));
        }
      }
    } catch {
      // Ignore missing bundle subdirectories.
    }
  }

  let copied = 0;
  for (const sourcePath of candidates) {
    const fileName = path.basename(sourcePath);
    const destinationPath = path.join(outputDir, fileName);
    await fs.copyFile(sourcePath, destinationPath);
    copied += 1;
    console.log(`Copied ${fileName} -> ${destinationPath}`);
  }

  if (copied === 0) {
    throw new Error(`No installer artifacts found under ${bundleDir}`);
  }

  console.log(`Installer output folder: ${outputDir}`);
}

copyInstallers().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
