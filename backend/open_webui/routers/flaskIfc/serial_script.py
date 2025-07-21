import serial
import sys
import time
#This is just a test to see if I can make changes on my local machine and copy them over to fpga4! Thank you!
#It worked! Thank you!

def abort_serial_portion(port,baudrate):
    ser = serial.Serial(port, baudrate)

    ser.write(b'\x03') # b'\x03' is Ctrl-C! 

    ser.close()

def explicit_boot_command(port,baudrate):

    ser = serial.Serial(port,baudrate)

    time.sleep(2)

    ser.write(b'boot\n')

    ser.close()

def explicit_root_command(port,baudrate,path):
    
    timeout = 180  # seconds
    ser = serial.Serial(port,baudrate)
    start_time = time.time()

    while True:
        if (time.time() - start_time >= timeout):
            break
        line = ser.readline().decode('utf-8', errors='replace').strip()
        print("SERIAL/TARGET:" + line)
        if line:
            #print(f"Received: {line}")
            if '(Yocto Project Reference Distro) 5.2.' in line and 'agilex7_dk_si_agf014ea' in line:
                time.sleep(3)
                ser.write(b'root\n')
                break

    ser.close()


def restart_txe_serial_portion(port, baudrate, path):

    explicit_boot_command(port,baudrate)

    explicit_root_command(port,baudrate,path)

    ser = serial.Serial(port,baudrate)

    time.sleep(3)

    ser.write(('cd ' + path + '\n').encode())

    time.sleep(3)

    ser.close()

def send_serial_command(port, baudrate, command):
    try:
        ser = serial.Serial(port, baudrate)
        ser.reset_output_buffer()
        ser.reset_input_buffer()
        ser.write((command + '\n').encode())  # Send command with newline '\n'
        ser.flush()
        # Wait to read the serial port
        data = '\0'
        first_time = 1
        while True:
            try:
                # read byte by byte to find either a new line character or a prompt marker
                # instead of new line using line = ser.readline()
                line = b""
                while True:
                    byte = ser.read(1)  # Read one byte at a time
                    line += byte
                    if (byte == b"\n") or (byte == b"#"):  # Stop when delimiter is found
                        break
                if line: # Check if line is not empty
                    try:
                        read_next_line = line.decode('utf-8', errors='replace')
                    except UnicodeDecodeError as e:
                        print("Decoding error:", e, "Raw line:", line)
                    if ("run-platform-done" in read_next_line.strip()) or \
                            ("SOCFPGA_AGILEX7 " in read_next_line.strip()) or \
                            ("Unknown command " in read_next_line.strip()) or \
                            ("@agilex7_dk_si_agf014ea" in read_next_line.strip()) or \
                            ("imx8mpevk" in read_next_line.strip()):
                        break
                    if (first_time == 1) :
                        first_time = 0
                    else:
                        if 'read in progress' not in read_next_line:
                            data += (read_next_line.strip() + '\n')  # Keep the line as-is with newline
                else:
                    break  # Exit loop if no data is received
                
            except serial.SerialException as e:
                ser.close()
                return (f"Error reading from serial port: {e}")
            except KeyboardInterrupt:
                ser.close()
                return ("Program interrupted by user")
        ser.close()
        return data

    except serial.SerialException as e:
        ser.close()
        return f"Error: {e}"

def pre_and_post_check(port,baudrate):
    flag = ['ok']
    ser = serial.Serial(port, baudrate)

    ser.write(('trash' + '\n').encode())
    time.sleep(0.1)
    ser.write(('trash' + '\n').encode())
    while True:
        line = b""
        while True:
            byte = ser.read(1)  # Read one byte at a time
            if (byte == b"\n") or (byte == b"#"):  # Stop when delimiter is found
                break
                
            line += byte
        if 'ogin incorrec' in line.decode('utf-8', errors='replace'):
            time.sleep(0.1)
            flag[0] = 'root issue'
            break
        elif 'nknown command \'trash\'' in line.decode('utf-8', errors='replace'):
            time.sleep(0.1)
            flag[0] = 'boot issue'
            break
        elif 'trash: command' in line.decode('utf-8', errors='replace'):
            time.sleep(0.1)
            break
    ser.close()
    if flag[0] == 'root issue':
        ser = serial.Serial(port, baudrate)
        time.sleep(0.1)
        ser.write(('root' + '\n').encode())
        time.sleep(0.1)
        ser.close()
    elif flag[0] == 'boot issue':
        explicit_boot_command(port,baudrate)
        explicit_root_command(port,baudrate,'anything')


# This script can be run in standalone as well
if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[3] == 'abort':
        port = sys.argv[1]
        baudrate = int(sys.argv[2])
        abort_serial_portion(port,baudrate)
        sys.exit(1)
    if len(sys.argv) == 5 and sys.argv[3] == 'restart':
        port = sys.argv[1]
        baudrate = int(sys.argv[2])
        path = sys.argv[4]
        restart_txe_serial_portion(port, baudrate,path)
        sys.exit(1)
    if len(sys.argv) < 4:
        print("Usage: python script.py <port> <baudrate> <command>")
        sys.exit(1)

    port = sys.argv[1]
    baudrate = int(sys.argv[2])
    command = sys.argv[3]
    response = send_serial_command(port, baudrate, command)
    
