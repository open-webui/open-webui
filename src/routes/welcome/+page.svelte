<script lang="ts">
	import { fade } from 'svelte/transition';

	let scrollY = 0;

	const features = [
		{ icon: 'AI', title: 'Multi Model Chat', description: 'Use GPT, Claude, Llama, Ollama, and more in one unified interface.' },
		{ icon: 'KB', title: 'Knowledge Grounding', description: 'Bring your documents and get context-aware, evidence-based answers.' },
		{ icon: 'PR', title: 'Privacy First', description: 'Deploy where you want and keep complete control over your data.' },
		{ icon: 'RT', title: 'Realtime Streams', description: 'Fast token streaming, task handling, and responsive interactions.' }
	];

	const handleMemberImageError = (event: Event) => {
		const img = event.currentTarget as HTMLImageElement;
		img.src = '/user.png';
	};

	const scrollToSection = (sectionId: string) => {
		const element = document.getElementById(sectionId);
		if (element) {
			element.scrollIntoView({ behavior: 'smooth' });
			// Prevent URL hash from being added
			window.history.replaceState({}, '', window.location.pathname);
		}
	};

	const allMembers = [
		
		{ name: 'H.E Hul Seingheng', image: '/assets/images/Hul_Seingheng.png' },
		{ name: 'Dr. Chen Sovann', image: '/user.png' },
		{ name: 'Mr. Rafael Torquato Cruz', image: '/user.png' },
		{ name: 'Mr. Phork Norak', image: '/assets/images/Norak Phork.jpg' },
		{ name: 'Mr. Tan Chesthareah', image: '/user.png' },
		{ name: 'Mr. Rop Borom', image: '/assets/images/RopBorom.jpg' },
		{ name: 'Ms. Nhor Povketya', image: '/user.png' },
		{ name: 'Ms. Jihyo Ryu', image: '/user.png' },
		{ name: 'Ms. Yan Shen', image: '/user.png' },
		{ name: 'Mr. Juntong Hou', image: '/user.png' },
		{ name: 'Ms. Nanyi Li', image: '/user.png' },
		{ name: 'Ms. Lilian Li', image: '/user.png' },
		{ name: 'Mr. Zheng Wang', image: '/user.png' },
		{ name: 'Mr. Toch Ensophea', image: '/user.png' },
		{ name: 'Mr. Savuth Run', image: '/user.png' },
		{ name: 'Mr. Chealyfey Vutha', image: '/user.png' },
		{ name: 'Mr. Pagnarith Srun', image: '/user.png' },
		{ name: 'Ms. Rupa Chanda', image: '/user.png' },
		{ name: 'Mr. Jonathan Tsuen Yip Wong', image: '/user.png' },
		{ name: 'Ms. Elena Mayer-Besting', image: '/user.png' },
		{ name: 'Mr. Seng Touch', image: '/user.png' },
		{ name: 'Ms. Iysang Kain', image: '/user.png' },
		{ name: 'Ms. Sreyneang Yung', image: '/user.png' },
		{ name: 'Ms. Sreylen Chab', image: '/user.png' },
		{ name: 'Mr. Krisna Keo', image: '/user.png' },
		{ name: 'Mr. Seang Sung', image: '/user.png' },
		{ name: 'Ms. Povvoliak Sakhan', image: '/user.png' },
		{ name: 'Ms. Sopanha Leavchum', image: '/user.png' },
		{ name: 'Mr. Yachao Wang', image: '/user.png' },
		{ name: 'Mr. Heng Sun', image: '/user.png' },
		{ name: 'Mr. Chettra Nang', image: '/user.png' },
		{ name: 'Mr. Songqi Sun', image: '/user.png' },
		{ name: 'Ms. Socheata Sokhachan', image: '/user.png' },
		{ name: 'Mr. Ly Hour', image: '/assets/images/LyHour.png' },
		{ name: 'Mr. Rath Chhnoeum', image: '/assets/images/Rath Chhnoeum.jpg' },
		{ name: 'Ms. Ye Lita', image: '/user.png' },
		{ name: 'Mr. Ly Panharith', image: '/user.png' },
		{ name: 'Ms. Chhoun Pisethchesda', image: '/user.png' },
		{ name: 'Ms. Chum Monika', image: '/user.png' },
		{ name: 'Mr. Cheang Yornphavorak', image: '/user.png' },
		{ name: 'Mr. Khut Buntha', image: '/user.png' },
		{ name: 'Mr. Oun MengHeang', image: '/user.png' },
		{ name: 'Mr. Kruy Monychotakna', image: '/user.png' },
		{ name: 'Mr. CHHOUN Oudom', image: '/user.png' }
	];
