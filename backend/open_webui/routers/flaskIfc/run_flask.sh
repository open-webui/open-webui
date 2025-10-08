#!/bin/bash
export TSI_HOSTNAME=$(hostname)
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
sudo -v
fi
PROCESS_FLASK_NAME="flaskIfc.py" # Flask process name 

# Get the PID of the STREAMLIT and FLASK processes
FLASKPID=$(ps aux | grep $PROCESS_FLASK_NAME | grep -v grep | awk '{print $2}')

# Check if the PID is not empty (meaning the process is running) If the process is running kill it
if [ -n "$FLASKPID" ]; then
  echo "Process '$PROCESS_FLASK_NAME' (PID: $FLASKPID) is already running. Killing it..."
  #kill -9 "$FLASKPID"
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
  ps aux | grep $PROCESS_FLASK_NAME | grep -v grep | awk '{print $2}' | sudo xargs kill
else
  ps aux | grep $PROCESS_FLASK_NAME | grep -v grep | awk '{print $2}' | xargs kill
fi
  echo "Process '$PROCESS_FLASK_NAME' killed."
else
  echo "Process '$PROCESS_FLASK_NAME' is not running."
fi
python3 -m venv tsi-flask
# Activate virtual envrionment
source tsi-flask/bin/activate
#install the requirements
pip install pyserial
pip install flask
pip install flask-terminal
pip install portalocker
pip install paramiko
pip3 install scp
# Run the flaskIfc server
if [ "${TSI_HOSTNAME}" == "fpga1.tsavoritesi.net" ] || [ "${TSI_HOSTNAME}" == "fpga2.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga3.tsavoritesi.net" ]  || [ "${TSI_HOSTNAME}" == "fpga4.tsavoritesi.net" ];
then
sudo python3 flaskIfc.py &
else
python3 flaskIfc.py &
fi
#flask -A flaskXterm.py --debug run --port 5000 --host 0.0.0.0  --cert=../../../../cert.pem --key=../../../../key.pem &
#sudo -b flask flaskIfc.py --debug run --port 5003 --host=0.0.0.0

