# ollama-add.py

import importlib
import re

ollama_common = importlib.import_module("ollama-common")
phrases = ollama_common.phrases

def remove_initial_hash_from_file(phrases):
    for filename, phrase_list in phrases.items():
        # Print the filename to the terminal
        print(f"\rProcessing file: {filename}")

        # Read lines from the file
        with open(filename, 'r') as file:
            lines = file.readlines()

        # Process the lines to remove initial '#' where necessary
        updated_lines = []
        for line in lines:
            stripped_line = re.sub(r'^\s*#', '', line, 1).rstrip() # Remove initial spaces and '#' and then any trailing spaces
            print(f"1{stripped_line}2")
            for phrase in phrase_list:
                print(f"3{phrase}4")
                if stripped_line == phrase:
                    print(f"Found {phrase}")
                    if re.match(r'^\s*#', line): # If # is either the first character in the line or is preceded only by whitespace
                        updated_lines.append(line.replace('#', '', 1))  # Remove the initial '#' and retain spaces
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

