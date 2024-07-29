import logging

from .graph import Graph
from .fill_form import FillLeaveForm
from docx2pdf import convert

class Mail:
    graph: Graph

    def __init__(self, client_id: str, tenant_id: str, authorization: str, graph_user_scopes: list[str] = ["Mail.Read", "Mail.Send"]):
        azure_settings={}
        azure_settings["client_id"] = client_id
        azure_settings["tenant_id"] = tenant_id
        azure_settings["graph_user_scopes"] = graph_user_scopes
        azure_settings["authorization"] = authorization
        self.graph: Graph = Graph(azure_settings)

    async def send_mail(self):
        # fill the leave form
        template_path = 'utils/mail/leave_template.docx'
        output_path = 'utils/mail/'

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
        recipient = "qinghao.zhang@mbzuai.ac.ae"
        attachment_path = pdf_path
        attachment_name = 'Leave_Application_Form.pdf'

        await self.graph.send_leave_mail(subject,body, recipient,attachment_path,attachment_name)