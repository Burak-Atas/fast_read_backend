import os
from email.message import EmailMessage
import ssl
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def random_number():
    return random.randint(100000, 999999)

class EmailVerification():
    def __init__(self,email_reciver,konu,kimden):
        self.code = str(random_number())
        self.konu = konu
        self.kimden = kimden
        self.context = ssl.create_default_context()
        self.email_password = "pcdo ooqr oprq xkoq"    
        self.email_sender = "firatshop5@gmail.com"
        self.email_reciver = email_reciver
        #self.em = EmailMessage()
        self.body = self.create_body()
        self.context = ssl.create_default_context()
        self.em = MIMEMultipart()
        self.em['From'] = 'İRİS AKADEMİ <{}>'.format(self.email_sender)
        self.em['To'] = self.email_reciver
        self.em['Subject'] = 'İRİS AKADEMİ BİLGİ MESAJI'
        self.em.attach(MIMEText(self.body, 'html'))
        self.send_code()

    def create_body(self):
        body = """
        <!DOCTYPE html>
            <html>
            <tbody>
                <div style="padding: 0 0%;">
                <tr>
                    <td width="8" style="width:8px"></td>
                    <td style="text-align:center;">
                        <div style="border-style:solid;border-width:thin;border-color:#dadce0;border-radius:8px;padding:40px 20px;max-width:400px;"
                            align="center" class="m_2576292137312987380mdv2rw">
                            <div
                                style="font-family:'Google Sans',Roboto,RobotoDraft,Helvetica,Arial,sans-serif;border-bottom:thin solid #dadce0;color:rgba(0,0,0,0.87);line-height:32px;padding-bottom:24px;text-align:center;word-break:break-word">
                                <div style="font-size:24px">e-posta doğrulama kodunuz </div>
                            </div>
                            <div
                                style="font-family:Roboto-Regular,Helvetica,Arial,sans-serif;font-size:14px;color:rgba(0,0,0,0.87);line-height:20px;padding-top:20px;text-align:left">
                                İrisAcademi için bir mesajınız var <a style="font-weight:bold">{}</a> İris academi yeni bir measjınız var <br>
                                <div style="text-align:center;font-size:36px;margin-top:20px;line-height:44px">{}</div><br> Mesaj<br><br>
                            </div>
                        </div>
                    </td>
                    <td width="8" style="width:8px"></td>
                </tr>
                </div>
            </tbody>
            </html>
        """.format(self.kimden,self.konu,self.email_reciver)
        return body

    def send_code(self):
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=self.context) as smtp:
            smtp.login(self.email_sender, self.email_password)
            smtp.sendmail(self.email_sender, self.email_reciver, self.em.as_string())


# her kayıt yaptıracak kullanıcı için bir nesne üretilecek
# gönderilen gönderilen kodu a.code ile bulabiliriz
class EmailVerificationCode:
    def __init__(self, email_receiver, subject, sender_name):
        self.code = str(random_number())  # 6 haneli doğrulama kodu
        self.subject = subject
        self.sender_name = sender_name
        self.context = ssl.create_default_context()
        self.email_password = "pcdo ooqr oprq xkoq"  # E-posta şifresi
        self.email_sender = "firatshop5@gmail.com"  # Gönderen e-posta adresi
        self.email_receiver = email_receiver  # Alıcı e-posta adresi
        self.body = self.create_body()  # E-posta içeriğini oluştur
        self.em = MIMEMultipart()
        self.em['From'] = 'İRİS AKADEMİ <{}>'.format(self.email_sender)
        self.em['To'] = self.email_receiver
        self.em['Subject'] = 'İRİS AKADEMİ BİLGİ MESAJI'
        self.em.attach(MIMEText(self.body, 'html'))  # HTML formatında e-posta ekle
        self.send_code()  # Kodu gönder

    def create_body(self):
        body = """
        <!DOCTYPE html>
        <html>
        <body>
            <div style="text-align: center; padding: 20px;">
                <h2>e-posta doğrulama kodunuz</h2>
                <p>{sender_name} tarafından gönderildi</p>
                <h1 style="font-size: 36px; margin: 20px 0;">{code}</h1>
                <p>Kodunuzu kimseyle paylaşmayın.</p>
            </div>
        </body>
        </html>
        """.format(sender_name=self.sender_name, code=self.code)
        return body

    def send_code(self):
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=self.context) as smtp:
            smtp.login(self.email_sender, self.email_password)  # Giriş yap
            smtp.sendmail(self.email_sender, self.email_receiver, self.em.as_string())  # E-postayı gönder
        return self.code






if __name__ == "__main__":
    a = EmailVerification("kimsesiz34km@gmail.com")

    print("e mail adresinize gönderilen kodu giriniz")
    for i in range(5):
        code = input("Code: ")
        if code == a.code:
            print("eposta doğrulama başarılı")
        else:
            print("hatalı kod")