from urllib.parse import quote as url_quote
from flask import Flask, render_template, request, jsonify, make_response
import subprocess
import threading
import json
import time
import os
import subprocess
import mmap
import signal
import serial
import serial_script
import re
from werkzeug.datastructures import FileStorage


job_status = {"running": False, "result": "", "thread": None}

app = Flask(__name__)

port = '/dev/ttyUSB3'
#port = '/dev/ttyUSB2'
baudrate = '921600'
#baudrate = '115200'
exe_path = "/usr/bin/tsi/v0.1.1*/bin/"

DEFAULT_MODEL = "TinyLlama:latest"
DEFAULT_BACKEND = "tSavorite"
DEFAULT_TOKEN = 12
DEFAULT_REPEAT_PENALTY = 1.5
DEFAULT_BATCH_SIZE = 1024
DEFAULT_TOP_K = 50
DEFAULT_TOP_P = 0.9
DEFAULT_LAST_N = 5
DEFAULT_CONTEXT_LENGTH = 12288
DEFAULT_TEMP = 0.0

parameters = {    'target': 'opu',
                  'num_predict': DEFAULT_TOKEN,
                  'repeat_penalty': DEFAULT_REPEAT_PENALTY,
                  'num_batch': DEFAULT_BATCH_SIZE,
                  'top_k': DEFAULT_TOP_K,
                  'top_p': DEFAULT_TOP_P,
                  'repeat_last_n': DEFAULT_LAST_N,
                  'num_ctx': DEFAULT_CONTEXT_LENGTH,
                  'temperature': DEFAULT_TEMP
                }

def is_job_running():
    if job_status['running'] == True:
        time.sleep(0.1)
    return
@app.route('/')
def index():

    serial_script.pre_and_post_check(port,baudrate)

    return render_template('index.html')

@app.route('/llama-cli', methods=['GET'])
def llama_cli_serial_command():

    serial_script.pre_and_post_check(port,baudrate)

    #./run_llama_cli.sh "my cat's name" "10" "tinyllama-vo-5m-para.gguf" "none"
    model = request.args.get('model')
    backend = request.args.get('backend')
    tokens = request.args.get('tokens')
    prompt = request.args.get('prompt')
    repeat_penalty = request.args.get('repeat-penalty', DEFAULT_REPEAT_PENALTY)
    batch_size = request.args.get('batch-size', DEFAULT_BATCH_SIZE)
    top_k = request.args.get('top-k', DEFAULT_TOP_K)
    top_p = request.args.get('top-p', DEFAULT_TOP_P)
    last_n = request.args.get('last-n', DEFAULT_LAST_N)
    context_length = request.args.get('context-length', DEFAULT_CONTEXT_LENGTH)
    temp = request.args.get('temp', DEFAULT_TEMP)

    # Define the model path (update with actual paths)
    model_paths = {
        "tiny-llama": "tinyllama-vo-5m-para.gguf",
        "Tiny-llama-F32": "Tiny-Llama-v0.3-FP32-1.1B-F32.gguf"
    }

    model_path = model_paths.get(model, "")
    if not model_path:
        model_path = model
    # Build llama-cli command
    #command = [
    #    "./llama-cli",
    #    "-p", prompt,
    #    "-m", model_path,
    #    "--device", backend,
    #    "--temp", "0",
    #    "--n-predict", tokens,
    #    "--repeat-penalty", "1",
    #    "--top-k", "0",
    #    "--top-p", "1"
    #]
    # URL to Test this end point is as follows
    # http://10.50.30.167:5001/llama-cli?model=tiny-llama&backend=tSavorite&tokens=5&prompt=Hello+How+are+you
    script_path = "./run_llama_cli.sh"
    command = f"cd {exe_path}; {script_path} \"{prompt}\" {tokens} {model_path} {backend} {repeat_penalty} {batch_size} {top_k} {top_p} {last_n} {context_length} {temp}"
    try:
        job_status['running'] = True
        result = serial_script.send_serial_command(port,baudrate,command)
        job_status['running'] = False
        return result,200
    except subprocess.CalledProcessError as e:
        return f"Error executing script: {e.stderr}", 500

UPLOAD_FOLDER = './' # Directory where recvFromHost is loaded 
destn_path='/tsi/proj/model-cache/gguf/' # Destination Directory in FPGA where uploaded files will be stored
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Create the upload folder if it doesn't exist

