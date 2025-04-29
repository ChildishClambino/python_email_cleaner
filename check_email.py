import imaplib
import email
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
from email.header import decode_header

# Load environment variables
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# Connect to Gmail
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(EMAIL, PASSWORD)
mail.select("inbox")

# GUI setup
root = tk.Tk()
root.title("Email Filter & Deletion Tool")
root.geometry("700x500")

status_label = tk.Label(root, text="Connected to Gmail", fg="green")
status_label.pack()

sender_entry = tk.Entry(root, width=50)
sender_entry.pack()
sender_entry.insert(0, "From:")

subject_entry = tk.Entry(root, width=50)
subject_entry.pack()
subject_entry.insert(0, "Subject contains:")

date_entry = tk.Entry(root, width=50)
date_entry.pack()
date_entry.insert(0, "Since date (e.g., 01-Apr-2024):")

results_listbox = tk.Listbox(root, width=80, height=10)
results_listbox.pack()

preview_area = scrolledtext.ScrolledText(root, width=80, height=10, wrap=tk.WORD)
preview_area.pack()

uid_map = []  # Holds (uid, subject)

def decode_mime_words(s):
    decoded = decode_header(s)
    return ''.join([str(t[0], t[1] or 'utf-8') if isinstance(t[0], bytes) else t[0] for t in decoded])

def build_search_query():
    query = []
    from_val = sender_entry.get().replace("From:", "").strip()
    if from_val:
        query += ["FROM", f'"{from_val}"']

    subject_val = subject_entry.get().replace("Subject contains:", "").strip()
    if subject_val:
        query += ["SUBJECT", f'"{subject_val}"']

    date_val = date_entry.get().replace("Since date (e.g., 01-Apr-2024):", "").strip()
    if date_val:
        query += ["SINCE", date_val]

    return query if query else ["ALL"]

def search_emails():
    results_listbox.delete(0, tk.END)
    preview_area.delete("1.0", tk.END)
    global uid_map
    uid_map.clear()

    query = build_search_query()
    status, messages = mail.search(None, *query)
    if status != "OK":
        status_label.config(text="Search failed", fg="red")
        return

    email_ids = messages[0].split()
    for num in email_ids:
        status, data = mail.fetch(num, '(RFC822)')
        if status != "OK":
            continue
        msg = email.message_from_bytes(data[0][1])
        subject = decode_mime_words(msg["subject"] or "(No Subject)")
        uid_map.append((num, subject))
        results_listbox.insert(tk.END, subject)

    status_label.config(text=f"Found {len(uid_map)} emails.", fg="blue")

def preview_email():
    preview_area.delete("1.0", tk.END)
    selection = results_listbox.curselection()
    if not selection:
        return
    uid = uid_map[selection[0]][0]
    status, data = mail.fetch(uid, '(RFC822)')
    if status != "OK":
        return
    msg = email.message_from_bytes(data[0][1])

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not part.get("Content-Disposition"):
                body += part.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/html" and not part.get("Content-Disposition"):
                body += "\n[HTML content available. Use a browser/email client to view.]\n"
    else:
        body += msg.get_payload(decode=True).decode(errors="ignore")

    preview_area.insert(tk.END, body[:5000])

def delete_email():
    selection = results_listbox.curselection()
    if not selection:
        return
    uid = uid_map[selection[0]][0]
    subject = uid_map[selection[0]][1]

    confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n{subject}")
    if confirm:
        mail.store(uid, '+FLAGS', '\\Deleted')
        mail.expunge()
        results_listbox.delete(selection[0])
        preview_area.delete("1.0", tk.END)
        del uid_map[selection[0]]
        status_label.config(text="Email deleted.", fg="red")

search_button = tk.Button(root, text="Search", command=search_emails)
search_button.pack()

preview_button = tk.Button(root, text="Preview", command=preview_email)
preview_button.pack()

delete_button = tk.Button(root, text="Delete", command=delete_email)
delete_button.pack()

root.mainloop()

# Cleanup on exit
mail.logout()
