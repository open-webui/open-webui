<script lang="ts">
	import { getVersionUpdates } from '$lib/apis';
	import { getOllamaVersion } from '$lib/apis/ollama';
	import { WEBUI_BUILD_HASH, WEBUI_VERSION } from '$lib/constants';
	import { WEBUI_NAME, config, showChangelog } from '$lib/stores';
	import { compareVersion } from '$lib/utils';
	import { onMount, getContext } from 'svelte';

	import Tooltip from '$lib/components/common/Tooltip.svelte';

	const i18n = getContext('i18n');

	let ollamaVersion = '';

	let updateAvailable = null;
	let version = {
		current: '',
		latest: ''
	};

	const checkForVersionUpdates = async () => {
		updateAvailable = null;
		version = await getVersionUpdates(localStorage.token).catch((error) => {
			return {
				current: WEBUI_VERSION,
				latest: WEBUI_VERSION
			};
		});

		console.log(version);

		updateAvailable = compareVersion(version.latest, version.current);
		console.log(updateAvailable);
	};

	onMount(async () => {
		ollamaVersion = await getOllamaVersion(localStorage.token).catch((error) => {
			return '';
		});

		checkForVersionUpdates();
	});
</script>

<div class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class=" space-y-3 overflow-y-scroll max-h-[28rem] lg:max-h-full">
		<div>
			<div class=" mb-2.5 text-sm font-medium flex space-x-2 items-center">
				<div>
					{$WEBUI_NAME} ‧ {WEBUI_VERSION}
				</div>
			</div>
		</div>
		<h2>Wat kun je ermee?</h2>
		<ul>
			<li><strong>Snel antwoord</strong> op vragen over studie, administratie of ICT-services.</li>
			<li>
				<strong>Brainstormen</strong>: ideeën genereren voor projecten, presentaties of lessen.
			</li>
			<li>
				<strong>Code-snippets &amp; debugging</strong>: laat Deltion-GPT meekijken naar je code.
			</li>
			<li><strong>Vertalingen &amp; samenvattingen</strong> in meerdere talen.</li>
		</ul>
		<blockquote>
			<p>
				Allemaal in begrijpelijk Nederlands, maar Deltion-GPT schakelt net zo makkelijk over naar
				Engels of een andere taal.
			</p>
		</blockquote>

		<h2>Waarom nog Beta?</h2>
		<ul>
			<li>Antwoorden kunnen soms <em>onnauwkeurig of onvolledig</em> zijn.</li>
			<li>Functionaliteit en vormgeving <em>veranderen regelmatig</em>.</li>
			<li><em>Feedback</em> van gebruikers is cruciaal om Deltion-GPT te verbeteren.</li>
		</ul>
		<p>Heb je een suggestie of loop je tegen een fout aan? Laat het me weten!</p>

		<h2>Privacy & veiligheid</h2>
		<ul>
			<li>
				Chats worden <strong>lokaal gelogd</strong> binnen het Deltion-netwerk; data verlaat onze omgeving
				alleen voor model-processing bij OpenAI.
			</li>
			<li>Deel <strong>geen vertrouwelijke persoonsgegevens</strong> of examenopgaven.</li>
			<li>
				Wij handelen volgens de <strong>AVG-richtlijnen</strong> van het Deltion&nbsp;College.
			</li>
		</ul>

		<h2>Roadmap (globaal)</h2>
		<table>
			<thead>
				<tr><th>Periode</th><th>Feature</th><th>Status</th></tr>
			</thead>
			<tbody>
				<tr><td>Q3 2025</td><td>Integratie met interne kennisbank</td><td>🔄 Onderzoek</td></tr>
				<tr><td>Q4 2025</td><td>Single Sign-On met Microsoft 365</td><td>⏳ In planning</td></tr>
				<tr><td>2026</td><td>Dashboarding van gebruiks­statistieken</td><td>💡 Idee</td></tr>
			</tbody>
		</table>

		<h2>Meebouwen?</h2>
		<p>
			Heb je zin om mee te testen, nieuwe features te bedenken of wil je gewoon even sparren over AI
			op school? Stuur me een mail op
			<a href="mailto:j.demeester@deltion.nl">j.demeester@deltion.nl</a> of maak een ticket in
			<strong>Topdesk</strong> (categorie “AI&nbsp;Services”).
		</p>

		<h2>Versie-info</h2>
		<p>{WEBUI_NAME} · {WEBUI_VERSION}</p>

		<footer>© 2025 Deltion College · Gemaakt met ❤ door Jerdi</footer>
		<div></div>
	</div>
</div>
