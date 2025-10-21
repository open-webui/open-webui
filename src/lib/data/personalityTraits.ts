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
			},
			{
				id: 'unsympathetic',
				name: 'Feels little sympathy for others',
				description: 'May struggle with empathy or understanding others\' emotions',
				questions: {
					positive: [
						"Can you teach me what empathy means?",
						"Why is being kind important?",
						"What are ways to be more caring?"
					],
					neutral: [
						"Why do people cry when others are sad?",
						"Why should I care when someone is upset?"
					],
					negative: [
						"What if I don't feel bad when someone gets hurt?",
						"Why do I not understand people's feelings?",
						"How can I act nice even if I don't feel it?",
						"What happens when I don't care about others?",
						"Why do I feel annoyed when people are emotional?"
					]
				}
			},
			{
				id: 'polite',
				name: 'Is polite, courteous to others',
				description: 'Uses good manners and shows consideration',
				questions: {
					positive: [
						"Can you teach me nice words to use every day?",
						"What are polite ways to ask for things?",
						"How can I be courteous at school?"
					],
					neutral: [
						"Why do adults care about manners so much?",
						"What's a polite way to leave a conversation?"
					],
					negative: [
						"What if I forget to say please and thank you?",
						"Why do I feel awkward being too polite?",
						"How do I be polite to people I don't like?",
						"What should I do when other kids think being polite is weird?",
						"Why does being courteous feel uncomfortable sometimes?"
					]
				}
			},
			{
				id: 'argumentative',
				name: 'Starts arguments with others',
				description: 'May be confrontational or quick to disagree',
				questions: {
					positive: [
						"How can I disagree without starting a fight?",
						"What are calm ways to stand my ground?",
						"Why is it okay to have different opinions?"
					],
					neutral: [
						"How do I know when to drop an argument?",
						"What does it mean to agree to disagree?"
					],
					negative: [
						"Why do I always want to argue?",
						"What if I can't stop myself from disagreeing?",
						"How do I stay calm when people are wrong?",
						"Why do I get into arguments so easily?",
						"What should I do when people say I'm too argumentative?"
					]
				}
			},
			{
				id: 'fault_finding',
				name: 'Tends to find fault with others',
				description: 'Often notices what\'s wrong or criticizes others',
				questions: {
					positive: [
						"How can I give helpful feedback instead of criticism?",
						"What are nice ways to point out mistakes?",
						"How do I focus on the good instead of the bad?"
					],
					neutral: [
						"Why do I notice problems so easily?",
						"What does constructive criticism mean?"
					],
					negative: [
						"Why do I always see what's wrong with others?",
						"How can I stop criticizing people in my head?",
						"What if people think I'm mean for pointing out mistakes?",
						"Why do I focus on negatives more than positives?",
						"How do I stop judging people so much?"
					]
				}
			},
			{
				id: 'suspicious',
				name: 'Is suspicious of others\' intentions',
				description: 'May distrust others or question their motives',
				questions: {
					positive: [
						"How can I learn to trust people more?",
						"What are signs someone is trustworthy?",
						"Why is it good to give people the benefit of the doubt?"
					],
					neutral: [
						"How do I know if someone is being honest?",
						"What should I do when I'm unsure about someone?"
					],
					negative: [
						"Why do I think people are lying all the time?",
						"How can I stop doubting everyone's intentions?",
						"What if I can't trust anyone?",
						"Why do I feel like people are trying to trick me?",
						"How do I stop being so paranoid about others?"
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
			},
			{
				id: 'tidy',
				name: 'Keeps things neat and tidy',
				description: 'Maintains cleanliness and order in personal spaces',
				questions: {
					positive: [
						"What are fun ways to organize my room?",
						"Can you help me create a cleaning routine?",
						"How can I make tidying up feel less boring?"
					],
					neutral: [
						"Why does keeping things clean matter?",
						"What's the best way to sort my stuff?"
					],
					negative: [
						"Why do I hate cleaning my room?",
						"What if I can't keep things tidy no matter what?",
						"How do I stop losing things in my mess?",
						"Why does my stuff get messy so fast?",
						"What should I do when tidying feels overwhelming?"
					]
				}
			},
			{
				id: 'disorganized',
				name: 'Tends to be disorganized',
				description: 'May struggle with keeping things in order',
				questions: {
					positive: [
						"How can I get better at organizing?",
						"What are simple ways to stay organized?",
						"Can you help me create a system to track my things?"
					],
					neutral: [
						"Why do I lose track of my stuff?",
						"What happens when I'm disorganized?"
					],
					negative: [
						"Why can't I ever find my things?",
						"How do I stop being so messy?",
						"What if I always forget where I put stuff?",
						"Why does organizing feel so hard for me?",
						"How can I stay organized when my brain feels scattered?"
					]
				}
			},
			{
				id: 'lazy',
				name: 'Tends to be lazy',
				description: 'May lack motivation or avoid effort',
				questions: {
					positive: [
						"How can I motivate myself to do things?",
						"What are ways to get more energy?",
						"How do I start tasks when I don't feel like it?"
					],
					neutral: [
						"Why don't I feel like doing anything sometimes?",
						"What makes some tasks feel easier than others?"
					],
					negative: [
						"Why do I always put things off?",
						"How can I stop being lazy?",
						"What if I never feel motivated?",
						"Why do I avoid doing work even when I know I should?",
						"How do I overcome feeling too tired to try?"
					]
				}
			},
			{
				id: 'careless',
				name: 'Can be somewhat careless',
				description: 'May make mistakes due to lack of attention',
				questions: {
					positive: [
						"How can I pay better attention to details?",
						"What are ways to check my work?",
						"How do I slow down and be more careful?"
					],
					neutral: [
						"Why do I make silly mistakes?",
						"What does it mean to be more mindful?"
					],
					negative: [
						"Why do I mess things up so often?",
						"How can I stop being so careless?",
						"What if I always make mistakes?",
						"Why don't I notice when I do things wrong?",
						"How do I stop rushing and missing important stuff?"
					]
				}
			},
			{
				id: 'irresponsible',
				name: 'Sometimes behaves irresponsibly',
				description: 'May not always follow through on commitments',
				questions: {
					positive: [
						"How can I become more responsible?",
						"What are ways to remember my responsibilities?",
						"How do I take ownership of my actions?"
					],
					neutral: [
						"Why is being responsible important?",
						"What happens when I don't follow through?"
					],
					negative: [
						"Why do I forget to do what I promised?",
						"How can I stop letting people down?",
						"What if I keep making the same mistakes?",
						"Why do I avoid responsibilities?",
						"How do I fix things when I've been irresponsible?"
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
			},
			{
				id: 'quiet',
				name: 'Tends to be quiet',
				description: 'Prefers listening over speaking, more reserved',
				questions: {
					positive: [
						"Is it okay to be quiet?",
						"What are good things about being a listener?",
						"How can I show I care without talking much?"
					],
					neutral: [
						"Why do I prefer to listen instead of talk?",
						"What are ways to enjoy quiet time?"
					],
					negative: [
						"Why do people think I'm shy because I'm quiet?",
						"How can I speak up when I need to?",
						"What if people think I'm boring?",
						"Why do I feel nervous to talk in groups?",
						"How do I stop feeling left out when I don't talk much?"
					]
				}
			},
			{
				id: 'shy',
				name: 'Is sometimes shy, introverted',
				description: 'May feel uncomfortable in social situations',
				questions: {
					positive: [
						"How can I feel more comfortable around new people?",
						"What are ways to make friends when I'm shy?",
						"Can you help me practice starting conversations?"
					],
					neutral: [
						"Why do I feel nervous meeting people?",
						"What's good about being introverted?"
					],
					negative: [
						"Why am I so shy all the time?",
						"How can I stop feeling scared to talk?",
						"What if I never get over being shy?",
						"Why do I freeze up when people talk to me?",
						"How do I make friends when I'm too shy to speak?"
					]
				}
			},
			{
				id: 'dominant',
				name: 'Is dominant, acts as a leader',
				description: 'Takes charge and leads others',
				questions: {
					positive: [
						"How can I be a good leader?",
						"What are ways to inspire my team?",
						"How do I help everyone work together?"
					],
					neutral: [
						"What makes someone a good leader?",
						"How do I know when to take charge?"
					],
					negative: [
						"Why do people say I'm too bossy?",
						"How can I lead without controlling everyone?",
						"What if people don't want to follow me?",
						"Why do I always want to be in charge?",
						"How do I share leadership with others?"
					]
				}
			},
			{
				id: 'not_influential',
				name: 'Finds it hard to influence people',
				description: 'May struggle to convince or persuade others',
				questions: {
					positive: [
						"How can I get better at sharing my ideas?",
						"What are ways to be more persuasive?",
						"How do I speak so people listen?"
					],
					neutral: [
						"Why don't people listen to me?",
						"What makes someone influential?"
					],
					negative: [
						"Why can't I ever change people's minds?",
						"How do I stop feeling ignored?",
						"What if no one takes my ideas seriously?",
						"Why do others always win arguments?",
						"How can I be more convincing?"
					]
				}
			},
			{
				id: 'follower',
				name: 'Prefers to have others take charge',
				description: 'More comfortable following than leading',
				questions: {
					positive: [
						"Is it okay to let others lead?",
						"What are good things about being a follower?",
						"How can I be a great team member?"
					],
					neutral: [
						"Why do I prefer when others decide?",
						"What does it mean to be a good follower?"
					],
					negative: [
						"Why can't I ever take charge?",
						"How do I stop always depending on others?",
						"What if people think I'm weak for not leading?",
						"Why do I feel scared to make decisions?",
						"How can I be more confident in taking the lead?"
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
			},
			{
				id: 'relaxed',
				name: 'Is relaxed, handles stress well',
				description: 'Remains calm under pressure',
				questions: {
					positive: [
						"How can I stay calm in stressful situations?",
						"What are ways to help others relax?",
						"Can you teach me breathing exercises?"
					],
					neutral: [
						"Why don't things stress me out as much?",
						"What helps me stay relaxed?"
					],
					negative: [
						"What if people think I don't care because I'm so calm?",
						"How do I show concern when I don't feel worried?",
						"Why don't things bother me like they bother others?",
						"What if being too relaxed makes me miss important stuff?",
						"How can I take things seriously while staying calm?"
					]
				}
			},
			{
				id: 'optimistic',
				name: 'Stays optimistic after experiencing a setback',
				description: 'Bounces back from difficulties with a positive outlook',
				questions: {
					positive: [
						"How can I stay positive when things go wrong?",
						"What are ways to cheer myself up?",
						"Can you tell me a story about bouncing back?"
					],
					neutral: [
						"Why is it good to stay optimistic?",
						"How do I find the good in bad situations?"
					],
					negative: [
						"What if trying to be positive feels fake?",
						"How do I stay hopeful when everything keeps going wrong?",
						"Why do people say I'm too optimistic?",
						"What if staying positive makes me ignore real problems?",
						"How can I be realistic and optimistic at the same time?"
					]
				}
			},
			{
				id: 'stable',
				name: 'Is emotionally stable, not easily upset',
				description: 'Maintains emotional balance and composure',
				questions: {
					positive: [
						"How can I help friends who get upset easily?",
						"What are ways to stay balanced?",
						"Why is emotional stability helpful?"
					],
					neutral: [
						"Why don't I get upset as easily as others?",
						"What helps me stay emotionally steady?"
					],
					negative: [
						"What if people think I'm cold because I don't get upset?",
						"How do I show I care when I don't react emotionally?",
						"Why don't things bother me like they should?",
						"What if my calmness makes others feel alone?",
						"How can I be more emotionally expressive?"
					]
				}
			},
			{
				id: 'controlled',
				name: 'Keeps their emotions under control',
				description: 'Manages and regulates emotional expressions',
				questions: {
					positive: [
						"How can I stay calm when I'm angry?",
						"What are ways to control my reactions?",
						"Can you teach me techniques to manage emotions?"
					],
					neutral: [
						"Why is it important to control my emotions?",
						"How do I express feelings in a healthy way?"
					],
					negative: [
						"What if keeping emotions in makes me explode later?",
						"How do I know if I'm suppressing too much?",
						"Why do I bottle up my feelings?",
						"What if people think I'm hiding something?",
						"How can I be open while staying in control?"
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
			},
			{
				id: 'non_intellectual',
				name: 'Avoids intellectual, philosophical discussions',
				description: 'Prefers practical, concrete topics over abstract ideas',
				questions: {
					positive: [
						"What are fun, simple topics to talk about?",
						"How can I enjoy learning without getting too deep?",
						"What are practical skills I can learn?"
					],
					neutral: [
						"Why do I prefer simple explanations?",
						"What's good about focusing on the basics?"
					],
					negative: [
						"Why do deep conversations bore me?",
						"What if people think I'm not smart?",
						"How do I stay interested in philosophical stuff?",
						"Why don't I like thinking about abstract ideas?",
						"What if I'm missing out by not thinking deeply?"
					]
				}
			},
			{
				id: 'aesthetically_appreciative',
				name: 'Values art and beauty',
				description: 'Appreciates aesthetics and artistic expression',
				questions: {
					positive: [
						"What makes something beautiful?",
						"Can you show me famous works of art?",
						"How can I notice beauty in everyday things?"
					],
					neutral: [
						"Why do people create art?",
						"What are different types of beauty?"
					],
					negative: [
						"What if I don't understand modern art?",
						"Why do people spend so much on art?",
						"How can I appreciate art I don't like?",
						"What if my taste in art is different?",
						"Why does beauty matter so much?"
					]
				}
			},
			{
				id: 'unartistic',
				name: 'Has few artistic interests',
				description: 'Less drawn to arts and creative activities',
				questions: {
					positive: [
						"What are non-art hobbies I can try?",
						"How can I enjoy activities without art?",
						"What skills don't require creativity?"
					],
					neutral: [
						"Why am I not into art?",
						"What's good about focusing on other things?"
					],
					negative: [
						"What if everyone thinks I'm boring for not liking art?",
						"How do I appreciate art when it doesn't interest me?",
						"Why don't I get excited about music or painting?",
						"What if I'm missing out on something important?",
						"How can I connect with artistic people?"
					]
				}
			},
			{
				id: 'uncreative',
				name: 'Has little creativity',
				description: 'May struggle with creative or imaginative tasks',
				questions: {
					positive: [
						"How can I get better at creative thinking?",
						"What are ways to be more imaginative?",
						"Can you give me exercises to boost creativity?"
					],
					neutral: [
						"Why don't I think of creative ideas?",
						"What makes someone creative?"
					],
					negative: [
						"Why can't I think of original ideas?",
						"How do I stop copying others?",
						"What if I'm just not a creative person?",
						"Why do creative projects feel so hard?",
						"How can I succeed without creativity?"
					]
				}
			},
			{
				id: 'unimaginative',
				name: 'Has difficulty imagining things',
				description: 'Struggles with visualization or abstract thinking',
				questions: {
					positive: [
						"How can I improve my imagination?",
						"What are ways to practice visualizing?",
						"Can you help me with imagination exercises?"
					],
					neutral: [
						"Why is it hard for me to picture things?",
						"What's the difference between imagination and memory?"
					],
					negative: [
						"Why can't I imagine things like others do?",
						"How do I read books when I can't picture the scenes?",
						"What if I can never imagine well?",
						"Why do I struggle with pretend play?",
						"How can I be successful without a good imagination?"
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
