# Journal des modifications

Tous les changements notables apportés à ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et ce projet adhère au [Versionnage sémantique](https://semver.org/lang/fr/spec/v2.0.0.html).

## [Non publié] - À déterminer

### Corrigé

- **🔒 Données sensibles dans les journaux** : Les invites des utilisateurs, les réponses des modèles, les fragments de jetons d'accès Graph, les clés d'API, les jetons et revendications OAuth, les adresses courriel, les URL de webhooks et le texte des documents ne sont plus écrits dans les journaux du serveur. Des longueurs, des décomptes et des identifiants sont journalisés à la place.

## [0.5.7-ccv2-1.16.0] - 2026-08-12

### Ajouté

- **📄 Conditions d'utilisation** : Ajout d'une page de conditions d'utilisation avec un lien de retour vers l'application.
- **🌐 Affichage des modèles en français** : Ajout de noms d'affichage en français pour les modèles.
- **🌐 Affichage des étiquettes de modèles en français** : Ajout de noms d'affichage en français pour les étiquettes de modèles.

### Modifié

- **📦 Dépendances** : Mise à jour des dépendances pour corriger les vulnérabilités.

### Corrigé

- **🔒 Rafraîchissement des jetons** : Ajout d'un rafraîchissement sécurisé des jetons, avec récupération silencieuse et restauration de session entre les onglets.
- **🗃️ Basculement Redis** : Empêche Redis de basculer vers un état en mémoire.
- **🐳 Dockerfile** : Mise à jour du conteneur afin qu'il s'exécute sans privilèges de superutilisateur.

### Retiré

- **🗑️ API Electron** : Suppression de l'API Electron.

## [0.5.7-ccv2-1.15.1] - 2026-06-19

### Modifié

- **✨ Points de terminaison de santé** : Mise à jour des points de terminaison de santé pour offrir une meilleure visibilité sur l'état des services.
- **📦 Dépendances** : Mise à jour des dépendances pour corriger les vulnérabilités.

## [0.5.7-ccv2-1.15.1] - 2026-06-17

### Modifié

- **🔒 Affichage de l'URL Redis** : Retrait de l'affichage de l'URL Redis pour des raisons de sécurité.
- **📦 Dépendances** : Mise à jour des dépendances pour corriger des vulnérabilités.
- **🔗 Lien du dépôt** : Retrait du lien vers un dépôt différent.

### Corrigé

- **🧮 Encapsulation TeX** : Correction de la fonctionnalité d'encapsulation TeX au traitement du contenu des réponses.
- **🧠 Modèle d'invite** : Correction du modèle d'invite pour ne pas ajouter de raisonnement/chaîne de pensées.
- **🏗️ Flux de travail Docker Build** : Correction de la vérification de l'existence du dossier de cache avant df dans le flux de travail docker-build.
- **📥 Importation SharePoint** : Correction de la gestion de l'importation pour SharePointOAuthClient et ajustement de requirements.txt pour les problèmes de dépendances.
- **📄 Pages d'erreur** : Mise à jour des messages des pages d'erreur pour une meilleure clarté et orientation des utilisateurs.

## [0.5.7-ccv2-1.15.0] - 2026-05-19

### Ajouté

- **🧪 Tests E2E Playwright** : Ajout d'une couverture de tests exhaustive pour le téléversement de documents et les flux d'authentification.
- **📝 Journalisation de la recherche web** : Ajout d'une journalisation de diagnostic améliorée pour les opérations de recherche web.

### Modifié

- **🏢 Intégration MCP SharePoint** : Refonte de l'intégration pour prendre entièrement en charge les configurations multi-départements.
- **📦 Dépendances de sécurité** : Mise à jour de plusieurs dépendances pour corriger des problèmes de vulnérabilités connus.
- **📈 Tableau de bord de l'espace de travail** : Mise à jour du tableau de bord d'utilisation dans la section de l'espace de travail.
- **🎨 Logo CANChat** : Mise à jour du logo principal de l'application.
- **🔗 Liens de recherche web** : Modification du routage des liens afin que les résultats de la recherche web ne pointent plus directement vers Google.
- **🏷️ Étiquette de suppression de chat** : Mise à jour de l'étiquette de l'interface utilisateur concernant la suppression automatique des chats après 30 jours d'inactivité.

### Corrigé

- **🧹 Assainissement Markdown** : Correction d'un problème empêchant l'assainissement adéquat du contenu markdown.
- **📱 Interface d'ancrage Wikipédia** : Correction d'un bogue d'affichage affectant l'étiquette d'ancrage Wikipédia sur les petits écrans.
- **🧠 Affichage du modèle de réflexion** : Correction de problèmes de rendu avec l'affichage du processus de réflexion du modèle.

## [0.5.7-ccv2-1.14.0] - 2026-03-23

### Ajouté

- **🗑️ Fenêtres modales de confirmation de suppression** : Ajout de plusieurs fenêtres modales de confirmation de suppression manquantes.
- **🌐 Journal des modifications en français** : Ajout du journal des modifications en français.

### Modifié

- **🔐 Générateur de nombres pseudo-aléatoires** : Remplacement du générateur de nombres pseudo-aléatoires faible.

### Corrigé

- **🔄 Initialisation des sockets** : Correction de l'initialisation unifiée des sockets et du bassin Redis/local.
- **📥 Fenêtre modale d'importation d'utilisateurs CSV** : Correction du chargement et du masquage de la fenêtre modale lors de l'importation d'utilisateurs par CSV.

## [0.5.7-ccv2-1.13.0] - 2026-03-16

### Ajouté

- **🧹 Nettoyage automatisé du bassin d'utilisateurs** : Ajout du nettoyage automatisé du bassin d'utilisateurs.
- **🗑️ Bouton de suppression d'élément de clavardage** : Réajout du bouton de suppression dans le menu d'élément de clavardage.

### Modifié

- **📎 Valeur par défaut du nombre maximal de fichiers RAG** : Le nombre maximal de fichiers RAG a maintenant une valeur par défaut de 5 fichiers.
- **📦 Mise à jour des dépendances** : Mise à jour des exigences de dépendances.
- **🧹 Valeurs par défaut du nettoyage des clavardages** : Mise à jour des valeurs par défaut pour le nettoyage des clavardages.
- **🔒 Verrouillage du nettoyage des clavardages** : Utilise maintenant un système de verrouillage centralisé pour le nettoyage des clavardages afin d'améliorer la fiabilité.

### Corrigé

- **📊 Filtrage par plage de dates des métriques** : Filtrage par plage de dates pour le tableau de bord des métriques pour plus de précision et de rapidité.
- **🖼️ Validation du chemin de génération d'images** : Validation du chemin Posix dans la génération d'images pour éviter les plantages du cache.
- **🔄 Fiabilité de la recherche de documents** : Correction d'un problème de synchronisation pouvant causer des échecs intermittents lors de la recherche de documents.
- **☑️ Comportement de la sélection globale** : Correction de la sélection globale qui ajoutait aussi les éléments épinglés et ceux dans les dossiers.

### Retiré

- **🧠 Paramètre de mémoire personnalisée** : Retrait de la fonctionnalité de mémoire personnalisée dans les paramètres.

## [0.5.7-ccv2-1.12.5] - 2026-02-26

### Corrigé

- **🌐 Requête de recherche Web** : Correction de la gestion du délai d'attente lors de résultats partiels de recherche Web.

## [0.5.7-ccv2-1.12.4] - 2026-02-25

### Corrigé

- **🔧 Champ de saisie du clavardage** : Correction de la taille et de l'alignement du champ de saisie du clavardage.
- **💬 Titres de clavardage trop verbeux** : Résolution des titres de clavardage trop verbeux.
- **🧹 Invites persistantes** : Suppression des invites persistantes lors du passage à un nouveau clavardage.
- **📝 Liens Markdown** : Échappement des tildes dans les liens Markdown pour éviter le texte barré.
- **🌐 Contexte de recherche Web** : Application de la troncature aux limites du contexte de recherche Web.
- **🔧 Planificateur de nettoyage des clavardages** : Résolution du problème du planificateur de nettoyage des clavardages.
- **🔌 Gestionnaire WebSocket** : Rétablissement du mécanisme de secours du gestionnaire WebSocket lorsque Redis est indisponible.
- **♿ Repères d'accessibilité** : Ajout de repères au clavardage, du rôle de navigation à la barre latérale et d'un titre de page au clavardage.
- **🌐 Requête de recherche Web** : Résolution du problème de persistance des requêtes de recherche Web.

## [0.5.7-ccv2-1.12.3] - 2026-02-18

### Corrigé

- **🔧 Ajout de modèle Ollama** : Correction d'un plantage lorsqu'un administrateur tente d'ajouter un nouveau modèle Ollama.
- **🔄 Rafraîchissement après suppression de modèle** : Récupération des modèles après la suppression pour garantir que la liste reste à jour.
- **🏷️ Libellé Enregistrer comme copie** : Mise à jour de la traduction du libellé du bouton « Enregistrer comme copie » pour assurer la cohérence de la casse.
- **🔧 Appel de fonction MCP** : Correction de l'appel de fonction MCP manquant pour permettre l'itération.
- **🌐 Erreur NoneType de recherche Web** : Correction de l'erreur de retour NoneType de la recherche Web.
- **⏳ Délai d'attente de recherche Web** : Correction des problèmes de délai d'attente lors de la recherche Web.
- **🛠️ Sélection des outils du menu** : Correction de la sélection des outils du menu en ajoutant l'assainissement, les garde-fous et la traduction à la saisie.

## [0.5.7-ccv2-1.12.2] - 2026-02-06

### Corrigé

- **🔧 Problème de barre de navigation** : Correction d'une incohérence lors d'un nouveau clavardage dans la barre de navigation.

## [0.5.7-ccv2-1.12.1] - 2026-02-05

### Corrigé

- **🧼 Assainissement du journal des modifications** : Correction du problème du journal des modifications pour les variables d'environnement.

## [0.5.7-ccv2-1.12.0] - 2026-02-05

### Ajouté

- **🏷️ Étiquette Protégé** : Ajout d'une étiquette Protégé B.
- **🧪 Couverture de tests** : Ajout de tests supplémentaires.

### Modifié

- **🚫 Comportement du badge de rôle** : Désactivation des changements de rôle via les clics sur le badge de rôle.
- **🔍 Recherche SharePoint** : Amélioration de la fonctionnalité de recherche SharePoint MCP.
- **🔢 Formatage des métriques** : Amélioration du formatage des grands nombres dans le tableau de bord des métriques.

### Corrigé

- **🧼 Assainissement des entrées** : Correction de plusieurs problèmes d'entrées non assainies.
- **🧭 Disposition de la barre de navigation** : Correction des éléments qui se chevauchaient dans la barre de navigation.
- **🧩 Extension de bloc de code** : Correction de l'extension de bloc de code en double.
- **📦 Composants de clavardage** : Correction des importations manquantes.
- **🌐 Contexte i18n** : Correction de l'erreur de contexte du magasin i18n.
- **💬 Infobulle MCP** : Correction de l'infobulle de l'indicateur MCP qui émettait un descripteur d'outil JSON.
- **🌍 Traductions** : Correction des traductions manquantes et de l'affichage de la traduction des erreurs MCP.
- **📤 Traduction du téléversement de fichiers** : Correction du problème de traduction après un téléversement de fichiers réussi.
- **📌 Épinglage des dépendances** : Correction de l'épinglage de version de dépendance manquant.
- **🖱️ Survol du bouton de clavardage** : Correction des éléments manquants au survol.
- **📁 Fenêtre modale d'archive** : Correction du plantage lors de la sortie de la fenêtre modale d'archive de clavardage.
- **🧪 Configuration Pytest** : Correction de la configuration du cadriciel pytest.
- **🧵 Fil d'exécution de recherche Web** : Correction de la recherche Web bloquant le fil d'exécution principal.
- **♿ Étiquettes d'accessibilité** : Correction de plusieurs problèmes d'étiquetage d'accessibilité.
- **🔐 Synchronisation du jeton WebSocket MCP** : Les sessions WebSocket utilisent maintenant toujours le jeton d'accès le plus récent.
- **💡 Infobulle du message suivant** : Ajout de l'infobulle manquante.
- **🔄 Rafraîchissement du bouton Nouveau clavardage** : Le bouton Nouveau clavardage efface maintenant l'identifiant de clavardage au clic, forçant un rafraîchissement.

### Retiré

- **🧹 Mise en cache de la recherche Web** : Retrait de la mise en cache de la recherche Web.

## [0.5.7-ccv2-1.11.5] - 2026-01-09

### Corrigé

- **🔧 MCP vers Sharepoint** : Augmentation de la valeur du délai d'attente.

## [0.5.7-ccv2-1.11.4] - 2026-01-09

### Corrigé

- **🔧 MCP vers Sharepoint** : Problèmes de jeton d'accès délégué via WebSocket.
- **🔧 Wiki-Grounding** : Mise à jour de la contrainte de dépendance.

## [0.5.7-ccv2-1.11.3] - 2026-01-07

### Corrigé

- **🔧 MCP vers Sharepoint** : Problèmes de latence et de délai d'attente lors de la récupération de documents.
- **🔧 Durée de vie des clavardages** : Le nettoyage s'effectue maintenant par lots pour éviter les plantages.

## [0.5.7-ccv2-1.11.2] - 2026-01-05

### Corrigé

- **🔧 MCP vers Sharepoint** : Limitation de la profondeur de recherche et des résultats lors de la récupération de documents.
- **🔧 Wiki Grounding** : Contraintes de version des dépendances pyarrow et datasets.

## [0.5.7-ccv2-1.11.2] - 2026-01-05

### Corrigé

- **🔧 MCP vers Sharepoint** : Limitation de la profondeur de recherche et des résultats lors de la récupération de documents.

## [0.5.7-ccv2-1.11.1] - 2025-12-18

### Corrigé

- **🔧 Gestionnaire MCP** : Erreur lors de l'obtention des outils qui fermait la session de manière inattendue.

## [0.5.7-ccv2-1.11.0] - 2025-12-17

### Ajouté

- **📜 Prise en charge de Docling** : Ajout de la prise en charge avancée du chargement de documents.
- **📈 Service de métriques OpenTelemetry** : Introduction du service de métriques OpenTelemetry pour une meilleure observabilité.
- **🔧 Bascule d'accès de groupe** : Ajout de la bascule d'accès de groupe au MCP.
- **⏳ Suppression en masse des clavardages** : Ajout d'un indicateur de chargement lors de la suppression en masse des clavardages.
- **🛠️ Analyse statique** : Intégration de l'analyse statique dans les compilations et l'intégration continue.

### Modifié

- **🗑️ Logique de disposition des clavardages** : Ajustement pour considérer les clavardages non utilisés depuis 30 jours plutôt que ceux créés dans les 30 derniers jours.
- **🎨 Couleurs des paramètres MCP** : Mise à jour des paramètres MCP pour utiliser les couleurs communes.
- **🎨 Couleurs de la page des paramètres de domaine** : Révision de la page des paramètres de domaines pour utiliser les couleurs communes.
- **⚙️ Dépendance CrewAI** : Ajout de la dépendance de prise en charge MCP à CrewAI.

### Corrigé

- **📏 En-tête des paramètres d'administration** : Correction de la hauteur de l'en-tête des paramètres d'administration.
- **🖥️ Espacement des paramètres de recherche Web** : Correction d'un espace manquant entre l'interrupteur à bascule sur la page des paramètres de recherche Web.
- **🌗 Contraste en mode sombre** : Amélioration du contraste des contrôles à bascule en mode sombre.
- **♿ Améliorations de l'accessibilité** : Correction de divers attributs ARIA d'accessibilité.
- **🔄 Nettoyage asynchrone** : Résolution du manque d'asynchronisme dans le nettoyage des vecteurs de fichiers.
- **🖲️ Affichage de l'état des bascules** : Correction des bascules d'activation des modèles pour afficher correctement l'état réel.
- **⏳ Délai de connexion** : Augmentation du délai d'attente Qdrant pour atténuer les erreurs de connexion transitoires.

### Retiré

- **🗑️ Cadriciel de tests Cypress** : Retrait du cadriciel de tests Cypress inutilisé.

## [0.5.7-ccv2-1.10.0] - 2025-12-08

### Ajouté

- **🔗 MCP vers Sharepoint** : Mise en œuvre de MCP vers SharePoint pour améliorer l'accessibilité des documents.

## [0.5.7-ccv2-1.9.0] - 2025-11-05

### Ajouté

- **💻 Gestion de la durée de vie des clavardages** : Mise en œuvre de la gestion de la durée de vie des clavardages avec des nettoyages automatisés.
- **⚙️ Configuration de Wiki Grounding** : Ajout de la configuration de la concurrence maximale et mise à jour des fonctions de récupération associées pour prendre en charge les opérations asynchrones.
- **🧠 Filtre de raisonnement** : Ajout d'un filtre de raisonnement au traitement des messages pour la génération de titres et d'étiquettes.

### Modifié

- **⚠️ Avertissement d'invite** : Révision du texte d'avertissement pour clarifier que les enregistrements sont transitoires.

### Corrigé

- **📊 Enregistrements de métriques** : Lors de l'utilisation de plusieurs modèles, les métriques d'enregistrement sont maintenant collectées.
- **📅 Extraction de métriques du jour même** : Correction d'un problème où l'extraction de métriques pour le jour même échouait.
- **🌍 Améliorations des traductions** : Amélioration de certaines traductions pour assurer une expérience utilisateur plus cohérente et accessible.
- **🔄 Appels asynchrones à la base de données vectorielle** : Correction des problèmes liés aux appels asynchrones aux bases de données vectorielles pour une meilleure fiabilité.
- **🌐 Récupérations de recherche Web** : Résolution des problèmes d'appels asynchrones lors des récupérations de recherche Web pour améliorer les performances et la précision.

## [0.5.7-ccv2-1.8.2] - 2025-10-14

### Corrigé

- **📌 Épinglage de la dépendance pydantic** : Épinglage à la version 2.11.10 en raison de problèmes avec les versions 2.12.1 et 2.12.2.

## [0.5.7-ccv2-1.8.1] - 2025-10-14

### Modifié

- **💬 Bascule de recherche Web** : Ajout de l'étiquette bêta à la bascule.

## [0.5.7-ccv2-1.8.0] - 2025-10-03

### Ajouté

- **💻 Exportation des métriques** : Ajout de la fonctionnalité d'exportation des données et des journaux de métriques.
- **🔗 Attribution et gestion de groupes** : Mise en œuvre de l'attribution et de la gestion de groupes basées sur le domaine.

### Modifié

- **⚙️ Valeurs par défaut de l'interface des paramètres avancés** : Section « Paramètres avancés » repliable fermée par défaut dans les contrôles.
- **⚙️ Bascules de fonctionnalités** : Empêchement de l'activation simultanée des fonctionnalités de recherche Web et de Wiki Grounding.

### Retiré

- **🔧 Optimisation de la compilation** : Retrait des configurations de compilation hatch inutilisées pour permettre des améliorations avec uv.
- **🔗 Nettoyage des dépendances** : Retrait de la dépendance torch inutilisée des exigences.

## [0.5.7-ccv2-1.7.1] - 2025-09-22

### Amélioré

- **🗑️ Réactivité de la suppression de clavardage** : Lorsqu'un clavardage est supprimé, il est immédiatement retiré de l'interface.
- **🕰️ Heure actuelle dans le contexte** : Le contexte contient toujours l'heure actuelle.
- **🌐 Wiki-Grounding : Meilleure compréhension temporelle** :

### Corrigé

- **🌐 Wiki-Grounding : Verrouillage des requêtes** : Prévention de certaines erreurs en séparant l'accès aux ressources par requête.

## [0.5.7-ccv2-1.7.0] - 2025-09-05

### Ajouté

- **🌐 Wiki-Grounding** : Nouvelle fonctionnalité pouvant ajouter des informations de Wikipédia aux clavardages pour enrichir les connaissances d'un modèle.
- **📶 Latence inter-invites** : Fourniture d'un histogramme sur la latence inter-invites dans les métriques.

### Amélioré

- **🤖 Recherche d'utilisateurs** : Permet d'utiliser plus de champs lors de la recherche d'utilisateurs.
- **🔠 Liste de modèles alphabétique** : Les modèles sont maintenant affichés par ordre alphabétique.

### Corrigé

- **💬 Modèle par défaut lors d'un nouveau clavardage** : Correction du modèle par défaut qui n'était pas toujours utilisé lors de la création d'un nouveau clavardage.
- **🪪 Mise à jour du rôle** : Correction de la définition du rôle d'un utilisateur via la fenêtre modale de modification de l'utilisateur.
- **</> Récupération des invites** : Les appels sont maintenant asynchrones pour éviter les blocages lors de requêtes volumineuses.

## [0.5.7-ccv2-1.6.2] - 2025-08-21

### Corrigé

- **🚨 Ajout de la dépendance manquante** : Ajout de la dépendance tiktoken manquante.

## [0.5.7-ccv2-1.6.1] - 2025-08-14

### Corrigé

- **🚨 Coquille dans l'avertissement** : Correction du libellé de l'avertissement pour assurer la véracité des données en français et en anglais.
- **🗃️ Verrouillage de la base de données** : Correction d'un problème causant le verrouillage de la base de données par une transaction ouverte.
- **📝 Visibilité des invites** : Correction des invites publiques non visibles par les utilisateurs.

## [0.5.7-ccv2-1.6.0] - 2025-08-07

### Ajouté

- **📑 Pagination et chargement dynamique de la liste d'invites** : Amélioration de l'expérience utilisateur lors de la consultation des invites en incluant la pagination.
- **✍️ Fonctionnalités de gestion de la rétroaction pour les administrateurs** : Possibilité d'exporter ou de supprimer toute la rétroaction.
- **🗂️ Index sur les invites et la rétroaction** : Ajout d'index sur les tables d'invites et de rétroaction pour accélérer les requêtes à la base de données.
- **🧹 Scripts de nettoyage pour Qdrant** : Ajout de scripts permettant le nettoyage des collections.
- **📚 Réindexation des fichiers permise** : Réindexation des fichiers si une collection n'est pas en place mais que le fichier est encore disponible.

### Modifié

- **🚨 Amélioration de la gestion et du signalement des erreurs** : Amélioration de la description et de la gestion des erreurs dans les couches intermédiaires.
- **🩺 Amélioration du bilan de santé de la base de données** : Amélioration du bilan de santé de la base de données pour éviter de bloquer le fil d'exécution principal.
- **🗃️ Refactorisation de l'initialisation de la base de données** : Refactorisation de l'initialisation de la base de données pour simplifier l'utilisation et les tests.

### Corrigé

- **3️⃣ Limite de sélection de modèles simultanés** : Limitation du nombre de modèles simultanés à 3.
- **🔍 Bascules de contexte complet** : Correction de la mauvaise configuration du contexte complet lors de l'utilisation de la recherche Web.

## [0.5.7-ccv2-1.5.0] - 2025-07-10

### Ajouté

- **🔗 Intégration de serveur MCP** : Intégration de la prise en charge des serveurs MCP, élargissant les options de connexion et la flexibilité de déploiement.
- **📰 Bureau de nouvelles avec MCP** : Introduction de l'intégration du Bureau de nouvelles aux côtés de la prise en charge des serveurs MCP, permettant la gestion centralisée des nouvelles et des mises à jour.
- **🎓 Liens vers les cours de formation (EN/FR)** : Ajout de liens vers les cours de formation officiels en anglais et en français pour un accès plus facile aux ressources d'apprentissage.
- **🛠️ Fenêtre modale de signalement de problèmes** : Accès à la fenêtre modale de signalement via une icône d'exclamation dans le menu de réponse des clavardages.
- **💡 Fenêtre modale de suggestions** : Accès à la fenêtre modale de suggestions via une icône d'ampoule dans le menu de réponse des clavardages.
- **🔍 Analyse de sécurité Trivy dans l'intégration continue** : Ajout de l'analyse Trivy au pipeline d'intégration continue pour la détection automatisée des vulnérabilités et une sécurité améliorée.

### Modifié

- **📊 Mise à jour de la marque du fichier ReadMe** : Mise à jour du fichier README pour afficher la marque CANChat.
- **🏆 ELO hybride de rétroaction des modèles** : Changement du système ELO de rétroaction des modèles vers une solution hybride pour une meilleure précision du classement.

### Corrigé

- **🛡️ Validation d'URL de recherche Brave** : Validation maintenant de l'URL des résultats de recherche Brave et journalisation de toute URL malformée pour améliorer la fiabilité et la sécurité.
- **🔒 Amélioration de la gestion des erreurs de verrouillage Redis** : Amélioration de la gestion des erreurs pour la gestion et le nettoyage des verrous Redis, augmentant la fiabilité et la stabilité.
- **📝 Accessibilité améliorée** : Amélioration de l'accessibilité pour une meilleure expérience utilisateur.
- **📊 Tableau de bord des métriques** : Amélioration de l'accès et de l'affichage des métriques de modèles pour les analystes.

### Retiré

- **🔕 Notification de nouvelle version retirée** : Retrait de la notification toast pour les mises à jour de nouvelle version.

## [0.5.7-ccv2-1.4.0] - 2025-06-11

### Ajouté

- **📊 Colonnes de rétroaction supplémentaires** : Ajout de colonnes supplémentaires au système de rétroaction pour un meilleur suivi et une meilleure analyse.
- **📈 Rôles d'analyse et d'analyse globale** : Ajout de nouveaux rôles pour accéder au tableau de bord des métriques, permettant une accessibilité plus granulaire pour l'analyse.
- **🌍 Localisation des bannières** : Ajout de la prise en charge des bannières localisées, permettant l'affichage des annonces en plusieurs langues.
- **📝 Indicateur de récupération complète de documents** : Ajout d'un indicateur pour permettre le traitement du document complet lors de la récupération Web.

### Modifié

- **📊 Graphique d'inscription des utilisateurs** : Changement du graphique du nombre total d'utilisateurs quotidiens au nombre d'inscriptions.
- **💡 Suggestions d'invites par défaut** : Mise à jour des suggestions d'invites par défaut pour fournir des suggestions plus pertinentes et utiles aux utilisateurs.

### Corrigé

- **📊 Données du graphique historique d'utilisateurs quotidiens** : Correction des données historiques du graphique d'utilisateurs quotidiens qui étaient incorrectes ou incomplètes, assurant un rapport précis.

### Retiré

- **🧹 Nettoyage des dépendances** : Retrait des anciennes dépendances pour simplifier le projet et améliorer la maintenabilité.
- **🔗 Importation d'invites V1** : Retrait de la possibilité d'importer les invites privées V1 dans l'espace de travail des invites.

## [0.5.7-ccv2-1.3.1] - 2025-05-15

### Corrigé

- **📊 Tableau de bord des métriques** : Résolution des problèmes de plage de dates dans les graphiques pour une analyse plus précise.

## [0.5.7-ccv2-1.3.0] - 2025-05-15

### Modifié

- **🛡️ Licences** : Ajout des licences de la Couronne canadienne au projet pour la conformité et la transparence.

### Ajouté

- **📊 Tableau de bord des métriques** : Le tableau de bord inclut maintenant un graphique pour l'inscription historique des utilisateurs, et la sélection de plage de dates a été ajoutée pour une analyse plus flexible.

### Corrigé

- **📊 Normalisation de l'horodatage des métriques de messages** : Les métriques de messages utilisent maintenant un format d'horodatage cohérent améliorant la précision des données.
- **🌍 Améliorations des traductions** : Ajout des traductions manquantes pour assurer une expérience utilisateur plus cohérente et accessible pour les locuteurs de toutes les langues prises en charge.
- **💡 Espacement des suggestions IA** : Les suggestions IA incluent maintenant toujours un espace au début de la phrase pour une meilleure lisibilité.

## [0.5.7-ccv2-1.2.1] - 2025-04-28

### Modifié

- **📊 Tableau de bord des métriques** : Le tableau de bord a maintenant des onglets et une analyse des modèles fournissant des mises à jour en temps réel et une meilleure clarté.

### Corrigé

- **📊 Tableau de bord des métriques** : Correction des problèmes de données avec les invites quotidiennes et les jetons.

## [0.5.7-ccv2-1.2.0] - 2025-04-04

### Modifié

- **⚙️ Emplacement du bouton d'aide** : Déplacement du bouton d'aide vers le menu supérieur droit pour un accès plus facile et une meilleure navigation.
- **🔄 Améliorations de la page d'attente** : La page d'attente se rafraîchit automatiquement lors des changements de rôle, fournissant des mises à jour en temps réel et une meilleure clarté.

### Ajouté

- **🔗 Importation d'invites V1** : Les utilisateurs peuvent maintenant importer leurs invites privées V1 dans leur espace de travail d'invites dédié.
- **📋 Formulaires de signalement de problèmes et de suggestions** : Ajout de formulaires pour signaler des problèmes et soumettre des suggestions.
- **🌐 Domaine utilisateur** : Ajout du domaine utilisateur pour le multilocataire.
- **📊 Tableau de bord des métriques d'utilisation pour les administrateurs** : Ajout d'un tableau de bord administrateur pour suivre les métriques d'utilisation.

### Corrigé

- **🔧 Problème de sauvegarde des groupes RBAC de modèles** : Correction d'un problème de sauvegarde des modèles lié aux groupes RBAC.
- **🔧 Manifeste PWA** : Correction d'un problème avec le manifeste de l'application Web progressive (PWA) pour assurer un fonctionnement et une compatibilité appropriés sur tous les appareils.

## [0.5.7-ccv2-1.1.2] - 2025-02-27

### Corrigé

- **🌐 Internationalisation améliorée (i18n)** : Traductions affinées et élargies.
- **📂 Dossiers** : Retrait de l'exportation JSON.
- **✏️ Éléments de clavardage** : Le renommage des éléments de clavardage dans un dossier se fait maintenant instantanément.
- **📂 Clavardages archivés** : Retrait de l'exportation JSON.
- **📌 Clavardages épinglés** : Les clavardages épinglés affichent maintenant une option de désépinglage.
- **🖼️ Affichage des invites** : Correction des problèmes visuels et affichage correct de la couleur du texte selon le mode sombre/clair.

## [0.5.7-ccv2-1.1.1] - 2025-02-21

### Corrigé

- **🔧 Télécharger les clavardages** : Retrait de l'exportation JSON.

## [0.5.7-ccv2-1.1.0] - 2025-02-20

### Modifié

- **⚙️ Stabilité du versionnage** : Pour des raisons de stabilité, nous avons cessé de rebaser notre code depuis Open WebUI à la version v0.5.7.
- **🎨 Refonte de la page de création/modification d'invites** : Nouvelle interface pour créer et modifier des invites.
- **🌍 Bouton de traduction** : Nous avons déplacé le bouton de langue des fenêtres modales de paramètres vers le menu de la barre latérale.
- **⚙️ Flux de travail CI/CD** : Retrait des flux de travail défectueux/non souhaités dédiés à Open WebUI.
- **🔗 Marque blanche Open WebUI** : Retrait de la marque Open WebUI.
- **🔧 Marque blanche Open WebUI** : Retrait d'Open WebUI.
- **🔗 Nouvel écran d'activation en attente** : L'écran d'attente correspond maintenant à la marque CANChat avec un lien pour demander l'accès dans les deux langues officielles.

### Ajouté

- **🔗 Espace de travail d'invites privées pour les utilisateurs** : Les utilisateurs ont maintenant la possibilité de créer/modifier leurs propres invites privées dans leur espace de travail d'invites.
- **💡 Documentation EN/FR** : Liens vers la documentation de CANChat.
- **🔍 Sondage de rétroaction EN/FR** : Sondage permettant la rétroaction des utilisateurs.
- **🌍 Descriptions des modèles** : Les modèles ont maintenant une description rapide dans les deux langues officielles.

### Corrigé

- **✨ Logo Favicon** : Les logos favicon utilisent maintenant le logo DSAI.
- **🌍 Internationalisation améliorée (i18n)** : Traductions affinées et élargies.
- **📚 Accessibilité** : Correction de certains problèmes d'accessibilité principalement sur la page de clavardage/principale.
- **⚙️ Page de paramètres** : Retrait des paramètres non souhaités.
- **🔧 Licences** : Réajout des licences requises.
- **🧠 Suggestions d'invites** : Lorsqu'un nouveau clavardage est lancé, les suggestions d'invites parcourent maintenant toutes les options disponibles.
- **🌍 Étiquette/Recherche** : tag:search se traduit maintenant dans les deux langues officielles.

## [0.5.7-ccv2-1.0.0] - 2025-01-23

### Corrigé

- **🔧 Rebasage** : Rebasage à la version v0.5.7, conservation de notre client qdrant.

## [0.5.4-ccv2-1.0.4] - 2025-01-27

### Corrigé

- **🌍 Traductions fr-CA** : Traductions manquantes/corrections.

## [0.5.4-ccv2-1.0.3] - 2025-01-23

### Corrigé

- **🌍 Traductions fr-CA** : Traductions manquantes/corrections.

## [0.5.4-ccv2-1.0.2] - 2025-01-21

### Corrigé

- **🌍 Section À propos** : Retrait de l'ancien contenu d'Open WebUI.

## [0.5.4-ccv2-1.0.1] - 2025-01-16

### Corrigé

- **🌍 Traductions fr-CA** : Traductions manquantes.

## [0.5.4-ccv2-1.0.0] - 2025-01-15

### Corrigé

- **🔧 Rebasage** : Rebasage à la version v0.5.4, conservation de notre client qdrant.

## [0.4.6-ccv2-1.0.1] - 2024-11-29

### Corrigé

- **🔧 Suggestions d'invites** : Ajout du code de persistance manquant du rebasage.
- **🔧 Titre de l'application** : Retrait de Web OpenUI du nom.

## [0.4.6-ccv2-1.0.0] - 2024-11-28

### Corrigé

- **🔧 Rebasage** : Rebasage à la version v0.4.6, conservation de notre client qdrant.

## [0.4.5-ccv2-1.0.1] - 2024-11-27

### Corrigé

- **🔧 DockerFile** : Attribution au groupe des mêmes permissions que l'utilisateur pour OpenShift.

## [0.4.5-ccv2-1.0.0] - 2024-11-26

### Ajouté

- **🔧 Rebasage** : Rebasage à la version v0.4.5, conservation de notre client qdrant.

## [0.4.4-ccv2-1.0.0] - 2024-11-25

### Ajouté

- **🔧 Rebasage** : Rebasage à la version v0.4.4, conservation de notre client qdrant.

## [0.4.1-ccv2-1.0.0] - 2024-11-20

### Ajouté

- **🔧 Rebasage** : Rebasage à la version v0.4.1, conservation de notre client qdrant.

## [0.3.35-ccv2-1.0.1] - 2024-11-07

### Corrigé

- **🔧 DockerFile** : Correction d'un répertoire manquant.

## [0.3.35-ccv2-1.0.0] - 2024-11-07

### Ajouté

- **🔧 Rebasage** : Rebasage à la version v0.3.35, conservation de notre client qdrant.

## [0.3.32-ccv2-1.0.3] - 2024-11-07

### Corrigé

- **🔧 DockerFile** : Retrait d'un fichier non nécessaire du COPY.

## [0.3.32-ccv2-1.0.2] - 2024-11-07

### Corrigé

- **🔧 DockerFile** : Correction du fichier Docker pour qu'il fonctionne avec Qdrant.
- **🤖 Client Qdrant** : Correction de la recherche par Qdrant.

## [0.3.32-ccv2-1.0.1] - 2024-10-18

### Corrigé

- **🔧 Client Qdrant** : Correction de la recherche par Qdrant.

## [0.3.32-ccv2-1.0.0] - 2024-10-10

### Ajouté

- **🤖 Client Qdrant** : Remplacement du client Chroma par Qdrant.
- **🌍 Traductions fr-CA** : Ajout des traductions canadiennes-françaises pour l'interface.
- **🏛️ Licence Couronne** : Ajout de la licence de la Couronne du Canada.
- **🎨 Marque CANChat** : Application de la marque CANChat.
- **🔧 Invites par défaut** : Ajout des invites de suggestions par défaut.
