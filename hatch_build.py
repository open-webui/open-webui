# noqa: INP001
import os
import shutil
import subprocess
from sys import stderr

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        super().initialize(version, build_data)
        stderr.write('>>> Building Open Webui frontend\n')
        npm = shutil.which('npm')
        if npm is None:
            raise RuntimeError('NodeJS `npm` is required for building Open Webui but it was not found')
        stderr.write('### npm install\n')
        subprocess.run([npm, 'install', '--force'], check=True)  # noqa: S603
        stderr.write('\n### npm run build\n')
        os.environ['APP_BUILD_HASH'] = version
        node_options = os.environ.get('NODE_OPTIONS', '')
        if '--max-old-space-size' not in node_options:
            os.environ['NODE_OPTIONS'] = f'{node_options} --max-old-space-size=8192'.strip()
        subprocess.run([npm, 'run', 'build'], check=True)  # noqa: S603
