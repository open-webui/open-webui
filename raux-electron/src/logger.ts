import log from 'electron-log';
import { getAppInstallDir } from './envUtils';
import { join, dirname } from 'path';
import { existsSync, mkdirSync, writeFileSync } from 'fs';


const logPath = join(getAppInstallDir(), 'raux.log');

const logDir = dirname(logPath);

if (!existsSync(logDir)) {
  mkdirSync(logDir, { recursive: true });
}

writeFileSync(logPath, `Main process started\nArgs: ${process.argv.join(' ')}\n`, { flag: 'a' });

console.log('RAUX log file path:', logPath);

// Set log file location
log.transports.file.resolvePath = () => logPath;

export function logInfo(message: string) {
  log.info(message);
}

export function logError(message: string) {
  log.error(message);
}
