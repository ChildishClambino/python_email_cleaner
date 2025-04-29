import imaplib
import email
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox, simpledialog, Listbox, Scrollbar
from datetime import datetime

load_dotenv()

EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

class EmailApp:
    def __init__(self, master):
        self.master = master
        master.title("Email Filter and Viewer")

        # Input fields
        tk.Label(master, text="From:").grid(row=0, column=0)
        self.from_entry = tk.Entry(master)
        self.from_entry.grid(row=0, column=1)

        tk.Label(master, text="Subject Contains:").grid(row=1, column=0)
        self.subject_entry = tk.Entry(master)
        self.subject_entry.grid(row=1, column=1)

        tk.Label(master, text="Since (DD-Mon-YYYY):").grid(row=2, column=0)
        self.since_entry = tk.Entry(master)
        self.since_entry.grid(row=2, column=1)

        # Search button
        self.search_button = tk.Button(master, text="Search", command=self.search_emails)
        self.search_button.grid(row=3, column=0, columnspan=2)

        # Listbox for results
        self.email_listbox = Listbox(master, width=80, height=10)
        self.email_listbox.grid(row=4, column=0, columnspan=2)

        scrollbar = Scrollbar(master)
        scrollbar.grid(row=4, column=2, sticky='ns')
        self.email_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.email_listbox.yview)

        # Preview and status
        self.status_label = tk.Label(master, text="Status: Waiting...")
        self.status_label.grid(row=5, column=0, columnspan=2)

        self.email_data = []

    def search_emails(self):
        sender = self.from_entry.get().strip()
        subject = self.subject_entry.get().strip()
        since = self.since_entry.get().strip()

        # Build IMAP filter
        criteria = []
        if sender:
            criteria.append(f'FROM "{sender}"')
        if subject:
            criteria.append(f'SUBJECT "{subject}"')
        if since:
            try:
                datetime.strptime(since, "%d-%b-%Y")
                criteria.append(f'SINCE "{since}"')
            except ValueError:
                messagebox.showerror("Date Error", "Date must be in format DD-Mon-YYYY (e.g. 01-Apr-2024)")
                return

        search_filter = f'({" ".join(criteria)})' if criteria else "ALL"

        try:
            self.status_label.config(text="Connecting to Gmail...")
            mail = imaplib.IMAP4_SSL("imap.gmail.com")
            mail.login(EMAIL, PASSWORD)
            mail.select("inbox")

            status, messages = mail.search(None, search_filter)
            if status != "OK":
                self.status_label.config(text="Failed to retrieve emails.")
                return

            email_ids = messages[0].split()
            self.email_listbox.delete(0, tk.END)
            self.email_data = []

            for num in email_ids[-10:]:  # Show only last 10
                typ, msg_data = mail.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(msg_data[0][1])
                subject = msg["subject"] or "(No Subject)"
                self.email_listbox.insert(tk.END, subject)
                self.email_data.append((num, msg))

            self.status_label.config(text=f"✅ Found {len(email_ids)} email(s). Showing last {min(len(email_ids), 10)}")
            mail.logout()

        except Exception as e:
            self.status_label.config(text=f"❌ Error: {e}")
            messagebox.showerror("Connection Error", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = EmailApp(root)
    root.mainloop()
