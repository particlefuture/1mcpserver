#!/usr/bin/env node

const { spawnSync } = require("child_process");
const process = require("process");

const args = process.argv.slice(2);

let port = "8080";
let local = false;

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--local") local = true;
  if (args[i] === "-p" || args[i] === "--port") {
    port = args[i + 1];
    i++;
  }
}

const dockerArgs = [
  "run",
  "--rm",
  "-i",
  "-v", `${process.cwd()}:/data`,
];

if (!local) {
  dockerArgs.push("-p", `${port}:8080`);
}

dockerArgs.push("ghcr.io/particlefuture/1mcpserver:latest");

if (local) dockerArgs.push("--local");

const result = spawnSync("docker", dockerArgs, { stdio: "inherit" });
process.exit(result.status ?? 1);
