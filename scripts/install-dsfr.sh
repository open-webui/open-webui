#!/bin/sh

# Copy DSFR files to static
mkdir -p static/utility
cp -R \
  node_modules/@gouvfr/dsfr/dist/dsfr.min.css \
  node_modules/@gouvfr/dsfr/dist/dsfr.module.min.js \
  node_modules/@gouvfr/dsfr/dist/dsfr.module.min.js.map \
  node_modules/@gouvfr/dsfr/dist/dsfr.nomodule.min.js \
  node_modules/@gouvfr/dsfr/dist/dsfr.nomodule.min.js.map \
  node_modules/@gouvfr/dsfr/dist/favicon \
  node_modules/@gouvfr/dsfr/dist/fonts \
  node_modules/@gouvfr/dsfr/dist/icons \
  static/
cp -R \
  node_modules/@gouvfr/dsfr/dist/utility/utility.min.css \
  static/utility/
