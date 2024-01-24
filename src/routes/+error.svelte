<script>
	import { page } from '$app/stores';
</script>



<div class="flex flex-col min-h-screen bg-white lg:grid lg:grid-cols-[max(50%,36rem),1fr]">
  <header class="mx-auto w-full max-w-7xl px-6 pt-6 sm:pt-10 lg:col-span-2 lg:col-start-1 lg:row-start-1 lg:px-8">
	<a href="/">
	  <span class="sr-only">FI-TS</span>
	  <img
		class="h-10 w-auto sm:h-12 rounded-md"
		src="/fi-ts_boxlogo.png"
		alt=""
	  />
	</a>
  </header>
  <main class="flex-grow mx-auto w-full max-w-7xl px-6 py-24 sm:py-32 lg:col-span-2 lg:col-start-1 lg:row-start-2 lg:px-8">
	<div class="max-w-lg">
	  <p class="text-base font-semibold leading-8 text-red-500">
		{$page.status}: {$page.error.message}
	  </p>
	  <h1 class="mt-4 text-3xl font-bold tracking-tight text-gray-900 sm:text-5xl">
		Page not found
	  </h1>
	  <p class="mt-6 text-base leading-7 text-gray-600">
		Die Seite nach der Sie suchen existiert nicht.
	  </p>
	  <div class="mt-10">
		<a
		  href="/"
		  class="text-sm font-semibold leading-7 text-red-500"
		>
		  <span aria-hidden="true">&larr;</span> Zurück zur Startseite
		</a>
	  </div>
	</div>
  </main>
  <footer class="self-end lg:col-span-2 lg:col-start-1 lg:row-start-3">
	<div class="border-t border-gray-100 bg-gray-50 py-10">
	  <nav class="mx-auto flex w-full max-w-7xl items-center gap-x-4 px-6 text-sm leading-7 text-gray-600 lg:px-8">
		<div class="relative group">
		  <a href="#" class="cursor-not-allowed text-gray-500">Feedback</a>
		  <div class="absolute left-0 bottom-full mb-2 w-auto bg-white border border-gray-300 text-gray-700 text-xs rounded-md px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
			Kommt bald!
		  </div>
		</div>
		<svg
		  viewBox="0 0 2 2"
		  aria-hidden="true"
		  class="h-0.5 w-0.5 fill-gray-300"
		>
		  <circle cx={1} cy={1} r={1} />
		</svg>
		<button
		on:click={async () => {
			localStorage.removeItem('token');
			location.href = '/auth';
		}}>Abmelden</button
	>
	  </nav>
	</div>
  </footer>
  <div class="hidden lg:relative lg:col-start-2 lg:row-start-1 lg:row-end-4 lg:block">
	<img
	  src="/FI-TS-Bruecke.jpeg"
	  alt=""
	  class="absolute inset-0 h-full w-full object-cover"
	/>
  </div>
</div>
