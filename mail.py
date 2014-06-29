from subprocess import Popen, PIPE, STDOUT
from email.mime.text import MIMEText
import smtplib


def send_email(content,subject):
    process = Popen(['cat','gmail'], stdout=PIPE, stderr=PIPE)
    password = process.communicate()[0].decode('utf-8').strip()
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SMTP_USERNAME = "eric.peeton@gmail.com"
    SMTP_PASSWORD = password

    EMAIL_TO = ["ea.peyton@gmail.com"]
    EMAIL_FROM = "eric.peeton@gmail.com"

    DATE_FORMAT = "%d/%m/%Y"
    EMAIL_SPACE = ", "

    msg = MIMEText(content, 'html')
    msg['Subject'] = subject
    msg['To'] = EMAIL_SPACE.join(EMAIL_TO)
    msg['From'] = EMAIL_FROM
    mail = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    mail.starttls()
    mail.login(SMTP_USERNAME, SMTP_PASSWORD)
    mail.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
    mail.quit()

send_email("<h3>Booyah!</h3>", "Boohoo!")
