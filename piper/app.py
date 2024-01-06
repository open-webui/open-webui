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
