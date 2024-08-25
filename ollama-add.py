# ollama-add.py

import importlib

ollama_common = importlib.import_module("ollama-common")
phrases = ollama_common.phrases

def remove_initial_hash_from_file(phrases):
    for filename, phrase_list in phrases.items():
        # Print the filename to the terminal
        print(f"Processing file: {filename}")

        # Read lines from the file
        with open(filename, 'r') as file:
            lines = file.readlines()

        # Process the lines to remove initial '#' where necessary
        updated_lines = []
        for line in lines:
            stripped_line = line.lstrip('#').strip()  # Remove initial '#' and then any leading spaces
            #print(f"{stripped_line}")
            for phrase in phrase_list:
                if stripped_line == phrase:
                    if line.startswith('#'):
                        updated_lines.append(line[1:])  # Remove the initial '#' and retain spaces
                    else:
                        updated_lines.append(line)
                    break
            else:
                updated_lines.append(line)

        # Write the updated lines back to the file
        with open(filename, 'w') as file:
            file.writelines(updated_lines)

# Call the function to process all files listed in the phrases dictionary
remove_initial_hash_from_file(phrases)

