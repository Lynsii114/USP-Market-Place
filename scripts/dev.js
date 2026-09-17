const { spawn } = require("node:child_process");

const commands = [
  ["backend", "npm run backend"],
  ["frontend", "npm run frontend"],
];

const children = commands.map(([name, command]) => {
  const child = spawn(commandShell(), commandArgs(command), {
    cwd: process.cwd(),
    stdio: "inherit",
    shell: false,
  });

  child.on("error", (error) => {
    console.error(`${name} failed to start: ${error.message}`);
    shutdown(1);
  });

  child.on("exit", (code, signal) => {
    if (shuttingDown) return;
    if (code !== 0) {
      console.error(`${name} stopped unexpectedly${signal ? ` (${signal})` : ""}.`);
      shutdown(code || 1);
    }
  });

  return child;
});

let shuttingDown = false;

function shutdown(code = 0) {
  if (shuttingDown) return;
  shuttingDown = true;

  for (const child of children) {
    if (!child.killed) child.kill("SIGINT");
  }

  setTimeout(() => process.exit(code), 300);
}

process.on("SIGINT", () => shutdown(0));
process.on("SIGTERM", () => shutdown(0));

function commandShell() {
  return process.platform === "win32" ? "cmd.exe" : "/bin/sh";
}

function commandArgs(command) {
  return process.platform === "win32"
    ? ["/d", "/s", "/c", command]
    : ["-c", command];
}
