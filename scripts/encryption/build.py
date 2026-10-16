"""Manual artifact release only; never invoked by the application build."""

import json
import os
import subprocess
import tempfile
from functools import cache
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'crypto/encryption'
OUTPUT = ROOT / 'src/lib/encryption/vendor'


def run(*args, **kwargs):
    return subprocess.run(args, cwd=SOURCE, check=True, **kwargs)


run('cargo', 'test', '--locked')
run('cargo', 'build', '--locked', '--release', '--target', 'wasm32-unknown-unknown')
run(
    'wasm-bindgen',
    '--target',
    'web',
    '--out-name',
    'encryption',
    '--out-dir',
    str(OUTPUT),
    str(SOURCE / 'target/wasm32-unknown-unknown/release/encryption.wasm'),
)
# Use Cargo's actual target build graph, excluding tests and unused optional crates.
metadata = json.loads(run('cargo', 'metadata', '--locked', '--format-version', '1', capture_output=True).stdout)
tree = run(
    'cargo',
    'tree',
    '--locked',
    '--target',
    'wasm32-unknown-unknown',
    '--edges',
    'normal,build',
    '--prefix',
    'none',
    '--format',
    '{p}',
    capture_output=True,
).stdout.decode()
used = {tuple(line.split()[:2]) for line in tree.splitlines()}
metadata['packages'] = [p for p in metadata['packages'] if (p['name'], 'v' + p['version']) in used]
assert {(p['name'], 'v' + p['version']) for p in metadata['packages']} == used


@cache
def download(url):
    with urlopen(url, timeout=30) as response:
        return response.read().decode('utf-8')


texts = {}
notices = [
    'Third-Party Licenses',
    '===================',
    '',
    'Scope: Encryption WebAssembly artifact and its build-time dependencies.',
    'Packages are listed alphabetically with references to the full license and notice texts below.',
    'Identical texts are included once; package-specific copyright notices are preserved.',
    'Source code, including MPL-2.0 dependencies, is available at each Source URL below.',
]
for package in sorted(metadata['packages'], key=lambda p: (p['name'], p['version'])):
    if package['source'] is None:
        continue  # The local wrapper is not a third-party dependency.
    license = package['license'] or ''
    choices = {
        'MIT',
        'Apache-2.0',
        'BSD-2-Clause',
        'BSD-3-Clause',
        'ISC',
        'Unicode-3.0',
        'Zlib',
        'CC0-1.0',
        'Unlicense',
        'MPL-2.0',
    }
    if not any(x.strip(' ()') in choices for x in license.replace('/', ' OR ').split(' OR ')):
        raise RuntimeError(f'Review dependency license: {package["name"]} {license}')
    directory = Path(package['manifest_path']).parent
    documents = {
        path.name: path.read_text()
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name.upper().startswith(('LICENSE', 'COPYING', 'NOTICE'))
    }
    if package.get('license_file'):
        path = directory / package['license_file']
        documents[path.name] = path.read_text()
    if not documents:
        # Some published crates omit the workspace license; use their exact source revision.
        if license == 'MPL-2.0':
            url = 'https://www.mozilla.org/media/MPL/2.0/index.txt'
            expected = 'Mozilla Public License Version 2.0'
        else:
            repository = urlparse(package['repository'])
            if repository.netloc != 'github.com' or license not in ('MIT', 'Apache-2.0'):
                raise RuntimeError(f'Missing license notice: {package["name"]}')
            repo = '/'.join(repository.path.strip('/').split('/')[:2])
            revision = json.loads((directory / '.cargo_vcs_info.json').read_text())['git']['sha1']
            url = f'https://raw.githubusercontent.com/{repo}/{revision}/LICENSE'
            expected = 'Permission is hereby granted' if license == 'MIT' else 'Apache License'
        documents[url] = download(url)
        if expected not in documents[url]:
            raise RuntimeError(f'Unexpected license notice: {url}')
    references = []
    for name, text in documents.items():
        text = text.strip()
        if not text:
            raise RuntimeError(f'Empty license notice: {package["name"]}/{name}')
        number = texts.setdefault(text, len(texts) + 1)
        references.append(f'{name}: [{number}]')
    notices.append(
        f'\nPackage: {package["name"]}\nVersion: {package["version"]}\nLicense: {license}\n'
        f'Source: https://crates.io/api/v1/crates/{package["name"]}/{package["version"]}/download\n'
        + '\n'.join(references)
    )
notices.extend(
    f'\nLicense and notice text [{number}]\n--------------------------------\n{text}' for text, number in texts.items()
)
(OUTPUT / 'THIRD_PARTY_LICENSES.txt').write_text('\n'.join(notices) + '\n')
with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as temp:
    json.dump(metadata, temp)
    temp.flush()
    env = dict(
        os.environ,
        CRYPTO_SOURCE_REVISION=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
    )
    subprocess.run(
        ['node', str(ROOT / 'scripts/encryption/artifact.mjs'), '--write', '--metadata', temp.name], check=True, env=env
    )
