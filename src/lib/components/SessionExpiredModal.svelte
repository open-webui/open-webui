<script lang="ts">
    import { sessionExpired } from '$lib/stores';
    import * as Dialog from '$lib/components/ui/dialog'; // Pfad ggf. anpassen, falls bits-ui anders eingebunden ist
    import { Button } from '$lib/components/ui/button'; // Für den Reload-Button, Pfad ggf. anpassen
    import { page } from '$app/stores'; // Um die aktuelle URL für den Redirect zu bekommen
    import { goto } from '$app/navigation'; // Um zur Login-Seite zu navigieren
 import { WEBUI_BASE_URL } from '$lib/constants'; // Basis-URL für den Redirect

    // Reagiere auf Änderungen im sessionExpired Store
    let isOpen = false;
    sessionExpired.subscribe((value) => {
        isOpen = value;
    });

    // Funktion, um zur Login-Seite weiterzuleiten
  function redirectToLogin() {
    // Setze den Store zurück, falls der Benutzer auf "Erneut anmelden" klickt,
    // obwohl ein Neuladen der Seite dies ohnehin tun würde. Sicher ist sicher.
    sessionExpired.set(false);

    const currentUrl = `${$page.url.pathname}${$page.url.search}`;
      const encodedUrl = encodeURIComponent(currentUrl);

    // Navigiere zur Auth-Seite mit Redirect-Parameter
    // (Verwendet die Konstante WEBUI_BASE_URL, falls nötig, ansonsten reicht der Pfad)
    goto(`${WEBUI_BASE_URL}/auth?redirect=${encodedUrl}`, { replaceState: true });
  }

</script>

{#if isOpen}
    <Dialog.Root
        open={isOpen}
        preventScroll={true}
        closeOnOutsideClick={false}  _<!-- Macht das Modal nicht durch Klick daneben schließbar -->_
        closeOnEscape={false}       _<!-- Macht das Modal nicht durch ESC schließbar -->_
    >
        <Dialog.Portal>
            <Dialog.Overlay class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
            <Dialog.Content
                class="fixed left-1/2 top-1/2 z-50 grid w-full max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 border bg-background p-6 shadow-lg sm:rounded-lg"
                aria-describedby="dialog-description"
            >
                <Dialog.Header class="flex flex-col items-center text-center">
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="2"
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        class="h-10 w-10 text-destructive mb-2" >
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                    <Dialog.Title class="text-lg font-semibold">
                        (Session Expired)
                    </Dialog.Title>
                </Dialog.Header>
                <div id="dialog-description" class="text-sm text-muted-foreground text-center">
          <!-- i18n Placeholder für Beschreibung -->
                    (Your session has expired. Please log in again to continue. You may want to copy any unsaved work before proceeding.)
                </div>
                <Dialog.Footer class="flex justify-center mt-4">
          <!-- Kein Schließen-Button, nur ein "Neu Anmelden"-Button -->
                    <Button on:click={redirectToLogin} variant="destructive">
            <!-- i18n Placeholder für Button -->
            (Log In Again)
          </Button>
                </Dialog.Footer>
            </Dialog.Content>
        </Dialog.Portal>
    </Dialog.Root>
{/if}

<style>
/* Optional: Füge hier spezifische Styles hinzu, falls nötig.
   Die Klassen oben (bg-background, text-destructive etc.) kommen wahrscheinlich von Tailwind/ShadCN.
   Stelle sicher, dass die benötigten CSS-Klassen verfügbar sind.
*/
</style>
