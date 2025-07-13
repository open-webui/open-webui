This tool provides you an interface to Tsavorite FPGA via a serial console

The tool consists of following files

.
├── flaskCommon.py    << Common code but currently not used
├── flaskIfc.py       << Browser based console interface to TSI device
├── flaskXterm.py     << Browser based terminal emulation
├── README.md         << Readme file
└── serial_script.py  << File with serial interface to console


The command to run to run the service on FPGA machine is
```
flask -A flaskIfc.py --debug run --port 5000
```

This command runs a webserver at port number 500

The curl command to connect to this server and communicate is as follows as 
an example

```
curl "http://localhost:5000/serial?command=cd+%20/usr/bin/tsi/v0.1.1.tsv31_06_06_2025/bin/;./run_platform_test.sh"
```

In the above command the command being run is

```
cd /usr/bin/tsi/v0.1.1.tsv31_06_06_2025/bin
./run_platform_test.sh
```

You can also get full fledged Terminal within a browser by running following

```
flask -A flaskXterm.py --debug run --port 5000
```

You can connect to this flaskTerm by doing as follows

```
http://127.0.0.1:5000/terminal
```

If your machine does not have flask terminal installed these are the typical packages you will have to install
```
sudo apt install flask
sudo pip install flask-terminal
pip install blinker
pip install flask
pip install flask-terminal
```
