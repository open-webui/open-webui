Falcor: A Guide

This guide will go over all of the features included in Falcor, an all-in-one AI productivity application. Please keep in mind that Falcor is an ever evolving project. While I will do my best to keep this guide updated, keep in mind that it may take a little time before new features are added to this guide. If you are having any technical issues while using Falcor and would just like to know more about a certain feature, feel free to connect with Austin via the Falcor office hours on Teams, or through email at . Thanks for using Falcor!

# Getting Started

### Signing-Up

Before using Falcor, you must sign up with a username and password. To do this:

While on the Capella VPN (Via Citrix or a company laptop), navigate to Falcors internal URL. Get this from your administrator.

You should now see the sign in screen. Under the Sign In button is a link to sign up. Click this link.

Sign up for Falcor. Enter your Name, Capella email address, and a unique password. Then click create account.

If successful, you should now be logged into Falcor and will see the applications main screen.

### Signing In

If you already have an account, you can proceed to sign in with your username and password. If you are having trouble signing in with your username and password please contact one of the administrators ( or ).

### Home Screen Overview

Place an edited picture here that highlights each feature of the main screen.

### Choosing a Model

Choosing the correct model for the task you want to accomplish is critical to getting the best output possible. Each model has it’s own strengths and weaknesses. Each model should have a descriptor in its title, followed by the actual model name and how many parameters it has been trained on. If you hover over the “i” icon next to the model, you will see a short description of that models capabilities. You can also see this description by selecting the model and looking under its name in the chat window.

Here is the description for each model type currently in Falcor and what use cases they will exceed at.

General Models

These models tend to be well rounded and are decent at all tasks. However, for specialized tasks you can probably choose something better.

Chat Models

Great for regular conversations, brainstorming, and writing tasks. These may not be great for answering questions from the database. Their response time may also be slower than other models.

Coder Models

As the name suggests, these models are better for coding tasks. They should have knowledge of most popular coding languages.

Speed Models

These models tend to generate quick responses. However, their responses will not be as robust or as accurate as other models. These are typically only used during moments of high latency on the server or when they are needed to perform certain tasks that require speed over accuracy.

Q&A Models

These models are best used for asking the database questions. These models are geared towards searching and formulating answers from vector databases. When seeking specific answers from the database, it is highly recommended you use one of these models.

Vision Models

Vision models are best used for vision tasks. For instance, if you have an image that needs alt text, a vision model would be the best for this. 

### Send a Message

Sending a message to a model on Falcor is very easy. Follow the steps below.

Log into Falcor. Once logged in you will see the main screen.

Before sending a message, you must select a model from the model drop down menu in the upper left corner of the screen. Choose a model that will work best for the task at hand.

In the text input box (at the bottom where it says “Send a Message”), type in your message and hit enter or click the send message button to the right of the input box.

Allow the model a moment to read your message and come up with an answer.

Once a model has answered a message you have several options below your message and the models answer available to you. Here is what each option does, going from left to right.

Edit – You have the option to edit both your own message and the models response. Editing your own message will generate a new response from the model. Editing the response message is useful to correct anything in the response you don’t like or that isn’t factual. The model will then only keep the edited version of its response within its memory, allowing you to continue the conversation without having to waste tokens or your time giving the model context.

Copy – This copies the message under the chat bubble. You can copy both the user message and the model response.

Read Aloud – This will read the message text to you using the voice feature.

Generation Info – This gives you technical information about a the messages generation statistics. This is mainly for advanced users to determine how quickly a response is generated and how many tokens it took to create that text.

Good Response/Bad Response – Falcor uses real time human evaluation to help improve its responses. By clicking the thumbs up or down under a message, and providing feedback, you can slowly train Falcor to generate answers in the way you prefer. This feedback works on a user by user basis, so it will conform to your preferences.

Continue Response – For long responses, some models will run out of context space. You can reset this context space by clicking the continue response button. After the context is reset it will continue generating it’s response until it runs out of context space again or it has finished the response.

Regenerate – If you do not like the response that was generated, you can click the regenerate button to get a new response. You can even change models and then hit the button to get a new response from that model.

### Uploading Documents

Falcor has the ability to read most document types. If you have a document that you would like to upload a document to give Falcor contextual information or to ask questions about the document follow the steps below.

In the send message box at the bottom of the main screen, click the “+” symbol.

A small window will pop up above the send message box. Click “Upload Files”

Browse to the file(s) location. You can select more than one file to upload. Once you have selected all the files you intend to upload, click open.

Falcor should be able to recognize most popular document types such as PDF, DOCX, DOC, TXT, and PPT.

