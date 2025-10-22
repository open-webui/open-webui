export TSI_HOSTNAME=$(hostname)
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
sudo -v
fi
if [ -e .venv ] && [ "$1" != "-f" ]
then
source .venv/bin/activate
else
if [ "${TSI_HOSTNAME}" == "qemuarm64" ]
then
pip install uv==0.9.1
pip install uvicorn==0.37.0
else
pip install uv
pip install uvicorn
fi
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "qemuarm64" ];
then
uv venv
else
uv venv --python=python3.12
fi
if [ "${TSI_HOSTNAME}" == "qemuarm64" ];
then
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | sh
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
uv pip install -r backend/requirements.txt
export WEBUI_NAME="TSI WebUI"
export NODE_OPTIONS="--max-old-space-size=4096"
nvm install 20.18.1
nvm use 20.18.1
node -v
npm -v
pip install --upgrade chromadb
fi
source .venv/bin/activate
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash 
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
uv pip install -r backend/requirements.txt
export WEBUI_NAME="TSI WebUI"
nvm install 20.18.1
nvm use 20.18.1
node -v
npm -v
pip install --upgrade chromadb
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
sudo pip install portalocker
elif [ "${TSI_HOSTNAME}" == "qemuarm64" ]
then
export NODE_OPTIONS="--max-old-space-size=4096"
curl -fsSL https://ollama.com/install.sh | sh
pip install portalocker
else
pip install portalocker
fi
ln -s $(pwd)/build backend/open_webui/frontend
fi
black backend/
npm run format
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
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
  ps aux | grep $PROCESS_OPEN_WEBUI_NAME | grep -v grep | awk '{print $2}' | sudo xargs kill
else
  ps aux | grep $PROCESS_OPEN_WEBUI_NAME | grep -v grep | awk '{print $2}' | xargs kill
fi
  echo "Process '$PROCESS_OPEN_WEBUI_NAME' killed."
else
  echo "Process '$PROCESS_OPEN_WEBUI_NAME' is not running."
fi

uv run open-webui serve > open-webui.log &

