# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <ProgramSnippet>
import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph import Graph
from fill_form import FillLeaveForm
from docx2pdf import convert

async def main():
    print('Python Graph Tutorial\n')

    # Load settings
    config = configparser.ConfigParser()
    config.read(['config.cfg', 'config.dev.cfg'])
    azure_settings = config['azure']

    graph: Graph = Graph(azure_settings)

    await greet_user(graph)

async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print('Hello,', user.display_name)
        # For Work/school accounts, email is in mail property
        # Personal accounts, email is in userPrincipalName
        print('Email:', user.mail or user.user_principal_name, '\n')
    choice = -1

    while choice != 0:
        print('Please choose one of the following options:')
        print('1. Send mail')

        try:
            choice = int(input())
        except ValueError:
            choice = -1

        try:
            if choice == 0:
                print('Goodbye...')
            elif choice == 1:
                await send_mail(graph)
            else:
                print('Invalid choice!\n')
        except ODataError as odata_error:
            print('Error:')
            if odata_error.error:
                print(odata_error.error.code, odata_error.error.message)

async def send_mail(graph: Graph):
    # fill the leave form
    template_path = '/Users/Shuanghai.Yu/Desktop/projects/rags/leave_template.docx'
    output_path = '/Users/Shuanghai.Yu/Desktop/projects/rags/out/'

    # jsonStringFromFront = '{ "id": 121, "name": "Naveen", "course": "MERN Stack"}'
    # data = json.loads(jsonStringFromFront)
    data = {
                '{NAME}': 'John Doe',
                '{ID}': 'AI40051',
                '{JOBTITLE}': 'NLP Engineer',
                '{DEPT}': 'CIAI Engineering Team',
                '{LEAVETYPE}': 'Annual Leave',
                '{REMARKS}': '3 days WFH, 1st Dec, 5th Dec, 7th Dec 1 day Sick Leave 6th Dec',
                '{LEAVEFROM}': '30-11-23',
                '{LEAVETO}': '14-12-23',
                '{DAYS}': '6',
                '{ADDRESS}': 'Mayan 4, 807, Yas Island, Abu Dhabi',
                '{TELE}': '0504678502',
                '{EMAIL}': 'nikhil.ranjan@mbzuai.ac.ae',
                '{DATE}': '19-07-24',
            }
    #get the form file path
    file_path = FillLeaveForm(template_path, output_path, data).fill_template()
    #make the mail content and send the mail can customize the subject and body
    pdf_path = file_path.replace('.docx','.pdf')
    convert(file_path,pdf_path)
    subject = 'Apply for a leave'
    body = 'Dear HR, \n   My leave application form is in the attachment. Thanks!'
    recipient = "shuanghai.yu@mbzuai.ac.ae"
    attachment_path = pdf_path
    attachment_name = 'Leave_Application_Form.pdf'

    user = await graph.get_user()
    if user:
        user_email = user.mail or user.user_principal_name
        await graph.send_leave_mail(subject,body, recipient,attachment_path,attachment_name)
        print('Mail sent.\n')

# Run main
asyncio.run(main())
