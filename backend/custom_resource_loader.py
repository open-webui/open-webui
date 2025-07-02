from typing import Optional
import json
import os
import base64

from open_webui.models.models import (
    ModelForm,
    ModelMeta,
    ModelParams,
    ModelModel,
    ModelResponse,
    ModelUserResponse,
    Models,
)

from open_webui.models.auths import (
    Auths,
)

from open_webui.models.users import Users

from open_webui.utils.auth import (
    get_password_hash,
)

DEFAULT_RESOURCES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_resources')

# Will be set in check_required_env_vars()
resources_path = None

def load_json_file(file_path: str):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON in file '{file_path}'.")
        return None

def load_image_file_base64_string(file_path: str):
    try:
        with open(file_path, 'rb') as icon_file:
            icon_data = icon_file.read()
            if icon_data:
                base64_image_string = base64.b64encode(icon_data).decode('utf-8')
                return f'data:image/png;base64,{base64_image_string}'
            else:
                print(f"Error reading icon file '{file_path}'.")
                return None
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None

def load_db_models():
    return Models.get_models()

def delete_model_by_id(id: str):
    result = Models.delete_model_by_id(id)
    return result

def create_new_model(form_data: ModelForm):
    model = Models.insert_new_model(form_data, user.id)
    if model:
        return true

def update_model_by_id(id: str, form_data: ModelForm):
    model = Models.update_model_by_id(id, form_data)
    return model


def handle_model_update(admin_user_id, db_models, json_models):
    if not resources_path:
        raise Exception("Assertion error: resources_path not defined")

    db_model_id_set = set([model.id for model in db_models])
    json_model_id_set = set([model['id'] for model in json_models])

    for model in json_models:
        meta_data = model.get('meta', {})
        icon_path = meta_data.get('profile_image_url', None)
        if icon_path:
            # Load icon file from path and replace the icon field with the icon data as base64 string with the prefix 'data:image/png;base64,'
            icon_data = load_image_file_base64_string(resources_path + '/' + icon_path)
            if icon_data:
                meta_data['profile_image_url'] = icon_data
                model['meta'] = meta_data
            else:
                print(f"Error reading icon file '{icon_path}'.")
        else:
            print(f"Icon path not found in meta data.")


    # Get Set of model which in exist in database but not in json
    model_delete_set = db_model_id_set.difference(json_model_id_set)
    # Get Set of model which in exist in json but not in database
    model_create_set = json_model_id_set.difference(db_model_id_set)
    # Get Set of model which in exist in both database and json
    model_update_set = db_model_id_set.intersection(json_model_id_set)

    print(f"Found {len(model_delete_set)} model{'s' if len(model_delete_set) != 1 else ''} in the database that do{'es' if len(model_delete_set) == 1 else ''} not exist in the JSON file.")
    for model_id in model_delete_set:
        result = delete_model_by_id(model_id)
        if result:
            print(f"Model with id '{model_id}' deleted successfully.")
        else:
            print(f"Error deleting model with id '{model_id}'.")

    print(f"Found {len(model_create_set)} model{'s' if len(model_create_set) != 1 else ''} in the JSON file that do{'es' if len(model_create_set) == 1 else ''} not exist in the database.")
    for model in json_models:
        if model['id'] in model_create_set:
            form_data = getModelForm(model)
            result = Models.insert_new_model(form_data, admin_user_id)
            if result:
                print(f"Model with id '{model['id']}' created successfully.")
            else:
                print(f"Error creating model with id '{model['id']}'.")

    print(f"Found {len(model_update_set)} model{'s' if len(model_update_set) != 1 else ''} that exist in both the database and the JSON file.")
    for model in json_models:
        if model['id'] in model_update_set:
            form_data = getModelForm(model)
            result = update_model_by_id(model['id'], form_data)
            if result:
                print(f"Model with id '{model['id']}' updated successfully.")
            else:
                print(f"Error updating model with id '{model['id']}'.")


def getModelForm(model_data: dict[str, any]):

    isPrivate = model_data.get('isPrivate', False) is True
    access_control = None

    if isPrivate:
        access_control = {
            "read": {
                "group_ids": [],
                "user_ids": []
            },
            "write": {
                "group_ids": [],
                "user_ids": []
            },
        }

    model_form_data = {
        "id": model_data.get("id", "default_id"),
        "base_model_id": model_data.get("base_model_id"),
        "name": model_data.get("name", "default_name"),
        "meta": model_data.get("meta", {}),
        "params": ModelParams(**model_data.get("params", {})),
        "access_control": access_control,
        "is_active": model_data.get("is_active", True),
    }

    # Create a ModelForm instance
    model_form = ModelForm(**model_form_data)
    return model_form

def sync_models(admin_user_id: str):
    if not resources_path:
        raise Exception("Assertion error: resources_path not defined")

    file_path = resources_path + '/models.json'
    db_models = load_db_models()
    print(f"Found {len(db_models)} models in database.")
    data = None
    if os.path.exists(file_path):
        data = load_json_file(file_path)
        if not data:
            raise Exception("Error loading json file.")
    else:
        print(f"File '{file_path}' not found.")
    print(f"Found {len(data)} models in json.")
    handle_model_update(admin_user_id, db_models, data)

def create_admin_user(email, password):
    hashed = get_password_hash(password)
    role = "admin"
    user = Auths.insert_new_auth(email.lower(),hashed,email.lower(),"/user.png", role)
    return user.id

def update_password(user, password):
    hashed = get_password_hash(password)
    updated = Auths.update_user_password_by_id(user.id, hashed)
    return updated

def sync_admin_user() -> str:
    """Synchronize the admin user by updating their password or creating a new user."""
    admin_email = os.getenv('ADMIN_EMAIL').lower()
    admin_password = os.getenv('ADMIN_PASSWORD')

    admin = Users.get_user_by_email(admin_email)
    if admin:
        if not update_password(admin, admin_password):
            raise RuntimeError("Error updating admin user password.")
        print("Admin user password updated successfully.")
        return admin.id
    else:
        print("Admin user not found. Creating new admin user...")
        user_id = create_admin_user(admin_email, admin_password)
        if not user_id:
            raise RuntimeError("Error creating new admin user.")
        print(f"Admin user created with id: {user_id}")
        return user_id

def check_required_env_vars() -> bool:
    global resources_path

    """Check if required environment variables are set."""
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')

    if not admin_email:
        print("Admin email (ADMIN_EMAIL) environment variable not set.")
        return False

    if not admin_password:
        print("Admin password (ADMIN_PASSWORD) environment variable not set.")
        return False

    # Use this if defined, otherwise fall back to default
    custom_resources_path_from_env = os.getenv('CUSTOM_RESOURCE_PATH')

    if custom_resources_path_from_env and os.path.exists(custom_resources_path_from_env):
        print("Custom resource path set per environment variable.")
        resources_path = custom_resources_path_from_env
    elif os.path.exists(DEFAULT_RESOURCES_PATH):
        print("Using default custom resources path %s" % (DEFAULT_RESOURCES_PATH))
        resources_path = DEFAULT_RESOURCES_PATH
    else:
        print("Nor per-environment not default custom resource path '%s' exist." % (DEFAULT_RESOURCES_PATH))
        return False

    print(f"Admin email: {admin_email}")
    print(f"Admin password: {'*' * len(admin_password)}")
    print(f"Custom resource path: {resources_path}")
    return True

def main():

    if not check_required_env_vars():
        print("Required environment variables not set. Skip syncing resources.")
        return

    admin_id = sync_admin_user()
    sync_models(admin_id)


if __name__ == "__main__":
    main()
