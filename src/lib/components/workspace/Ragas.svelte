<script lang="ts">
    //import { getRagasConfig, getRagasEvalConfig, updateRagasEvalConfig, ragasEval,eraseQA } from '$lib/apis/ragas';
    import { getRagasConfig, getRagasEvalConfig, updateRagasEvalConfig, eraseQA } from '$lib/apis/ragas';
    import {getKnowledgeBases} from '$lib/apis/knowledge'
    import {getFiles} from '$lib/apis/files'
    import { getModels} from '$lib/apis';
    import { onMount, getContext } from 'svelte';
    import {generateChatCompletion} from '$lib/apis/ollama'
    import {generateOpenAIChatCompletion} from '$lib/apis/openai'
    import {launchQuestionEval} from '$lib/stores'
    import { toast } from 'svelte-sonner';
    import {
        promptTemplate,
    } from '$lib/utils';
    const i18n = getContext('i18n');

    let settings = {};
    let liste_knowledge=[]
    let liste_files=[]
    let liste_modeles=[];
    let launchquestion=false;
    let evaluation=[];

    $ : console.log("Ragas Settings ",settings)
    $ : console.log("Liste Connaissances ",liste_knowledge)
    $ : console.log("Liste Files ",liste_files)
    $ : console.log("Liste modeles ",liste_modeles)
    $ : console.log("Activated "+settings.ENABLE_RAGAS)
    $ : console.log("Evaluation "+JSON.stringify(evaluation))
    $ : console.log("Hidden Evaluation "+hiddenEvaluation)
    $ : console.log("Eval settings "+JSON.stringify(eval_settings))
    let eval_settings = {
        question: [],
        ground_truth: [],
        documentId: [],
        modelId:[],
        answer:[]
    };

    let hidden = true;
    let hiddenFiles = true;
    let hiddenDocs = true;
    let hiddenModels = true;
    let hiddenQuestion = true;
    let hiddenEvaluation=true;

    let evalQuestion=""

    // Nouveau élément temporaire pour l'ajout
    let newQuestion = '';
    let newGroundTruth = '';
    let globalDocumentId = '';
    let globalModelId = '';

    const getRagasSettings = async () => {
        settings = await getRagasConfig(localStorage.token);
        if (settings && settings.ragas_eval_file_path) {
            try {
                eval_settings = await getRagasEvalConfig();
                console.log("Ragas evaluation settings loaded successfully", eval_settings);
            } catch (error) {
                console.error("Error while fetching Ragas evaluation settings:", error.message);
            }
        } else {
            console.log("No ragas_eval_file_path in ", JSON.stringify(settings));
        }
    }; 

    const getEvalSourceFiles =async()=>{
        liste_knowledge=await getKnowledgeBases(localStorage.token);
        liste_files=await getFiles(localStorage.token)
        liste_modeles=await getModels(localStorage.token)
    }

    // Modifier une paire existante
    const updatePair = (index: number, field: 'question' | 'ground_truth', value: string) => {
        eval_settings = {
            ...eval_settings,
            [field]: eval_settings[field].map((item, i) => (i === index ? value : item))
        };
    };

    const removePair = (index: number) => {
        eval_settings = {
            ...eval_settings,
            question: eval_settings.question.filter((_, i) => i !== index),
            ground_truth: eval_settings.ground_truth.filter((_, i) => i !== index),
            documentId: eval_settings.documentId.filter((_, i) => i !== index),
            modelId:eval_settings.modelId.filter((_, i) => i !== index)
        };
    };

    const addPair = () => {
        if (newQuestion && newGroundTruth && globalDocumentId && globalModelId) {
            eval_settings = {
                ...eval_settings,
                question: [...eval_settings.question, newQuestion],
                ground_truth: [...eval_settings.ground_truth, newGroundTruth],
                documentId: [...eval_settings.documentId, globalDocumentId],
                modelId: [...eval_settings.modelId, globalModelId]
            };
            newQuestion = '';
            newGroundTruth = '';
        } else {
            console.log("Error: Champs manquants");
        }
    };

    const applyToAll = () => {
        eval_settings = {
            ...eval_settings,
            documentId: eval_settings.question.map(() => globalDocumentId),
            modelId: eval_settings.question.map(() => globalModelId)
        };
    };

    // Enregistrer les modifications
    const saveChanges = async () => {
        console.log("Update with ",eval_settings);
        try {
            await updateRagasEvalConfig(localStorage.token,eval_settings);
            alert('Modifications enregistrées avec succès !');
        } catch (error) {
            console.error(error);
            alert("Erreur lors de l'enregistrement.");
        }
    };

    onMount(() => {
        console.log("Mise à jour des variables")
        getRagasSettings();
        getEvalSourceFiles();
    });
   
    function getFileFromName(documentName) {
        const document = liste_files.find(file => file.filename === documentName);

        if (!document) {
            console.error(`Document with name "${documentName}" not found.`);
            return null;
        }

        return {
            type: "file",
            meta: document.meta,
            id: document.id,
            name: document.filename,
            content: document.content || {},  
            status:"processed"
           
        };
    }
 

   function getFileFromId(id) {
        console.log("Recherche file avec id "+id +" liste_files="+JSON.stringify(liste_files))
        const file = liste_files.find(file => {
            console.log("File id "+file.id)
            return (file.id === id)
        })

    if (!file) {
        console.error(`File with name "${id}" not found.`);
        return null;
    }

    return {
        filename: file.filename,
    }
   }
    
   async function createChatCompletionBody(model, documentName, question) {
    const file = getFileFromName(documentName);

    if (!file) {
        console.error("Unable to create chat completion body due to missing file details.");
        return null;
    }

    const messages = [];
    messages.push({ role: "user", content: question });

    return {
        stream: false,
        model: model,
        messages: [
            { role: "user", content: question }
        ],
        options: {},
        files: [file],
        session_id: "ragas-session-id",
        chat_id: "ragas-chat-id",
        id: "ragas-message-id"
    };
    }


    function is_owned_by(modelname){
        const model = liste_modeles.find(model => model.name === modelname);
        return model?model.owned_by:"unknwon"
    }

 
    async function launchQuestions() {
    try {
        // Activer/désactiver l'état de lancement des questions
        launchQuestionEval.set(!$launchQuestionEval);

        // Boucle sur les questions
        for (let index = 0; index < eval_settings.question.length; index++) {
            // Vérifier à qui appartient le modèle
            let owned_by = is_owned_by(eval_settings.modelId[index]);
            console.log("Owned by " + owned_by);

            // Préparer la question pour l'évaluation
            evalQuestion = "Question=" + eval_settings.question[index];

            // Créer le corps de la requête pour l'API OpenAI
            let body = await createChatCompletionBody(
                eval_settings.modelId[index],
                eval_settings.documentId[index],
                eval_settings.question[index]
            );

            // Appeler l'API OpenAI pour générer une réponse
            const response = await generateOpenAIChatCompletion(localStorage.token, body);

            // Log de la réponse brute
            console.log("Raw response:", response);

            // Extraire les données de la réponse
            const data = response;

            // Vérifier si la réponse contient des choix
            if (data.choices && data.choices.length > 0) {
                // Récupérer la réponse de l'assistant
                const assistantMessage = data.choices[0].message.content;
                eval_settings.answer[index] = assistantMessage;
                console.log("Assistant response:", assistantMessage);
                evalQuestion = "Reponse=" + assistantMessage;
            } else {
                console.error("No choices found in the API response.");
            }
        }

        // Désactiver l'état de lancement des questions
        launchQuestionEval.set(!$launchQuestionEval);

        // Sauvegarder les changements
        let ret = await saveChanges();
    } catch (error) {
        // Gestion des erreurs
        console.error("An error occurred:", error);

        // Afficher un toaster avec le message d'erreur
        toast.error(error)
    }
}

    /**
    async function launchEvaluation(){
        evaluation= await ragasEval(localStorage.token)
        console.log("Evaluation "+JSON.stringify(evaluation))
    }
    */

    hiddenQuestion = !("answer" in eval_settings);

    const requiredFields = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"];

    hiddenEvaluation = !evaluation.every(item =>
        requiredFields.every(field => field in item && item[field] !== undefined && item[field] !== null)
    );

    function getBackgroundColor(value) {
            const green = Math.round(value * 255);
            const red = Math.round((1 - value) * 255);
            return `rgb(${red}, ${green}, 0)`;
        }