def read_cmd_from_serial(port,baudrate,command):
    job_status['running'] = True
    temp = serial_script.send_serial_command(port,baudrate,command) 
    print(temp)
    job_status['running'] = False

@app.route('/delete-file', methods=['POST', 'GET'])
def delete_file():

    serial_script.pre_and_post_check(port,baudrate)

    if request.method == 'POST':
        
        d_path = request.form.get("deletion_file_path")
        filename = request.form.get("file_name")
        command = f"cd {d_path}; rm {filename}"
        read_cmd_from_serial(port,baudrate,command)
        return 'Done'
    return render_template('delete.html')

@app.route('/upload-gguf', methods=['POST', 'GET'])
def upload_serial_command():

    serial_script.pre_and_post_check(port,baudrate)

    if request.method == 'POST':
        # Check if a file was submitted
        if 'file' not in request.files:
            return "No file part"
        file = request.files['file']

        # Check if the file is empty
        if file.filename == '':
            return "No file selected"

        # Save the file if it exists
        if file:
            filename = file.filename #secure_filename(file.filename)
            process = subprocess.Popen(["./copy2fpga-x86.sh", filename], text=True)
            copy2fpgax86prints = "Starting copy2fpga-x86 and sending file..."
            print (copy2fpgax86prints)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            time.sleep(3)
            script_path = "./recvFromHost "
            command = f"cd {exe_path}; {script_path} {destn_path}{filename}"
            def scriptRecvFromHost():
                 try:
                     result = serial_script.send_serial_command(port,baudrate,command)
                     job_status["result"] = result
                     print(result)
                     recv_output = result
                 except subprocess.CalledProcessError as e:
                     job_status["result"] = f"Error: {e.stderr}"
                 finally:
                     job_status["running"] = False
            thread = threading.Thread(target=scriptRecvFromHost)
            job_status = {"running": True, "result": "", "thread": thread}
            thread.start()
            thread.join()
            stdout, stderr = process.communicate()
        
        read_cmd_from_serial(port,baudrate,f"cd {destn_path}; ls -lt")

        return render_template('uploadtofpga.html', apple = process, recvoutput=f"On FPGA Target, recvFromHost completed ; transfered file:{filename} received")
    return render_template('upload.html') # Display the upload form

def actual_transfer(file):
    # Check if the file is empty
        if file.filename == '':
            return "No file selected"

        # Save the file if it exists
        if file:
            filename = file.filename #secure_filename(file.filename)
            process = subprocess.Popen(["./copy2fpga-x86.sh", filename], text=True)
            copy2fpgax86prints = "Starting copy2fpga-x86 and sending file..."
            print (copy2fpgax86prints)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            time.sleep(3)
            script_path = "./recvFromHost "
            command = f"cd {exe_path}; {script_path} {destn_path}{filename}"
            def scriptRecvFromHost():
                 try:
                     result = serial_script.send_serial_command(port,baudrate,command)
                     job_status["result"] = result
                     print(result)
                     recv_output = result
                 except subprocess.CalledProcessError as e:
                     job_status["result"] = f"Error: {e.stderr}"
                 finally:
                     job_status["running"] = False
            thread = threading.Thread(target=scriptRecvFromHost)
            job_status = {"running": True, "result": "", "thread": thread}
            thread.start()
            thread.join()
            stdout, stderr = process.communicate()
        time.sleep(1)
        read_cmd_from_serial(port,baudrate,f"cd {destn_path}; ls -lt")
        time.sleep(1)

@app.route('/api/receive', methods=['GET', 'POST'])
def receive_pull_model():
    data = request.get_json()
    path = "/usr/share/ollama/.ollama/models/blobs/" + data['actual_name']
    file_obj = open(path, "rb")
    upload = FileStorage(stream=file_obj, filename=data['actual_name'], content_type="application/octet-stream")

    actual_transfer(upload)

    return manual_response(content="File Download Done",thinking="File Download Done",), 200


#    command = f"upload file"
#    try:
#        result = subprocess.run(['python3', 'serial_script.py', port, baudrate, command], capture_output=True, text=True, check=True)
#        return result.stdout, 200
#    except subprocess.CalledProcessError as e:
#        return f"Error executing script: {e.stderr}", 500




