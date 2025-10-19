// Big Five Personality Traits and their sub-characteristics
export interface PersonalityTrait {
	id: string;
	name: string;
	description: string;
	subCharacteristics: SubCharacteristic[];
}

export interface SubCharacteristic {
	id: string;
	name: string;
	description: string;
	questions: {
		positive: string[];
		neutral: string[];
		negative: string[];
	};
}

export const personalityTraits: PersonalityTrait[] = [
	{
		id: 'agreeableness',
		name: 'Agreeableness',
		description: 'How cooperative, trusting, and helpful the child is',
		subCharacteristics: [
			{
				id: 'compassionate',
				name: 'Is compassionate, has a soft heart',
				description: 'Shows empathy and care for others',
				questions: {
					positive: [
						"What can I do to help someone who's sad?",
						"Can you help me write a nice note to a friend?",
						"What are kind things I can say to someone?"
					],
					neutral: [
						"How can I be a good friend today?",
						"What are ways to help people who are hurt or sick?"
					],
					negative: [
						"Why do I feel bad when other people are upset?",
						"What should I do if I can't stop worrying about someone?",
						"Why do I cry when my friends are sad?",
						"What if people don't care when I try to help?",
						"How do I stop feeling too sensitive?"
					]
				}
			},
			{
				id: 'helpful',
				name: 'Is helpful and unselfish with others',
				description: 'Willing to assist others without expecting anything in return',
				questions: {
					positive: [
						"How can I help my teacher in class?",
						"What are ways I can help my family today?",
						"How can I be a good teammate?"
					],
					neutral: [
						"Can you make a list of good deeds I can do?",
						"What are fun ways to help my friends?"
					],
					negative: [
						"Why do I feel tired from helping too much?",
						"What if people never help me back?",
						"How do I say no when I don't want to help?",
						"What should I do when I feel taken for granted?",
						"Why do people ignore my help sometimes?"
					]
				}
			},
			{
				id: 'respectful',
				name: 'Is respectful, treats others with respect',
				description: 'Shows consideration and courtesy to others',
				questions: {
					positive: [
						"What are ways to show respect to my teacher?",
						"How can I show respect at home?",
						"How do I be respectful when I disagree?"
					],
					neutral: [
						"What are respectful ways to ask for help?",
						"What are respectful rules I can follow?"
					],
					negative: [
						"What should I do if someone isn't respectful to me?",
						"Why do people sometimes ignore me?",
						"What if I lose my temper when I feel disrespected?",
						"How do I earn respect from others?",
						"Why do people act rude even when I'm nice?"
					]
				}
			},
			{
				id: 'forgiving',
				name: 'Has a forgiving nature',
				description: 'Able to let go of grudges and move past conflicts',
				questions: {
					positive: [
						"How do I forgive someone who hurt my feelings?",
						"Why is forgiving people a good thing?",
						"Can you help me write a letter of forgiveness?"
					],
					neutral: [
						"What should I do when someone says sorry?",
						"Why does forgiveness make me feel better?"
					],
					negative: [
						"Why is it hard to forgive people sometimes?",
						"What if I don't want to forgive someone?",
						"How do I stop thinking about what they did?",
						"What happens if I never forgive?",
						"How can I move on when I still feel angry?"
					]
				}
			},
			{
				id: 'trusting',
				name: 'Assumes the best about people',
				description: 'Tends to see the good in others and give them the benefit of the doubt',
				questions: {
					positive: [
						"Why is it good to give second chances?",
						"How can I stay hopeful about others?",
						"How do I believe the best in people?"
					],
					neutral: [
						"Can you tell me a story where someone turned out better than expected?",
						"What does it mean to see the good in someone?"
					],
					negative: [
						"What if I trust people too easily?",
						"How can I tell when someone is lying?",
						"Why do I feel disappointed in people sometimes?",
						"What if my friend breaks my trust?",
						"How do I stop being naive?"
					]
				}
			}
		]
	},
	{
		id: 'conscientiousness',
		name: 'Conscientiousness',
		description: 'How organized, responsible, and self-disciplined the child is',
		subCharacteristics: [
			{
				id: 'organized',
				name: 'Is systematic, likes to keep things in order',
				description: 'Prefers structure and organization',
				questions: {
					positive: [
						"Can you help me make a plan for my day?",
						"What are fun ways to organize my room?",
						"How do I keep my backpack neat and tidy?"
					],
					neutral: [
						"What's a good way to sort my toys or books?",
						"How can I make a list to stay on track?"
					],
					negative: [
						"Why do I feel stressed when things are messy?",
						"How can I stop getting frustrated when my plans change?",
						"What should I do when I lose track of my things?",
						"Why does being organized feel so hard sometimes?",
						"How do I stay calm when everything feels out of order?"
					]
				}
			},
			{
				id: 'efficient',
				name: 'Is efficient, gets things done',
				description: 'Able to complete tasks effectively and on time',
				questions: {
					positive: [
						"How can I finish my homework faster?",
						"What are smart ways to use my time?",
						"Can you help me plan my afternoon productively?"
					],
					neutral: [
						"How do I stay focused while working?",
						"What's the best way to finish a big project?"
					],
					negative: [
						"Why do I get distracted so easily?",
						"What should I do when I can't focus?",
						"Why do I take so long to finish things?",
						"How do I stop wasting time on small stuff?",
						"What if I always feel behind?"
					]
				}
			},
			{
				id: 'persistent',
				name: 'Is persistent, works until the task is finished',
				description: 'Doesn\'t give up easily and follows through on commitments',
				questions: {
					positive: [
						"Can you tell me a story about not giving up?",
						"What are ways to stay motivated when something's hard?",
						"How do I feel proud after finishing something big?"
					],
					neutral: [
						"What can I do when I get bored halfway through?",
						"How do I remind myself to keep going?"
					],
					negative: [
						"Why do I give up so easily?",
						"What if I never finish anything I start?",
						"How do I stop quitting when things get tough?",
						"Why do I lose interest so fast?",
						"What should I do when I feel like failing?"
					]
				}
			},
			{
				id: 'dependable',
				name: 'Is dependable, steady',
				description: 'Reliable and consistent in behavior',
				questions: {
					positive: [
						"How can I show people they can count on me?",
						"What are ways to prove I'm trustworthy?",
						"How do I keep my promises even when I'm busy?"
					],
					neutral: [
						"What does it mean to be dependable?",
						"How can I remember what I said I'd do?"
					],
					negative: [
						"Why do I forget to do things people ask?",
						"How do I make up for letting someone down?",
						"What should I do when people stop trusting me?",
						"Why do I feel guilty when I forget?",
						"How can I be steady when I feel all over the place?"
					]
				}
			},
			{
				id: 'responsible',
				name: 'Is reliable, can always be counted on',
				description: 'Takes responsibility for actions and commitments',
				questions: {
					positive: [
						"How do I show my friends I'll always be there?",
						"What are good habits that make me reliable?",
						"How can I act responsible in school and at home?"
					],
					neutral: [
						"Why is being reliable important?",
						"What should I do when someone needs my help?"
					],
					negative: [
						"Why do people say I forget too much?",
						"What if I mess up when someone's counting on me?",
						"How do I stay calm when I make a mistake?",
						"Why do I feel like I'm not dependable enough?",
						"How do I fix my reputation if people think I'm unreliable?"
					]
				}
			}
		]
	},
	{
		id: 'extraversion',
		name: 'Extraversion',
		description: 'How outgoing, social, and energetic the child is',
		subCharacteristics: [
			{
				id: 'outgoing',
				name: 'Is outgoing, sociable',
				description: 'Enjoys being around people and social situations',
				questions: {
					positive: [
						"What are fun ways to meet new friends?",
						"Can you help me plan a fun group activity?",
						"How can I make people feel welcome when they join my game?"
					],
					neutral: [
						"What should I say when someone invites me to play?",
						"What are fun questions to ask someone I just met?"
					],
					negative: [
						"What if people don't want to talk to me?",
						"How do I stop feeling left out at recess?",
						"People say I talk too much — what should I do?",
						"Why does making friends feel hard sometimes?",
						"What if I get nervous when everyone's looking at me?"
					]
				}
			},
			{
				id: 'talkative',
				name: 'Is talkative',
				description: 'Enjoys conversation and verbal expression',
				questions: {
					positive: [
						"Can you give me some cool stories to tell my friends?",
						"Can you teach me a tongue twister to say fast?",
						"What are silly jokes I can tell my classmates?"
					],
					neutral: [
						"What are some questions I can ask my teacher?",
						"Can you help me practice for a class presentation?"
					],
					negative: [
						"People say I talk too much — how can I fix that?",
						"What if my friends get annoyed when I keep talking?",
						"How do I stop interrupting people by accident?",
						"Why do people ignore me when I talk a lot?",
						"How can I know when it's my turn to speak?"
					]
				}
			},
			{
				id: 'assertive',
				name: 'Has an assertive personality',
				description: 'Confident in expressing opinions and taking charge',
				questions: {
					positive: [
						"How do I lead a team in a group project?",
						"What are ways to be a great leader at school?",
						"How can I speak up if someone is being unfair?"
					],
					neutral: [
						"Can you help me sound more confident?",
						"What are smart ways to be in charge?"
					],
					negative: [
						"How do I stop sounding bossy when I lead?",
						"What if people get upset when I share my opinion?",
						"How can I speak up without scaring others?",
						"What if I feel nervous telling people what to do?",
						"How do I handle people not listening to me?"
					]
				}
			},
			{
				id: 'energetic',
				name: 'Is full of energy',
				description: 'High energy levels and enthusiasm',
				questions: {
					positive: [
						"What are games I can play that use lots of energy?",
						"Can you create a high-speed treasure hunt?",
						"What are sports I can try at recess?"
					],
					neutral: [
						"How do I burn energy before bedtime?",
						"What are fun dares I can try?"
					],
					negative: [
						"What should I do when I can't sit still in class?",
						"Why do adults say I'm too hyper?",
						"How can I calm down when I feel jumpy?",
						"What if my friends get tired of my energy?",
						"How do I focus when I have too much energy?"
					]
				}
			},
			{
				id: 'enthusiastic',
				name: 'Shows a lot of enthusiasm',
				description: 'Expresses excitement and passion easily',
				questions: {
					positive: [
						"Can you help me make a cheer for my team?",
						"What are fun ways to get excited for school?",
						"How can I show my friends I love their ideas?"
					],
					neutral: [
						"What are cool ways to share good news?",
						"Can you give me silly celebration ideas?"
					],
					negative: [
						"Why do people say I'm too loud?",
						"What if others roll their eyes when I'm excited?",
						"How do I calm down when I get overly happy?",
						"Why do I feel embarrassed when people don't match my energy?",
						"What if people think I'm annoying when I'm enthusiastic?"
					]
				}
			}
		]
	},
	{
		id: 'neuroticism',
		name: 'Neuroticism (Emotional Stability)',
		description: 'How emotionally stable and resilient the child is',
		subCharacteristics: [
			{
				id: 'anxious',
				name: 'Can be tense',
				description: 'Experiences anxiety and worry',
				questions: {
					positive: [
						"Can you teach me stretches to help me relax?",
						"What are ways to feel calm before school?",
						"How can I make a peaceful bedtime routine?"
					],
					neutral: [
						"Why does my body feel tight sometimes?",
						"What are relaxing things I can think about?"
					],
					negative: [
						"Why do I get nervous for no reason?",
						"How can I stop clenching my fists when I'm scared?",
						"Why does my heart race when I worry?",
						"What should I do when I feel tense all day?",
						"How do I stop feeling jumpy before a big test?"
					]
				}
			},
			{
				id: 'worried',
				name: 'Worries a lot',
				description: 'Tends to worry and overthink situations',
				questions: {
					positive: [
						"Can you help me make a worry journal?",
						"What are ways to stay calm when I'm nervous?",
						"Can you tell me a story about facing fears?"
					],
					neutral: [
						"Why do I worry about things that haven't happened?",
						"How do I feel okay when something goes wrong?"
					],
					negative: [
						"Why can't I stop thinking about bad things?",
						"How do I sleep when my brain won't stop worrying?",
						"What should I do when I feel scared every day?",
						"Why do I imagine bad stuff all the time?",
						"What if I never stop worrying?"
					]
				}
			},
			{
				id: 'sad',
				name: 'Often feels sad',
				description: 'Experiences sadness and low moods',
				questions: {
					positive: [
						"Can you tell me a happy story when I feel down?",
						"What are fun things to do when I'm sad?",
						"How can I cheer myself up on a bad day?"
					],
					neutral: [
						"Why do I miss people sometimes?",
						"How can I talk about my sad feelings?"
					],
					negative: [
						"Why do I feel sad for no reason?",
						"What should I do when I want to cry all the time?",
						"Why do I feel left out even with friends?",
						"What if I can't stop thinking sad thoughts?",
						"How can I make the sadness go away?"
					]
				}
			},
			{
				id: 'moody',
				name: 'Is moody, has up and down mood swings',
				description: 'Emotions change frequently and unpredictably',
				questions: {
					positive: [
						"How can I understand my moods better?",
						"What helps balance my feelings?",
						"Can you teach me calm-down tricks for when I feel off?"
					],
					neutral: [
						"Why do I feel happy and sad in the same day?",
						"What are ways to explain my moods to friends?"
					],
					negative: [
						"Why do I get mad so fast sometimes?",
						"How can I stop snapping at people?",
						"What do I do when I suddenly feel sad?",
						"Why do my feelings change for no reason?",
						"How do I handle big emotions without yelling?"
					]
				}
			},
			{
				id: 'emotional',
				name: 'Is temperamental, gets emotional easily',
				description: 'Strong emotional reactions to situations',
				questions: {
					positive: [
						"How can I tell people how I feel without yelling?",
						"Can you help me cool down when I'm upset?",
						"What are safe ways to let out emotions?"
					],
					neutral: [
						"Why do small things make me emotional?",
						"What can I do when I feel too many feelings?"
					],
					negative: [
						"Why do I cry or yell so easily?",
						"How do I stop exploding when I'm angry?",
						"Why can't I control my feelings sometimes?",
						"What should I do when I say things I regret?",
						"How do I keep my emotions from taking over?"
					]
				}
			}
		]
	},
	{
		id: 'openness',
		name: 'Openness to Experience',
		description: 'How curious, creative, and open to new ideas the child is',
		subCharacteristics: [
			{
				id: 'curious',
				name: 'Is curious about many different things',
				description: 'Has a strong desire to learn and explore',
				questions: {
					positive: [
						"Can you teach me something cool I don't know?",
						"Why do animals act differently at night?",
						"What are mysteries scientists haven't solved yet?"
					],
					neutral: [
						"Why is the sky blue but space black?",
						"How does a rainbow happen?"
					],
					negative: [
						"Why do I get bored so easily?",
						"What if I'm not interested in learning new things?",
						"Why does school feel boring sometimes?",
						"How do I stay curious when lessons feel hard?",
						"What should I do when I stop caring about things?"
					]
				}
			},
			{
				id: 'deep_thinker',
				name: 'Is complex, a deep thinker',
				description: 'Enjoys philosophical and abstract thinking',
				questions: {
					positive: [
						"Can you help me think about big questions?",
						"Why do people dream?",
						"Why do we feel emotions?"
					],
					neutral: [
						"Why do people believe different things?",
						"What is time, really?"
					],
					negative: [
						"Why do my thoughts never stop?",
						"What if thinking too much makes me sad?",
						"Why do I get lost in my thoughts so often?",
						"How do I stop worrying about deep stuff?",
						"What if nobody understands how I think?"
					]
				}
			},
			{
				id: 'artistic',
				name: 'Is fascinated by art, music, or literature',
				description: 'Appreciates and engages with creative arts',
				questions: {
					positive: [
						"Can you show me a cool drawing idea?",
						"Can you help me write my own story?",
						"What's the story behind a famous painting?"
					],
					neutral: [
						"Why do some songs make me cry?",
						"How do artists get their ideas?"
					],
					negative: [
						"What if I think my art isn't good enough?",
						"Why do people not like what I make?",
						"How do I stop comparing my drawings to others?",
						"What if I lose interest in art?",
						"Why do I get upset when my art doesn't look right?"
					]
				}
			},
			{
				id: 'creative',
				name: 'Is inventive, finds clever ways to do things',
				description: 'Comes up with original solutions and ideas',
				questions: {
					positive: [
						"Can you help me invent something new?",
						"What's a fun invention challenge I can try?",
						"How do inventors come up with ideas?"
					],
					neutral: [
						"How do I think outside the box?",
						"Can you give me a puzzle to solve?"
					],
					negative: [
						"Why can't I think of good ideas?",
						"What if my inventions always fail?",
						"Why do people say my ideas are weird?",
						"How do I stop giving up when my idea doesn't work?",
						"What if I'm not as creative as other kids?"
					]
				}
			},
			{
				id: 'imaginative',
				name: 'Is original, comes up with new ideas',
				description: 'Has a vivid imagination and original thinking',
				questions: {
					positive: [
						"Can you help me invent a new holiday?",
						"How do I make something that doesn't exist yet?",
						"What's an idea for a school project no one's done?"
					],
					neutral: [
						"How do I make up my own stories?",
						"Can you help me name a new planet?"
					],
					negative: [
						"Why do people not like my ideas?",
						"How do I stop doubting my imagination?",
						"What if my ideas sound silly?",
						"Why do I feel nervous sharing my thoughts?",
						"What should I do when nobody listens to my ideas?"
					]
				}
			}
		]
	}
];

