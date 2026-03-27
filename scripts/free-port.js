import { execSync } from 'node:child_process';

const portArg = process.argv[2];
const port = Number(portArg);

if (!Number.isInteger(port) || port <= 0 || port > 65535) {
	console.error(`[free-port] Invalid port: ${portArg}`);
	process.exit(1);
}

const run = (cmd) => {
	try {
		return execSync(cmd, { stdio: ['ignore', 'pipe', 'pipe'] }).toString();
	} catch {
		return '';
	}
};

const killOnWindows = (targetPort) => {
	const output = run('netstat -ano -p tcp');
	if (!output) return;

	const pids = new Set();
	for (const line of output.split(/\r?\n/)) {
		const normalized = line.trim().replace(/\s+/g, ' ');
		if (!normalized) continue;
		if (!normalized.includes('LISTENING')) continue;
		if (!normalized.includes(`:${targetPort}`)) continue;

		const parts = normalized.split(' ');
		const pid = parts[parts.length - 1];
		if (/^\d+$/.test(pid)) pids.add(pid);
	}

	for (const pid of pids) {
		if (String(process.pid) === pid) continue;
		run(`taskkill /F /PID ${pid}`);
		console.log(`[free-port] Killed PID ${pid} on port ${targetPort}`);
	}
};

const killOnUnix = (targetPort) => {
	const output = run(`lsof -ti tcp:${targetPort}`);
	if (!output) return;

	const pids = output
		.split(/\r?\n/)
		.map((v) => v.trim())
		.filter((v) => /^\d+$/.test(v));

	for (const pid of pids) {
		if (String(process.pid) === pid) continue;
		run(`kill -9 ${pid}`);
		console.log(`[free-port] Killed PID ${pid} on port ${targetPort}`);
	}
};

if (process.platform === 'win32') {
	killOnWindows(port);
} else {
	killOnUnix(port);
}
