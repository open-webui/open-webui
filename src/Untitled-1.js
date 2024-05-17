function execute(id, text) {
	// pyscript
	let div = document.createElement('div');
	let html = `
            <py-script type="mpy">
${text}
            </py-script>
            `;
	div.innerHTML = html;
	const pyScript = div.firstElementChild;
	try {
		document.body.appendChild(pyScript);
		setTimeout(() => {
			document.body.removeChild(pyScript);
		}, 0);
	} catch (error) {
		console.error('Python error:');
		console.error(error);
	}
}
