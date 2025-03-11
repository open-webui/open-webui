import json
from pathlib import Path
from open_webui.models.users import Users
from open_webui.models.functions import (
    FunctionForm,
    FunctionMeta,
    Functions
)

def main():
    print("Running installation script...")

    # Get the current file's directory
    current_dir = Path(__file__).parent

    admin = Users.get_first_user()
    if admin:
        # Iterate through all .json files in the same directory
        for json_file in current_dir.glob("*.json"):
            print(f"Found JSON file: {json_file.name}")
            try:
                # Open and parse the JSON content
                with json_file.open('r', encoding='utf-8') as f:
                    function = json.load(f)[0]
                    if Functions.get_function_by_id(function["id"]):
                        Functions.update_function_by_id(function["id"], {
                            "name": function["name"],
                            "content": function["content"],
                            "meta": {
                                "description": function["meta"]["description"],
                                "manifest": function["meta"]["manifest"]
                            }
                        })
                    else:
                        form_data = FunctionForm(
                            id=function["id"],
                            name=function["name"],
                            content=function["content"],
                            meta=FunctionMeta(
                                description=function["meta"]["description"],
                                manifest=function["meta"]["manifest"],
                            ),
                        )
                        Functions.insert_new_function(admin.id, function["type"], form_data)
                    
                    Functions.update_function_by_id(
                        function["id"], {"is_active": True}
                    )
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON in {json_file.name}: {e}")
            except Exception as e:
                print(f"Error reading {json_file.name}: {e}")

if __name__ == "__main__":
    main()