</script>

<svelte:window bind:scrollY />

<svelte:head>
	<title>COPAI — Community of Practice: AI</title>
	<meta name="description" content="COPAI is a collaborative platform for AI research, innovation, and community development in Cambodia." />
</svelte:head>

<div class="w-full h-screen overflow-y-auto overflow-x-hidden bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100">

	<!-- Navigation -->
	<nav class="fixed top-0 inset-x-0 z-50 border-b border-orange-100 dark:border-gray-800 bg-white/95 dark:bg-gray-950/95 backdrop-blur-xl shadow-sm">
		<div class="w-full h-16 px-4 sm:px-8 lg:px-12">
			<div class="max-w-7xl mx-auto h-full flex items-center justify-between">
				<button on:click={() => scrollToSection('home')} class="flex items-center gap-2 group cursor-pointer bg-none border-none p-0">
					<img src="/static/favicon.png" alt="COPAI Logo" class="w-10 h-10 rounded-lg shadow-md ring-2 ring-orange-100 dark:ring-orange-800/50 transform group-hover:scale-110 transition-transform duration-200" />
					<span class="font-sans font-bold text-lg text-gray-900 dark:text-white group-hover:text-orange-500 transition">COPAI</span>
				</button>
				<div class="hidden md:flex items-center gap-1 rounded-full border border-orange-100 dark:border-gray-700 bg-white/80 dark:bg-gray-900 px-2 py-1 shadow-sm">
					<button on:click={() => scrollToSection('home')} class="px-4 py-1.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-orange-100 dark:hover:bg-gray-800 hover:text-orange-500 transition bg-none border-none cursor-pointer">Home</button>
					<button on:click={() => scrollToSection('about')} class="px-4 py-1.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-orange-100 dark:hover:bg-gray-800 hover:text-orange-500 transition bg-none border-none cursor-pointer">About</button>
					<button on:click={() => scrollToSection('community')} class="px-4 py-1.5 rounded-full text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-orange-100 dark:hover:bg-gray-800 hover:text-orange-500 transition bg-none border-none cursor-pointer">Community</button>
				</div>
				<div class="flex items-center gap-2 sm:gap-4">
					<a href="/auth" class="text-sm px-3 py-2 text-gray-600 dark:text-gray-400 hover:text-orange-500 dark:hover:text-orange-400 transition font-medium">Sign in</a>
					<a href="/register" class="text-sm px-4 py-2 rounded-lg bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white font-semibold transition shadow-md hover:shadow-lg transform hover:scale-105">Get started</a>
				</div>
			</div>
		</div>
	</nav>

	<!-- Hero Section -->
	<section id="home" class="relative w-full bg-white dark:bg-gray-900">
		<div class="absolute -top-32 left-10 w-96 h-96 rounded-full bg-orange-200/50 blur-3xl animate-drift"></div>
		<div class="absolute top-20 right-5 w-80 h-80 rounded-full bg-orange-100/40 blur-3xl animate-drift-slow"></div>
		<div class="w-full px-4 sm:px-8 lg:px-12 pt-24 sm:pt-32 pb-16 sm:pb-24 overflow-hidden">
			<div class="max-w-7xl mx-auto">
				<div class="grid lg:grid-cols-[1.1fr_0.9fr] gap-8 md:gap-12 items-center relative z-10">
					<div class="space-y-8" in:fade={{ delay: 100, duration: 500 }}>
						<div class="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-orange-200 bg-orange-50 dark:bg-orange-950/30">
							<div class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
							<span class="text-xs tracking-widest font-bold uppercase text-orange-600 dark:text-orange-400">Community of Practice on AI</span>
						</div>
						<h1 class="font-sans text-5xl sm:text-6xl lg:text-7xl font-bold leading-[1.1] tracking-tight text-gray-900 dark:text-white" style="transform: translateY({Math.max(-scrollY * 0.08, -36)}px);">
							Build AI Impact,
							<span class="block bg-gradient-to-r from-orange-500 to-orange-400 bg-clip-text text-transparent">Together as a Community</span>
						</h1>
						<p class="text-lg sm:text-xl text-gray-700 dark:text-gray-300 max-w-2xl leading-relaxed font-medium">
							COPAI connects researchers, policymakers, innovators, and students to accelerate AI capacity, policy readiness, and inclusive innovation in Cambodia.
						</p>
						<div class="flex flex-col sm:flex-row gap-4 pt-4">
							<a href="/register" class="px-8 py-3.5 rounded-lg bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white font-bold transition shadow-lg hover:shadow-xl transform hover:scale-105">Start collaborating</a>
							<button on:click={() => scrollToSection('about')} class="px-8 py-3.5 rounded-lg border-2 border-orange-300 bg-white dark:bg-gray-900 text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-gray-800 font-bold transition bg-none cursor-pointer">Explore COPAI</button>
						</div>
						<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-6">
							{#each features as item}
								<div class="group rounded-xl border border-orange-100 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-4 shadow-sm hover:shadow-md hover:border-orange-300 transition-all duration-200">
									<div class="text-[11px] font-bold tracking-widest text-orange-500 dark:text-orange-400 mb-2 uppercase">{item.icon}</div>
									<div class="text-sm font-bold text-gray-900 dark:text-white mb-2">{item.title}</div>
									<div class="text-xs text-gray-600 dark:text-gray-400 leading-relaxed font-medium">{item.description}</div>
								</div>
							{/each}
						</div>
					</div>

					<!-- Live Panel Card -->
					<div class="rounded-2xl border border-orange-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-2xl overflow-hidden" in:fade={{ delay: 220, duration: 550 }}>
						<div class="px-6 py-5 border-b border-orange-100 dark:border-gray-700 bg-gradient-to-r from-orange-400 to-orange-500 text-white">
							<div class="text-sm font-bold tracking-wide">✨ COPAI Live Panel</div>
						</div>
						<div class="p-6 space-y-5">
							<div class="rounded-xl bg-orange-50 dark:bg-orange-950/20 border border-orange-100 dark:border-orange-900/30 px-4 py-3">
								<div class="text-xs uppercase font-bold tracking-widest text-orange-600 dark:text-orange-400">Current Focus</div>
								<div class="text-sm font-bold mt-2 text-gray-900 dark:text-white">AI Research Capacity & Inclusive Innovation</div>
							</div>
							<div class="rounded-xl bg-orange-50 dark:bg-orange-950/20 border border-orange-100 dark:border-orange-900/30 px-4 py-3">
								<div class="text-xs uppercase font-bold tracking-widest text-orange-600 dark:text-orange-400">Stakeholders</div>
								<div class="text-sm mt-2 leading-relaxed text-gray-700 dark:text-gray-300 font-medium">Government, academia, private sector, and civil society working together.</div>
							</div>
							<div class="grid grid-cols-3 gap-3">
								<div class="rounded-xl bg-orange-100 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 px-3 py-3 text-center">
									<div class="text-xl font-bold text-orange-600 dark:text-orange-400">2030</div>
									<div class="text-[11px] text-orange-600 dark:text-orange-500 font-bold">STI Roadmap</div>
								</div>
								<div class="rounded-xl bg-orange-100 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 px-3 py-3 text-center">
									<div class="text-xl font-bold text-orange-600 dark:text-orange-400">4+</div>
									<div class="text-[11px] text-orange-600 dark:text-orange-500 font-bold">Core Outputs</div>
								</div>
								<div class="rounded-xl bg-orange-100 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 px-3 py-3 text-center">
									<div class="text-xl font-bold text-orange-600 dark:text-orange-400">ASEAN</div>
									<div class="text-[11px] text-orange-600 dark:text-orange-500 font-bold">Regional Link</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</section>

	<!-- About Section -->
	<section id="about" class="w-full px-4 sm:px-8 lg:px-12 py-16 sm:py-24 bg-white dark:bg-gray-900">
		<div class="max-w-7xl mx-auto">
			<div class="mb-16">
				<div class="inline-block px-4 py-2 rounded-full bg-orange-100 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-700 mb-6">
					<span class="text-sm font-bold text-orange-600 dark:text-orange-400 uppercase tracking-widest">About COPAI</span>
				</div>
				<h2 class="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-6 leading-tight">Community of Practice on <span class="text-orange-500">Artificial Intelligence</span></h2>
				<p class="text-lg text-gray-600 dark:text-gray-300 max-w-3xl leading-relaxed">
					Established by ESCAP in collaboration with the Ministry of Industry, Science, Technology & Innovation (MISTI), COPAI functions as a multi-stakeholder platform dedicated to enhancing Cambodia's capabilities in AI research and innovation.
				</p>
			</div>

			<div class="grid lg:grid-cols-3 gap-8 mb-16">
				<div class="lg:col-span-2">
					<div class="bg-gradient-to-br from-orange-50 to-white dark:from-orange-950/20 dark:to-gray-900 p-8 rounded-2xl border border-orange-100 dark:border-orange-900/30">
						<h3 class="text-2xl font-bold text-gray-900 dark:text-white mb-4">About</h3>
						<p class="text-gray-700 dark:text-gray-300 leading-relaxed mb-6">
							Cambodia is well-positioned to benefit significantly from AI-driven economic and social growth. However, realizing this potential requires targeted efforts to strengthen AI research capabilities, enhance digital infrastructure, and cultivate innovation ecosystems.
						</p>
						<p class="text-gray-700 dark:text-gray-300 leading-relaxed">
							COPAI supports this goal by aligning its activities with existing national frameworks, including the National STI Roadmap 2030, National Research Agenda, and Digital Economy and Society Policy Framework.
						</p>
					</div>
				</div>
				<div class="space-y-4">
					<div class="bg-orange-500 text-white p-6 rounded-xl shadow-lg">
						<div class="text-4xl font-bold mb-2">44</div>
						<p class="text-orange-100">Members</p>
					</div>
					
				</div>
			</div>

			<div class="mb-16">
				<h3 class="text-3xl font-bold text-gray-900 dark:text-white mb-8">Our Objectives</h3>
				<div class="grid md:grid-cols-2 gap-6">
					<div class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition">
						<div class="flex gap-4">
							<div class="flex-shrink-0"><div class="flex items-center justify-center h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-950/50 text-orange-600 dark:text-orange-400 text-xl">🔬</div></div>
							<div>
								<h4 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Research & Innovation</h4>
								<p class="text-gray-600 dark:text-gray-400 text-sm">Foster AI research and innovation through collaborative projects and knowledge exchange.</p>
							</div>
						</div>
					</div>
					<div class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition">
						<div class="flex gap-4">
							<div class="flex-shrink-0"><div class="flex items-center justify-center h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-950/50 text-orange-600 dark:text-orange-400 text-xl">🎓</div></div>
							<div>
								<h4 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Capacity Building</h4>
								<p class="text-gray-600 dark:text-gray-400 text-sm">Build capacity among researchers, policymakers, and youth in AI implementation and innovation management.</p>
							</div>
						</div>
					</div>
					<div class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition">
						<div class="flex gap-4">
							<div class="flex-shrink-0"><div class="flex items-center justify-center h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-950/50 text-orange-600 dark:text-orange-400 text-xl">🤝</div></div>
							<div>
								<h4 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Cross-Sector Partnerships</h4>
								<p class="text-gray-600 dark:text-gray-400 text-sm">Facilitate continuous dialogue among government institutions, academia, private sector, and civil society.</p>
							</div>
						</div>
					</div>
					<div class="bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-lg transition">
						<div class="flex gap-4">
							<div class="flex-shrink-0"><div class="flex items-center justify-center h-12 w-12 rounded-lg bg-orange-100 dark:bg-orange-950/50 text-orange-600 dark:text-orange-400 text-xl">🌐</div></div>
							<div>
								<h4 class="text-lg font-bold text-gray-900 dark:text-white mb-2">Regional Synergy</h4>
								<p class="text-gray-600 dark:text-gray-400 text-sm">Promote regional and international synergy, particularly with ASEAN and global AI networks.</p>
							</div>
						</div>
					</div>
				</div>
			</div>

			<div class="bg-gray-50 dark:bg-gray-800/50 p-8 sm:p-10 rounded-2xl border border-gray-200 dark:border-gray-700">
				<h3 class="text-3xl font-bold text-gray-900 dark:text-white mb-4">Methodology & Expected Outputs</h3>
				<p class="text-gray-700 dark:text-gray-300 leading-relaxed mb-8">
					COPAI employs a collaborative and inclusive approach, actively engaging diverse stakeholders such as policymakers, academics, entrepreneurs and students in co-creating impactful outcomes.
				</p>
				<div class="grid md:grid-cols-2 gap-6">
					{#each [['Landscape Study','Comprehensive analysis of Cambodia\'s AI Research and Innovation ecosystem.'],['Priority Initiatives','Identification and facilitation of priority AI research initiatives aligned with national goals.'],['Community Building','Establishment of a vibrant community of AI researchers, practitioners, and experts.'],['Knowledge Base','Dynamic resource featuring AI research resources, case studies, webinars, and best practices.']] as [title, desc], i}
						<div class="flex gap-4">
							<div class="flex-shrink-0">
								<div class="flex items-center justify-center h-10 w-10 rounded-full bg-orange-500 text-white font-bold text-lg">{i + 1}</div>
							</div>
							<div>
								<h4 class="font-bold text-gray-900 dark:text-white mb-1">{title}</h4>
								<p class="text-gray-600 dark:text-gray-400 text-sm">{desc}</p>
							</div>
						</div>
					{/each}
				</div>
			</div>
		</div>
	</section>

	<!-- ══════════════════════════════════
	     COMMUNITY SECTION
	═══════════════════════════════════ -->
	<section id="community" class="w-full px-4 sm:px-8 lg:px-12 py-16 sm:py-24 bg-gray-50 dark:bg-gray-950">
		<div class="max-w-7xl mx-auto">

			<!-- Header -->
			<div class="flex flex-col sm:flex-row sm:items-end justify-between gap-6 mb-12">
				<div>
					<div class="inline-flex items-center gap-2 mb-4">
						<span class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
						<span class="text-xs font-bold tracking-[0.18em] uppercase text-orange-500 dark:text-orange-400">COPAI Network</span>
					</div>
					<h2 class="text-4xl sm:text-5xl font-black tracking-tight text-gray-900 dark:text-white leading-tight">
						Our <span class="text-orange-500">Community</span>
					</h2>
					<p class="mt-3 text-base text-gray-500 dark:text-gray-400 max-w-md">
						Researchers, innovators, and practitioners united for AI in Cambodia.
					</p>
				</div>
				<!-- <div class="flex items-center gap-3 shrink-0">
					<span class="px-4 py-2 rounded-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 text-sm font-semibold text-gray-600 dark:text-gray-300 shadow-sm">
						{allMembers.length} members
					</span>
					<a href="/register" class="px-5 py-2 rounded-full bg-orange-500 hover:bg-orange-600 text-white text-sm font-bold transition-all duration-200 shadow-md hover:shadow-lg hover:-translate-y-0.5">
						Join us →
					</a>
				</div> -->
			</div>

			<!-- Members Grid — 6 columns, image + name only -->
			<div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3 sm:gap-4">
				{#each allMembers as member, i}
					<div
						class="member-card group relative bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:border-orange-200 dark:hover:border-orange-700"
						style="animation-delay: {i * 35}ms"
					>
						<!-- Photo area — square -->
						<div class="aspect-square w-full overflow-hidden bg-orange-50 dark:bg-gray-800">
							{#if member.image && (member.image.startsWith('/') || member.image.startsWith('http'))}
								<img
									src={member.image}
									alt={member.name}
									class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
									on:error={handleMemberImageError}
								/>
							{:else}
								<div class="w-full h-full flex items-center justify-center bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-950/30 dark:to-orange-900/20">
									<span class="text-5xl select-none">{member.image}</span>
								</div>
							{/if}
						</div>

						<!-- Name only — always visible -->
						<div class="px-3 py-3 text-center">
							<p class="text-[14px] font-bold text-gray-900 dark:text-white leading-snug truncate">
								{member.name}
							</p>
						</div>
					</div>
				{/each}
			</div>

			

		</div>
	</section>

	<!-- Footer -->
	<footer class="w-full px-4 sm:px-8 lg:px-12 py-8 border-t border-orange-100 dark:border-orange-800 text-sm text-gray-600 dark:text-gray-400">
		<div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
			<div class="font-semibold">© {new Date().getFullYear()} COPAI</div>
			<div class="flex items-center gap-6">
				<a href="/auth" class="hover:text-orange-600 dark:hover:text-orange-400 transition font-medium">Sign in</a>
				<a href="/auth" class="hover:text-orange-600 dark:hover:text-orange-400 transition font-medium">Register</a>
			</div>
		</div>
	</footer>

</div>

<style>
	:global(html) {
		scroll-behavior: smooth;
		scroll-padding-top: 80px;
	}
	:global(body) {
		min-height: 100vh;
	}
	:global(section) {
		scroll-margin-top: 80px;
	}
	@keyframes drift {
		0%, 100% { transform: translateY(0px); }
		50% { transform: translateY(14px); }
	}
	@keyframes drift-slow {
		0%, 100% { transform: translateY(0px); }
		50% { transform: translateY(-10px); }
	}
	@keyframes fadeIn {
		from { opacity: 0; transform: translateY(-10px); }
		to { opacity: 1; transform: translateY(0); }
	}
	:global(.animate-drift) { animation: drift 8s ease-in-out infinite; }
	:global(.animate-drift-slow) { animation: drift-slow 11s ease-in-out infinite; }
	:global(.animate-fadeIn) { animation: fadeIn 0.3s ease-out; }

	.member-card {
		animation: memberFadeIn 0.45s ease both;
	}
	@keyframes memberFadeIn {
		from { opacity: 0; transform: translateY(16px); }
		to { opacity: 1; transform: translateY(0); }
	}
</style>