</script>

<div>
    {#if settings.ENABLE_RAGAS}
    <div class="text-lg font-semibold self-center">
        Evaluations
    </div>
    <br/>
    <ul>
        <li><strong>ragas_eval_file_path</strong>: {settings.ragas_eval_file_path}</li>
        <li><strong>ragas_eval_logs_path</strong>: {settings.ragas_eval_logs_path}</li>
    </ul>
    <br>
    <div>

    </div>
   
    <button class="text-lg font-semibold self-center hover:bg-blue-500 hover:text-white transition-colors duration-300 ease-in-out" on:click={() => {hidden = !hidden}} aria-controls="content" aria-expanded={!hidden}>
        Questions et Réponses ({eval_settings?(eval_settings.question? eval_settings.question.length:0):0})
    </button>
    
    <div {hidden}>
        <!-- Sélecteurs globaux -->
        <div class="mb-4">
            <div class="grid grid-cols-2 gap-4 mb-2">
                <select 
                    class="border border-gray-300 p-2 w-full"
                    bind:value={globalDocumentId}
                >
                    <option value="">Sélectionner un document</option>
                    {#each liste_knowledge as doc}
                        <option value={doc.name}>{doc.description}</option>
                    {/each}
                </select>

                <select 
                    class="border border-gray-300 p-2 w-full"
                    bind:value={globalModelId}
                >
                    <option value="">Sélectionner un modèle</option>
                    {#each liste_modeles as model}
                        <option value={model.name}>{model.name}</option>
                    {/each}
                </select>
            </div>
            
            <button 
                class="p-2 bg-blue-500 text-white rounded"
                on:click={applyToAll}
                disabled={!globalDocumentId || !globalModelId}
            >
                Appliquer à toutes les questions
            </button>
        </div>

        {#if eval_settings && eval_settings.question}
        <table class="table-auto border-collapse border border-gray-300 w-full text-left">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">Question</th>
                    <th class="border border-gray-300 px-4 py-2">Réponse (Ground Truth)</th>
                    <th class="border border-gray-300 px-4 py-2">Nom du document</th>
                    <th class="border border-gray-300 px-4 py-2">Nom du modele</th>
                    <th class="border border-gray-300 px-4 py-2">Actions</th>
                </tr>
            </thead>
            <tbody>
                {#each eval_settings.question as question, index}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">
                        <input
                            type="text"
                            class="w-full"
                            bind:value={eval_settings.question[index]}
                            on:input={(e) => updatePair(index, 'question', e.target.value)}
                        />
                    </td>
                    <td class="border border-gray-300 px-4 py-2">
                        <input
                            type="text"
                            class="w-full"
                            bind:value={eval_settings.ground_truth[index]}
                            on:input={(e) => updatePair(index, 'ground_truth', e.target.value)}
                        />
                    </td>
                    <td class="border border-gray-300 px-4 py-2">
                        <input
                            type="text"
                            class="w-full"
                            bind:value={eval_settings.documentId[index]}
                            on:input={(e) => updatePair(index, 'documentId', e.target.value)}
                        />
                    </td>
                    <td class="border border-gray-300 px-4 py-2">
                        <input
                            type="text"
                            class="w-full"
                            bind:value={eval_settings.modelId[index]}
                            on:input={(e) => updatePair(index, 'modelId', e.target.value)}
                        />
                    </td>
                    <td class="border border-gray-300 px-4 py-2 text-center">
                        <button class="p-1 px-3 text-xs flex rounded bg-red-500 text-white" type="button" on:click={() => removePair(index)}>
                            Supprimer
                        </button>
                    </td>
                </tr>
                {/each}
            </tbody>
        </table>
        {/if}
        <h3 class="mt-4">Ajouter une nouvelle paire</h3>
        <form on:submit|preventDefault={addPair}>
            <div class="grid grid-cols-2 gap-4">
                <input type="text" placeholder="Nouvelle question" bind:value={newQuestion} class="border border-gray-300 p-2 w-full" />
                <input type="text" placeholder="Nouvelle réponse de terrain" bind:value={newGroundTruth} class="border border-gray-300 p-2 w-full" />
            </div>
            <button class="mt-2 p-2 bg-blue-500 text-white rounded">Ajouter</button>
        </form>

        <br />
        <button class="mt-2 p-2 bg-greengit s-500 text-white rounded" on:click={saveChanges}>
            Enregistrer les modifications
        </button>
    </div>
    
    <br/>
      <!-- Section Liste des Connaissances -->
    {#if liste_files && liste_files.length>0}
     <button class="text-lg font-semibold self-center hover:bg-blue-500 hover:text-white transition-colors duration-300 ease-in-out" on:click={() => {hiddenDocs = !hiddenDocs}} aria-controls="content" aria-expanded={!hiddenDocs}>
        Liste des Connaissances ({liste_knowledge.length})
    </button>
    <div hidden={hiddenDocs}>
        <table class="table-auto border-collapse border border-gray-300 w-full text-left mt-4">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">Nom du Document (name)</th>
                    <th class="border border-gray-300 px-4 py-2">Files</th>
                    <th class="border border-gray-300 px-4 py-2">Description</th>
                </tr>
            </thead>
            <tbody>
                {#each liste_knowledge as doc}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">{doc.name}</td>
                    <td class="border border-gray-300 px-4 py-2">
                        <ul class="list-disc list-inside">
                            {#each doc.files as file}
                            <li>
                                {file.id} (Filename: {getFileFromId(file.id).filename})
                            </li>
                            {/each}
                        </ul>
                    </td>
                    <td class="border border-gray-300 px-4 py-2">{doc.description}</td>
                </tr>
                {/each}
            </tbody>
        </table>
    </div>
    {/if}
    <br/>
    <!-- Section Liste des Files -->
    <button class="text-lg font-semibold self-center hover:bg-blue-500 hover:text-white transition-colors duration-300 ease-in-out" on:click={() => {hiddenFiles = !hiddenFiles}} aria-controls="content" aria-expanded={!hiddenFiles}>
        Liste des Fichiers ({liste_files.length})
    </button>
    <div hidden={hiddenFiles}>
        <table class="table-auto border-collapse border border-gray-300 w-full text-left mt-4">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">Filename</th>
                    <th class="border border-gray-300 px-4 py-2">Meta.name</th>
                    <th class="border border-gray-300 px-4 py-2">ID</th>
                </tr>
            </thead>
            <tbody>
                {#each liste_files as file}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">{file.filename}</td>
                    <td class="border border-gray-300 px-4 py-2">{file.meta.name}</td>
                    <td class="border border-gray-300 px-4 py-2">{file.id}</td>
                </tr>
                {/each}
            </tbody>
        </table>
    </div>
    <br/>
    <!-- Section Liste des Modeles -->
    <button class="text-lg font-semibold self-center hover:bg-blue-500 hover:text-white transition-colors duration-300 ease-in-out" on:click={() => {hiddenModels = !hiddenModels}} aria-controls="content" aria-expanded={!hiddenModels}>
        Liste des Modeles ({liste_modeles.length})
    </button>
    <div hidden={hiddenModels}>
        <table class="table-auto border-collapse border border-gray-300 w-full text-left mt-4">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">Name</th>
                    <th class="border border-gray-300 px-4 py-2">Owned by</th>              
                    <th class="border border-gray-300 px-4 py-2">Size</th>       
                    <th class="border border-gray-300 px-4 py-2">Format</th>   
                    <th class="border border-gray-300 px-4 py-2">Nombre de paramètres</th> 
                    <th class="border border-gray-300 px-4 py-2">Quantification</th> 
                </tr>
            </thead>
            <tbody>
                {#each liste_modeles as model}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">{model.name}</td>
                    <td class="border border-gray-300 px-4 py-2">{model.owned_by}</td>
                    {#if model.owned_by=="ollama"}
                    <td class="border border-gray-300 px-4 py-2">{model.ollama.size}</td>
                    <td class="border border-gray-300 px-4 py-2">{model.ollama.details.format}</td>
                    <td class="border border-gray-300 px-4 py-2">{model.ollama.details.parameter_size}</td>
                    <td class="border border-gray-300 px-4 py-2">{model.ollama.details.quantization_level}</td>
                    {:else}
                    <td class="border border-gray-300 px-4 py-2 undef ">Non défini</td>
                    <td class="border border-gray-300 px-4 py-2 undef">Non défini</td>
                    <td class="border border-gray-300 px-4 py-2 undef">Non défini</td>
                    <td class="border border-gray-300 px-4 py-2 undef">Non défini</td>
                    {/if}
                </tr>
                {/each}
            </tbody>
        </table>
    </div>
    <br/>

     
    {#if eval_settings && eval_settings.question}
    <button class="mt-2 p-2 bg-blue-500 text-white rounded" on:click={() => {
       
        console.log("Launching questions")
            launchquestion = !launchquestion;
            launchQuestions();
        }}
        >
        Envoyer les questions
    </button>
    <strong>{evalQuestion}
    </strong>
    <div hidden={hiddenQuestion}>
        <table class="table-auto border-collapse border border-gray-300 w-full text-left">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">Question</th>
                    <th class="border border-gray-300 px-4 py-2">Réponse </th>
                </tr>
            </thead>
            <tbody>
                {#each eval_settings.question as question, index}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">{eval_settings.question[index]}</td>
                    <td class="border border-gray-300 px-4 py-2">{eval_settings.answer[index]}</td>
                   
                </tr>
                {/each}
            </tbody>
        </table>
    </div>
     {/if}
    <br/>
    {#if eval_settings && eval_settings.qa && eval_settings.qa.length>0}
    <button class="mt-2 p-2 bg-red-500 text-white rounded" on:click={() => {
       
        console.log("Erase qa")
           eraseQA(localStorage.token)
        }}
        >
        Effacer QA
    </button>
<br/>
    {/if}
    <!--
    {#if eval_settings && eval_settings.question}
    <button class="mt-2 p-2 bg-blue-500 text-white rounded"  on:click={() => {      
        console.log("Launching Evaluation")      
            launchEvaluation();
        }}>Lancer l'evaluation RAGAS</button>
    {:else}  
    <div class="text-lg font-semibold self-center">
        {$i18n.t('Ragas not activated')}
    </div>
    {/if}


    <div hidden={hiddenEvaluation}>
        <h3>Evaluation Summary  ({evaluation.length})</h3>
        <table class="border-collapse border border-gray-400 w-full text-left">
            <thead>
                <tr>
                    <th class="border border-gray-300 px-4 py-2">User Input</th>
                    <th class="border border-gray-300 px-4 py-2">Context Precision</th>
                    <th class="border border-gray-300 px-4 py-2">Context Recall</th>
                    <th class="border border-gray-300 px-4 py-2">Faithfulness</th>
                    <th class="border border-gray-300 px-4 py-2">Answer Relevancy</th>
                </tr>
            </thead>
            <tbody>
                {#each evaluation as item}
                <tr>
                    <td class="border border-gray-300 px-4 py-2">{item.user_input}</td>
                    <td
                        class="border border-gray-300 px-4 py-2"
                        style="background-color: {getBackgroundColor(item.context_precision)}">
                        {item.context_precision}
                    </td>
                    <td
                        class="border border-gray-300 px-4 py-2"
                        style="background-color: {getBackgroundColor(item.context_recall)}">
                        {item.context_recall}
                    </td>
                    <td
                        class="border border-gray-300 px-4 py-2"
                        style="background-color: {getBackgroundColor(item.faithfulness)}">
                        {item.faithfulness}
                    </td>
                    <td
                        class="border border-gray-300 px-4 py-2"
                        style="background-color: {getBackgroundColor(item.answer_relevancy)}">
                        {item.answer_relevancy}
                    </td>
                </tr>
                {/each}
            </tbody>
        </table>
    </div>
    -->
    {:else}  
    <div class="text-lg font-semibold self-center">
        {$i18n.t('Ragas not activated')}
    </div>
    {/if} 
</div>

<style>
    table {
        margin-top: 1rem;
    }
    th, td {
        padding: 0.5rem;
 
    }
    th {
        background-color: #22C55E;
    }
    input:hover {
        border: 1px solid black;
    }
    td.undef {
        background-color: #EF4444;
    }
    input {
        padding: 0.5rem;
        border-radius: 5px;
        border: 1px solid #ddd;
    }
</style>
