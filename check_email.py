import imaplib
import email
import os
import threading
from dotenv import load_dotenv
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import calendar
from datetime import datetime

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

def build_search_query():
    query = []
    from_val = sender_entry.get().replace("From:", "").strip()
    subject_val = subject_entry.get().replace("Subject contains:", "").strip()

    date_val = ""
    if day_var.get().isdigit() and month_var.get() != "Month" and year_var.get().isdigit():
        date_val = f"{day_var.get()}-{month_var.get()}-{year_var.get()}"

    if not from_val and not subject_val and not date_val:
        messagebox.showwarning("Empty Search", "Please enter at least one filter.")
        return None

    if from_val:
        query += ["FROM", f'"{from_val}"']
    if subject_val:
        query += ["SUBJECT", f'"{subject_val}"']
    if date_val:
        query += ["SINCE", date_val]

    return query

def search_emails():
    results_listbox.delete(0, tk.END)
    preview_area.delete("1.0", tk.END)
    global uid_map
    uid_map.clear()

    query = build_search_query()
    if not query:
        return

    try:
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
            subject = msg["subject"] or "(No Subject)"
            uid_map.append((num, subject))
            results_listbox.insert(tk.END, subject)
            root.update()

        status_label.config(text=f"Found {len(uid_map)} emails.", fg="blue")

    except imaplib.IMAP4.abort as e:
        status_label.config(text="IMAP aborted. Trying to reconnect...", fg="orange")
        try:
            mail.logout()
        except:
            pass
        reconnect_and_search()

    except Exception as e:
        status_label.config(text=f"Error: {str(e)}", fg="red")

def reconnect_and_search():
    global mail
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL, PASSWORD)
        mail.select("inbox")
        search_emails()
    except Exception as e:
        status_label.config(text=f"Reconnect failed: {str(e)}", fg="red")

def threaded_search():
    threading.Thread(target=search_emails, daemon=True).start()

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
            if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                body += part.get_payload(decode=True).decode(errors="ignore")
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
        if safe_mode.get():
            messagebox.showinfo("Safe Mode", "Safe Mode is ON — no email was deleted.")
        else:
            mail.store(uid, '+FLAGS', '\\Deleted')
            mail.expunge()
            results_listbox.delete(selection[0])
            preview_area.delete("1.0", tk.END)
            del uid_map[selection[0]]
            status_label.config(text="Email deleted.", fg="red")

def delete_all_results():
    if not uid_map:
        return
    confirm = messagebox.askyesno("Confirm Mass Delete", f"Are you sure you want to delete ALL {len(uid_map)} emails?")
    if not confirm:
        return

    if safe_mode.get():
        messagebox.showinfo("Safe Mode", "Safe Mode is ON — no emails were deleted.")
        return

    for uid, subject in uid_map:
        mail.store(uid, '+FLAGS', '\\Deleted')
    mail.expunge()
    uid_map.clear()
    results_listbox.delete(0, tk.END)
    preview_area.delete("1.0", tk.END)
    status_label.config(text="All emails deleted.", fg="red")

search_button = tk.Button(root, text="Search", command=threaded_search)
search_button.pack()

preview_button = tk.Button(root, text="Preview", command=preview_email)
preview_button.pack()

delete_button = tk.Button(root, text="Delete", command=delete_email)
delete_button.pack()

delete_all_button = tk.Button(root, text="Delete All Results", command=delete_all_results)
delete_all_button.pack()

def on_closing():
    try:
        mail.logout()
    except Exception as e:
        print("Logout failed:", e)
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)
root.mainloop()
