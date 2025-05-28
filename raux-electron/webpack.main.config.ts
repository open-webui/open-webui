import type { Configuration } from 'webpack';
import type { ForgeConfig } from '@electron-forge/shared-types';
import { FusesPlugin } from '@electron-forge/plugin-fuses';
import { FuseV1Options, FuseVersion } from '@electron/fuses';
import * as path from 'path';
import * as fs from 'fs';
import webpack from 'webpack';
import CopyWebpackPlugin from 'copy-webpack-plugin';

import { rules } from './webpack.rules';
import { plugins } from './webpack.plugins';

// Read the package.json file to get RAUX version
const packageJsonPath = path.resolve(__dirname, 'package.json');
const packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
const rauxVersion = packageJson['raux-version'] || 'latest';

// Create a new array with all existing plugins plus our DefinePlugin
const allPlugins = [
  ...plugins,
  // Define RAUX_VERSION as a global constant available at runtime
  new webpack.DefinePlugin({
    'process.env.RAUX_VERSION': JSON.stringify(rauxVersion),
  }),
  new CopyWebpackPlugin({
    patterns: [
      {
        from: path.resolve(__dirname, 'static'),
        to: path.resolve(__dirname, '.webpack/static'),
        globOptions: {
          ignore: ['**/.*'], // ignore hidden files
        },
        noErrorOnMissing: true,
      },
    ],
  }),
];

export const mainConfig: Configuration = {
  /**
   * This is the main entry point for your application, it's the first file
   * that runs in the main process.
   */
  entry: './src/index.ts',
  // Put your normal webpack config below here
  module: {
    rules,
  },
  plugins: allPlugins,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
  },
};

export default mainConfig;
