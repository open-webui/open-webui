"""
StoryWeaver — Dépendance get_current_novel
===========================================

Description fonctionnelle:
    Fournit la dépendance FastAPI `get_current_novel` injectable dans n'importe
    quel router aval (ex: Prompt Builder, Context Injection).
    Retourne le roman courant de l'utilisateur ou None si aucun n'est sélectionné.

Règles métier:
    - Aucune exception n'est levée si aucun roman n'est sélectionné (retourne None).
    - Si le roman référencé n'existe plus, retourne None silencieusement.
    - La dépendance est read-only : elle ne modifie jamais l'état.

Architecture tech:
    - Utilise `get_verified_user` pour récupérer le user courant.
    - Utilise `get_session` pour la session SQLAlchemy.
    - S'importe avec : `from open_webui.utils.sw_dependencies import get_current_novel`

Usage dans un router:
    ```python
    from open_webui.utils.sw_dependencies import get_current_novel
    from open_webui.models.sw_novels import NovelModel

    @router.get("/example")
    async def my_endpoint(
        current_novel: Optional[NovelModel] = Depends(get_current_novel),
    ):
        if current_novel:
            # contexte roman actif
        else:
            # pas de roman sélectionné
    ```
"""

from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.utils.auth import get_verified_user
from open_webui.models.sw_novels import NovelModel, Novels


async def get_current_novel(
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
) -> Optional[NovelModel]:
    """
    Dépendance FastAPI — retourne le roman actuellement sélectionné par l'utilisateur.

    Ne lève jamais d'exception. Retourne None si :
        - Aucun roman n'est sélectionné (current_novel_id est None).
        - Le roman référencé a été supprimé.
        - Le roman appartient à un autre utilisateur (sécurité défensive).

    Returns:
        Optional[NovelModel]: Le roman courant, ou None.
    """
    current_novel_id = getattr(user, "current_novel_id", None)
    if not current_novel_id:
        return None

    novel = Novels.get_novel_by_id(id=current_novel_id, db=db)

    # Vérifie que le roman existe et appartient bien à cet utilisateur
    if not novel or novel.user_id != user.id:
        return None

    return novel
