How to test piper online/offline, and how piper works.

Create a virtual environment:

```
python -m venv .env
source .env/bin/activate
```

`pip install piper-tts`

Directory structure:
How to test Piper offline and online. You can create this in your ollama-webui root repo:

/piper
│
├── app.py
├── static
│   └── welcome.wav
│
└── templates
     └── index.html

Python:

```
from flask import Flask, render_template, request, send_file
import os  # Add this import statement

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/play', methods=['POST'])
def play_text():
    if 'text' in request.form:
        text = request.form['text']

        # Generate the audio file
        generate_audio(text)

        # Return the generated audio file to the client
        return send_file('static/welcome.mp3', mimetype='audio/mp3', as_attachment=False)

    return render_template('index.html')

def generate_audio(text):
    # Use os.system to execute the piper command
    piper_command = f'echo "{text}" | piper --model en_US-amy-low --output_file static/welcome.mp3'
    os.system(piper_command)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

Here's the html (which you can convert to svelte):

```
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flask Piper App</title>
</head>
<body>
    <h4>Welcome to Piper App</h4>
    <p>Click "Play Audio" to hear the synthesized speech.</p>

    <!-- Display the text inside a div for user reference -->
    <div id="displayText">
        This is the text that will be read aloud. You can customize this paragraph.
    </div>

    <form id="textForm" method="post" action="/play">
        <input type="submit" value="Play Audio">
    </form>

    <hr>

    <!-- Audio player to play the generated audio -->
    <audio id="audioPlayer">
        <source id="audioSource" src="" type="audio/wav">
        Your browser does not support the audio element.
    </audio>

    <script>
        // Update the audio source when the form is submitted
        document.getElementById('textForm').addEventListener('submit', function(event) {
            event.preventDefault();
            var text = document.getElementById('displayText').innerText;

            // Make an asynchronous POST request to the /play route
            fetch('/play', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'text=' + encodeURIComponent(text),
            })
            .then(response => response.blob())
            .then(blob => {
                // Create a Blob URL for the audio source
                var blobUrl = URL.createObjectURL(blob);
                document.getElementById('audioSource').src = blobUrl;

                // Load and play the audio
                document.getElementById('audioPlayer').load();
                document.getElementById('audioPlayer').play();
            })
            .catch(error => console.error('Error:', error));
        });
    </script>
</body>
</html>
```


This way, our model responses will not sound like Stephen Hawking.

Taken from an original issue/PR from [Ollama-WebUI](https://github.com/ollama-webui/ollama-webui/issues/126)

Code documentaiton for Ollama Web UI integration/PR:

Replace the below code:

```
	const toggleSpeakMessage = async () => {
		if (speaking) {
			speechSynthesis.cancel();
			speaking = null;
		} else {
			speaking = true;
			const speak = new SpeechSynthesisUtterance(message.content);
			speechSynthesis.speak(speak);
		}
	};


	// Keep track of the last played text
	let lastPlayedText = '';
```

with the following:

```
	const toggleSpeakMessage = async () => {
		const audioPlayer = document.getElementById('audioPlayer');

		if (speaking) {
			// If already speaking, pause the audio
			audioPlayer.pause();
			speaking = null;
		} else {
			// If not speaking, start speaking the content of the message
			speaking = true;

			const text = message.content;

			// Check if the text is the same as the last played text
			if (text != lastPlayedText) {
				// Make an asynchronous POST request to the /play route
				fetch('/play', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/x-www-form-urlencoded',
					},
					body: 'text=' + encodeURIComponent(text),
				})
				.then(response => response.blob())
				.then(blob => {
					// Create a Blob URL for the audio source
					const blobUrl = URL.createObjectURL(blob);
					audioPlayer.src = blobUrl;

					// Load and play the audio
					audioPlayer.load();
					audioPlayer.play();
				})
				.catch(error => console.error('Error:', error));

				// Update the last played text
				lastPlayedText = text;
			} else {
				// If the text is the same, resume playing the current audio
				audioPlayer.play();
			}
		}
	};
```

Also replace the line:

```
									</button>

									<button
										class="{isLastMessage
											? 'visible'
											: 'invisible group-hover:visible'} p-1 rounded dark:hover:bg-gray-800 transition"
										on:click={() => {
											toggleSpeakMessage(message);
										}}
									>
										{#if speaking}
```

with the following:

```

									</button>

									<!-- Audio player to play the generated audio -->
									<audio id="audioPlayer">
										<source id="audioSource" src="" type="audio/mp3">
										Your browser does not support the audio element.
									</audio>

									<button
										class="{isLastMessage
											? 'visible'
											: 'invisible group-hover:visible'} p-1 rounded dark:hover:bg-gray-800 transition"
										on:click={() => {
											toggleSpeakMessage(message);
										}}
									>
										{#if speaking}
```

Create this directory structure code in your ollama-webui repo:

/piper
│
├── app.py
├── static
│   └── welcome.wav
│
└── templates
     └── index.html (for testing purposes only)
run:

`python app.py`

Apache configuration to map /play to the flask port:

```
    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders On

    ProxyPass / http://yourgui.com:3000/ nocanon
    ProxyPassReverse / http://yourgui.com:3000/
    SSLProxyEngine on

    <Location "/play">
        ProxyPass http://yourgui.com:5000/play nocanon
        ProxyPassReverse http://yourgui.com:5000/play
    </Location>
```

How I run my site:

yourgui.com.com.conf:

```
<VirtualHost *:80>
    ServerName yourgui.com.com
    ServerAlias www.yourgui.com.com

    ProxyPass / http://yourgui.com.com:3000/
    ProxyPassReverse / http://yourgui.com.com:3000/
    ErrorLog ${APACHE_LOG_DIR}/yourgui.com_error.log
    CustomLog ${APACHE_LOG_DIR}/yourgui.comi_access.log combined
RewriteEngine on
RewriteCond %{SERVER_NAME} =yourgui.com.com [OR]
RewriteCond %{SERVER_NAME} =www.yourgui.com.com
RewriteRule ^ https://%{SERVER_NAME}%{REQUEST_URI} [END,NE,R=permanent]
</VirtualHost>
```
sudo a2ensite yourgui.com.com.conf

Run lets encrypt:
sudo certbot --apache -d yourgui.com.com

yourgui.com.com-le-ssl.conf

```
    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders On

    ProxyPass / http://yourgui.com:3000/ nocanon
    ProxyPassReverse / http://yourgui.com:3000/
    SSLProxyEngine on

    <Location "/play">
        ProxyPass http://yourgui.com:5000/play nocanon
        ProxyPassReverse http://yourgui.com:5000/play
    </Location>

</IfModule>
```

Full config:

```
    ProxyRequests Off
    ProxyPreserveHost On
    ProxyAddHeaders On
    SSLProxyEngine on

    ProxyPass / http://yourgui.com:3000/ nocanon
    ProxyPassReverse / http://yourgui.com:3000/
    SSLProxyEngine on

    <Location "/play">
        ProxyPass http://yourgui.com:5000/play nocanon
        ProxyPassReverse http://yourgui.com:5000/play
    </Location>
```
