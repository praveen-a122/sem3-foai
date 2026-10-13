const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const electronFolder = path.join(__dirname, "node_modules", "electron");
const binaryPath = path.join(
  electronFolder,
  "dist",
  process.platform === "win32" ? "electron.exe" : "electron"
);
const installerPath = path.join(
  __dirname,
  "node_modules",
  ".bin",
  process.platform === "win32" ? "install-electron.cmd" : "install-electron"
);
const fallbackMirror = "https://npmmirror.com/mirrors/electron/";

function binaryExists() {
  return fs.existsSync(binaryPath);
}

function runInstall(label, env) {
  console.log(`\n[MindSpring] ${label}`);

  let result;
  if (process.platform === "win32") {
    // .cmd files must be run through cmd.exe on Windows.
    result = spawnSync(
      process.env.ComSpec || "cmd.exe",
      ["/d", "/c", `"${installerPath}" --no`],
      { cwd: __dirname, env, stdio: "inherit", windowsHide: true }
    );
  } else {
    result = spawnSync(installerPath, ["--no"], {
      cwd: __dirname,
      env,
      stdio: "inherit"
    });
  }

  if (result.error) {
    console.error(`[MindSpring] Could not start the installer: ${result.error.message}`);
  }

  return binaryExists();
}

if (binaryExists()) {
  console.log("[MindSpring] Electron binary is already installed.");
  process.exit(0);
}

if (!fs.existsSync(path.join(electronFolder, "package.json"))) {
  console.error("[MindSpring] Electron's npm package is missing.");
  console.error("From this folder, run: npm install");
  process.exit(1);
}

if (!fs.existsSync(installerPath)) {
  console.error("[MindSpring] The install-electron command is missing.");
  console.error("Try reinstalling the project dependencies with: npm install");
  process.exit(1);
}

const originalMirror = process.env.ELECTRON_MIRROR || "";
const primaryEnv = { ...process.env };
if (runInstall("Checking/downloading the Electron binary...", primaryEnv)) {
  process.exit(0);
}

if (originalMirror.replace(/\/$/, "") !== fallbackMirror.replace(/\/$/, "")) {
  const fallbackEnv = {
    ...process.env,
    ELECTRON_MIRROR: fallbackMirror,
    force_no_cache: "true"
  };

  console.warn("\n[MindSpring] The first download did not complete. Retrying with the alternate Electron mirror.");
  if (runInstall(`Retrying through ${fallbackMirror}`, fallbackEnv)) {
    process.exit(0);
  }
}

console.error("\n[MindSpring] Electron's desktop binary still could not be downloaded.");
console.error("This happens before the game starts and usually means the current network cannot reach the download host.");
console.error("Try another network, or configure your network proxy and run this again.");
console.error("Manual retry from the electron folder:");
console.error("  npx install-electron --no");
console.error("Optional mirror retry in PowerShell:");
console.error('  $env:ELECTRON_MIRROR = "https://npmmirror.com/mirrors/electron/"');
console.error("  npx install-electron --no");
process.exit(1);
