import { get } from 'svelte/store';
import { chapters, currentNovel } from '$lib/stores/sw';
import fileSaver from 'file-saver';
const { saveAs } = fileSaver;

/**
 * Exporte le manuscrit complet
 * @param format 'formatageLivre' | 'markdown'
 */
export async function exportManuscript(format: 'formatageLivre' | 'markdown') {
	const allChapters = [...get(chapters)].sort((a, b) => a.order - b.order);
	const novel = get(currentNovel);
	const title = novel?.title || 'Mon Roman';

	if (format === 'markdown') {
		let md = `# ${title}\n\n`;
		allChapters.forEach((ch) => {
			md += `## ${ch.title}\n\n${ch.content || ''}\n\n---\n\n`;
		});

		const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
		saveAs(blob, `${title.replace(/\s+/g, '_')}_manuscrit.md`);
		return;
	}

	if (format === 'formatageLivre') {
		const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
			import('jspdf'),
			import('html2canvas-pro')
		]);

		// Création d'un élément caché pour le rendu
		const exportRoot = document.createElement('div');
		exportRoot.style.width = '800px';
		exportRoot.style.padding = '60px';
		exportRoot.style.backgroundColor = '#ffffff';
		exportRoot.style.color = '#000000';
		exportRoot.style.fontFamily = "'EB Garamond', 'Georgia', serif";
		exportRoot.style.position = 'absolute';
		exportRoot.style.left = '-9999px';
		exportRoot.style.top = '0';
		exportRoot.style.lineHeight = '1.6';

		// Titre du livre
		const titleEl = document.createElement('h1');
		titleEl.textContent = title;
		titleEl.style.textAlign = 'center';
		titleEl.style.fontSize = '42px';
		titleEl.style.marginTop = '100px';
		titleEl.style.marginBottom = '200px';
		exportRoot.appendChild(titleEl);

		// Chapitres
		allChapters.forEach((ch, index) => {
			// Page break if not first
			if (index > 0) {
				const pb = document.createElement('div');
				pb.style.pageBreakBefore = 'always';
				pb.style.height = '40px'; // Spacer
				exportRoot.appendChild(pb);
			}

			const chTitle = document.createElement('h2');
			chTitle.textContent = `Chapitre ${index + 1} : ${ch.title}`;
			chTitle.style.fontSize = '28px';
			chTitle.style.marginTop = '60px';
			chTitle.style.marginBottom = '30px';
			chTitle.style.borderBottom = '1px solid #eee';
			chTitle.style.paddingBottom = '10px';
			exportRoot.appendChild(chTitle);

			const chContent = document.createElement('div');
			chContent.style.fontSize = '16px';
			chContent.style.whiteSpace = 'pre-wrap';
			chContent.textContent = ch.content || '';
			exportRoot.appendChild(chContent);
		});

		document.body.appendChild(exportRoot);

		// Rendu du canvas
		const canvas = await html2canvas(exportRoot, {
			scale: 2,
			useCORS: true,
			backgroundColor: '#ffffff'
		});

		document.body.removeChild(exportRoot);

		// Création du PDF A4
		const imgData = canvas.toDataURL('image/jpeg', 0.85);
		const pdf = new jsPDF('p', 'mm', 'a4');
		const imgWidth = 210;
		const pageHeight = 297;
		const imgHeight = (canvas.height * imgWidth) / canvas.width;
		
		let heightLeft = imgHeight;
		let position = 0;

		pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
		heightLeft -= pageHeight;

		while (heightLeft > 0) {
			position -= pageHeight;
			pdf.addPage();
			pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
			heightLeft -= pageHeight;
		}

		pdf.save(`${title.replace(/\s+/g, '_')}_manuscrit.pdf`);
	}
}
