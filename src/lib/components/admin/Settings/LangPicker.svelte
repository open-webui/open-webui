<script lang="ts">
  export let selected: string[] = []; // array of selected codes

  let query = '';
  let open = false;
  let highlighted = 0;
  let inputEl: HTMLInputElement | null = null;

  const codes: string[] = [
    "aa","ab","ae","af","ak","am","an","ar","as","av","ay","az",
    "ba","be","bg","bh","bi","bm","bn","bo","br","bs",
    "ca","ce","ch","co","cr","cs","cu","cv","cy",
    "da","de","dv","dz",
    "ee","el","en","eo","es","et","eu",
    "fa","ff","fi","fj","fo","fr","fy",
    "ga","gd","gl","gn","gu","gv",
    "ha","he","hi","ho","hr","ht","hu","hy","hz",
    "ia","id","ie","ig","ii","ik","io","is","it","iu",
    "ja","jv",
    "ka","kg","ki","kj","kk","kl","km","kn","ko","kr","ks","ku","kv","kw","ky",
    "la","lb","lg","li","ln","lo","lt","lu","lv",
    "mg","mh","mi","mk","ml","mn","mr","ms","mt","my",
    "na","nb","nd","ne","ng","nl","nn","no","nr","nv","ny",
    "oc","oj","om","or","os",
    "pa","pi","pl","ps","pt",
    "qu",
    "rm","rn","ro","ru","rw",
    "sa","sc","sd","se","sg","si","sk","sl","sm","sn","so","sq","sr","ss","st","su","sv","sw",
    "ta","te","tg","th","ti","tk","tl","tn","to","tr","ts","tt","tw","ty",
    "ug","uk","ur","uz",
    "ve","vi","vo",
    "wa","wo",
    "xh",
    "yi","yo",
    "za","zh","zu"
  ];

  const allOptions = codes.map(code => ({ code, label: code }));

  $: suggestions = query
    ? allOptions
        .filter(o => !selected.includes(o.code))
        .filter(o => o.code.includes(query.toLowerCase()))
        .slice(0, 10)
    : allOptions.filter(o => !selected.includes(o.code)).slice(0, 10);

  function add(code: string) {
    const trimmedCode = code.trim();
    if (trimmedCode && !selected.includes(trimmedCode)) {
      selected = [...selected, trimmedCode];
    }
    query = '';
    highlighted = 0;
    inputEl?.focus();
  }

  function remove(code: string) {
    selected = selected.filter(c => c !== code);
    inputEl?.focus();
  }

  function onKeydown(e: KeyboardEvent) {
    if (!open && (e.key === 'ArrowDown' || e.key === 'Enter')) open = true;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      highlighted = Math.min(highlighted + 1, suggestions.length - 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      highlighted = Math.max(highlighted - 1, 0);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (suggestions.length > 0) add(suggestions[highlighted].code);
    } else if (e.key === 'Escape') {
      open = false;
    }
  }

  function clickOutside(node: HTMLElement) {
    const onDocClick = (e: MouseEvent) => {
      if (!node.contains(e.target as Node)) open = false;
    };
    document.addEventListener('mousedown', onDocClick);
    return { destroy() { document.removeEventListener('mousedown', onDocClick); } };
  }
</script>

<div use:clickOutside class="w-full relative">
  <div class="flex flex-wrap gap-1 border rounded px-2 py-1 min-h-[2.5rem] items-center">
    {#each selected as code (code)}
      <span class="px-2 py-0.5 bg-gray-200 dark:bg-gray-700 rounded flex items-center gap-1 text-xs">
        {code}
        <button
          type="button"
          aria-label={`Remove ${code}`}
          class="text-xs font-bold"
          on:click={() => remove(code)}
        >
          ×
        </button>
      </span>
    {/each}

    <input
      bind:this={inputEl}
      class="flex-1 outline-none bg-transparent min-w-[5ch]"
      placeholder="Type code..."
      bind:value={query}
      on:input={() => { open = true; highlighted = 0; }}
      on:keydown={onKeydown}
      aria-haspopup="listbox"
      aria-expanded={open}
    />
  </div>

  {#if open && suggestions.length > 0}
    <ul
      class="absolute z-10 mt-1 w-full max-h-40 overflow-auto border rounded bg-white dark:bg-gray-900 shadow-md"
      role="listbox"
    >
      {#each suggestions as s, i (s.code)}
        <li
          role="option"
          aria-selected={i === highlighted}
          class="px-3 py-1 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 {i === highlighted ? 'bg-gray-200 dark:bg-gray-700' : ''}"
          tabindex="0"
          on:click={() => add(s.code)}
          on:keydown={(e) => { if(e.key==='Enter') add(s.code) }}
        >
          {s.code}
        </li>
      {/each}
    </ul>
  {/if}
</div>