// Helper function to get questions for scenario generation
export function getQuestionsForCharacteristics(selectedCharacteristics: string[]): string[] {
	const questions: string[] = [];
	
	// Calculate how many questions per characteristic
	const questionsPerCharacteristic = Math.floor(10 / selectedCharacteristics.length);
	const remainingQuestions = 10 % selectedCharacteristics.length;
	
	selectedCharacteristics.forEach((charId, index) => {
		// Find the characteristic in our data
		const trait = personalityTraits.find(t => 
			t.subCharacteristics.some(sub => sub.id === charId)
		);
		
		if (trait) {
			const subChar = trait.subCharacteristics.find(sub => sub.id === charId);
			if (subChar) {
				// Get questions from all three categories in a consistent order
				const allQuestions = [
					...subChar.questions.positive,
					...subChar.questions.neutral,
					...subChar.questions.negative
				];
				
				// Take the required number of questions in order (no randomization)
				const numQuestions = questionsPerCharacteristic + (index < remainingQuestions ? 1 : 0);
				questions.push(...allQuestions.slice(0, numQuestions));
			}
		}
	});
	
	return questions;
}

// Function to load and parse JSON data from ContextBased_Prompt_Generation
export async function loadPersonalityDataFromJSON(): Promise<any> {
	try {
		// Import the personality questions data
		const { personalityQuestions } = await import('./personalityQuestions');
		return personalityQuestions;
	} catch (error) {
		console.error('Error loading personality data from JSON:', error);
		return null;
	}
}

// Function to generate scenarios from JSON data
export function generateScenariosFromJSON(jsonData: any, selectedCharacteristics: string[]): string[] {
	const questions: string[] = [];
	
	if (!jsonData) return questions;
	
	// Calculate how many questions per characteristic
	const questionsPerCharacteristic = Math.floor(10 / selectedCharacteristics.length);
	const remainingQuestions = 10 % selectedCharacteristics.length;
	
	selectedCharacteristics.forEach((charName, index) => {
		// Search through all personality traits for the characteristic
		const allTraits = [
			jsonData.openness,
			jsonData.conscientiousness,
			jsonData.agreeableness,
			jsonData.neuroticism,
			jsonData.extraversion
		];
		
		for (const trait of allTraits) {
			if (trait && trait[charName]) {
				// Get questions from all three categories in a consistent order
				const allQuestions = [
					...(trait[charName].positive || []),
					...(trait[charName].neutral || []),
					...(trait[charName].negative || [])
				];
				
				// Take the required number of questions in order (no randomization)
				const numQuestions = questionsPerCharacteristic + (index < remainingQuestions ? 1 : 0);
				questions.push(...allQuestions.slice(0, numQuestions));
				break; // Found the characteristic, move to next
			}
		}
	});
	
	return questions;
}
