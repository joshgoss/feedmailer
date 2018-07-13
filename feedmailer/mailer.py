from email.message import EmailMessage
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Template
import smtplib

from feedmailer import constants


class Mailer:
    def __init__(self, **kwargs):
        self.host = kwargs['host']
        self.user = kwargs['user']
        self.password = kwargs['password']
        self.auth = kwargs['auth']
        self.ssl = kwargs['ssl']
        self.port = kwargs['port']
        self.to_email = kwargs['to_email']

    def send_article(self, **kwargs):
        feed_title = kwargs['feed_title']
        article = kwargs['article']
        content_type = kwargs['content_type']
        template_file = constants.TEMPLATES[content_type].article_template

        with open(template_file) as f:
            template = Template(f.read())

            subject = subscription['title'] + ' - ' + a['title']

            content = template.render(
                article=article,
                feed_title = feed_title
            )

            max_length = 80

            self.send(
                subject[:max_length],
                content,
                constants.TEMPLATES[content_type]['content_type']
            )

    def send_digest(self, **kwargs):
        feed_title = kwargs['feed_title']
        articles = kwargs['articles']
        content_type = kwargs['content_type']
        template_file = constants.TEMPLATES[content_type]['digest_template']

        with open(template_file) as f:
                template = Template(f.read())

                content = template.render(
                    articles=articles,
                    feed_title=feed_title
                )

        self.send(
            feed_title + ' Digest',
            content,
            constants.TEMPLATES[content_type]['content_type']
        )

    def send(self, subject, content, content_type='plain'):
        constructor = smtplib.SMTP

        if self.ssl:
            constructor = smtplib.SMTP_SSL

        with constructor(host=self.host, port=self.port) as s:
            if self.auth:
                s.login(self.user, self.password)

            msg = MIMEMultipart('alternative')
            msg['From'] = self.user
            msg['To'] = self.to_email
            msg['Subject'] = subject

            part = MIMEText(content, content_type)

            msg.attach(part)
            msg.set_default_type(content_type)

            s.send_message(msg)
