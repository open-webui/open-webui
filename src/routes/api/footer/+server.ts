import fs from 'fs/promises';
import { error } from '@sveltejs/kit';

const FOOTER_PATH = process.env.FOOTER_PATH || 'open_webui//FOOTER.html';

export async function GET() {
    try {
        const html = await fs.readFile(FOOTER_PATH, 'utf8');
        return new Response(html, {
            headers: {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'no-store'
            }
        });
    } catch (e) {
        throw error(404, 'FOOTER.html not found');
    }
}
