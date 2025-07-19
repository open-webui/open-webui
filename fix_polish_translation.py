#!/usr/bin/env python3
import re

# Read the file
with open('src/lib/i18n/locales/pl-PL/translation.json', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to match conflict markers
conflict_pattern = r'<<<<<<< HEAD\n.*?\n=======\n(.*?)\n>>>>>>> v0.6.17'

# Replace conflicts by keeping the v0.6.17 version (incoming changes)
def resolve_conflict(match):
    return match.group(1)

# Resolve all conflicts
resolved_content = re.sub(conflict_pattern, resolve_conflict, content, flags=re.DOTALL)

# Write back
with open('src/lib/i18n/locales/pl-PL/translation.json', 'w', encoding='utf-8') as f:
    f.write(resolved_content)

print("Polish translation conflicts resolved!")