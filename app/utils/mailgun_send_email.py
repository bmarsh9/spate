import requests

class Mailgun(object):
    """
    class to send email via mailgun
    """
    def __init__(self, mailgun_api_key, mailgun_domain, from_email):
        self.api_key = mailgun_api_key
        self.mailgun_domain = mailgun_domain
        self.from_email = from_email

    def send_email(self, to_email, subject, text):
        """
        send email via mailgun
        """
        return requests.post(
            "https://api.mailgun.net/v3/{0}/messages".format(self.mailgun_domain),
            auth=("api", self.api_key),
            data={"from": self.from_email,
                  "to": [to_email],
                  "subject": subject,
                  "text": text})

    def send_email_with_attachment(to_email, cc_email, subject, text, attachment=None, html=None):
        return requests.post(
            "https://api.mailgun.net/v3/{0}/messages".format(self.mailgun_domain),
            auth=("api", self.api_key),
            files=[("attachment", open(attachment))],
            data={"from": self.from_email,
                  "to": [to_email],
                  "cc": [cc_email],
                  "subject": subject,
                  "text": text,
                  "html": html})