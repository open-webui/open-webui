# Pyodide JavaScript package

<a href="https://www.npmjs.com/package/pyodide"><img src="https://img.shields.io/npm/v/pyodide" alt="npm"></a>

## Usage

Download and extract Pyodide packages from [Github
releases](https://github.com/pyodide/pyodide/releases)
(`pyodide-build-*.tar.bz2`). The version of the release needs to match exactly the version of this package.

Then you can load Pyodide in Node.js as follows,

```js
// hello_python.js
const { loadPyodide } = require("pyodide");

async function hello_python() {
  let pyodide = await loadPyodide({
    indexURL: "<pyodide artifacts folder>",
  });
  return pyodide.runPythonAsync("1+1");
}

hello_python().then((result) => {
  console.log("Python says that 1+1 =", result);
});
```

```
$ node hello_python.js
Python says that 1+1= 2
```

Or you can use the REPL. To start the Node.js REPL with support for top level
await, use `node --experimental-repl-await`:

```
$ node --experimental-repl-await
Welcome to Node.js v18.5.0.
Type ".help" for more information.
> const { loadPyodide } = require("pyodide");
undefined
> let pyodide = await loadPyodide();
undefined
> await pyodide.runPythonAsync("1+1");
2
```

## Details

The JavaScript code in this package is responsible for the following tasks:

1. Defines the public [JavaScript API](https://pyodide.org/en/stable/usage/api/js-api.html)
   - Package loading code to allow loading of other Python packages.
   - Can load
     [micropip](https://pyodide.org/en/stable/usage/api/micropip-api.html) to
     bootstrap loading of pure Python wheels
2. Loads the CPython interpreter and the core/pyodide emscripten application
   which embeds the interpreter.
3. Injects the `js/pyodide` JavaScript API into `sys.modules`. This is the
   final runtime dependency for `core/pyodide` & `py/pyodide`, so after this step
   the interpreter is fully up and running.
