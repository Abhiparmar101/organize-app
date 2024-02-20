import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from app.config import SENDER_EMAIL,SMTP_PASSWORD,SMTP_PORT,SMTP_SERVER,SMTP_USERNAME,RECIPIENT_EMAIL

import os





#######################################################################################
def send_email_notification_with_image(subject, body, image_path):
    try:
        # Set up the SMTP server
        server = smtplib.SMTP(host=SMTP_SERVER, port=SMTP_PORT)
        server.starttls()  # Upgrade the connection to secure
        server.login(SMTP_USERNAME, SMTP_PASSWORD)

        # Create the email message
        message = MIMEMultipart()
        message['From'] = SENDER_EMAIL
        message['To'] = RECIPIENT_EMAIL
        message['Subject'] = subject

        # Attach the email body
        message.attach(MIMEText(body, 'plain'))

        # Open the image file in binary mode and attach it to the email
        with open(image_path, 'rb') as file:
            img = MIMEImage(file.read(), name=os.path.basename(image_path))
            message.attach(img)

        # Send the email and close the server connection
        server.send_message(message)
        server.quit()
        print("Email with image sent successfully.")
    except Exception as e:
        print(f"Failed to send email with image: {e}")