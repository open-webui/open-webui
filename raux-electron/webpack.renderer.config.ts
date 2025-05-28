import type { Configuration } from 'webpack';
import * as path from 'path';
import * as fs from 'fs';
import webpack from 'webpack';
import CopyPlugin from 'copy-webpack-plugin';

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
  new CopyPlugin({
    patterns: [
      { from: 'src/pages', to: 'pages' },
    ],
  }),
];

rules.push({
  test: /\.css$/,
  use: [{ loader: 'style-loader' }, { loader: 'css-loader' }],
});

export const rendererConfig: Configuration = {
  module: {
    rules,
  },
  plugins: allPlugins,
  resolve: {
    extensions: ['.js', '.ts', '.jsx', '.tsx', '.css', '.json'],
  },
};
