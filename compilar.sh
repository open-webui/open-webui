npm install
NODE_OPTIONS=--max_old_space_size=12000  npm run build
cd backend
pip install -r requirements.txt -U --break-system-packages