### Using Tools

Similar to uploading documents, any tools that can be used by the model you have currently selected can be accessed by clicking the + icon in the Send Message box and turning the tool to ON. You know the tool is turned ON when the toggle is green. Note, that while that tool is turned ON, the model will try to use the tool to answer any query submitted. For instance, if the web search tool is turned ON, it will try to find answers via the internet. If you don’t want it to search for answers on the internet, you would have to turn that tool off before submitting a message.

### Accessing the Prompt Library

One of Falcors most useful features is its prompt library. The prompt library has been designed to allow users easy access to a wide range of prompt templates. These can be accessed via the Send Message box at the bottom of the main screen. To use a prompt, follow the steps below.

Navigate to the Send Message box at the bottom of the main screen. Click the box as if you were about to type a message.

Type a single forward slash ( / ) into the text box. This will bring up the prompt template menu. Scroll through this menu, reading the titles and descriptions for each of the prompts. Once you have found the prompt you would like to use, click on it.

Once you’ve clicked a prompt, it will populate within the Send Message box. Go through the prompt template and fill in user provided information which is anything within brackets ( [example of bracketed text] ).

Note: The first bracketed space that the user needs to input information into will be highlighted so it is easy to locate. Once you have finished filling out the first custom information spot, clicking tab will highlight the next spot you need to fill out. This makes it easy to check if you’ve filled out all the required information.

Once you’ve filled out each of the bracketed parts of the prompt submit the message to get a generated response.

You can edit prompts any way that you would like to. It will not change the prompts stored within the library.

If you have a prompt you would like to add to the library, feel free to contact Austin or David and they can add it to the library for you.

### Accessing the Database

Another useful feature is the vector database that allows Falcor to provide quick answers on documentation that has been uploaded to it. To access the vector database, follow the steps below.

Navigate to the Send Message box at the bottom of the main screen. Clock the box as if you were about to type a message.

