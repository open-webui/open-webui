from pathlib import Path
import json
import os
import logging
from fastapi import HTTPException
from open_webui.env import SRC_LOG_LEVELS
from open_webui.config import (
    OPENAI_API_KEYS,
)
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.chat_models import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate

from langchain_core.runnables import (
    RunnableParallel,
    RunnablePassthrough
)
from langchain.schema.output_parser import StrOutputParser
from datasets import Dataset
#from ragas import evaluate
'''
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
'''
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import glob
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd
from pathlib import Path
import json
import logging
from fastapi import HTTPException

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAGAS"])
log.setLevel(logging.INFO)


required_keys = {
    "embedding_engine",
    "embedding_model",
    "reranking_model",
    "chunk",
    "template",
    "k",
    "r",
    "hybrid",
    "graphRag"
}

def save_trace_data(file_path, trace_data={}, target="qa"):
    """
    Sauvegarde ou met à jour les données de trace dans un fichier JSON.
    
    :param file_path: Chemin du fichier à mettre à jour
    :param trace_data: Données à ajouter ou à mettre à jour
    :param target: Section cible à mettre à jour ('config' ou 'qa')
    :raises HTTPException: En cas d'erreur lors de la mise à jour du fichier
    :return: Message de succès
    """
    if target not in ["config", "qa"]:
        raise HTTPException(
            status_code=400,
            detail="Cible invalide. La cible doit être 'config' ou 'qa'."
        )

    try:
        # Convertir le chemin en objet Path
        file_path = Path(file_path)
        
        # Vérifier si le fichier existe et charger son contenu
        data = {}
        if file_path.exists():
            with file_path.open("r", encoding="utf-8") as file:
                log.info(f"Chargement du fichier existant : {file_path}")
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Fichier JSON invalide ou corrompu : {file_path}"
                    )

                if target == "config" and "config" in data:
                    config = data.get("config", {})
                    if isinstance(config, dict) and required_keys.issubset(config.keys()):
                        log.info("Détection de configuration existante.")
                        raise HTTPException(
                            status_code=409,
                            detail="Configuration déjà existante. Aucune mise à jour effectuée."
                        )
                    else:
                        log.info("Clés manquantes dans la configuration. Config non valide.")
            
        # Initialiser les sections si elles n'existent pas
        if "config" not in data:
            data["config"] = {}
        if "qa" not in data:
            data["qa"] = []
        if "documentId" not in data:
            data["documentId"] = []
        if "modelId" not in data:
            data["modelId"] = []
        if "ground_truth" not in data:
            data["ground_truth"] = []
        if "question" not in data:
            data["question"] = []
        if "answer" not in data:
            data["answer"] = []
        # Mise à jour des données selon la cible
        if target == "config":
            if isinstance(trace_data, dict):
                data["config"].update(trace_data)
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Les données pour 'config' doivent être un dictionnaire."
                )
        elif target == "qa":
            if isinstance(trace_data, dict):
                data["qa"].append(trace_data)
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Les données pour 'qa' doivent être un dictionnaire."
                )

        # Sauvegarder les données mises à jour dans le fichier
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        
        log.info(f"Fichier {file_path} mis à jour avec succès.")
        return {"message": "Fichier mis à jour avec succès"}

    except HTTPException as e:
        raise e  # Renvoyer les exceptions HTTP spécifiques déjà levées
    except Exception as e:
        log.error(f"Erreur inattendue lors de la mise à jour : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur inattendue lors de la mise à jour du fichier."
        )


