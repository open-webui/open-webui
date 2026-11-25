import dayjs from 'dayjs';

// Locales load on demand; English is built into dayjs.
/** @type {Record<string, () => Promise<unknown>>} */
const locales = {
	af: () => import('dayjs/locale/af'),
	am: () => import('dayjs/locale/am'),
	ar: () => import('dayjs/locale/ar'),
	az: () => import('dayjs/locale/az'),
	be: () => import('dayjs/locale/be'),
	bg: () => import('dayjs/locale/bg'),
	bi: () => import('dayjs/locale/bi'),
	bm: () => import('dayjs/locale/bm'),
	bn: () => import('dayjs/locale/bn'),
	bo: () => import('dayjs/locale/bo'),
	br: () => import('dayjs/locale/br'),
	bs: () => import('dayjs/locale/bs'),
	ca: () => import('dayjs/locale/ca'),
	cs: () => import('dayjs/locale/cs'),
	cv: () => import('dayjs/locale/cv'),
	cy: () => import('dayjs/locale/cy'),
	da: () => import('dayjs/locale/da'),
	de: () => import('dayjs/locale/de'),
	dv: () => import('dayjs/locale/dv'),
	el: () => import('dayjs/locale/el'),
	eo: () => import('dayjs/locale/eo'),
	es: () => import('dayjs/locale/es'),
	eu: () => import('dayjs/locale/eu'),
	fa: () => import('dayjs/locale/fa'),
	fi: () => import('dayjs/locale/fi'),
	fo: () => import('dayjs/locale/fo'),
	fr: () => import('dayjs/locale/fr'),
	fy: () => import('dayjs/locale/fy'),
	ga: () => import('dayjs/locale/ga'),
	gd: () => import('dayjs/locale/gd'),
	gl: () => import('dayjs/locale/gl'),
	gu: () => import('dayjs/locale/gu'),
	he: () => import('dayjs/locale/he'),
	hi: () => import('dayjs/locale/hi'),
	hr: () => import('dayjs/locale/hr'),
	ht: () => import('dayjs/locale/ht'),
	hu: () => import('dayjs/locale/hu'),
	id: () => import('dayjs/locale/id'),
	is: () => import('dayjs/locale/is'),
	it: () => import('dayjs/locale/it'),
	ja: () => import('dayjs/locale/ja'),
	jv: () => import('dayjs/locale/jv'),
	ka: () => import('dayjs/locale/ka'),
	kk: () => import('dayjs/locale/kk'),
	km: () => import('dayjs/locale/km'),
	kn: () => import('dayjs/locale/kn'),
	ko: () => import('dayjs/locale/ko'),
	ku: () => import('dayjs/locale/ku'),
	ky: () => import('dayjs/locale/ky'),
	lb: () => import('dayjs/locale/lb'),
	lo: () => import('dayjs/locale/lo'),
	lt: () => import('dayjs/locale/lt'),
	lv: () => import('dayjs/locale/lv'),
	me: () => import('dayjs/locale/me'),
	mi: () => import('dayjs/locale/mi'),
	mk: () => import('dayjs/locale/mk'),
	ml: () => import('dayjs/locale/ml'),
	mn: () => import('dayjs/locale/mn'),
	mr: () => import('dayjs/locale/mr'),
	ms: () => import('dayjs/locale/ms'),
	mt: () => import('dayjs/locale/mt'),
	my: () => import('dayjs/locale/my'),
	nb: () => import('dayjs/locale/nb'),
	ne: () => import('dayjs/locale/ne'),
	nl: () => import('dayjs/locale/nl'),
	nn: () => import('dayjs/locale/nn'),
	pl: () => import('dayjs/locale/pl'),
	pt: () => import('dayjs/locale/pt'),
	ro: () => import('dayjs/locale/ro'),
	ru: () => import('dayjs/locale/ru'),
	rw: () => import('dayjs/locale/rw'),
	sd: () => import('dayjs/locale/sd'),
	se: () => import('dayjs/locale/se'),
	si: () => import('dayjs/locale/si'),
	sk: () => import('dayjs/locale/sk'),
	sl: () => import('dayjs/locale/sl'),
	sq: () => import('dayjs/locale/sq'),
	sr: () => import('dayjs/locale/sr'),
	ss: () => import('dayjs/locale/ss'),
	sv: () => import('dayjs/locale/sv'),
	sw: () => import('dayjs/locale/sw'),
	ta: () => import('dayjs/locale/ta'),
	te: () => import('dayjs/locale/te'),
	tet: () => import('dayjs/locale/tet'),
	tg: () => import('dayjs/locale/tg'),
	th: () => import('dayjs/locale/th'),
	tk: () => import('dayjs/locale/tk'),
	tlh: () => import('dayjs/locale/tlh'),
	tr: () => import('dayjs/locale/tr'),
	tzl: () => import('dayjs/locale/tzl'),
	tzm: () => import('dayjs/locale/tzm'),
	uk: () => import('dayjs/locale/uk'),
	ur: () => import('dayjs/locale/ur'),
	uz: () => import('dayjs/locale/uz'),
	vi: () => import('dayjs/locale/vi'),
	yo: () => import('dayjs/locale/yo'),
	zh: () => import('dayjs/locale/zh'),
	'zh-tw': () => import('dayjs/locale/zh-tw'),
	et: () => import('dayjs/locale/et'),
	'en-gb': () => import('dayjs/locale/en-gb'),
	'bn-bd': () => import('dayjs/locale/bn-bd'),
	'fr-ca': () => import('dayjs/locale/fr-ca'),
	'ms-my': () => import('dayjs/locale/ms-my'),
	'pt-br': () => import('dayjs/locale/pt-br'),
	'pa-in': () => import('dayjs/locale/pa-in'),
	'ug-cn': () => import('dayjs/locale/ug-cn'),
	'zh-cn': () => import('dayjs/locale/zh-cn')
};

/** @param {string | undefined} language */
export const getDayjsLocale = (language) => {
	const code = (language ?? 'en').toLowerCase();
	return [code, code.split('-')[0], 'en'].find((candidate) => dayjs.Ls[candidate]);
};

/**
 * Load the locale for a language, then return the name to pass to dayjs.locale().
 * @param {string | undefined} language
 */
export const loadDayjsLocale = async (language) => {
	const code = (language ?? 'en').toLowerCase();
	const name = [code, code.split('-')[0]].find((candidate) => candidate in locales);
	if (name && !dayjs.Ls[name]) await locales[name]().catch(() => {});
	return getDayjsLocale(language);
};

export default dayjs;