Type a single number sign (#) into the text box. This will bring up the database menu. 

In the database menu, you will have the option to search all documents, a single collection, or even just a single file.

Searching All Documents will search all documents that are currently held within the vector database. This is the slowest option of search. This is also the least accurate way of searching, as it can possibly pull info not directly related to your query. Use this for very broad search results.

Searching a particular collection is usually the best way to search the database. Each collection represents a particular topic or set of documents. Searching within a collection will be much quicker and accurate than searching all documents.

Searching a particular file is the last way you can do a search. This will be the fastest and most accurate way of searching. However, having to find the specific file you want to search could be time consuming, therefore it is usually better to just search by collection. 

Once the database has been searched, Falcor will review the relevant documents and generate an answer based off of that review. Under Falcors response, you will see all the sources of information it used to generate its response. This is a good way to check the accuracy of the response to make sure it didn’t hallucinate. 

If you would like to add any documents to the vector database, feel free to get in touch with Austin or David.

### Speech to Text

Besides typing a message and sending it, you can also record a message via voice and send that instead. To do this, click the microphone icon in the send message box. Once you have clicked the microphone, start talking until you have spoken your entire message. Then click the check mark icon to stop the recording. You can also click the X icon if you want to discard the current recording. Falcor will automatically turn this recording into text. Click enter or the send button to send the message to Falcor. Note, that when first clicking the microphone button, you will be asked by your browser to give Falcor microphone permissions. Agree to these, otherwise the speech to text feature will not work.

### Voice to Voice Mode

Another option for communicating with Falcor is through the voice to voice, or voice call feature. This allows you to talk with the model of your choice. Falcor has a number of voices to choose from which you can find in the audio settings. To use this feature, click the headphones icon to the right of the send message box. This will take you into the voice chat screen. While the “listening” message is displayed, Falcor will be listening to what you are saying. After hearing silence for a few seconds, it will begin formulating a response. Once generated, it will speak this response back to you. You can go back and forth with it like you’re having a normal conversation. You have the option to use your camera, which can be turned on by clicking the camera icon. To exit voice call mode, click the X button which will return you to the main screen.

### Chat History Menu

To the left of the chat box on the main screen, you will see the Chat History Menu. Going from top to bottom, you can start a new chat by clicking the pen and paper icon next to the New Chat text. Below This is a search bar that allows you to search your chat history by keyword. Below the search bar you will see any categories that you’ve tagged chats with. See more information on tagged chats in the Chat Instance Options. Click a chat to continue that particular chat thread. The bottom of the chat window displays your user badge, which when click, gives you the option to go to settings, archived chats, or to sign out. The chat history menu can be minimized by clicking the three lines in the upper right corner of the menu.

### Chat Instance Options

Each chat instance within the chat history bar has several options available to it. To access these options, hover over a chat instance and click the three dots that appear. That will bring up the chat instance options, which are explained below.

Pin

This will pin the selected chat instance to the top of the chat history menu. This makes it easy to find chat instances you want easy access to.

Rename

You can rename any chat instance using this option.

Clone

You can clone chat instances. This is useful if you want to take the conversation in multiple directions using the same conversational context.

Archive

An archive chat option is available for improved organization and to reduce clutter in the chat history menu.

Share

Individual chats can be shared with peers. This is great when working on a group project and chat context is needed by multiple members of the group. Clicking copy link will give the user a shareable link. When clicked, the conversation will be cloned to the new users chat history menu.

Delete

You can delete a chat instance by clicking the delete option.

Add Tags

Tags can be created for any chat instance for better organization. Tags will appear at the top of the chat history menu. When clicked, they will display only the chats that have been tagged with that category. This is extremely useful when working on specific courses and projects.

### Getting Help

If you ever run into any issues or need help, feel free to reach out to  or  via email or Teams. You can also get help in the weekly Falcor Office Hours, held every Monday from 3-4 PM Central time.

For help with quick keys and accessing prompts and the database, click the ? icon in the lower right corner of the main screen. This will give you the option of opening the documentation or viewing the keyboard shortcuts for accessing features like the prompt library or the database. 

# Chat Controls

## Valves

## System Prompt

A set of instructions given to the AI at the start of a conversation. This option can be used to set the AI's behavior, knowledge, or role for a specific task or conversation. For example, you might set the system prompt to "You are a helpful French tutor" to make the AI assist with French language learning.

## Advanced Parameters

A collection of settings that fine-tune how the AI generates responses. Users might adjust these to customize the AI's output for specific needs or preferences. For instance, changing these parameters could make the AI's responses more creative for storytelling or more factual for technical writing.

### Seed

A number that initializes the AI's random number generator. Changing this can help get consistent results across multiple conversations or explore different response variations. For example, using the same seed might make the AI generate the same story outline each time, while changing it could produce different plot ideas.

### Stop Sequence

A specific word or phrase that tells the AI to stop generating text. Users might modify this to control where the AI ends its response, especially for formatting purposes. For instance, setting "END" as a stop sequence would make the AI stop writing when it reaches that word.

### Temperature

This controls how random or focused the AI's responses are. Users can lower it for more predictable responses or raise it for more creative or varied outputs. A low temperature might be used for factual Q&A, while a higher temperature could be better for brainstorming sessions.

### Mirostat

An algorithm that helps maintain consistent surprise levels in the AI's responses. It can be adjusted to balance between coherence and creativity in the AI's outputs. This could be useful in maintaining a certain level of engagement in a long conversation or story.

### Mirostat Eta

This controls how quickly Mirostat adjusts to changes. Users might fine-tune this to adjust how responsive the AI is to shifts in conversation complexity. A higher value might make the AI adapt more quickly to a sudden change in topic.

### Mirostat Tau

This sets the target surprise level for Mirostat. Adjusting it allows users to change the balance between predictable and surprising responses. A higher value might lead to more unexpected turns in a story generation task.

### Top K

This limits the AI's word choices to the K most likely options. Users can change this to control the diversity of the AI's vocabulary and ideas. For example, a lower K value might make the AI use more common words, while a higher value could introduce more varied vocabulary.

### Top P

This limits the AI's word choices based on cumulative probability. Similar to Top K, it allows for more flexibility in word selection. Adjusting this could influence how conventional or unconventional the AI's language use is.

### Min P

This sets a minimum probability threshold for word choices. Users might adjust it to exclude very unlikely words from the AI's responses. This could be useful in preventing the AI from using rare or contextually inappropriate words.

### Frequency Penalty

This discourages the AI from repeating words or phrases. Changing it can help reduce repetition and increase variety in the AI's responses. A higher value might be useful when asking the AI to write a long, varied text.

### Repeat Last N

This specifies how many previous tokens the AI should consider when avoiding repetition. Users can fine-tune this to adjust how the AI avoids repeating recent content. For instance, a higher value might prevent the AI from repeating ideas across paragraphs.

### Tfs Z

This adjusts how much the AI focuses on the most likely words. Users might change it to balance between using common words and more unique vocabulary. A lower value could lead to more straightforward language, while a higher value might introduce more uncommon terms.

### Context Length

This determines the amount of previous conversation the AI considers when responding. Adjusting it controls how much past information influences the AI's responses. A longer context might help the AI maintain consistency in a long story or conversation.

### Batch Size (num_batch)

This setting determines how many tokens the AI processes at once. Users might change it to balance between response speed and quality on different devices. A larger batch size might speed up processing on powerful hardware.

### Tokens To Keep On Context Refresh (num_keep)

This controls how much of the conversation to keep when the context gets too long. Users can adjust it to maintain important information while making room for new input. For example, in a long conversation, this might help retain key points while allowing new topics to be introduced.

### Max Tokens (num_predict)

This sets the maximum length of the AI's response. Users might change this to control how long or detailed the AI's answers can be. For instance, setting a low max tokens value could be useful for generating short summaries or headlines.

# Settings

There are a number of custom settings available to the user. See each of the sections below for more information.

## General

The general settings allow the user to change the theme, language, notifications, system prompt, and advanced parameters.

Theme

System

This option will change the UI theme the same option as your system. Either light or dark mode.

Dark

This UI theme is the default dark mode. 

OLED Dark

This UI theme is a dark mode optimized for OLED displays.

Light

This is the default UI theme and is the default light mode.

Her

This is an alternate light mode UI theme that uses elements seen in the AI’s UI in the movie “Her”.

Language

There are a wide variety of languages the user can choose from. Most major languages are included.

Notifications

Notifications can be sent via banners at the top of the app if this option is turned on.

System Prompt

See the Chat Controls section for an explanation of what a system prompt does. The system prompt in the settings menu allows the user to set a more permanent system prompt that will be used with any model selected instead of just the current model.

Advanced Parameters

See the Chat Controls section for explanations of each parameter. Much like the system prompt, these parameters can be set within the settings so they can be used with any model and not just the current one selected.

## Interface

The interface section has numerous settings the user can customize for the UI and Chat components of Falcor.

Default Model

This allows the user to choose their own default model. The default model is what will automatically be selected when starting a new chat.

Chat Bubble UI

This option will change the orientation of the chat bubbles within the chat window. Turning this on will make the chat bubbles look similar to texts on your phone. The user chat bubble will be on the right and Falcors chat bubble will be on the left. Turning this off puts all chats on the left.

Display Username Instead of You in the Chat

Title explains this option. Turning this on will display your username instead of you over your chat bubbles.

Widescreen Mode

Turns widescreen mode on and off

Chat Direction

This changes the direction of the chat bubbles between left to right and right to left

Fluidly Stream Large External Response Chunks

Fluidly Stream Large External Response Chunks refers to the process of smoothly displaying lengthy AI-generated responses in real-time segments, allowing users to see content immediately as it's created rather than waiting for the entire response to be completed.

Chat Background Image

Upload your own image to customize your chat background.

Title Auto-Generation

This will automatically generate a title for your chat instance if turned on.

Response AutoCopy to Clipboard

Automatically copies Falcors response to your clipboard if turned on.

Allow User Location

Allows Falcor to know the users location which can be used for further customization if turned on.

## Personalization

The personalization section allows the user to toggle, add and manage the memory feature. Memory allows Falcor to remember things across chat instances. This can help tailor Falcors responses to you, making them more helpful. To use this feature, do the following:

Toggle the memory feature to on. You know it’s on when the toggle is colored green.

Click Manage.

The memory menu will appear. Here you can add, edit, and delete memories. 

When creating a memory, make sure to refer to yourself as “user”. For instance, if I want Falcor to always know that my favorite color is blue, I would create a memory that said, “Users favorite color is blue”. 

Clicking clear memory will delete all memories from the menu. 

## Audio

This section allows the user to change their audio settings. Specifically, the speech to text and text to speech settings.

STT Settings

Speech-to-Text Engine – Users can choose between the default engine or a Web API engine.

Instant Auto-Send After Voice Transcription – When this is turned on, voice input will be sent immediately after the engine has transcribed it to text. When this is turned off, you will have to click enter to send the transcribed text.

TTS Settings

Auto-playback response – When this is turned on, text to speech responses from Falcor will play immediately once they are transcribed. When this is off, you will have to initiate this manually.

Set Voice – You can set a custom voice by entering a valid voice ID.

## Chats

This section allows you to import and export your chats. You also have the option to archive all chats and delete all chats. When exporting chats, Falcor will export these as .JSON files. To import a chat, select a valid .JSON file. 

## Account

The account section allows the user to change their profile image, badge, name, and password. You also have access to Falcors API key if you want to use it in a 3rd party application.

## About

This section tells you the version of Falcor that is currently running, the Ollama version that is running, and information on the creation of Falcor.