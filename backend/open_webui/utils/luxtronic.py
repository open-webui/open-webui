import os

def get_luxtronic_model_names() -> list[str]: 
    luxtronic_model_names = ["lux_docquestion"]
    tenent_models_comma_seperated = os.environ.get("LUXTRONIC_MODELS", "")
    if tenent_models_comma_seperated:
        tenent_models_names = [m.strip() for m in tenent_models_comma_seperated.split(",")]
        luxtronic_model_names.extend(tenent_models_names )
    return luxtronic_model_names
