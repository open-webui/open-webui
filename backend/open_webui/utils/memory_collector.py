import json
import logging
import asyncio
from typing import Any, Callable
from fastapi import Request

from open_webui.models.memories import Memories
from open_webui.retrieval.vector.connector import VECTOR_DB_CLIENT
from open_webui.env import SRC_LOG_LEVELS
from open_webui.models.users import Users

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])
PERIOD_LENGTH = 3

async def extract_and_save_memory(
    request: Request, 
    form_data: dict, 
    user: Any, 
    generate_completion_func: Callable
):
    """
    Periodically extracts educational facts from the chat and saves them to the vector DB.
    """
    try:
        messages = form_data.get("messages", [])
        
        # 1. Periodic Check: Only run every PERIOD_LENGTH user messages
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages or len(user_messages) % PERIOD_LENGTH != 0:
            log.info(f"[MEMORIES] ignoring collection, number of messages {len(user_messages)}")
            return


        # 2. Check User Preferences: Respect the opt-out toggle
        db_user = Users.get_user_by_id(user.id)
        if db_user:
            db_user = db_user.model_dump()
            user_settings = db_user.get("settings", {})
            ui_settings = user_settings.get("ui", {})
            memory_enabled = ui_settings.get("memory", False)
            
            if not memory_enabled:
                log.info(f"[MEMORIES] User {user.id} has memory disabled. Skipping extraction.")
                return

        log.info("[MEMORIES] Memory activated, running periodic background memory collection...")
        log.info(f"[MEMORIES] starting collection, number of messages {len(user_messages)}")

        # 3. Format the transcript (grab the last PERIOD_LENGTH messages for context)
        transcript = ""
        for m in messages[-PERIOD_LENGTH:]:
            role = m.get("role", "unknown")
            content = m.get("content", "")
            transcript += f"{role.capitalize()}: {content}\n\n"

        # 4. Memory collection prompt
        system_prompt = """Tu es l'analyste de mémoire en arrière-plan pour l'IA Compagnon d'Oreegami. 
        Analyses la conversation et extraits UNIQUEMENT les faits durables concernant le parcours éducatif et professionnel de l'apprenant (objectifs, sujets difficiles, préférences, infos spécifiques à l'apprenant...).
        N'extraits pas de tâches à court terme, de salutations...

        Règles à respecter :
        - La mémoire doit être aussi concise que possible (une seule phrase factuelle).
        - Ne conserves que le fait le plus important (une seule mémoire au maximum doit être extraite).
        - Généres UNIQUEMENT un tableau JSON valide de chaînes de caractères.
        - S'il n'y a rien ou de pertinent à mémoriser, renvois strictement un tableau vide : []

        Exemples de mémoires valides à extraire :
        - ["L'apprenant recherche activement une alternance en tant que Product Builder."]
        - ["L'utilisateur est basé dans la région IDF."]
        - ["L'utilisateur souhaite se positionner sur un poste de community manager."]

        Exemples d'informations à IGNORER :
        - Actions quotidiennes ("J'ai fini mon exercice du jour.")
        - Salutations ("Bonjour, comment vas-tu ?")

        *IMPORTANT* 
        Si l'utilisateur demande explicitement de mémoriser une information, sauvegardes-la impérativement."""

        # 5. Create the silent extraction payload
        payload = {
            "model": form_data["model"],
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation:\n{transcript}"}
            ],
            "stream": False
        }

        # 6. Ask the LLM (using the passed generation function)
        response = await generate_completion_func(request, payload, user, bypass_filter=True)
        
        content = ""
        if isinstance(response, dict):
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # 7. Parse the JSON array
        start = content.find('[')
        end = content.rfind(']')
        if start == -1 or end == -1:
            log.error(f"[MEMORIES] memory parsing error, Raw LLM response: {content}")
            return
            
        facts = json.loads(content[start:end+1])
        log.info(f"[MEMORIES] LLM evaluated the chat and decided to extract: {facts}")

        # 8. Save to the vector database
        for fact in facts:
            if not isinstance(fact, str): continue
            
            memory = Memories.insert_new_memory(user.id, fact)
            VECTOR_DB_CLIENT.upsert(
                collection_name=f"user-memory-{user.id}",
                items=[{
                    "id": memory.id,
                    "text": memory.content,
                    "vector": request.app.state.EMBEDDING_FUNCTION(memory.content, user=user),
                    "metadata": {"created_at": memory.created_at},
                }],
            )
            log.info(f"[MEMORIES] Oreegami Memory Saved: {fact}")

    except Exception as e:
        log.error(f"Background memory extraction failed: {e}")