cp -R ./node_modules/@pyscript/core/dist ./static/pyscript

# mkdir -p ./static/micropython
# cp -R ./node_modules/@micropython/micropython-webassembly-pyscript/micropython.* ./static/micropython

mkdir -p ./static/pyodide
cp ./node_modules/pyodide/pyodide* ./static/pyodide/
cp ./node_modules/pyodide/python_stdlib.zip ./static/pyodide/