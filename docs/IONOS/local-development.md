# Local development

## Checkout

After cloning update the submodules:

```
$ git submodule update --init
```

(Do this every time the config changes and needs to be reflected locally.)


## Configure .env

See the sample [`.env`](.env.ionos.sample) and copy it to the project root. Adapt values appropriately.


## Dev environment with Docker compose (or Podman compose)

Build the image once:

```
$ podman-compose -f docker-compose.dev.yaml build
```

This is needed for the first time and

* every time a backend dependency is changed (which includes merges of upstream changes)
* in some cases if backend code is changed
* the application needs to be served through the backend, not via the Vite dev server (i.e. when testing OIDC logins)


Start the containers:

```
$ podman-compose -f docker-compose.dev.yaml up
```


## Running linters, typecheckers and tests

With the containers running:

```
     host $ podman-compose -f docker-compose.dev.yaml exec frontend /bin/sh
```


```
container $ npm run ...
```

See [`customizations.md`](customizations.md) for how to run linters and typecheckers.

Run tests:

```
container $ npm run test:frontend
```
