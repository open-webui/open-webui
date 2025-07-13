
from flask import Flask
from flask_terminal import terminal_blueprint, configure_logger
from flask import Flask, render_template, request
import serial


app = Flask(__name__)
app.logger = configure_logger('flask_terminal')

app.config['SECRET_KEY'] = 'your_secret_key_here'


@app.route('/ping')
def ping():
    app.logger.info("Accessed /ping route")
    try:
        app.logger.info("Successfully returned 'pong'")
        return 'pong', 200
    except Exception as e:
        app.logger.error(f"Error in ping route: {e}", exc_info=True)
        return "An error occurred", 500

####
## IMPLEMENT SOME SORT OF SECURITY 
## Around your application, below is an example
###
def is_authenticated():
    """Check if the user is authenticated based on a token stored in the session."""
    # Example logic for checking if a user is authenticated
    return 'user_token' in session and session['user_token'] == 'your_secure_token'

#@terminal_blueprint.before_request
#def before_request_func():
#    if not is_authenticated():
        # Redirect to login page or return an error
#        current_app.logger.info("User not authenticated, redirecting to login.")
#        return redirect('/login')  # Adjusted to use a direct path


# Register the terminal blueprint
#app.register_blueprint(terminal_blueprint, url_prefix='/terminal')

#if __name__ == '__main__':
#    app.run(port=8080)



try:
    ser = serial.Serial('/dev/ttyUSB3', 921600) # Replace /dev/ttyUSB3 with your port and baud rate
except serial.SerialException as e:
    print(f"Error opening serial port: {e}")
    ser = None # Handle case where serial port cannot be opened

@app.route('/send', methods=['POST'])
def send_data():
    if ser is None:
        return "Serial port not available", 500
    data = request.form['data'] # Get data from the form
    try:
        ser.write(data.encode()) # Convert to bytes and send
        return 'Data sent successfully'
    except serial.SerialException as e:
        return f"Error writing to serial port: {e}", 500


@app.route('/receive')
def receive_data():
    if ser is None:
        return "Serial port not available", 500
    try:
        if ser.in_waiting > 0:
            data = ser.readline().decode().strip() # Read and decode
            return data
        else:
            return "No data available"
    except serial.SerialException as e:
        return f"Error reading from serial port: {e}", 500

# Register the terminal blueprint
#app.register_blueprint(terminal_blueprint, url_prefix='/terminal')

if __name__ == '__main__':
    app.run(port=8080)

