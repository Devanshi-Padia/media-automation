import aiosmtplib
from email.message import EmailMessage
from jose import jwt
from datetime import datetime, timedelta

async def send_verification_email(to_email: str, token: str):
    msg = EmailMessage()
    msg["From"] = "no-reply@yourdomain.com"
    msg["To"] = to_email
    msg["Subject"] = "Verify your email"
    msg.set_content(f"Click the link to verify your email: https://yourdomain.com/api/v1/verify-email?token={token}")

    await aiosmtplib.send(
        msg,
        hostname="smtp.yourdomain.com",
        port=587,
        username="your_smtp_user",
        password="your_smtp_password",
        start_tls=True,
    )

def create_email_token(email: str, secret: str, expires_in=3600):
    expire = datetime.utcnow() + timedelta(seconds=expires_in)
    return jwt.encode({"sub": email, "exp": expire}, secret, algorithm="HS256")