@app.route('/upload-file', methods=['GET', 'POST'])
def upload_file():

    serial_script.pre_and_post_check(port,baudrate)

    if request.method == 'POST':
        # Check if a file was submitted
        if 'file' not in request.files:
            return "No file part"
        file = request.files['file']

        # Check if the file is empty
        if file.filename == '':
            return "No file selected"

        # Save the file if it exists
        if file:
            filename = secure_filename(file.filename)
            process = subprocess.Popen(["./copy2fpga-x86.sh", filename], text=True)
            copy2fpgax86prints = "Starting copy2fpga-x86 and sending file..."
            print (copy2fpgax86prints)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

            script_path = "./recvFromHost "
            temporary_destination_path = request.form.get("destination_file_path") # I've tested this on fpga4 and it correctly gets the user-inputted file path
            command = f"cd {exe_path}; {script_path} {temporary_destination_path}{filename}" 
            def scriptRecvFromHost():
                 try:
                     result = serial_script.send_serial_command(port,baudrate,command)
                     job_status["result"] = result
                     
                     print(result)
                     
                     recv_output = result
                 except subprocess.CalledProcessError as e:
                     job_status["result"] = f"Error: {e.stderr}"
                 finally:
                     job_status["running"] = False
            thread = threading.Thread(target=scriptRecvFromHost)
            job_status = {"running": True, "result": "", "thread": thread}
            thread.start()
            thread.join()
            stdout, stderr = process.communicate()
        
        read_cmd_from_serial(port,baudrate,f"cd {temporary_destination_path}; ls -lt")
        
        return render_template('uploadtofpga.html', apple = process, recvoutput=f'On FPGA Target, recvFromHost completed ; transfered file:{filename} received ')
    return render_template('upload.html') # Display the upload form

def internal_restart_txe():
    command = f"cd /tsi/fpga_card/latest_sof_release; sudo make all; make juart"

    process = subprocess.Popen([command],shell=True,preexec_fn=os.setsid,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,bufsize=1,text=True)
    


    
    start = time.time()
    try:
        for line in process.stdout:
            print("HOST:" + line)
            if "Global Reset exercised" in line:
                time.sleep(2)
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                break
            current = time.time()
            if current - start >= 1000:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except Exception as e:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    finally:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    process.wait()
    
    
    serial_script.restart_txe_serial_portion(port,baudrate,exe_path) 
    

    print("Finished Everything Hooray")

@app.route('/restart-txe', methods=['GET'])
def restart_txe_serial_command():

    serial_script.pre_and_post_check(port,baudrate)

    internal_restart_txe()

    return "Done"

    


    

@app.route('/health-check', methods=['GET'])
def health_check_serial_command():

    serial_script.pre_and_post_check(port,baudrate)

    command = f"free -h; df -h; top -b -n1"

    try:
        result = serial_script.send_serial_command(port,baudrate,command)
        return result, 200
    except subprocess.CalledProcessError as e:
        return f"Error executing script: {e.stderr}", 500

@app.route('/test', methods=['GET'])
def test_serial_command():
    
    serial_script.pre_and_post_check(port,baudrate)
    
    command = f"test"

    try:
        result = serial_script.send_serial_command(port,baudrate,command)
        return result, 200
    except subprocess.CalledProcessError as e:
        return f"Error executing script: {e.stderr}", 500

@app.route('/system-info', methods=['GET'])
def system_info_serial_command():

    serial_script.pre_and_post_check(port,baudrate)

    command = f"{exe_path}../install/tsi-version;lsmod; lscpu; lsblk"

    try:
        result = serial_script.send_serial_command(port,baudrate,command)
        return result, 200
    except subprocess.CalledProcessError as e:
        return f"Error executing script: {e.stderr}", 500

def manual_response(status="success",model="ollama",content=None,thinking=None,tool_calls=None,openai_tool_calls=None,name="Alice",id="12345",email="alice@example.com",role="admin",some_key="some_value",profile_data=None):
    json_string ={
            "status": status,
            "model": model,
            "message": {
                "content": content,
                "thinking": thinking,
                "tool_calls": tool_calls,
                "openai_tool_calls": openai_tool_calls,
                "meta": profile_data
                },
            "user": {
                "name": name,
                "id": id,
                "email": email,
                "role": role
                },
            "data": {
                "some_key": some_key,
                "profile_data": profile_data
                },
            "done": True #This is to indicate that we are one command at a time, not interactive
            }
    print("Response:\n", json.dumps(json_string), "\n")
    response = make_response(json.dumps(json_string))
    response.headers["Content-Type"] = "application/json"
    return response

