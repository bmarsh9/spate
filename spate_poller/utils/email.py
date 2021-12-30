import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from mako.template import Template
import os

def send_email(app, step, recipients):
    title = "{}: We need your input".format(app.APP_NAME)
    content = "We need to collect your input for the paused workflow"
    button_link = os.path.join(app.API_HOST,"resume/{}".format(step.uuid))

    msg = MIMEMultipart('alternative')
    msg['Subject'] = title
    msg['From'] = app.MAIL_USERNAME
    msg['To'] = recipients

    template = Template(filename='utils/user_input.html')
    html = template.render(app_name=app.APP_NAME,title=title,
        content=content,button_link=button_link)

    part1 = MIMEText(content, 'plain')
    part2 = MIMEText(html, 'html')

    msg.attach(part1)
    msg.attach(part2)
    mail = smtplib.SMTP(app.MAIL_SERVER, int(app.MAIL_PORT))
    mail.ehlo()
    mail.starttls()

    mail.login(app.MAIL_USERNAME,app.MAIL_PASSWORD)
    mail.sendmail(app.MAIL_USERNAME, recipients, msg.as_string())
    mail.quit()
    return True
