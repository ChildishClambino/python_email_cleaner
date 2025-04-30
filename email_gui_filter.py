import imaplib
import email
import os
import threading
import sys
import re
from pathlib import Path
from dotenv import load_dotenv, dotenv_values
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import calendar
from datetime import datetime

# Load environment variables (PyInstaller-compatible)
base_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
dotenv_path = base_dir / ".env"
print(f"[DEBUG] Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path)

# Load credentials
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

if not EMAIL or not PASSWORD:
    missing_keys = []
    config_values = dotenv_values(dotenv_path)
    if "EMAIL" not in config_values:
        missing_keys.append("EMAIL")
    if "PASSWORD" not in config_values:
        missing_keys.append("PASSWORD")

    error_message = "Missing or empty keys in .env: " + ", ".join(missing_keys)
    print("[ERROR]", error_message)
    messagebox.showerror("Missing Credentials", f"Could not load the following keys from .env:\n{error_message}\n\nExpected file path: {dotenv_path}")
    sys.exit(1)

# Connect to Gmail
print("[DEBUG] Connecting to Gmail IMAP...")
mail = imaplib.IMAP4_SSL("imap.gmail.com")
mail.login(EMAIL, PASSWORD)
mail.select("inbox")
print("[DEBUG] Logged in and selected inbox")

# GUI setup
root = tk.Tk()
root.title("Email Filter & Deletion Tool")
root.geometry("700x550")

status_label = tk.Label(root, text="Connected to Gmail", fg="green")
status_label.pack()

sender_entry = tk.Entry(root, width=50)
sender_entry.pack()
sender_entry.insert(0, "From:")

subject_entry = tk.Entry(root, width=50)
subject_entry.pack()
subject_entry.insert(0, "Subject contains:")

# Date dropdowns
date_frame = tk.Frame(root)
date_frame.pack()

day_var = tk.StringVar(value="Day")
month_var = tk.StringVar(value="Month")
year_var = tk.StringVar(value="Year")

day_menu = tk.OptionMenu(date_frame, day_var, *[str(i).zfill(2) for i in range(1, 32)])
month_menu = tk.OptionMenu(date_frame, month_var, *calendar.month_abbr[1:])
year_menu = tk.OptionMenu(date_frame, year_var, *[str(y) for y in range(datetime.now().year, datetime.now().year - 10, -1)])

day_menu.pack(side="left")
month_menu.pack(side="left")
year_menu.pack(side="left")

safe_mode = tk.BooleanVar(value=True)
safe_mode_checkbox = tk.Checkbutton(root, text="Safe Mode (Preview Only)", variable=safe_mode)
safe_mode_checkbox.pack()

results_listbox = tk.Listbox(root, width=80, height=10)
results_listbox.pack()

preview_area = scrolledtext.ScrolledText(root, width=80, height=10, wrap=tk.WORD)
preview_area.pack()

uid_map = []  # Holds (uid, subject)

def encode_uid(uid):
    return uid.decode() if isinstance(uid, bytes) else str(uid)

def reconnect():
    global mail
    try:
        print("[DEBUG] Reconnecting to Gmail IMAP...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        print("[DEBUG] Reconnected and inbox selected")
        return True
    except Exception as e:
        print("[ERROR] Reconnect failed:", str(e))
        status_label.config(text=f"Reconnect failed: {str(e)}", fg="red")
        return False

def delete_email():
    def task():
        print("[DEBUG] Starting single email deletion task")
        selection = results_listbox.curselection()
        if not selection:
            print("[DEBUG] No selection made")
            return
        uid = uid_map[selection[0]][0]
        subject = uid_map[selection[0]][1]
        print(f"[DEBUG] Selected UID: {uid}, Subject: {subject}")

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete:\n{subject}")
        if confirm:
            if safe_mode.get():
                print("[DEBUG] Safe mode ON — email not deleted")
                messagebox.showinfo("Safe Mode", "Safe Mode is ON — no email was deleted.")
                return
            try:
                uid_str = encode_uid(uid).strip()
                result, _ = mail.uid('STORE', uid_str.encode(), '+FLAGS', r'(\Deleted)')
                if result != "OK":
                    raise Exception(f"UID STORE command failed with status: {result}")
                mail.expunge()
                results_listbox.delete(selection[0])
                preview_area.delete("1.0", tk.END)
                del uid_map[selection[0]]
                status_label.config(text="Email deleted.", fg="red")
                print("[DEBUG] Email deleted successfully")
            except imaplib.IMAP4.abort:
                print("[ERROR] Connection aborted, attempting to reconnect...")
                if reconnect():
                    task()
            except Exception as e:
                print(f"[ERROR] Failed to delete email: {e}")
                messagebox.showerror("Error", f"Failed to delete email: {e}")

    threading.Thread(target=task, daemon=True).start()

def delete_all_results():
    def task():
        print("[DEBUG] Starting bulk delete task")
        if not uid_map:
            print("[DEBUG] No emails in uid_map")
            return
        confirm = messagebox.askyesno("Confirm Mass Delete", f"Are you sure you want to delete ALL {len(uid_map)} emails?")
        if not confirm:
            print("[DEBUG] Deletion not confirmed")
            return

        if safe_mode.get():
            print("[DEBUG] Safe mode ON — no emails deleted")
            messagebox.showinfo("Safe Mode", "Safe Mode is ON — no emails were deleted.")
            return

        try:
            for uid, subject in uid_map:
                uid_str = encode_uid(uid).strip()
                print(f"[DEBUG] Deleting UID: {uid_str}, Subject: {subject}")
                result, _ = mail.uid('STORE', uid_str.encode(), '+FLAGS', r'(\Deleted)')
                if result != "OK":
                    raise Exception(f"UID STORE command failed with status: {result}")
            mail.expunge()
            uid_map.clear()
            results_listbox.delete(0, tk.END)
            preview_area.delete("1.0", tk.END)
            status_label.config(text="All emails deleted.", fg="red")
            print("[DEBUG] All emails deleted successfully")
        except imaplib.IMAP4.abort:
            print("[ERROR] Connection aborted during bulk delete, attempting to reconnect...")
            if reconnect():
                task()
        except Exception as e:
            print(f"[ERROR] Failed to delete emails: {e}")
            messagebox.showerror("Error", f"Failed to delete emails: {e}")

    threading.Thread(target=task, daemon=True).start()

def extract_uid_and_subject(data):
    try:
        if not data or not data[0] or not isinstance(data[0], tuple):
            print("[ERROR] Invalid fetch data format:", data)
            return None, None

        raw_header = data[0][0]
        if not raw_header:
            print("[ERROR] Missing raw header in fetch data:", data)
            return None, None

        header_str = raw_header.decode(errors="ignore")
        uid_match = re.search(r"UID (\d+)", header_str)
        uid = uid_match.group(1) if uid_match else None

        if not uid or not uid.isdigit():
            print("[ERROR] UID not found or invalid in header:", header_str)
            return None, None

        msg = email.message_from_bytes(data[0][1])
        subject = msg["subject"] or "(No Subject)"
        return uid, subject

    except Exception as e:
        print(f"[ERROR] Exception during UID extraction: {e}")
        return None, None

def threaded_search():
    def search_emails():
        print("[DEBUG] Starting search thread")
        results_listbox.delete(0, tk.END)
        preview_area.delete("1.0", tk.END)
        global uid_map
        uid_map.clear()

        query = []
        from_val = sender_entry.get().replace("From:", "").strip()
        subject_val = subject_entry.get().replace("Subject contains:", "").strip()
        if from_val:
            query += ["FROM", f'"{from_val}"']
        if subject_val:
            query += ["SUBJECT", f'"{subject_val}"']

        if day_var.get().isdigit() and month_var.get() != "Month" and year_var.get().isdigit():
            date_val = f"{day_var.get()}-{month_var.get()}-{year_var.get()}"
            query += ["SINCE", date_val]

        if not query:
            messagebox.showwarning("Empty Search", "Please enter at least one filter.")
            return

        try:
            status, messages = mail.search(None, *query)
            if status != "OK":
                status_label.config(text="Search failed", fg="red")
                return

            email_ids = messages[0].split()
            for num in email_ids:
                status, data = mail.fetch(num, "(UID RFC822)")
                if status != "OK":
                    continue
                uid, subject = extract_uid_and_subject(data)
                if uid:
                    uid_map.append((uid, subject))
                    results_listbox.insert(tk.END, subject)

            status_label.config(text=f"Found {len(uid_map)} emails.", fg="blue")
            print(f"[DEBUG] Found {len(uid_map)} emails.")

        except imaplib.IMAP4.abort:
            print("[ERROR] IMAP connection aborted during search, attempting reconnect...")
            if reconnect():
                threaded_search()

        
        except Exception as e:
            status_label.config(text=f"Error: {str(e)}", fg="red")
            print("[ERROR]", str(e))

    threading.Thread(target=search_emails, daemon=True).start()

tk.Button(root, text="Search", command=threaded_search).pack()
tk.Button(root, text="Preview", command=lambda: None).pack()
tk.Button(root, text="Delete", command=delete_email).pack()
tk.Button(root, text="Delete All Results", command=delete_all_results).pack()

def on_closing():
    try:
        mail.logout()
    except Exception as e:
        print("Logout failed:", e)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