def clean_up_json_string(string):
    # 1️⃣ Extract just the JSON-looking portion
    match = re.search(r'\{.*?\}', string)
    if match:
        json_candidate = match.group(0)

        # 2️⃣ Replace escape sequences
        cleaned = json_candidate.encode('utf-8').decode('unicode_escape')

        # 3️⃣ Load and parse JSON
        try:
            parsed = json.loads(cleaned)
            #print(json.dumps(parsed, indent=2))
            return parsed
        except json.JSONDecodeError as e:
            #print("JSON parsing failed:", e)
            return cleaned
    else:
        #print("No JSON object found")
        return string

def extract_final_output_after_chat_history(text):
    chat_history_phrase = "</chat_history>"
    if chat_history_phrase in text:
        #parts = text.split(chat_history_phrase)
        #filtered_text = parts[-1]  # content after the last tag
        filtered_text = text.split(chat_history_phrase, 1)[1] # Split once and take the second part
    else:
        filtered_text = text
    return filtered_text

def extract_chat_history(text):
    chat_history_phrase = "Chat History:"
    if chat_history_phrase in text:
        #parts = text.split(chat_history_phrase)
        #filtered_text = parts[-1]  # content after the last tag
        filtered_text = text.split(chat_history_phrase, 1)[1] # Split once and take the second part
    else:
        filtered_text = text
    return filtered_text

def extract_json_output(text):
    start_phrase = "JSON format:"
    if start_phrase in text:
        #parts = text.split(start_phrase)
        #filtered_text = parts[-1]  # content after the last tag
        filtered_text = text.split(start_phrase, 1)[1] # Split once and take the second part
    else:
        filtered_text = text
    return clean_up_json_string(filtered_text)

@app.route('/_app', methods=['POST', 'GET'])
@app.route('/api/chats', methods=['POST', 'GET'])
def chats():
    global job_status
    global parameters

    serial_script.pre_and_post_check(port,baudrate)
    
    data = request.get_json()
    if 'options' in data:
        for item in parameters:
            if item in data['options']:
                parameters[item] = data['options'][item]

    original_prompt = data['messages'][-1]['content']
    flattened_prompt = re.sub(r'\s+', ' ', original_prompt).strip()
    tmpprompt = flattened_prompt.replace('"', '\\"').encode('utf-8')
    prompt = tmpprompt.decode('utf-8')

    model = DEFAULT_MODEL

    if parameters['target'] == 'cpu':
        backend = 'none'
    elif parameters['target'] == 'opu':
        backend = 'tSavorite'
    if 'model' in data:
        model = data['model']

    tokens = parameters['num_predict']
    repeat_penalty = parameters['repeat_penalty']
    batch_size = parameters['num_batch']
    top_k = parameters['top_k']
    top_p = parameters['top_p']
    last_n = parameters['repeat_last_n']
    context_length = parameters['num_ctx']
    temp = parameters['temperature']
    
    # Define the model path (update with actual paths)
    model_paths = {
        "tiny-llama": "tinyllama-vo-5m-para.gguf",
        "TinyLlama:latest": "Tiny-Llama-v0.3-FP32-1.1B-F32.gguf"
    }
    model_path = model_paths.get(model, "")
    if not model_path:
        model_path = model
    # Build llama-cli command
    #command = [
    #    "./llama-cli",
    #    "-p", prompt,
    #    "-m", model_path,
    #    "--device", backend,
    #    "--temp", "0",
    #    "--n-predict", tokens,
    #    "--repeat-penalty", "1",
    #    "--top-k", "0",
    #    "--top-p", "1"
    #]
    script_path = "./run_llama_cli.sh"
    command = f"cd {exe_path}; {script_path} \"{prompt}\" {tokens} {model_path} {backend} {repeat_penalty} {batch_size} {top_k} {top_p} {last_n} {context_length} {temp}"
    def run_script(command):
        try:
            is_job_running()
            job_status["running"] = True
            result = serial_script.send_serial_command(port,baudrate,command)
            if result:
                response_text = result
                start_phrase = "llama_perf_sampler_print: "
                if start_phrase in response_text:
                    filtered_text = response_text.split(start_phrase, 1)[0] # Split once and drop the second part
                    formatted_text = response_text.split(start_phrase, 1)[1]
                else:
                    filtered_text = result
            else:
                filtered_text = "Result Empty: Desired phrase not found in the response."
                job_status["result"] = filtered_text

            job_status["running"] = False
            return filtered_text, formatted_text
        except subprocess.CalledProcessError as e:
            filtered_text = f"Error: {e.stderr}"
            job_status["result"] = filtered_text
            job_status["running"] = False
        return filtered_text, formatted_text

    filtered_text, profile_text = run_script(command)
    extracted_json = extract_json_output(filtered_text)
    chat_history = extract_chat_history(filtered_text)
    final_chat_output = extract_final_output_after_chat_history(chat_history)
    return manual_response(content=final_chat_output,thinking=chat_history,profile_data=profile_text), 200

