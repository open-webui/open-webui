// Normal builds only read committed files. No Rust or network required.
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join, posix } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('../../', import.meta.url));
const source = 'crypto/encryption';
const artifact = 'src/lib/encryption/vendor';
const hash = (data) => createHash('sha256').update(data).digest('hex');
function files(dir) {
	return readdirSync(join(root, dir), { withFileTypes: true })
		.flatMap((e) => {
			if (e.name === 'target' || e.name.startsWith('.')) return [];
			const path = posix.join(dir, e.name);
			return e.isDirectory() ? files(path) : [path];
		})
		.sort();
}
const inputs = [
	...files(source),
	'scripts/encryption/build.py',
	'scripts/encryption/artifact.mjs'
].sort();
const sourceFingerprint = hash(
	inputs
		.map((p) => `${p}\0${hash(readFileSync(join(root, p), 'utf8').replaceAll('\r\n', '\n'))}`)
		.join('\n')
);
const manifestPath = join(root, artifact, 'manifest.json');
if (process.argv.includes('--write')) {
	const metadata = JSON.parse(
		readFileSync(process.argv[process.argv.indexOf('--metadata') + 1], 'utf8')
	);
	const checksums = Object.fromEntries(
		files(artifact)
			.filter((p) => !p.endsWith('/manifest.json'))
			.map((p) => [posix.relative(artifact, p), hash(readFileSync(join(root, p)))])
	);
	writeFileSync(
		manifestPath,
		JSON.stringify(
			{
				format: 1,
				sourceFingerprint,
				sourceRevision: process.env.CRYPTO_SOURCE_REVISION,
				toolchain: '1.95.0',
				wasmBindgen: '0.2.126',
				dependencies: metadata.packages.map(({ name, version, license }) => ({
					name,
					version,
					license
				})),
				checksums
			},
			null,
			2
		) + '\n'
	);
} else {
	const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
	if (manifest.sourceFingerprint !== sourceFingerprint)
		throw Error('Encryption source changed: rebuild and review the artifact.');
	const actual = files(artifact)
		.filter((p) => !p.endsWith('/manifest.json'))
		.map((p) => posix.relative(artifact, p))
		.sort();
	if (JSON.stringify(actual) !== JSON.stringify(Object.keys(manifest.checksums).sort()))
		throw Error('Unexpected crypto artifact files');
	for (const [p, digest] of Object.entries(manifest.checksums)) {
		if (hash(readFileSync(join(root, artifact, p))) !== digest)
			throw Error(`Crypto artifact checksum mismatch: ${p}`);
	}
	console.log('Encryption artifact source and checksums verified');
}
