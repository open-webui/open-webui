# Welcome to CANChat 👋

![GitHub stars](https://img.shields.io/github/stars/dto-btn/canchat-v2?style=social)
![GitHub forks](https://img.shields.io/github/forks/dto-btn/canchat-v2?style=social)
![GitHub watchers](https://img.shields.io/github/watchers/dto-btn/canchat-v2?style=social)
![GitHub repo size](https://img.shields.io/github/repo-size/dto-btn/canchat-v2)
![GitHub last commit](https://img.shields.io/github/last-commit/dto-btn/canchat-v2?color=red)

([Français](#bienvenue-à-canchat))

**CANChat is an extensible, feature-rich, and user-friendly self-hosted AI platform designed to operate entirely offline.** It supports various LLM runners like **Ollama** and **OpenAI-compatible APIs**, with **built-in inference engine** for RAG, making it a **powerful AI deployment solution**.

**For more information, be sure to check out our [Documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat.aspx).**

## CANChat's Key Features

- 🚀 **Effortless Setup**: Install seamlessly using Docker or Kubernetes (kubectl, kustomize or helm) for a hassle-free experience with support for both `:ollama` and `:cuda` tagged images.

- 🤝 **Ollama/OpenAI API Integration**: Effortlessly integrate OpenAI-compatible APIs for versatile conversations alongside Ollama models. Customize the OpenAI API URL to link with **LMStudio, GroqCloud, Mistral, OpenRouter, and more**.

- 🛡️ **Granular Permissions and User Groups**: By allowing administrators to create detailed user roles and permissions, we ensure a secure user environment. This granularity not only enhances security but also allows for customized user experiences, fostering a sense of ownership and responsibility amongst users.

- 📱 **Responsive Design**: Enjoy a seamless experience across Desktop PC, Laptop, and Mobile devices.

- 📱 **Progressive Web App (PWA) for Mobile**: Enjoy a native app-like experience on your mobile device with our PWA, providing offline access on localhost and a seamless user interface.

- ✒️🔢 **Full Markdown and LaTeX Support**: Elevate your LLM experience with comprehensive Markdown and LaTeX capabilities for enriched interaction.

- 🎤📹 **Hands-Free Voice/Video Call**: Experience seamless communication with integrated hands-free voice and video call features, allowing for a more dynamic and interactive chat environment.

- 🛠️ **Model Builder**: Easily create Ollama models via the Web UI. Create and add custom characters/agents, customize chat elements.

- 🐍 **Native Python Function Calling Tool**: Enhance your LLMs with built-in code editor support in the tools workspace. Bring Your Own Function (BYOF) by simply adding your pure Python functions, enabling seamless integration with LLMs.

- 📚 **Local RAG Integration**: Dive into the future of chat interactions with groundbreaking Retrieval Augmented Generation (RAG) support. This feature seamlessly integrates document interactions into your chat experience. You can load documents directly into the chat or add files to your document library, effortlessly accessing them using the `#` command before a query.

- 🔍 **Web Search for RAG**: Perform web searches using providers like `SearXNG`, `Google PSE`, `Brave Search`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `TavilySearch`, `SearchApi` and `Bing` and inject the results directly into your chat experience.

- 🌐 **Web Browsing Capability**: Seamlessly integrate websites into your chat experience using the `#` command followed by a URL. This feature allows you to incorporate web content directly into your conversations, enhancing the richness and depth of your interactions.

- 🎨 **Image Generation Integration**: Seamlessly incorporate image generation capabilities using options such as AUTOMATIC1111 API or ComfyUI (local), and OpenAI's DALL-E (external), enriching your chat experience with dynamic visual content.

- ⚙️ **Many Models Conversations**: Effortlessly engage with various models simultaneously, harnessing their unique strengths for optimal responses. Enhance your experience by leveraging a diverse set of models in parallel.

- 🔐 **Role-Based Access Control (RBAC)**: Ensure secure access with restricted permissions; only authorized individuals can access your Ollama, and exclusive model creation/pulling rights are reserved for administrators.

- 🌐🌍 **Multilingual Support**: Experience CANChat in your preferred language with our internationalization (i18n) support. Join us in expanding our supported languages! We're actively seeking contributors!

- 🧩 **Pipelines, Open WebUI Plugin Support**: Seamlessly integrate custom logic and Python libraries into CANChat using a pipelines plugin framework. Launch your Pipelines instance, set the OpenAI URL to the Pipelines URL, and explore endless possibilities. Examples include **Function Calling**, User **Rate Limiting** to control access, **Usage Monitoring** with tools like Langfuse, **Live Translation with LibreTranslate** for multilingual support, **Toxic Message Filtering** and much more.

- 🌟 **Continuous Updates**: We are committed to improving CANChat with regular updates, fixes, and new features.

Want to learn more about CANChat's features? Check out our [documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat.aspx) for a comprehensive overview!

---

## Keyboard navigation

- Press **Alt+Up** (**Option+Up** on macOS) in the message composer to jump to the active message. **Shift+Tab** follows the normal focus order. Use **Up/Down** to move between messages, or **Home/End** for the first/last loaded message. Focusing a message reveals its timestamp and actions.
- Press **Enter** on a message to focus its actions. Use the **arrow keys** to choose an action and **Enter/Space** to activate it. **Escape** returns to the message; **Tab/Shift+Tab** lets you leave the message area.
- In a chat's **Chat Menu**, choose **Move to folder** to select an existing folder, remove the chat from its folder, or create a new destination folder without dragging. Choose **Tags** to manage tags.
- Use **Tab** within the model selector to reach the **Temporary Chat** switch. **Escape** closes the selector and returns focus to its button.
- Folder and Chat Controls expansion buttons support **Enter/Space**. Sidebar folders also support **Right/Left** to expand/collapse. On large screens (1024px and wider), the Chat Controls side panel is non-modal and does not trap keyboard focus. On smaller screens, and when zoomed in, it opens as a modal drawer that keeps focus inside until you close it.
- Hover-revealed controls also appear on keyboard focus and remain visible on devices without hover. Hidden controls do not intercept pointer clicks. Message action bars scroll horizontally on narrow screens.

The keyboard regression tests mount real components with mocked API responses; no running backend is required:

```bash
npx playwright test playwright/tests/e2e/accessibility/keyboard.spec.ts --project=chromium-en --project=firefox-en --no-deps --workers=1
```

## How to Install

### Prerequisites

Before you begin, ensure your system meets these minimum requirements:

- **Operating System**: Linux (or WSL on Windows), Windows 11, or macOS. (Recommended for best compatibility)
- **Python: Version 3.11 or higher**. (Required for backend services)
- **Node.js: Version 22.10 or higher**. (Required for frontend development)
- **IDE (Recommended)**: We recommend using an IDE like VS Code for code editing, debugging, and integrated terminal access. Feel free to use your favorite IDE if you have one!

### Setting Up Your Local Environment

We'll set up both the frontend (user interface) and backend (API and server logic).

---

#### 1. Clone the Repository

First, use `git clone` to download the CANChat V2 repository to your local machine. This will create a local copy of the project on your computer.

1. Open your terminal (or Git Bash if you're on Windows).
2. Navigate to the directory where you want to store the project.
3. Run the following commands:

   ```bash
   git clone https://github.com/dto-btn/canchat-v2.git
   cd canchat-v2
   ```

   - The `git clone` command downloads the project files from GitHub.
   - The `cd canchat-v2` command navigates you into the newly created project directory.

---

#### 2. Frontend Setup (User Interface)

Let's get the user interface (what you see in your browser) up and running first:

#### 2.1 Configure Environment Variables

Copy the example environment file to `.env`:

```bash
cp -RPp .env.example .env
```

- This command copies the `.env.example` file to a new file named `.env`.
- The `.env` file is where you'll configure environment variables for the frontend.
- If you have a mac you need to comment out certain lines as instructed.
- Reach out to a team member for the API Key to complete the config.

**Customize `.env`:**  
Open the `.env` file in your code editor (e.g., VS Code). For local development, the default settings in `.env.example` should suffice, but you can customize them if needed.

#### EKH Grounding (Optional)

To use the Enterprise Knowledge Hub (EKH) for knowledge grounding, set `WIKIPEDIA_GROUNDING_PROVIDER=ekh` and configure `EKH_BASE_URL` with the EKH service URL. `EKH_KNOWLEDGE_SOURCE` selects the initial source: `wikipedia` or `tbs-policies`. Set `EKH_API_KEY` if the EKH service requires authentication; `EKH_TIMEOUT_SECONDS` controls the request timeout (default: `5`). Administrators can switch between the indexed sources in **Admin Panel > Settings > Grounding**. Invalid provider/source values fall back to `txtai`/`wikipedia`, and invalid timeouts fall back to `5` seconds.

> **Important:** If you plan to contribute to the repository, **do not commit sensitive information to your `.env` file**. Always review your environment variables before pushing changes to ensure no secrets, credentials, or private data are exposed.

---

#### 2.2 Install Frontend Dependencies

Navigate to the frontend directory if you're not already there:

```bash
cd canchat-v2
```

Install the required JavaScript packages:

```bash
npm install
```

If you encounter compatibility warnings or errors, try:

```bash
npm install --force
```

---

#### 2.3 Start the Frontend Development Server

Launch the frontend development server:

```bash
npm run dev
```

- If successful, the server will indicate it's running and provide a local URL.
- Open your browser and navigate to **[http://localhost:5173](http://localhost:5173)**.
- You should see a message indicating that the frontend is running and is waiting for the backend to be available.

Keep this terminal running; it's serving your frontend!

#### 2.4 Frontend Accessibility Tests

Run the frontend unit and server-rendered component tests:

```bash
npm run test:frontend -- --run
```

Run the standalone accessibility browser tests (no backend or signed-in session required):

```bash
npx playwright install chromium
npx playwright test playwright/tests/e2e/accessibility --project=chromium-en --no-deps --reporter=list
```

The frontend CI workflow runs both suites. Browser coverage includes rendered navigation
structure, image alternatives, shared text/placeholder contrast, keyboard focus indicators,
border styling, upload error associations in both locales, and required rating feedback.
These focused checks do not replace a full-page accessibility audit.

---

#### 3. Backend Setup (API and Server)

Run the backend in a **separate terminal** to manage your workflows cleanly.

---

#### 3.1 Using VS Code Integrated Terminals (Optional)

- Open a new terminal in VS Code: go to `Terminal` > `New Terminal` or use the shortcut:
  - **Windows/Linux:** `Ctrl + Shift +`
  - **macOS:** `Cmd + Shift +`

- Navigate to the backend directory:

  ```bash
  cd backend
  ```

Now you’ll have two terminals: one for the frontend and one for the backend.

---

#### 3.2 Create and Activate a Conda Environment (Recommended)

To isolate project dependencies and avoid conflicts, use Conda:

```bash
conda create --name canchat-v2 python=3.11
conda activate canchat-v2
```

- **`conda create --name canchat-v2 python=3.11`:** Creates a Conda environment with Python 3.11.
- **`conda activate canchat-v2`:** Activates the Conda environment. The terminal prompt will change to include `(canchat-v2)`.

> If you're not using Conda, ensure you have Python 3.11 or higher installed.

---

#### 3.3 Install Backend Dependencies

Run the following command in the backend terminal:

```bash
pip install -r requirements.txt -U
```

- This installs all the Python libraries required for the backend from `requirements.txt`.
- The `-U` flag ensures the latest compatible versions are installed.

---

#### 3.4 Start the Backend Development Server

Run the backend development server script:

```bash
sh dev.sh
```

- This will start the backend server, and you should see output in the terminal.
- Access the API documentation in your browser: **[http://localhost:8080/docs](http://localhost:8080/docs)**.

---

#### 4. Final Steps: Run Everything Together

🎉 Congratulations! You now have both the frontend and backend running locally:

1. Return to the frontend URL: **[http://localhost:5173](http://localhost:5173)**.
2. Refresh the page.
   - You should see the full application connected to the backend!

That's it—you're all set up!

## How to Contribute

### Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT). By participating, you are expected to uphold this code. Please report unacceptable behavior to the [maintainers](mailto:ssc.canchat-support-assistance-canchat.spc@ssc-spc.gc.ca).

### Reporting Bugs

If you find a bug, please open an issue on our [issue tracker](https://github.com/dto-btn/canchat-v2/issues) and provide as much detail as possible, including your operating system, browser, and steps to reproduce the bug.

### Suggesting Enhancements

We welcome suggestions for enhancements. Open an issue on the [issue tracker](https://github.com/dto-btn/canchat-v2/issues) and include a detailed description of your proposed enhancement.

### Code Contribution

- Ensure your code follows our style guide.
- Test your changes thoroughly.
- Submit a pull request to the dev branch of the upstream repository.

### Security Issue

Do not post any security issues on the public repository! See [SECURITY.md](SECURITY)

## License

This project is licensed under the [BSD-3-Clause License](LICENSE) - see the [LICENSE](LICENSE) file for details.

## Support

If you have any questions, suggestions, or need assistance, please see our
[Documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat.aspx).

---

# Bienvenue à CANChat

**CANChat est une plateforme d’intelligence artificielle (IA) auto-hébergée, extensible, riche en fonctionnalités et conviviale, conçue pour fonctionner entièrement hors ligne.** Elle prend en charge divers moteurs LLM comme **Ollama** et les **APIs compatibles avec OpenAI**, avec un **moteur d'inférence intégré** pour le RAG, faisant ainsi de CANChat une **puissante solution de déploiement IA**.

**Pour plus d'informations, consultez notre [documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat_FR.aspx).**

## Principales fonctionnalités de CANChat

- 🚀 **Configuration facilitée** : Installez facilement avec Docker ou Kubernetes (kubectl, kustomize ou helm) pour une expérience sans souci, avec prise en charge des images marquées `:ollama` et `:cuda`.

- 🤝 **Intégration API Ollama/OpenAI** : Intégrez facilement des API compatibles avec OpenAI pour des conversations polyvalentes, en plus des modèles d’Ollama. Personnalisez l’URL API OpenAI pour vous connecter à **LMStudio, GroqCloud, Mistral, OpenRouter, et plus encore**.
- 🛡️ **Permissions granulaires et groupes d’utilisateurs** : Permettez aux administrateurs de créer des rôles et des permissions détaillés pour garantir un environnement sécurisé. Cette granularité renforce la sécurité et permet des expériences utilisateur personnalisées, favorisant un sentiment de responsabilité chez les utilisateurs.

- 📱 **Design réactif** : Profitez d'une expérience harmonieuse sur ordinateur de bureau, ordinateur portable et appareils mobiles.
- 📱 **Application web progressive (PWA) pour mobile** : Profitez d’une expérience semblable à une application native sur votre appareil mobile grâce à notre PWA, offrant un accès hors ligne sur localhost et une interface utilisateur fluide.
- ✒️🔢 **Prise en charge complète de Markdown et LaTeX** : Élevez votre expérience LLM avec des capacités Markdown et LaTeX complètes pour des interactions enrichies.
- 🎤📹 **Appel audio/vidéo mains libres** : Expérimentez une communication fluide grâce aux fonctionnalités d’appel audio et vidéo intégrées, permettant un environnement de discussion plus dynamique et interactif.
- 🛠️ **Créateur de modèles** : Créez facilement des modèles Ollama via l’interface Web. Ajoutez des personnages/agents personnalisés et personnalisez les éléments de discussion.
- 🐍 **Outil d’appel de fonctions Python natif** : Enrichissez vos LLM grâce à un éditeur de code intégré dans l'espace de travail des outils. Ajoutez vos propres fonctions Python pour une intégration transparente avec les LLM.
- 📚 **Intégration RAG locale** : Plongez dans l’avenir des interactions de discussion avec le support révolutionnaire du **RAG (Recovery Augmented Generation)**. Cette fonctionnalité intègre des documents dans vos conversations. Chargez des documents directement dans le chat ou ajoutez des fichiers à votre bibliothèque de documents pour les accéder facilement via la commande `#` avant une requête.
- 🔍 **Recherche web pour RAG** : Effectuez des recherches web à l'aide de fournisseurs comme `SearXNG`, `Google PSE`, `Brave Search`, `serpstack`, `serper`, `Serply`, `DuckDuckGo`, `TavilySearch`, `SearchApi` et `Bing`, et injectez les résultats directement dans votre discussion.
- 🌐 **Capacité de navigation web** : Intégrez des sites web directement dans votre expérience de chat avec la commande `#` suivie d'une URL. Cette fonctionnalité enrichit vos conversations en incorporant du contenu web.
- 🎨 **Intégration de génération d'images** : Profitez des capacités de génération d’images à l’aide d’options telles que l’API AUTOMATIC1111 ou ComfyUI (local), et DALL-E d’OpenAI (externe), enrichissant votre expérience de chat avec du contenu visuel dynamique.
- ⚙️ **Conversations multi-modèles** : Interagissez facilement avec différents modèles simultanément, en exploitant leurs forces uniques pour des réponses optimales. Améliorez votre expérience en utilisant un ensemble diversifié de modèles en parallèle.
- 🔐 **Contrôle d’accès basé sur les rôles (RBAC)** : Garantissez un accès sécurisé avec des permissions restreintes : seules les personnes autorisées ont accès à Ollama, et les droits exclusifs de création/téléchargement de modèles sont réservés aux administrateurs.
- 🌐🌍 **Support multilingue** : Utilisez CANChat dans la langue de votre choix grâce à notre support d’internationalisation (i18n). Participez à l'expansion de nos langues prises en charge ! Nous recherchons activement des contributeurs !

- 🧩 **Pipelines et support de plugins Open WebUI** : Intégrez facilement une logique personnalisée et des bibliothèques Python dans CANChat en utilisant un cadre de plugins pipelines. Lancez votre instance Pipelines, configurez l'URL OpenAI sur l'URL de Pipelines et explorez des possibilités infinies. Exemples : **Appels de fonctions Python**, **limitation d’usage utilisateur**, **suivi d'utilisation** avec des outils comme Langfuse, **traductions en direct avec LibreTranslate**, **filtrage de messages toxiques** et bien plus.

- 🌟 **Mises à jour continues** : Nous nous engageons à améliorer CANChat avec des mises à jour régulières, des correctifs et de nouvelles fonctionnalités.
  Vous souhaitez en savoir plus sur les fonctionnalités de CANChat ? Consultez notre [documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/CANchat_FR.aspx) pour un aperçu complet !

---

## Navigation au clavier

- Appuyez sur **Maj+Tab** dans le champ de message pour revenir au message actif. Utilisez les **flèches haut/bas** pour parcourir les messages, ou **Début/Fin** pour atteindre le premier/dernier message chargé. Le focus révèle l'horodatage et les actions du message.
- Appuyez sur **Entrée** sur un message pour accéder à ses actions. Utilisez les **flèches** pour choisir une action et **Entrée/Espace** pour l'activer. **Échap** revient au message; **Tab/Maj+Tab** permet de quitter la zone.
- Dans le **Menu du chat**, choisissez **Déplacer vers un dossier** pour sélectionner un dossier existant, retirer le chat de son dossier ou créer un dossier de destination sans glisser-déposer. Choisissez **Tags** pour gérer les étiquettes.
- Utilisez **Tab** dans le sélecteur de modèle pour atteindre le bouton **Chat temporaire**. **Échap** ferme le sélecteur et ramène le focus à son bouton.
- Les boutons des dossiers et des contrôles du chat prennent en charge **Entrée/Espace**. Les dossiers de la barre latérale prennent aussi en charge les **flèches droite/gauche** pour développer/réduire leur contenu. Le panneau non modal des contrôles du chat ne piège pas le focus.

## Comment installer CANChat

### Prérequis

Avant de commencer, assurez-vous que votre système répond à ces exigences minimales :

- **Système d’exploitation** : Linux (ou WSL sous Windows), Windows 11 ou macOS. (Recommandé pour une meilleure compatibilité)
- **Python** : Version 3.11 ou supérieure. (Requis pour les services backend)
- **Node.js** : Version 22.10 ou supérieure. (Requis pour le développement frontend)
- **IDE (recommandé)** : Nous recommandons d’utiliser un IDE comme VS Code pour l’édition, le débogage et l’accès au terminal intégré. Si vous le souhaitez, utilisez votre IDE préféré !
-

### Configurer votre environnement local

Nous allons configurer l'interface utilisateur (frontend) et l'API/serveur (backend).

---

#### 1. Cloner le dépôt

Pour commencer, utilisez `git clone` afin de télécharger le dépôt de CANChat V2 sur votre machine locale. Cela créera une copie locale sur votre ordinateur.

1. Ouvrez votre terminal (ou Git Bash si vous êtes sous Windows).
2. Naviguez vers le répertoire où vous voulez stocker le projet.
3. Exécutez les commandes suivantes :

   ```bash
   git clone https://github.com/dto-btn/canchat-v2.git
   cd canchat-v2
   ```

   - La commande `git clone` télécharge les fichiers du projet depuis GitHub.
   - La commande `cd canchat-v2` vous permet d’entrer dans le répertoire nouvellement créé.
   -

---

#### 2. Configuration du Frontend (interface utilisateur)

Commençons par mettre en place l’interface utilisateur.

#### 2.1 Configurer les variables d’environnement

Copiez le fichier d’environnement exemple vers `.env` :

```bash
cp -RPp .env.example .env
```

- Cette commande copie le fichier `.env.example` dans un nouveau fichier nommé `.env`.
- Le fichier `.env` est où vous pourrez configurer les variables d’environnement pour le frontend.
- Si vous avez un Mac, vous devez commenter certaines lignes comme indiqué.
- Contactez un membre de l’équipe pour obtenir la clé API afin de compléter la configuration.

**Personnaliser `.env` :**  
Ouvrez le fichier `.env` dans votre éditeur de code (VS Code, par exemple). Pour le développement local, les paramètres par défaut devraient suffire, mais vous pouvez les personnaliser si nécessaire.

> **Important :** Si vous prévoyez de contribuer au dépôt, **ne commitez pas d’informations sensibles dans votre fichier `.env`**. Vérifiez toujours vos variables d’environnement avant d’effectuer un commit pour vous assurer qu’aucune information privée ou confidentielle n'est exposée.

---

#### 2.2 Installer les dépendances du frontend

Si ce n’est pas encore fait, allez dans le répertoire du frontend :

```bash
cd canchat-v2
```

Installez les paquets JavaScript nécessaires :

```bash
npm install
```

En cas d’avertissements ou d'erreurs de compatibilité, essayez :

```bash
npm install --force
```

---

#### 2.3 Démarrer le serveur de développement du Frontend

Lancez le serveur de développement du frontend :

```bash
npm run dev
```

- Si tout se passe bien, le serveur indiquera qu'il est en fonctionnement et fournira une URL locale.
- Ouvrez votre navigateur et allez à **[http://localhost:5173](http://localhost:5173)**.
- Vous devriez voir un message indiquant que le frontend est opérationnel et attend la connexion avec le backend.
  Gardez ce terminal ouvert : il sert votre frontend !

---

#### 3. Configuration du Backend (API et serveur)

Pour le backend, ouvrez **un nouveau terminal** pour mieux organiser votre workflow.

---

#### 3.1 Utilisation des terminaux intégrés de VS Code (optionnel)

- Ouvrez un nouveau terminal dans VS Code en allant dans `Terminal` > `New Terminal`, ou utilisez les raccourcis suivants :
  - **Windows/Linux :** `Ctrl + Shift +`
  - **macOS :** `Cmd + Shift +`
- Naviguez vers le répertoire backend :
  ```bash
  cd backend
  ```
  Vous disposerez maintenant de deux terminaux : un pour le frontend et un pour le backend.

---

#### 3.2 Créer et activer un environnement Conda (recommandé)

Pour isoler les dépendances du projet et éviter les conflits, utilisez Conda :

```bash
conda create --name canchat-v2 python=3.11
conda activate canchat-v2
```

- **`conda create --name canchat-v2 python=3.11`** : Crée un environnement Conda avec Python 3.11.
- **`conda activate canchat-v2`** : Active l’environnement Conda. Le prompt du terminal affichera `(canchat-v2)`.
  > Si vous n’utilisez pas Conda, assurez-vous d’avoir Python 3.11 ou une version plus récente installée.

---

#### 3.3 Installer les dépendances du backend

Exécutez la commande suivante dans le terminal backend :

```bash
pip install -r requirements.txt -U
```

- Cela installe toutes les bibliothèques nécessaires au backend en se basant sur le fichier `requirements.txt`.
- Le flag `-U` garantit que les versions les plus récentes compatibles seront installées.

---

#### 3.4 Démarrer le serveur de développement du Backend

Lancez le script du serveur backend :

```bash
sh dev.sh
```

- Cela démarrera le serveur backend, et vous devriez voir sa sortie dans le terminal.
- Accédez à la documentation de l'API dans votre navigateur : **[http://localhost:8080/docs](http://localhost:8080/docs)**.

---

#### 4. Étapes finales : Tout faire fonctionner ensemble

🎉 Félicitations ! Vous avez maintenant le frontend et le backend en fonctionnement local :

1. Retournez sur l'URL du frontend : **[http://localhost:5173](http://localhost:5173)**.
2. Actualisez la page.
   - Vous devriez voir l’application complète connectée au backend !

C'est tout—vous êtes prêt à utiliser CANChat !

---

## Comment contribuer

### Code de conduite

Ce projet, ainsi que tous les participants, est régi par notre [Code de conduite](CODE_OF_CONDUCT). En participant, vous acceptez de respecter ce code. Veuillez signaler tout comportement inacceptable aux [mainteneurs](mailto:ssc.canchat-support-assistance-canchat.spc@ssc-spc.gc.ca).

### Signaler des bogues

Si vous trouvez un bogue, ouvrez une issue sur notre [traqueur d’issues](https://github.com/dto-btn/canchat-v2/issues) et fournissez autant de détails que possible, notamment votre système d'exploitation, navigateur et les étapes pour reproduire le bogue.

### Suggérer des améliorations

Nous accueillons avec plaisir vos suggestions d'améliorations. Ouvrez une issue sur le [traqueur d’issues](https://github.com/dto-btn/canchat-v2/issues) et décrivez votre proposition en détail.

### Contribuer au code

- Assurez-vous que votre code respecte notre guide de style.
- Testez minutieusement vos modifications.
- Soumettez une pull request vers la branche `dev` du dépôt principal.

### Problèmes de sécurité

Ne postez aucun problème de sécurité sur le dépôt public ! Consultez notre [SECURITY.md](SECURITY).

## Licence

Ce projet est sous licence [BSD-3-Clause License](LICENSE) - consultez le fichier [LICENSE](LICENSE) pour plus de détails.

## Support

Si vous avez des questions, des suggestions ou avez besoin d'assistance, veuillez consulter notre
[documentation](https://gcxgce.sharepoint.com/teams/1000538/SitePages/fr/CANChat.aspx).
