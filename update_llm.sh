#!/bin/bash
# update_llm.sh

# Récupère la liste des LLM installées dans le container Docker
llm_list=$(docker exec ollama ollama list | tail -n +2 | awk '{print $1}')

# Boucle sur chaque LLM pour la mettre à jour
for llm in $llm_list; do
  docker exec ollama ollama pull $llm
done
