from pdfrw import PdfReader, PdfWriter, PageMerge
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import io

from datetime import datetime
import time
import regex as re


class FillLeaveForm:

    def __init__(self, template_path, output_path, data):
        '''
        Initialize the FillLeaveForm class
        :param template_path: str: The path to the template file
        :param output_path: str: The path to the output file
        :param data: dict: The data to fill the template with
        '''
        self.template_path = template_path
        self.output_path = output_path
        self.data = data

    
    def generate_unique_code(self):
        '''
        Generate a unique code for the leave application
        :return: str: The unique code
        '''
        now = datetime.datetime.now()
        date_str = now.strftime("%Y%m%d") 
        timestamp = int(time.time())
        # random_number = random.randint(1000, 9999) 
        # unique_code = f"{date_str}{timestamp}{random_number}"
        # return unique_code
        return date_str+str(timestamp)
    
    def validate_context(self,data, required_keys):
        '''
        Validate the data dictionary
        :param data: dict: The data dictionary
        :param required_keys: list: The list of required keys
        :return: None
        '''
        missing_keys = [key for key in required_keys if key not in data]
        if '{NAME}' in missing_keys:
            raise ValueError("Name is required!")
        if '{ID}' in missing_keys:
            raise ValueError("ID # is required!")
        if '{JOBTITLE}' in missing_keys:
            raise ValueError("Job Title is required!")
        if '{DEPT}' in missing_keys:
            raise ValueError("Dept is required!")
        if '{LEAVETYPE}' in missing_keys:
            raise ValueError("Type of Leave is required!")
        if '{REMARKS}' in missing_keys:
            raise ValueError("Employee Remarks (Attach Required Documents) is required!")
        if '{LEAVEFROM}' in missing_keys:
            raise ValueError("Leave Applied From is required!")
        if '{LEAVETO}' in missing_keys:
            raise ValueError("Leave Applied To is required!")
        if '{DAYS}' in missing_keys:
            raise ValueError("# of days is required!")
        if '{ADDRESS}' in missing_keys:
            raise ValueError("Address while on leave is required!")
        if '{TELE}' in missing_keys:
            raise ValueError("Telephone (Local) is required!")
        if '{EMAIL}' in missing_keys:
            raise ValueError("Email is required!")
        if '{DATE}' in missing_keys:
            raise ValueError("Date is required!")
        
        leave_list = ['Annual Leave','Sick Leave','Maternity Leave','Paternity Leave','Unpaid Leave','Compassionate Leave',
                    'Administrative Leave','Emergency Leave','Educational Leave','Lecture, Course/ Exams','Escort Leave','Military Service','Iddah Leave','Haj Leave']
        if data['{LEAVETYPE}'] not in leave_list:
            raise ValueError(f"Leave Type must be one of these {leave_list}!")
        
        def is_valid_string(input_string):
            """
            Validates if the input string contains only letters, digits, and punctuation.
            """
            # Define the regular expression pattern
            pattern = r'^[\w\s\p{P}]*$'
            return bool(re.match(pattern, input_string))
        
        def is_valid_date(date_string, date_format):
            """
            Validates if the date string matches the given date format.
            """
            try:
                datetime.strptime(date_string, date_format)
                return True
            except ValueError:
                return False
            
        def is_valid_number(number_string):
            """
            Validates if the input string is a valid number (integer or float).
            """
            pattern = r'^-?\d+(\.\d+)?$'
            return bool(re.match(pattern, number_string))
        
        def is_valid_email(email_string):
            """
            Validates if the input string is a valid email address.
            """
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(pattern, email_string))
        
        def is_valid_phone_number(phone_number):
            """
            Validates if the input string is a valid phone number.
            """
            # Define the regular expression pattern for a phone number
            pattern = r'^(\+?\d{1,3}[- ]?)?\(?\d{1,4}\)?[- ]?\d{1,4}[- ]?\d{1,9}$'
            # Validate the phone number using the pattern
            return bool(re.match(pattern, phone_number))
        
        def is_valid_address(address):
            """
            Validates if the input string is a valid address.
            """
            # Define the regular expression pattern for a basic address
            # This pattern checks for common address components:
            # Street number, street name, city, state (optional), and postal code (optional)
            pattern = r'^\d+\s+[\w\s.,-]+(?:,\s*[\w\s.-]+)*$'
            return bool(re.match(pattern, address))

        if not is_valid_string(data['{NAME}']):
            raise ValueError("Name contains invalid characters!")
        if not is_valid_string(data['{ID}']):
            raise ValueError("ID # contains invalid characters!")
        if not is_valid_string(data['{JOBTITLE}']):
            raise ValueError("Job Title contains invalid characters!")
        if not is_valid_string(data['{DEPT}']):
            raise ValueError("Dept contains invalid characters!")
        if not is_valid_string(data['{REMARKS}']):
            raise ValueError("Employee Remarks (Attach Required Documents) contains invalid characters!")
        
        if not is_valid_date(data['{LEAVEFROM}'], "%d-%m-%y"):
            raise ValueError("Leave Applied From must be in the format DD-MM-YY!")
        if not is_valid_date(data['{LEAVETO}'], "%d-%m-%y"):
            raise ValueError("Leave Applied To must be in the format DD-MM-YY!")
        
        if not is_valid_date(data['{DATE}'], "%d-%m-%y"):
            raise ValueError("Date must be in the format DD-MM-YY!")

        if not is_valid_number(data['{DAYS}']):
            raise ValueError("# of days must be a valid number!")
        
        # if not is_valid_address(data['{ADDRESS}']):
        #     raise ValueError("Address is invalid!")

        if not is_valid_phone_number(data['{TELE}']):
            raise ValueError("Telephone number is invalid!")

        if not is_valid_email(data['{EMAIL}']):
            raise ValueError("Email is invalid!")

        
    def fill_template(self):
        '''
        Fill the template with the data
        :return: str: The path to the output file
        '''

        required_keys = ['{NAME}','{ID}','{JOBTITLE}','{DEPT}','{LEAVETYPE}','{REMARKS}','{LEAVEFROM}','{LEAVETO}','{DAYS}','{ADDRESS}','{TELE}','{EMAIL}','{DATE}']
        self.validate_context(self.data, required_keys)
        
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica", 10)
        can.drawString(120, 690, self.data['{NAME}'])
        can.drawString(400, 690, self.data['{ID}'])
        can.drawString(120, 666, self.data['{JOBTITLE}'])
        can.drawString(400, 666, self.data['{DEPT}'])
        can.drawString(50, 620, self.data['{LEAVETYPE}'])
        can.drawString(50, 570, self.data['{REMARKS}'])
        can.drawString(160, 490, self.data['{LEAVEFROM}'])
        can.drawString(320, 490, self.data['{LEAVETO}'])
        can.drawString(475, 490, self.data['{DAYS}'])
        can.drawString(160, 445, self.data['{ADDRESS}'])
        can.drawString(160, 415, self.data['{TELE}'])
        can.drawString(320, 415, self.data['{EMAIL}'])
        can.drawString(120, 245, self.data['{DATE}'])
        can.drawString(255, 245, self.data['{DATE}'])
        can.save()
        # Move to the beginning of the StringIO buffer
        packet.seek(0)
        # Read the existing PDF template
        template = PdfReader(self.template_path)
        overlay_pdf = PdfReader(packet)
        overlay_page = overlay_pdf.pages[0]
        # Merge the overlay with the template
        for page in template.pages:
            merger = PageMerge(page)
            merger.add(overlay_page).render()
        # leave_{first_name}_{last_name}_start_date_end_date.pdf
        out_file = self.output_path+'leave_'+'_'.join(self.data['{NAME}'].split())+'_'+self.data['{LEAVEFROM}'].replace('-', '_')+'_'+self.data['{LEAVETO}'].replace('-', '_')+'.docx'
        PdfWriter(out_file, trailer=template).write()
        return out_file