export VIRTUAL_ENV=tsi-openwebui
if [ -e tsi-openwebui ]
then
source tsi-openwebui/bin/activate
else
pip install uv
uv venv tsi-openwebui
source tsi-openwebui/bin/activate
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
uv pip install -r backend/requirements.txt
pip install npm
sudo apt install npm
node -v
npm -v
nvm install 20.18.1
nvm use 20.18.1
ln -s $(pwd)/build backend/open_webui/frontend
fi
uv run open-webui serve

