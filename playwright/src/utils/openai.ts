import fs from 'fs';
import OpenAI from 'openai';

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

export async function describeLocalImage(fileName: string): Promise<string> {
	const imageBase64 = fs.readFileSync(fileName).toString('base64');

	const response = await openai.chat.completions.create({
		model: 'gpt-4o-mini',
		messages: [
			{
				role: 'user',
				content: [
					{ type: 'text', text: 'Describe this image in detail.' },
					{
						type: 'image_url',
						image_url: {
							url: `data:image/jpeg;base64,${imageBase64}`
						}
					}
				]
			}
		],
		max_tokens: 300
	});

	return response.choices[0].message.content || 'Error: No description generated.';
}