def clear_qa_section(file_path):
    """
    Efface les données de la section `qa` dans un fichier JSON.

    :param file_path: Chemin du fichier à mettre à jour
    :raises HTTPException: En cas d'erreur lors de la mise à jour du fichier
    :return: Message de succès
    """
    try:
        # Convertir le chemin en objet Path
        file_path = Path(file_path)

        # Vérifier si le fichier existe et charger son contenu
        data = {}
        if file_path.exists():
            with file_path.open("r", encoding="utf-8") as file:
                log.info(f"Chargement du fichier existant : {file_path}")
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Fichier JSON invalide ou corrompu : {file_path}"
                    )

        # Réinitialiser la section `qa`
        data["qa"] = []

        # Sauvegarder les données mises à jour dans le fichier
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        log.info(f"Section 'qa' du fichier {file_path} effacée avec succès.")
        return {"message": "Section 'qa' effacée avec succès."}

    except HTTPException as e:
        raise e  # Renvoyer les exceptions HTTP spécifiques déjà levées
    except Exception as e:
        log.error(f"Erreur inattendue lors de la réinitialisation de 'qa' : {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur inattendue lors de la réinitialisation de la section 'qa'."
        )


def transform_data(input_file):
    """
    Transforme les données JSON pour correspondre au format attendu (nouveau format).

    Args:
        input_file (str): Chemin vers le fichier JSON contenant les données.

    Returns:
        dict: Objet contenant les questions, réponses générées, contextes, et réponses de référence.
    """
    with open(input_file, 'r', encoding='utf-8') as file:
        json_data = json.load(file)

    transformed_data = {
        "question": json_data.get("question", []),
        "answer": json_data.get("answer", []),
        "contexts": [],
        "ground_truth": json_data.get("ground_truth", [])
    }

    # Parcours des QA pour extraire les contextes
    for item in json_data.get("qa", []):     
        relevants=item.get("relevant_context", [])
        for context in relevants:
            print(f"Number of relevant context :{len(relevants)}")
            contexts = []
            documents = context.get("documents", [[]])
            print(f"Number of documents :{len(documents[0])}")
            for document in documents[0]:
                contexts.append(document)
        # Ajoute les contextes agrégés pour chaque QA
        transformed_data["contexts"].append(contexts)

    print(f"Len contexts {len(transformed_data['contexts'])}")
    print(transformed_data)
    return transformed_data

def load_dataset_from_json_object(json_data):

    """
    Charge des données JSON structurées en un objet Dataset Hugging Face à partir d'un objet JSON.

    Args:
        json_data (dict): Objet JSON contenant les données.

    Returns:
        Dataset: Dataset Hugging Face construit à partir des données JSON.
    """
    # Valider que les clés nécessaires sont présentes
    required_keys = {'question', 'answer', 'contexts', 'ground_truth'}
    if not all(key in json_data for key in required_keys):
        raise ValueError(f"L'objet JSON doit contenir les clés suivantes : {required_keys}")

    # Construire l'objet Dataset
    dataset = Dataset.from_dict(json_data)

    return dataset

'''
def evaluate_and_save_results_from_json(input_file,output_path):
    """
    Évalue un fichier contenant les données avec les métriques RAGas, génère un fichier HTML des résultats et retourne le DataFrame.

    Args:
        input_file (str): Chemin du fichier d'entrée contenant les données.

    Returns:
        pd.DataFrame: DataFrame contenant les résultats d'évaluation.
    """
    log.info("Evaluation of "+input_file)
    # Transformer les données depuis le fichier d'entrée
    json_data = transform_data(input_file)
    log.info(f"Json Data {json_data}")
    # Charger le dataset depuis l'objet JSON
    dataset = load_dataset_from_json_object(json_data)

    # Vérifier que la clé API est chargée
    api_key = OPENAI_API_KEYS
    if not api_key:
        raise Exception("API Key not found. Please check your environment variables.")

    # Évaluer le dataset avec les métriques
    result = evaluate(
        dataset=dataset, 
        metrics=[
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
        ],
    )

    # Convertir les résultats en DataFrame
    df = result.to_pandas()
    log.info(f"Dataframe RAGAS {df}")
    # Générer le nom du fichier de sortie
    date_str = datetime.now().strftime("%Y-%m-%d")
    input_file_name = os.path.basename(input_file).split('.')[0]  # Extraire le nom du fichier sans extension
    output_file_name = f"{input_file_name}_ragas_{date_str}.html"
    log.info(f"Saving RAGAS evaluation {output_file_name}")
    # Chemin complet pour le fichier de sortie
   
    os.makedirs(output_path, exist_ok=True)  # Créer le répertoire s'il n'existe pas
    output_file_path = os.path.join(output_path, output_file_name)

    # Sauvegarder le DataFrame en HTML
    df.to_html(output_file_path, index=False)
    print(f"Fichier HTML sauvegardé sous : {output_file_path}")

    # Tracés
    process_html_table(df,title='Tableau',save_path=output_path)
    plot_dataframe_metrics(df,title='Densite',save_path=output_path)
    # Convertir le DataFrame en JSON
    result_json = df.to_dict(orient="records")

    # Retourner les résultats sous forme de JSON
    return result_json
'''



