import serial
import sys
import time
import portalocker

SERIAL_LOCK_FILE = "./serial_port.lock"  # Use a lock file 
exe_path = "/usr/bin/tsi/v0.1.1*/bin/"

TXE_HOST = "localhost"
TXE_PORT = 8000
TXE_PROMPT = "tsi_apc_prompt>"
TXE_CLOSE_COMMAND = "close all"
LINUX_LOGGED_IN_PROMPT = "@agilex7_dk_si_agf014ea"
LINUX_LOGIN_PROMPT = "agilex7_dk_si_agf014ea"
def is_lock_available():
    try:
        with open(SERIAL_LOCK_FILE, 'w') as lock_fp:
            portalocker.lock(lock_fp, portalocker.LOCK_EX | portalocker.LOCK_NB)
            portalocker.unlock(lock_fp)
        return True  # Lock was successfully acquired
    except portalocker.exceptions.LockException:
        return False  # Lock is already held by another process

def check_for_specific_prompt(ser, timeout=10, prompt=LINUX_LOGGED_IN_PROMPT):
    # Wait to read the serial port
    data = '\0'
    first_time = 1
    ser.timeout = timeout
    start = time.time()
    while time.time() - start < timeout:
        try:
            # read byte by byte to find either a new line character or a prompt marker
            # instead of new line using line = ser.readline()
            line = b""
            while time.time() - start < timeout:
                byte = ser.read(1)  # Read one byte at a time
                line += byte
                if (byte == b"\n") or (byte == b"#") or (byte == b">"):  # Stop when delimiter is found
                    break
            if line: # Check if line is not empty
                try:
                    read_next_line = line.decode('utf-8', errors='replace')
                except UnicodeDecodeError as e:
                    print("Decoding error:", e, "Raw line:", line)
                if (prompt in read_next_line.strip()):
                    return True
            else:
                return False

        except serial.SerialException as e:
            return False
        except KeyboardInterrupt:
            return False
    return False

def check_for_prompt(ser, timeout=10):
    # Wait to read the serial port
    data = '\0'
    first_time = 1
    ser.timeout = timeout
    start = time.time()
    while time.time() - start < timeout:
        try:
            # read byte by byte to find either a new line character or a prompt marker
            # instead of new line using line = ser.readline()
            line = b""
            while time.time() - start < timeout:
                byte = ser.read(1)  # Read one byte at a time
                line += byte
                if (byte == b"\n") or (byte == b"#") or (byte == b">"):  # Stop when delimiter is found
                    break
            if line: # Check if line is not empty
                try:
                    read_next_line = line.decode('utf-8', errors='replace')
                except UnicodeDecodeError as e:
                    print("Decoding error:", e, "Raw line:", line)
                if ("run-platform-done" in read_next_line.strip()) or \
                        ("SOCFPGA_AGILEX7 " in read_next_line.strip()) or \
                        ("Unknown command " in read_next_line.strip()) or \
                        (LINUX_LOGGED_IN_PROMPT in read_next_line.strip()) or \
                        ("imx8mpevk" in read_next_line.strip()):
                    return True

                if TXE_PROMPT in read_next_line.strip():
                    ser.write(b'exit\n')
                    time.sleep(3)
                    return True

                if '(Yocto Project Reference Distro) 5.2.' in read_next_line.strip() and LINUX_LOGIN_PROMPT in read_next_line.strip():
                    time.sleep(3)
                    ser.write(b'root\n')
                    return True

                if (first_time == 1) :
                    first_time = 0
                else:
                    if 'read in progress' not in read_next_line:
                        data += (read_next_line.strip() + '\n')  # Keep the line as-is with newline
            else:
                break  # Exit loop if no data is received

        except serial.SerialException as e:
            return False 
        except KeyboardInterrupt:
            return False
    return False

def login_to_txe_mgr_and_send_close_all(ser):
    ser.write(f"telnet {TXE_HOST} {TXE_PORT}\n".encode())
    if not check_for_specific_prompt(ser, timeout=3, prompt=TXE_PROMPT):
        return None
    ser.write(f"{TXE_CLOSE_COMMAND}\n".encode())

