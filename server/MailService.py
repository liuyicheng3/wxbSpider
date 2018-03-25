#!/usr/bin/python
# coding=utf-8
from email.mime.text import MIMEText
import smtplib
import threading


class MailThread(threading.Thread):
    def __init__(self, mail):
        threading.Thread.__init__(self)
        self.mail = mail

    def run(self):
        print(threading.current_thread)
        self.mail.send_email()

class Mail(object):

    def __init__(self, title, content):
        # 第三方 SMTP 服务
        self.mail_host = "smtp.126.com"  # 设置服务器
        self.mail_user = "***"  # 用户名
        self.mail_pass = "***"  # 口令
        self.receiver = '"***"'  # 接收邮件，可设置为你的QQ邮箱或者其他邮箱

        self.message = MIMEText(content)
        self.message['Subject'] = title
        self.message['From'] = self.mail_user
        self.message['To'] = self.receiver

    def send_email(self):
        try:
            smtpObj = smtplib.SMTP()
            smtpObj.connect(self.mail_host, 25)
            smtpObj.login(self.mail_user, self.mail_pass)
            smtpObj.sendmail(self.mail_user, self.receiver, self.message.as_string())
            print "邮件发送成功"
        except smtplib.SMTPException, e:
            print "Error: 无法发送邮件"
            print e.message

