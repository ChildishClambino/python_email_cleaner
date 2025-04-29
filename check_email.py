import imaplib
import email
import os
from dotenv import load_dotenv



# STEP 1: Replace these with your actual values
EMAIL = os.get.env("EMAIL")
PASSWORD = os.get.env("PASSWORD")

# STEP 2: Connect to Gmail's IMAP server securely
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(EMAIL, PASSWORD)

# STEP 3: Select the inbox
mail.select("inbox")  # You could also use "All Mail" or other labels

# STEP 4: Search for all emails
status, messages = mail.search(None, "ALL")  # Use filters later if needed

if status != "OK":
    print("❌ Failed to retrieve emails.")
else:
    print("✅ Connected. Showing last 5 email subjects:\n")
    
    # Get the last 5 email IDs
    email_ids = messages[0].split()[-5:]

    for num in email_ids:
        typ, msg_data = mail.fetch(num, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])
        subject = msg["subject"]
        print("✉️ Subject:", subject)

# STEP 5: Logout
mail.logout()