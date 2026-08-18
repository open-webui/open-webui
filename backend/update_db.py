import sqlite3
import json

db_path = "data/webui.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("PRAGMA table_info(config)")
schema = c.fetchall()
print("Schema:", schema)

new_prompts = [
    {
        "title": ["Staging Analysis", "give me staging analysis"],
        "content": "GIVE ME STAGING ANALYSIS IN PAST 24 HOURS",
    },
    {
        "title": ["Current Status", "flow HLT and pumps"],
        "content": "FLOW HLT AND NUMBER OF PUMPS RUNNING IN PAST 24 HOURS",
    },
    {
        "title": ["Alerts", "anomaly analysis"],
        "content": "ANOMALY ANALYSIS IN PAST 24 HOURS",
    }
]

new_prompts_json = json.dumps(new_prompts)

# The table schema is either (key, value) or (id, data)
columns = [col[1] for col in schema]
if 'key' in columns and 'value' in columns:
    c.execute("UPDATE config SET value = ? WHERE key = 'ui.prompt_suggestions'", (new_prompts_json,))
    if c.rowcount == 0:
        c.execute("INSERT INTO config (key, value) VALUES (?, ?)", ('ui.prompt_suggestions', new_prompts_json))
    print("Updated using key/value schema.")
elif 'id' in columns and 'data' in columns:
    # Older schema
    c.execute("UPDATE config SET data = json_set(data, '$.ui.prompt_suggestions', json(?))", (new_prompts_json,))
    print("Updated using id/data schema.")
else:
    print("Unknown schema.")

conn.commit()
conn.close()