@app.route('/api/chat', methods=['POST', 'GET'])
@app.route('/api/chat/completion', methods=['POST', 'GET'])
@app.route('/api/chat/completed', methods=['POST', 'GET'])
@app.route('/api/generate', methods=['POST', 'GET'])
def chat():
    global job_status
    global parameters

    serial_script.pre_and_post_check(port,baudrate)
    
    data = request.get_json()

    if 'options' in data:
        for item in parameters:
            if item in data['options']:
                parameters[item] = data['options'][item]

    original_prompt = data['messages'][-1]['content']
    flattened_prompt = re.sub(r'\s+', ' ', original_prompt).strip()
    tmpprompt = flattened_prompt.replace('"', '\\"').encode('utf-8')
    prompt = tmpprompt.decode('utf-8')
      
    model = DEFAULT_MODEL

    if parameters['target'] == 'cpu':
        backend = 'none'
    elif parameters['target'] == 'opu':
        backend = 'tSavorite'
    if 'model' in data:
        model = data['model']

    tokens = parameters['num_predict']
    repeat_penalty = parameters['repeat_penalty']
    batch_size = parameters['num_batch']
    top_k = parameters['top_k']
    top_p = parameters['top_p']
    last_n = parameters['repeat_last_n']
    context_length = parameters['num_ctx']
    temp = parameters['temperature']
    
    # Define the model path (update with actual paths)
    model_paths = {
        "tiny-llama": "tinyllama-vo-5m-para.gguf",
        "TinyLlama:latest": "Tiny-Llama-v0.3-FP32-1.1B-F32.gguf"
    }
    model_path = model_paths.get(model, "")
    if not model_path:
        model_path = model
    # Build llama-cli command
    #command = [
    #    "./llama-cli",
    #    "-p", prompt,
    #    "-m", model_path,
    #    "--device", backend,
    #    "--temp", "0",
    #    "--n-predict", tokens,
    #    "--repeat-penalty", "1",
    #    "--top-k", "0",
    #    "--top-p", "1"
    #]
    script_path = "./run_llama_cli.sh"
    command = f"cd {exe_path}; {script_path} \"{prompt}\" {tokens} {model_path} {backend} {repeat_penalty} {batch_size} {top_k} {top_p} {last_n} {context_length} {temp}"
    def run_script(command):
        try:
            is_job_running()
            job_status["running"] = True
            result = serial_script.send_serial_command(port,baudrate,command)
            if result:
                response_text = result
                start_phrase = "llama_perf_sampler_print: "
                if start_phrase in response_text:
                    filtered_text = response_text.split(start_phrase, 1)[0] # Split once and drop the second part
                    formatted_text = response_text.split(start_phrase, 1)[1]
                else:
                    filtered_text = result
                    formatted_text = None
            else:
                filtered_text = "Result Empty: Desired phrase not found in the response."
                job_status["result"] = filtered_text

            job_status["running"] = False
            return filtered_text, formatted_text
        except subprocess.CalledProcessError as e:
            filtered_text = f"Error: {e.stderr}"
            job_status["result"] = filtered_text
            job_status["running"] = False
        return filtered_text, formatted_text

    filtered_text, profile_text = run_script(command)
    extracted_json = extract_json_output(filtered_text)
    chat_history = extract_chat_history(filtered_text)
    final_chat_output = extract_final_output_after_chat_history(chat_history)
    
    return manual_response(content=final_chat_output,thinking=chat_history,profile_data=profile_text), 200

@app.route('/api/restart-txe', methods=['GET', 'POST'])
def restart_txe_ollama_serial_command():
    global job_status
    global parameters
    serial_script.pre_and_post_check(port,baudrate)
    internal_restart_txe()
    
    return manual_response(content="Restarted OPU",thinking="Restarted OPU"), 200

