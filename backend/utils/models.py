from apps.webui.models.models import Models


def get_model_id_from_custom_model_id(id: str):
    model = Models.get_model_by_id(id)

    if model:
        return model.id
    else:
        return id
