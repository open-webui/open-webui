if [ -e .venv ] && [ "$1" != "-f" ]
then
source .venv/bin/activate
else
pip install uv
uv venv
source .venv/bin/activate
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
uv pip install -r backend/requirements.txt
pip install npm
node -v
npm -v
export WEBUI_NAME="TSI WebUI"
nvm install 20.18.1
nvm use 20.18.1
pip install --upgrade chromadb
ln -s $(pwd)/build backend/open_webui/frontend
fi
cd backend/open_webui/routers/flaskIfc
./run_flask.sh > flask.log &
cd -

PROCESS_OPEN_WEBUI_NAME="open-webui" # Flask process name

# Get the PID of the OPEN_WEBUI processes
OPEN_WEBUIPID=$(ps aux | grep $PROCESS_OPEN_WEBUI_NAME | grep -v grep | awk '{print $2}')

# Check if the PID is not empty (meaning the process is running) If the process is running kill it
if [ -n "$OPEN_WEBUIPID" ]; then
  echo "Process '$PROCESS_OPEN_WEBUI_NAME' (PID: $OPEN_WEBUIPID) is already running. Killing it..."
  #kill -9 "$OPEN_WEBUIPID"
  ps aux | grep $PROCESS_OPEN_WEBUI_NAME | grep -v grep | awk '{print $2}' | sudo xargs kill
  echo "Process '$PROCESS_OPEN_WEBUI_NAME' killed."
else
  echo "Process '$PROCESS_OPEN_WEBUI_NAME' is not running."
fi

uv run open-webui serve > open-webui.log &

