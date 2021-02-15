import smtplib
from email.mime.text import MIMEText

import pool

def SendMsg( to, subject, body ) :
    me = 'ifhl.statsgen@gmail.com'
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = me
    msg['To'] = to
    s = smtplib.SMTP()
    s.connect( 'smtp.gmail.com', 587 )
    s.ehlo()
    s.starttls()
    s.login( me, pool.Access )
    s.sendmail( me, [to], msg.as_string() )
    s.close()