def process_html_table(df, title, save_path):
    # Activer le style graphique
    sns.set_style("whitegrid")


    # Filtrer les colonnes pertinentes (question et résultats numériques)
    numeric_columns = df.select_dtypes(include=['float', 'int']).columns
    relevant_columns = ['user_input'] + list(numeric_columns)
    filtered_df = df[relevant_columns].copy()

    # Normaliser les valeurs numériques entre 0 et 1
    for col in numeric_columns:
        filtered_df[col] = filtered_df[col].apply(lambda x: max(0, min(1, x)) if pd.notnull(x) else np.nan)

    # Création des couleurs pour les valeurs numériques
    cmap = LinearSegmentedColormap.from_list('red_green', ['red', 'green'])
    cell_colors = filtered_df[numeric_columns].applymap(
    lambda x: cmap(1.0) if x == 1.0 else (cmap(x) if pd.notnull(x) else (1, 1, 1, 0)))


    # Matrice complète des couleurs
    full_colors = [[(1, 1, 1, 1)] * len(filtered_df.columns) for _ in range(len(filtered_df))]
    for i, row in enumerate(cell_colors.to_numpy()):
        for j, color in enumerate(row):
            full_colors[i][j + 1] = color  # Décale de +1 pour les colonnes numériques uniquement

    # Créer une figure pour le tableau
    fig, ax = plt.subplots(figsize=(12, len(filtered_df) * 0.6))
    ax.axis('tight')
    ax.axis('off')

    # Création du tableau
    table = plt.table(
        cellText=filtered_df.values,
        colLabels=filtered_df.columns,
        cellColours=full_colors,
        cellLoc='center',
        loc='center'
    )

    # Ajuster la taille des colonnes et du texte
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.auto_set_column_width(col=list(range(len(filtered_df.columns))))

    # Sauvegarder le graphique
    save_file = f"{save_path}/{title}.png"
    plt.savefig(save_file, bbox_inches='tight')
    plt.close()

# Fonction pour tracer les graphiques et calculer le RAGAS Score
def plot_dataframe_metrics(df, title, save_path):
    """
    Trace des graphiques KDE pour les colonnes avec variation,
    affiche les valeurs constantes et calcule le RAGAS Score.
    """
    metrics = ['faithfulness', 'answer_relevancy', 'context_recall', 'context_precision']
    
    # Calcul du RAGAS Score
    ragas_score = df[metrics].mean(axis=1).mean()  # Moyenne des métriques sur toutes les lignes
    print(f"RAGAS Score pour {title} : {ragas_score:.3f}")

    # Plot des métriques
    fig, axs = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 5))
    fig.suptitle(f"{title} (RAGAS Score: {ragas_score:.3f})", fontsize=16)
    
    for i, col in enumerate(metrics):
        if df[col].nunique() == 1:  # Vérifie si toutes les valeurs sont identiques
            axs[i].bar([col], [df[col].iloc[0]])  # Affiche une barre pour la valeur unique
            axs[i].set_title(f'{col} (Constant Value)')
            axs[i].set_ylabel('Value')
        else:
            sns.kdeplot(df[col], ax=axs[i], fill=True)
            axs[i].set_title(f'{col} Distribution')
            axs[i].set_xlabel('Score')
            axs[i].set_ylabel('Density')

    plt.tight_layout()
    plt.subplots_adjust(top=0.85)
    save_file = f"{save_path}/{title}.png"
    plt.savefig(save_file, bbox_inches='tight')
    print(f"Graphique sauvegardé : {save_file}")
   


