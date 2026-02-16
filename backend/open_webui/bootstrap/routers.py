from fastapi import FastAPI

from open_webui.env import ENABLE_SCIM
from open_webui.routers import (
    analytics,
    audio,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    notes,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    evaluations,
    skills,
    tools,
    users,
    utils,
    scim,
)


def register_api_routers(app: FastAPI) -> None:
    """Register HTTP API router groups."""
    app.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
    app.include_router(openai.router, prefix="/openai", tags=["openai"])

    app.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(images.router, prefix="/api/v1/images", tags=["images"])

    app.include_router(audio.router, prefix="/api/v1/audio", tags=["audio"])
    app.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["retrieval"])

    app.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])

    app.include_router(auths.router, prefix="/api/v1/auths", tags=["auths"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

    app.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
    app.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])
    app.include_router(notes.router, prefix="/api/v1/notes", tags=["notes"])

    app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
    app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
    app.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
    app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
    app.include_router(skills.router, prefix="/api/v1/skills", tags=["skills"])

    app.include_router(memories.router, prefix="/api/v1/memories", tags=["memories"])
    app.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
    app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
    app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    app.include_router(functions.router, prefix="/api/v1/functions", tags=["functions"])
    app.include_router(
        evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"]
    )
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])

    if ENABLE_SCIM:
        app.include_router(scim.router, prefix="/api/v1/scim/v2", tags=["scim"])
