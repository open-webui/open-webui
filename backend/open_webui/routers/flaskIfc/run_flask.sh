#!/bin/bash
sudo -v
PROCESS_FLASK_NAME="flaskIfc.py" # Flask process name 

# Get the PID of the STREAMLIT and FLASK processes
FLASKPID=$(ps aux | grep $PROCESS_FLASK_NAME | grep -v grep | awk '{print $2}')

# Check if the PID is not empty (meaning the process is running) If the process is running kill it
if [ -n "$FLASKPID" ]; then
  echo "Process '$PROCESS_FLASK_NAME' (PID: $FLASKPID) is already running. Killing it..."
  #kill -9 "$FLASKPID"
  ps aux | grep $PROCESS_FLASK_NAME | grep -v grep | awk '{print $2}' | sudo xargs kill
  echo "Process '$PROCESS_FLASK_NAME' killed."
else
  echo "Process '$PROCESS_FLASK_NAME' is not running."
fi
python3 -m venv tsi-flask
# Activate virtual envrionment
source tsi-flask/bin/activate
#install the requirements
pip install flask
pip install flask-terminal

# Run the flaskIfc server
sudo python3 flaskIfc.py 
#sudo -b flask flaskIfc.py --debug run --port 5003 --host=0.0.0.0


