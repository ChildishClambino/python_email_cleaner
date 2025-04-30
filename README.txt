# Email GUI Filter - README

## Overview

This tool is a desktop GUI application that connects to your Gmail account, allowing you to:

- Search emails using sender, subject, and date filters.
- Preview email content.
- Delete selected or all filtered emails (Safe Mode included).

---

## Features

- **Tkinter GUI** with input fields and list display.
- **Safe Mode** toggle to preview actions before deletion.
- **Threaded operations** to prevent UI freezing.
- **Error handling** and reconnect logic for IMAP aborts.

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Create a `.env` file in the root directory:

```
EMAIL=your_email@gmail.com
PASSWORD=your_app_password
```

Use [App Passwords](https://support.google.com/accounts/answer/185833?hl=en) if you have 2FA enabled.

### 3. Run the Application

```bash
python email_gui_filter.py
```

---

## Packaging into Executable (Optional)

If you'd like to share this app with others without requiring Python:

1. Ensure `PyInstaller` is installed:

```bash
pip install pyinstaller
```

2. Use the existing `email_gui_filter.spec` file:

```bash
pyinstaller email_gui_filter.spec
```

3. Distribute the `.exe` in `dist/email_gui_filter/`.

> Note: Be sure to include the `.env` file and `mail.ico` in the same folder if running standalone.

---

## License

MIT License

---

## Credits

Developed by Jacob Garcilazo with support from ChatGPT. 😊

