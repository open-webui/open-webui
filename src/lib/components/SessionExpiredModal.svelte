<script lang="ts">
    import { sessionExpired } from '$lib/stores';
    import Modal from '$lib/components/common/Modal.svelte'; // Verwende die allgemeine Modal-Komponente
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { WEBUI_BASE_URL } from '$lib/constants';
  import { getContext, onMount } from 'svelte'; // Importiere getContext für i18n

  // Hole i18n-Kontext (nötig, auch wenn wir Platzhalter verwenden, damit es konsistent ist)
  const i18n = getContext('i18n');

    // Reagiere auf Änderungen im sessionExpired Store
    let isOpen = false;
    sessionExpired.subscribe((value) => {
        isOpen = value;
    });

    // Funktion, um zur Login-Seite weiterzuleiten
    function redirectToLogin() {
        // Setze den Store zurück, falls der Benutzer auf "Erneut anmelden" klickt,
        sessionExpired.set(false);

        const currentUrl = `${$page.url.pathname}${$page.url.search}`;
        const encodedUrl = encodeURIComponent(currentUrl);

        goto(`${WEBUI_BASE_URL}/auth?redirect=${encodedUrl}`, { replaceState: true });
    }

</script>

<Modal bind:show={isOpen} size="sm" nonClosable={true}>_<!-- `nonClosable` hinzugefügt-->_
    <div>
        <div class=" flex justify-between dark:text-gray-100 px-5 pt-4 pb-2">
            <div class=" text-lg font-medium self-center font-primary">
        {/* i18n Placeholder für Titel */}
        {$i18n.t('(Session Expired)')}
            </div>

      __{/* Kein Standard-Schließen-X-Button hier, da nonClosable=true */}__
      __{/* Falls `nonClosable` nicht funktioniert, müssen wir den Button hier entfernen */}__

        </div>

        <div class=" px-4 pb-4 dark:text-gray-200 text-center">
      __{/* Warn-Icon */}__
      <div class="flex justify-center mb-3">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-10 w-10 text-destructive" __{/* mb-2 entfernt, da im div */}>__
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
          <line x1="12" y1="9" x2="12" y2="13"></line>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      </div>

      __{/* Beschreibungs-Text */}__
      <div id="dialog-description" class="text-sm text-muted-foreground">
         {/* i18n Placeholder für Beschreibung */}
        {$i18n.t('(Your session has expired. Please log in again to continue. You may want to copy any unsaved work before proceeding.)')}
            </div>
        </div>

    __{/* Footer mit Button */}__
    <div class="flex justify-center px-4 pb-4 pt-2">
      __{/* Verwende <button> mit Tailwind-Klassen, angepasst für einen "destructive" Look */}__
      <button
        class="px-3.5 py-1.5 text-sm font-semibold text-white bg-red-600 hover:bg-red-700 dark:bg-red-700 dark:hover:bg-red-800 transition rounded-full flex flex-row items-center"
        on:click={redirectToLogin}
      >
        {/* i18n Placeholder für Button */}
        {$i18n.t('(Log In Again)')}
      </button>
    </div>
    </div>
</Modal>
