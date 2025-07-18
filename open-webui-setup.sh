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
uv run open-webui serve

