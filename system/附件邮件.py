#!/bin/env python
###########coding=utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
import smtplib
from email.MIMEText import MIMEText 
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders
import time

if len(sys.argv) != 5:
	print "参数错误:python "+sys.argv[0]+" 收件人 附件 标题 正文"
	sys.exit()

# 构造MIMEMultipart对象做为根容器
msg=MIMEMultipart('related')
msg['Subject'] = unicode(sys.argv[3], "UTF-8")
mail_body= unicode(sys.argv[4], "UTF-8")
body=MIMEText(mail_body.encode('utf-8'), _subtype = 'html',_charset = 'utf-8')
msg.attach(body)

part = MIMEBase('application', 'octet-stream')

# 读入文件内容并格式化，此处文件为当前目录下，也可指定目录 例如：open(r'/tmp/123.txt','rb')
file_list=sys.argv[2]
part.set_payload(open(file_list,'rb').read())
Encoders.encode_base64(part)
## 设置附件头
part.add_header('Content-Disposition', 'attachment; filename='+file_list)
msg.attach(part)

# 设置根容器属性
from email.mime.text import MIMEText
mail_host = 'smtp.163.com'
mail_user = 'zabbixm@163.com'
mail_pwd = '1234'

to_list = sys.argv[1].split(",")
msg['From']=mail_user 
msg['date']=time.strftime('%a, %d %b %Y %H:%M:%S %z') 
msg['To']=",".join( to_list )
#如上得到了格式化后的完整文本msg.as_string()
#用smtp发送邮件
smtp=smtplib.SMTP_SSL(mail_host,465)
smtp.login(mail_user,mail_pwd)
smtp.sendmail(mail_user,to_list,msg.as_string())
smtp.quit()
print 'ok'



