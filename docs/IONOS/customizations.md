# Customizations

## Goals

* Customized UI
* Upstream-compatibility to benefit from updates with as little merge conflict potential as possible
* As little dead code (unreferenced compoents, unused props) as possible


## Approach

### For elements to be removed

1. use configs wherever possible
2. add configs wherever sensible (as in possibly upstreamable)
3. remove elements

### For elements to change

1. add configurabilitsy (when upstreaming looks reasonable)
2. change or replace by custom component

### For new functionality

1. add in own namespace

### Changes or new

For Typescript and Svelte use a file tree under `src/lib/IONOS` that mirrors `src/lib`.




