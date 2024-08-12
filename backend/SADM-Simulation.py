import logging
import os
import random
import time
import concurrent.futures
import signal
import uuid
from fpdf import FPDF
import pandas as pd
from datetime import datetime
import threading

from config import DOCS_DIR

# Configuration
NUM_THREADS = 10  # Number of concurrent threads (simulating user actions)
FILE_SIZE = 1024  # Size of the random file content in bytes
MAX_OPERATION_TIME = 1  # Maximum time for each operation in seconds
MIN_OPERATION_TIME = 1  # Minimum time for each operation in seconds

SIMULATION_FOLDER = 'Simulation-ENV'
SIMULATION_FOLDER_INSIDE_DOCS_DIR = os.path.join(DOCS_DIR, SIMULATION_FOLDER)

# Subdirectories for different file types
SUBDIRS = {
    'txt': 'TextFiles',
    'pdf': 'PDFs',
    'csv': 'CSVs'
}

# Ensure the main directory and subdirectories exist
os.makedirs(SIMULATION_FOLDER_INSIDE_DOCS_DIR, exist_ok=True)
for subdir in SUBDIRS.values():
    os.makedirs(os.path.join(SIMULATION_FOLDER_INSIDE_DOCS_DIR, subdir), exist_ok=True)

# Global flag to signal threads to stop
stop_signal = False

# Define static content for different file types
STATIC_CONTENT = {
    'txt': """
        Sample Text Document
        This is a static text file with a unique identifier. The content is pre-defined for simulation purposes.
    """,
    'pdf': """
        Sample PDF Document
        This is a static PDF file with a unique identifier. The content is pre-defined for simulation purposes.
    """,
    'csv': """
        Product,Sales,Revenue
    """
}

def generate_static_content(file_type, unique_id):
    """Generate static content with an added unique identifier."""
    content = STATIC_CONTENT[file_type]
    return f"{content}\nUnique Identifier: {unique_id}"

def generate_pdf(file_path):
    """Generate a PDF file with static content."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    unique_id = str(uuid.uuid4())  # Unique identifier for content
    content = generate_static_content('pdf', unique_id)
    pdf.set_title("Sample PDF Document")
    pdf.multi_cell(0, 10, content)
    pdf.output(file_path)

def generate_csv(file_path):
    """Generate a CSV file with unique content."""
    unique_id = str(uuid.uuid4())  # Unique identifier for content
    num_rows = 10
    num_cols = 3
    data = [[f"Product {i+1}"] + [random.randint(1, 1000) for _ in range(num_cols - 1)] for i in range(num_rows)]
    df = pd.DataFrame(data, columns=['Product', 'Sales', 'Revenue'])
    df['Unique Identifier'] = unique_id  # Add unique identifier as an extra column
    df.to_csv(file_path, index=False)

def generate_file_name(thread_id, file_extension, file_type):
    """Generate a realistic file name."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{file_type}_{timestamp}_thread_{thread_id}.{file_extension}"

def perform_operation(thread_id, file_names):
    """Perform a random file operation (create, edit, delete)."""
    # Get the current thread name
    thread_number = threading.current_thread().name
    operation = random.choice(['create', 'edit', 'delete'])
    
    if operation == 'create':
        file_extension = random.choice(['txt', 'pdf', 'csv'])
        subdir = SUBDIRS[file_extension]
        file_type = 'document' if file_extension != 'csv' else 'report'
        file_name = generate_file_name(thread_id, file_extension, file_type)
        file_path = os.path.join(SIMULATION_FOLDER_INSIDE_DOCS_DIR, subdir, file_name)
        
        if file_extension == 'txt':
            with open(file_path, 'w') as file:
                unique_id = str(uuid.uuid4())  # Unique identifier for content
                content = generate_static_content('txt', unique_id)
                file.write(content)
        elif file_extension == 'pdf':
            generate_pdf(file_path)
        elif file_extension == 'csv':
            generate_csv(file_path)
        
        file_names.append(file_path)  # Track the new file
        log.info(f"created file: {os.path.basename(file_path)}")

    elif operation == 'edit' and file_names:  # Edit an existing file
        file_path = random.choice(file_names)
        if file_path.endswith('.txt'):
            with open(file_path, 'a') as file:
                unique_id = str(uuid.uuid4())  # Unique identifier for additional content
                content = generate_static_content('txt', unique_id)
                file.write(content)
        
        log.info(f"edited file: {os.path.basename(file_path)}")

    elif operation == 'delete' and file_names:  # Delete an existing file
        file_path = random.choice(file_names)
        os.remove(file_path)
        file_names.remove(file_path)  # Remove from tracking list
        log.info(f"deleted file: {os.path.basename(file_path)}")

def user_simulation(thread_id):
    """Simulate a user performing file operations continuously."""
    file_names = []  # Track the paths of files created by this thread
    current_dir = SIMULATION_FOLDER_INSIDE_DOCS_DIR

    # Name the current thread
    threading.current_thread().name = f"Thread {thread_id}"

    while not stop_signal:
        # Randomly navigate to a subdirectory or stay in the current directory
        if random.random() < 0.1 and file_names:  # 10% chance to navigate
            subdir = random.choice(list(SUBDIRS.values()))
            current_dir = os.path.join(SIMULATION_FOLDER_INSIDE_DOCS_DIR, subdir)
        elif random.random() < 0.1 and current_dir != SIMULATION_FOLDER_INSIDE_DOCS_DIR:
            current_dir = SIMULATION_FOLDER_INSIDE_DOCS_DIR
        
        # Perform a random operation
        perform_operation(thread_id, file_names)
        
        # Random sleep to simulate real-time activity
        operation_time = random.uniform(MIN_OPERATION_TIME, MAX_OPERATION_TIME)
        time.sleep(operation_time)

def handle_sigint(signum, frame):
    """Handle SIGINT signal (Ctrl+C) to stop the simulation."""
    global stop_signal
    stop_signal = True
    log.info("Received interrupt signal. Stopping simulation…")

def start_simulation():
    """Start the simulation with a specified number of threads."""
    signal.signal(signal.SIGINT, handle_sigint)

    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = [executor.submit(user_simulation, thread_id) for thread_id in range(NUM_THREADS)]
        
        # Wait for all threads to complete
        concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_EXCEPTION)

if __name__ == "__main__":
    # Configure logging
    class ColoredFormatter(logging.Formatter):
        """Custom formatter to add color to log messages."""
        COLORS = {
            'INFO': '\033[92m',  # Green for INFO
            'WHITE': '\033[97m',  # White for the message
            'RESET': '\033[0m'  # Reset color
        }

        def format(self, record):
            # Get the color for the log level
            level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            # Set the color for the message to white
            message_color = self.COLORS['WHITE']
            return f"{level_color}{record.levelname}: {message_color} {record.threadName} {record.getMessage()}{self.COLORS['RESET']}"

    formatter = ColoredFormatter('%(levelname)s: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    log = logging.getLogger()
    log.setLevel(logging.INFO)
    log.handlers = []  # Remove existing handlers
    log.addHandler(handler)
    
    start_simulation()