def clean_up_after_abort(ser):
    print("Sending Ctrl-C to abort current task...")
    ser.write(b'\x03')
    ser.write(b'\x03')
    ser.flush()

    if not check_for_prompt(ser, 10):
        if not check_for_specific_prompt(ser, timeout=3, prompt=TXE_PROMPT):
            print("Error: TXE Manager prompt not detected, likely not running")
        else:
            print("Warning: TXE Manager prompt detected sending close all")
            login_to_txe_mgr_and_send_close_all(ser)
            if not check_for_prompt(ser, 3):
                print("Warning: TXE Manager did not respond to 'close all'.")
    else:
        login_to_txe_mgr_and_send_close_all(ser)
        if not check_for_prompt(ser, 3):
            print("Warning: TXE Manager did not respond to 'close all'.")

    ser.write(b'cd /usr/bin/tsi/v0.1.1*/bin/\n')
    ser.flush()
    ser.write(b'../install/tsi-start\n')
    ser.flush()

    print("TXE Manager cleanup and restart successful.")
    return True

def abort_serial_portion(port,baudrate):
   
    while is_lock_available() != True:
        time.sleep(1)
    with open(SERIAL_LOCK_FILE, 'w') as lock_fp:
        # Try to acquire an exclusive lock
        portalocker.lock(lock_fp, portalocker.LOCK_EX)

        try:
            ser = serial.Serial(port, baudrate)
            ser.reset_output_buffer()
            ser.reset_input_buffer()

            ser.write(b'\x03') # b'\x03' is Ctrl-C! 

            clean_up_after_abort(ser)

            ser.close()
        finally:
            # Always release the lock
            portalocker.unlock(lock_fp)


def explicit_boot_command(port,baudrate):
    if is_lock_available() != True:
        return None

    ser = serial.Serial(port,baudrate)

    time.sleep(2)

    ser.write(b'boot\n')

    ser.close()

def explicit_root_command(port,baudrate,path):
    if is_lock_available() != True:
        return None
    
    timeout = 180  # seconds
    ser = serial.Serial(port,baudrate)
    start_time = time.time()

    while True:
        if (time.time() - start_time >= timeout):
            break
        if is_lock_available() != True:
            ser.close()
            return None
        line = ser.readline().decode('utf-8', errors='replace').strip()
        print("SERIAL/TARGET:" + line)
        if line:
            #print(f"Received: {line}")
            if '(Yocto Project Reference Distro) 5.2.' in line and LINUX_LOGIN_PROMPT in line:
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

DEFAULT_COMMAND_TIMEOUT=7200

def send_serial_command(port, baudrate, command, timeout=DEFAULT_COMMAND_TIMEOUT):
    if is_lock_available() != True:
        return None

    try:
        ser = serial.Serial(port, baudrate)
        ser.reset_output_buffer()
        ser.reset_input_buffer()
        ser.write((command + '\n').encode())  # Send command with newline '\n'
        ser.flush()
        # Wait to read the serial port
        data = '\0'
        first_time = 1
        start = time.time()
        while time.time() - start < timeout:
            try:
                # read byte by byte to find either a new line character or a prompt marker
                # instead of new line using line = ser.readline()
                line = b""
                while time.time() - start < timeout:
                    if is_lock_available() != True:
                        ser.close()
                        return data
                    byte = ser.read(1)  # Read one byte at a time
                    line += byte
                    if ("File receive completed" in line.decode('utf-8', errors='ignore')):
                        ser.close()
                        return data
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
                            (LINUX_LOGGED_IN_PROMPT in read_next_line.strip()) or \
                            ("imx8mpevk" in read_next_line.strip()):
                        break
                    if (first_time == 1) :
                        first_time = 0
                    else:
                        if not any(keyword in read_next_line for keyword in ['read in progress', 'tSavorite']):
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
    if is_lock_available() != True:
        return None

    flag = ['ok']
    ser = serial.Serial(port, baudrate)

    ser.write(('trash' + '\n').encode())
    time.sleep(0.1)
    ser.write(('trash' + '\n').encode())
    while True:
        line = b""
        while True:
            if is_lock_available() != True:
                ser.close()
                return line
            try:
                byte = ser.read(1)  # Read one byte at a time
                if (byte == b"\n") or (byte == b"#"):  # Stop when delimiter is found
                    break
                
                line += byte
            except serial.SerialException as e:
                ser.close()
                return (f"Error reading from serial port: {e}")
            except KeyboardInterrupt:
                ser.close()
                return ("Program interrupted by user")

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
    
