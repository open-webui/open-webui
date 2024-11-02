interface TableToken 
{
    type: 'table'
    raw: string
    header: TableCell[]
    rows: Array<TableCell[]>
}

interface TableCell {
    text:string
}

export function markedTableToCSV(tableToken:TableToken) {
		
    let csvContent = '';
   
    if (tableToken.type === 'table') {
        const headers = tableToken.header.map(cell => `"${cell.text}"`);
        const rows = tableToken.rows.map(row => row.map(cell => `"${cell.text}"`));

        // Add header row
        csvContent += headers.join(',') + '\n';

        // Add data rows
        rows.forEach(row => {
            csvContent += row.join(',') + '\n';
        });
    }

    return csvContent;
}

export function downloadAsFile(fileContent:string, filename:string )
{
    if(fileContent)
    {
        // Create a Blob object representing the CSV data
        const blob = new Blob([fileContent], { type: 'text/csv;charset=utf-8;' });

        // Create a temporary link element
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        // Trigger the download
        link.click();
        // Clean up the temporary link
        URL.revokeObjectURL(link.href);
    }

}