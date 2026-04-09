# Guide de Déploiement — StoryWeaver (VPS)

Ce guide explique comment déployer votre instance StoryWeaver sur un VPS Linux en utilisant Docker.

## 1. Pré-requis

- **RAM** : 16 Go minimum recommandés (pour faire tourner Ollama + WebUI).
- **Stockage** : 50 Go SSD minimum.
- **Système** : Ubuntu 22.04 LTS ou supérieur.
- **Outils** : Docker & Docker-Compose installés.

## 2. Configuration de l'environnement

Clonez votre fork sur le VPS :
```bash
git clone https://github.com/votre-compte/open-webui-storywriter.git
cd open-webui-storywriter
```

Créez votre fichier `.env` :
```bash
cp .env.example .env
```
Assurez-vous de définir `WEBUI_SECRET_KEY` avec une valeur aléatoire sécurisée.

## 3. Lancement via Docker-Compose

Utilisez le fichier de configuration standard :
```bash
docker-compose up -d --build
```
Cela lancera :
1. Le backend (FastAPI avec les extensions StoryWeaver).
2. Le frontend (SvelteKit pré-compilé).
3. Ollama (en conteneur séparé ou via une instance locale).

## 4. Initialisation de la Base de Données

Si vous utilisez SQLite (par défaut), les fichiers seront créés automatiquement. Pour appliquer les schémas StoryWeaver initiaux :
```bash
docker exec -it open-webui alembic upgrade head
```

## 5. Modèles LLM recommandés

Pour une expérience de rédaction optimale (Storytelling & Brainstorm), installez les modèles suivants via Ollama :

| Modèle | Pourquoi ? | Commande |
|--------|------------|----------|
| **Mistral-Nemo (12B)** | Excellence en rédaction française et nuances. | `ollama pull mistral-nemo` |
| **Llama-3.1 (8B)** | Très bon raisonnement pour le brainstorm et l'outline. | `ollama pull llama3.1` |
| **Hermes-3 (8B)** | Très créatif, idéal pour débloquer des scènes complexes. | `ollama pull hermes3` |

## 6. Maintenance & Mise à jour

Pour mettre à jour votre instance avec vos derniers commits :
```bash
git pull origin main
docker-compose up -d --build
```
N'oubliez pas de relancer les migrations Alembic en cas de changement de modèle de données.
