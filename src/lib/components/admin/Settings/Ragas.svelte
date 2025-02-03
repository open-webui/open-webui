<script lang=ts>
    import { onMount, getContext, createEventDispatcher } from 'svelte';
    const dispatch = createEventDispatcher();
    import Switch from '$lib/components/common/Switch.svelte';
    import { toast } from 'svelte-sonner';
    import Tooltip from '$lib/components/common/Tooltip.svelte';
    const i18n = getContext('i18n');
   
 
    import {
         updateRagasSettings,
         getRagasConfig,
         getRagasEvalConfig
     } from '$lib/apis/ragas';
 
 
     let ragasSettings = {
          ENABLE_RAGAS:true,
          ragas_eval_logs_path:"",
          ragas_eval_file_path:""
     };
 
     let eval_settings;
     $:  console.log("Update Ragas Settings:", ragasSettings);
 
 
     const getRagasSettings = async () => {
     console.log("Getting Ragas Settings")
     try {
         // Récupération des settings
         ragasSettings = await getRagasConfig(localStorage.token);
         console.log("Retrieved settings="+JSON.stringify(ragasSettings))
         if (ragasSettings && ragasSettings.ragas_eval_file_path) {
             try {
                 // Récupération des settings d'évaluation
                 eval_settings = await getRagasEvalConfig();
             } catch (e) {
                 console.error("Error fetching Ragas Evaluation Config:", e);
                 // Fallback pour éviter un état non défini
                 eval_settings = null;
 
                 // Toast d'erreur pour l'utilisateur
                 toast.error("Failed to load Ragas Evaluation Config. Please try again later.");
             }
         } else {
             console.log("No ragas_eval_file_path in", JSON.stringify(ragasSettings));
         }
     } catch (e) {
         console.error("Error fetching Ragas Config:", e);
 
         // Toast d'erreur pour l'utilisateur
         toast.error("Failed to load Ragas Config. Please check your connection or token.");
     }
 };
 
     onMount(() => {
         getRagasSettings()
     });
   const submitHandler = async () => {
         // Validation : vérifier si les champs sont remplis
         if (!ragasSettings || !ragasSettings.ragas_eval_logs_path || !ragasSettings.ragas_eval_file_path){
             toast.error($i18n.t('Please fill in all required fields before saving.'));
             return;
         }
 
         // Envoi des paramètres
         try {
             await updateRagasSettings(localStorage.token, ragasSettings);
             toast.success($i18n.t('Settings saved successfully.'));
             dispatch('save');
         } catch (error) {
             toast.error(error);
         }
     };
 </script>
 
 <form
     class="flex flex-col h-full justify-between space-y-3 text-sm"
     on:submit|preventDefault={() => {
         submitHandler();
     }}
 >
 <div class="pr-1.5 space-y-2">
     <div class="flex justify-between items-center text-sm">
         <div class="  font-medium">{$i18n.t('Ragas')}</div>
 
         <div class="mt-1">
             <Switch
                 bind:state={ragasSettings.ENABLE_RAGAS}
                 on:change={async () => {
                     updateRagasSettings(localStorage.token, ragasSettings);
                 }}
             />
         </div>
     </div>
     {#if ragasSettings && ragasSettings.ENABLE_RAGAS !== null && ragasSettings.ragas_eval_logs_path !== null}
     {#if ragasSettings && ragasSettings.ENABLE_RAGAS == true}
     <div class=" space-y-2.5 overflow-y-scroll scrollbar-hidden h-full pr-1.5 ml-2.5">
         <div class="flex flex-col gap-0.5">
             <div class=" mb-0.5 text-sm font-medium">{$i18n.t('General Settings')}</div>
             <div class=" ">
                 <div class="text-sm font-medium">{$i18n.t('Ragas Logs Path')}</div>
                 <div class="mt-2">
                     <input
                         class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
                         placeholder={$i18n.t('Enter Ragas Logs Path')}
                         bind:value={ragasSettings.ragas_eval_logs_path}
                     />
                 </div>
                 <div class=" ">
                     <div class="text-sm font-medium">{$i18n.t('Ragas Eval File Path')}</div>
                     <div class="mt-2">
                         <input
                             class="w-full rounded-lg py-2 px-4 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none"
                             placeholder={$i18n.t('Enter Ragas Logs Path')}
                             bind:value={ragasSettings.ragas_eval_file_path}
                         />
                     </div>
                     
                 </div>
                 <div class="flex justify-end pt-3 text-sm font-medium">
                     <button
                         class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
                         type="submit"
                     >
                         {$i18n.t('Save')}
                     </button>
                 </div>
             </div>
             
         </div>
     </div>
     {/if}
     {/if}
     </div>
 </form>