@app.route('/api/system-info', methods=['GET', 'POST'])
def system_info_ollama_serial_command():
    result, error = system_info_serial_command()
    return manual_response(content=result,thinking="System Info"), error

@app.route('/api/health-check', methods=['GET', 'POST'])
def health_check_ollama_serial_command():
    result, error = health_check_serial_command()
    return manual_response(content=result,thinking="Health Check"), error

def aborttask():
    try:
        result = serial_script.abort_serial_portion(port,baudrate)
        return result, 200
    except subprocess.CalledProcessError as e:
        return f"Error executing script: {e.stderr}", 500

@app.route('/api/abort-task', methods=['GET', 'POST'])
def abort_task_ollama_serial_command():
    result, error = aborttask()
    return manual_response(content=result,thinking="Abort Task"), error

@app.route('/submit', methods=['POST'])
def submit():

    serial_script.pre_and_post_check(port,baudrate)

    global job_status

    if job_status["running"]:
        return "<h2>A model is already running. Please wait or abort.</h2>"

    #./run_llama_cli.sh "my cat's name" "10" "tinyllama-vo-5m-para.gguf" "none"
    model = request.form.get('model')
    backend = request.form.get('backend')
    tokens = request.form.get('tokens')
    prompt = request.form.get('prompt')
    repeat_penalty = request.form.get('repeat-penalty', DEFAULT_REPEAT_PENALTY)
    batch_size = request.form.get('batch-size', DEFAULT_BATCH_SIZE)
    top_k = request.form.get('top-k', DEFAULT_TOP_K)
    top_p = request.form.get('top-p', DEFAULT_TOP_P)
    last_n = request.form.get('last-n', DEFAULT_LAST_N)
    context_length = request.form.get('context-length', DEFAULT_CONTEXT_LENGTH)
    temp = request.form.get('temp', DEFAULT_TEMP)

    # Define the model path (update with actual paths)
    model_paths = {
        "tiny-llama": "tinyllama-vo-5m-para.gguf",
        "Tiny-llama-F32": "Tiny-Llama-v0.3-FP32-1.1B-F32.gguf"
    }

    model_path = model_paths.get(model, "")
    if not model_path:
        model_path = model

    # Build llama-cli command
    #command = [
    #    "./llama-cli",
    #    "-p", prompt,
    #    "-m", model_path,
    #    "--device", backend,
    #    "--temp", "0",
    #    "--n-predict", tokens,
    #    "--repeat-penalty", "1",
    #    "--top-k", "0",
    #    "--top-p", "1"
    #]

    script_path = "./run_llama_cli.sh"
    command = f"cd {exe_path}; {script_path} \"{prompt}\" {tokens} {model_path} {backend} {repeat_penalty} {batch_size} {top_k} {top_p} {last_n} {context_length} {temp}"

    def run_script():
        try:
            result = serial_script.send_serial_command(port,baudrate,command)
            job_status["result"] = result
        except subprocess.CalledProcessError as e:
            job_status["result"] = f"Error: {e.stderr}"
        finally:
            time.sleep(max(10,int(tokens)/5))
            job_status["running"] = False

    thread = threading.Thread(target=run_script)
    job_status = {"running": True, "result": "", "thread": thread}
    thread.start()

    return render_template("processing.html")


@app.route('/status')
def status():

    serial_script.pre_and_post_check(port,baudrate)

    if job_status["running"]:
        return "running"
    else:
        return "done"

@app.route('/result')
def result():
    
    return render_template("result.html", output=job_status["result"])


'''
Need to revert to an older version of Werkzeug to work!:

sudo python3 -m venv flasktest
source flasktest/bin/activate
sudo pip install "Werkzeug<3.0"

MISC. INFORMATION:

Takes around 2 minutes and 10 seconds to fully complete
At the end you should see the message: Finished Everything Hooray

'''
@app.route('/abort')
def abort():

    global job_status

    if job_status["running"] and job_status["thread"].is_alive():
        # Use subprocess.Popen + pid handling instead for real process termination
        job_status["running"] = False
        job_status["result"] = "Aborted by user."
        serial_script.abort_serial_portion(port,baudrate)
        internal_restart_txe()
        return "<h2>Job aborted.</h2><a href='/'>Home</a>"
    return "<h2>No job running.</h2><a href='/'>Home</a>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)

