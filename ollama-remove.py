# ollama-remove.py

import importlib

ollama_common = importlib.import_module("ollama-common")
phrases = ollama_common.phrases

input_file = 'docker-compose.api.yaml'

with open(input_file, 'r') as file:
    lines = file.readlines()

with open(input_file, 'w') as file:
    for line in lines:
        stripped_line = line.lstrip().rstrip()
        if any(stripped_line == phrase for phrase in phrases["docker-compose.api.yaml"]):
            indentation = len(line) - len(line.lstrip())
            file.write(' ' * indentation + f'#{line.lstrip()}')
        else:
            file.write(line)
