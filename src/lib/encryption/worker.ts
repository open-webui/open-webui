import init, { Session } from './vendor/encryption';
import wasmUrl from './vendor/encryption_bg.wasm?url';

let session: Session | undefined;
let queue = Promise.resolve();
const ready = init({ module_or_path: wasmUrl });
const allowed = new Set([
	'public_key',
	'key_package',
	'create',
	'join',
	'add',
	'remove',
	'update',
	'commit_updates',
	'encrypt',
	'process',
	'members'
]);

self.onmessage = ({ data }) => {
	queue = queue.then(async () => {
		try {
			await ready;
			let result: unknown;
			if (data.method === 'init' && !session) {
				session = new Session(data.args[0], data.args[1]);
			} else if (session && allowed.has(data.method)) {
				result = (session[data.method as keyof Session] as Function).apply(session, data.args);
			} else {
				throw new Error();
			}
			self.postMessage({ id: data.id, result });
		} catch {
			// Fail closed; do not serialize library exceptions or input into logs.
			self.postMessage({ id: data.id, error: true });
			session?.free();
			session = undefined;
			self.close();
		}
	});
};
