export const downloadPdf = async (note) => {
	const [{ default: jsPDF }, { default: html2canvas }] = await Promise.all([
		import('jspdf'),
		import('html2canvas-pro')
	]);

	// Define a fixed virtual screen size
	const virtualWidth = 1024; // Fixed width (adjust as needed)
	const virtualHeight = 1400; // Fixed height (adjust as needed)

	// STEP 1. Get a DOM node to render
	const html = note.data?.content?.html ?? '';
	const isDarkMode = document.documentElement.classList.contains('dark');

	let node;
	if (html instanceof HTMLElement) {
		node = html;
	} else {
		const virtualWidth = 800; // px, fixed width for cloned element

		// Clone and style
		node = document.createElement('div');

		// title node
		const titleNode = document.createElement('div');
		titleNode.textContent = note.title;
		titleNode.style.fontSize = '24px';
		titleNode.style.fontWeight = 'medium';
		titleNode.style.paddingBottom = '20px';
		titleNode.style.color = isDarkMode ? 'white' : 'black';
		node.appendChild(titleNode);

		const contentNode = document.createElement('div');

		contentNode.innerHTML = html;

		node.appendChild(contentNode);

		node.classList.add('text-black');
		node.classList.add('dark:text-white');
		node.style.width = `${virtualWidth}px`;
		node.style.position = 'absolute';
		node.style.left = '-9999px';
		node.style.height = 'auto';
		node.style.padding = '40px 40px';

		console.log(node);
		document.body.appendChild(node);
	}

	// Render to canvas with predefined width
	const canvas = await html2canvas(node, {
		useCORS: true,
		backgroundColor: isDarkMode ? '#000' : '#fff',
		scale: 2, // Keep at 1x to avoid unexpected enlargements
		width: virtualWidth, // Set fixed virtual screen width
		windowWidth: virtualWidth, // Ensure consistent rendering
		windowHeight: virtualHeight
	});

	// Remove hidden node if needed
	if (!(html instanceof HTMLElement)) {
		document.body.removeChild(node);
	}

	const imgData = canvas.toDataURL('image/jpeg', 0.7);

	// A4 page settings
	const pdf = new jsPDF('p', 'mm', 'a4');
	const imgWidth = 210; // A4 width in mm
	const pageWidthMM = 210; // A4 width in mm
	const pageHeight = 297; // A4 height in mm
	const pageHeightMM = 297; // A4 height in mm

	if (isDarkMode) {
		pdf.setFillColor(0, 0, 0);
		pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
	}

	// Maintain aspect ratio
	const imgHeight = (canvas.height * imgWidth) / canvas.width;
	let heightLeft = imgHeight;
	let position = 0;

	pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
	heightLeft -= pageHeight;

	// Handle additional pages
	while (heightLeft > 0) {
		position -= pageHeight;
		pdf.addPage();

		if (isDarkMode) {
			pdf.setFillColor(0, 0, 0);
			pdf.rect(0, 0, pageWidthMM, pageHeightMM, 'F'); // black bg
		}

		pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight);
		heightLeft -= pageHeight;
	}

	pdf.save(`${note.title}.pdf`);
};
