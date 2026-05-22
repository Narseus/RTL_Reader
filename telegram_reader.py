#!/usr/bin/env python3

import sys
import threading
from urllib.parse import quote
from datetime import datetime
from bs4 import BeautifulSoup
from curl_cffi import requests
from playwright.sync_api import sync_playwright
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ==================== CONFIGURATION ====================

CUSTOM_DNS = {
    "translate.google.com": "216.239.38.120",
    "translate.googleapis.com": "216.239.38.120",
    "fonts.googleapis.com": "216.239.38.120",
    "fonts.gstatic.com": "216.239.38.120",
    "www.gstatic.com": "216.239.38.120",
    "t-me.translate.goog": "216.239.38.120",
    "www.google.com": "216.239.38.120",
    "fonts.google.com": "216.239.38.120",
}
# Default channel (can be changed in GUI)
DEFAULT_CHANNEL = ""
DEFAULT_MAX_MSGS = 10
TIMEOUT = 30
# ========================================================

def has_rtl_chars(text: str) -> bool:
    """
    Detect if the text contains Arabic or Persian (RTL) Unicode characters.
    Ranges: Arabic (0600-06FF), Arabic Supplement (0750-077F),
    Arabic Presentation Forms (FB50-FDFF, FE70-FEFF)
    """
    for ch in text:
        code = ord(ch)
        if (0x0600 <= code <= 0x06FF) or (0x0750 <= code <= 0x077F) or \
           (0xFB50 <= code <= 0xFDFF) or (0xFE70 <= code <= 0xFEFF):
            return True
    return False

def build_custom_url(original_url: str) -> tuple[str, dict | None]:
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(original_url)
    if parsed.scheme != "https":
        return original_url, None
    domain = parsed.netloc.split(":")[0]
    if domain in CUSTOM_DNS:
        ip = CUSTOM_DNS[domain]
        new_netloc = ip + (f":{parsed.port}" if parsed.port else "")
        new_parsed = parsed._replace(netloc=new_netloc)
        new_url = urlunparse(new_parsed)
        headers = {"Host": domain}
        return new_url, headers
    return original_url, None

def fetch_with_curl_cffi(channel: str, max_msgs: int):
    original_url = f"https://t.me/s/{channel}?embed=1"
    proxy_url = f"https://translate.google.com/translate?sl=auto&tl=en&u={quote(original_url)}"
    real_url, extra_headers = build_custom_url(proxy_url)
    try:
        verify_ssl = extra_headers is None
        response = requests.get(
            real_url,
            impersonate="chrome",
            timeout=TIMEOUT,
            headers=extra_headers or {},
            verify=verify_ssl
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        message_containers = soup.find_all("div", class_="tgme_widget_message")
        result = []
        for container in message_containers[:max_msgs]:
            msg_div = container.find("div", class_="tgme_widget_message_text")
            if not msg_div:
                continue
            text = msg_div.get_text(strip=True)
            if not text:
                continue
            # Extract timestamp
            time_div = container.find("div", class_="tgme_widget_message_date")
            if not time_div:
                time_tag = container.find("time")
                if time_tag:
                    timestamp = time_tag.get_text(strip=True)
                else:
                    timestamp = None
            else:
                timestamp = time_div.get_text(strip=True)
            result.append((text, timestamp))
        return result if result else None
    except Exception as e:
        print(f"[curl_cffi] Error: {e}")
        return None

def fetch_with_playwright(channel: str, max_msgs: int):
    original_url = f"https://t.me/s/{channel}?embed=1"
    proxy_url = f"https://translate.google.com/translate?sl=auto&tl=en&u={quote(original_url)}"
    resolver_rules = [f"MAP {domain} {ip}" for domain, ip in CUSTOM_DNS.items()]
    resolver_arg = f"--host-resolver-rules={' '.join(resolver_rules)}" if resolver_rules else None
    with sync_playwright() as p:
        browser_args = [resolver_arg] if resolver_arg else []
        browser = p.chromium.launch(headless=True, args=browser_args)
        page = browser.new_page()
        try:
            page.goto(proxy_url, timeout=60000)
            page.wait_for_selector(".tgme_widget_message_text, a.tgme_action_button_preview", timeout=15000)
            button = page.query_selector("a.tgme_action_button_preview")
            if button:
                button.click()
                page.wait_for_selector(".tgme_widget_message_text", timeout=15000)
            message_elements = page.query_selector_all(".tgme_widget_message")
            result = []
            for el in message_elements[:max_msgs]:
                text_el = el.query_selector(".tgme_widget_message_text")
                if not text_el:
                    continue
                text = text_el.inner_text().strip()
                if not text:
                    continue
                # Extract timestamp
                time_el = el.query_selector(".tgme_widget_message_date")
                if not time_el:
                    time_el = el.query_selector("time")
                timestamp = time_el.inner_text().strip() if time_el else None
                result.append((text, timestamp))
            return result if result else None
        except Exception as e:
            print(f"[Playwright] Error: {e}")
            return None
        finally:
            browser.close()

def fetch_messages(channel: str, max_msgs: int, progress_callback=None, status_callback=None):
    """Returns list of (message_text, timestamp) or None"""
    if status_callback:
        status_callback("Using curl_cffi...")
    messages = fetch_with_curl_cffi(channel, max_msgs)
    if messages:
        return messages
    if status_callback:
        status_callback("curl_cffi failed, falling back to Playwright...")
    messages = fetch_with_playwright(channel, max_msgs)
    return messages if messages else None

# ----------------------------- GUI -----------------------------
class TelegramFetcherGUI:
    def __init__(self, root):
        self.root = root
        root.title("Telegram Channel Reader")
        root.geometry("750x700")
        root.resizable(True, True)
        root.configure(bg='#f0f2f5')

        self.font_family = "Calibri"
        self.default_font = (self.font_family, 10)
        self.heading_font = (self.font_family, 12, "bold")
        self.output_font = (self.font_family, 10)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('.', background='#f0f2f5', font=self.default_font)
        style.configure('TLabel', background='#f0f2f5', font=self.default_font)
        style.configure('TButton', font=self.default_font, padding=6)
        style.configure('TEntry', font=self.default_font, padding=4)
        style.configure('TSpinbox', font=self.default_font)
        style.configure('Header.TLabel', font=self.heading_font, foreground='#1a73e8')
        style.configure('Hint.TLabel', font=(self.font_family, 9), foreground='#5f6368')
        style.configure('Status.TLabel', font=(self.font_family, 9, 'italic'), foreground='#5f6368')
        style.configure('Count.TLabel', font=(self.font_family, 9), foreground='#1e8e3e')

        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Channel username (without @):", style='Header.TLabel').grid(row=0, column=0, sticky='w', pady=(0,5))
        input_frame = ttk.Frame(main_frame)
        input_frame.grid(row=1, column=0, sticky='ew', pady=(0,5))
        input_frame.columnconfigure(0, weight=1)
        self.channel_var = tk.StringVar(value=DEFAULT_CHANNEL)
        channel_entry = ttk.Entry(input_frame, textvariable=self.channel_var, width=35, font=self.default_font)
        channel_entry.grid(row=0, column=0, sticky='ew', padx=(0,10))
        self.fetch_btn = ttk.Button(input_frame, text="Fetch Messages", command=self.start_fetch)
        self.fetch_btn.grid(row=0, column=1)

        suggestions = "💡 Suggestions: cataphract1 • shin_persian • iranintltv • excition_missile_program"
        hint_label = ttk.Label(main_frame, text=suggestions, style='Hint.TLabel')
        hint_label.grid(row=2, column=0, sticky='w', pady=(0,10))

        ttk.Label(main_frame, text="Max messages:", style='Header.TLabel').grid(row=3, column=0, sticky='w', pady=(0,5))
        self.max_var = tk.IntVar(value=DEFAULT_MAX_MSGS)
        max_spin = ttk.Spinbox(main_frame, from_=1, to=50, textvariable=self.max_var, width=10, font=self.default_font)
        max_spin.grid(row=4, column=0, sticky='w', pady=(0,15))

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel')
        status_label.grid(row=5, column=0, sticky='w', pady=(0,5))

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, sticky='ew', pady=(0,10))

        # Message count label
        self.count_var = tk.StringVar(value="0 messages")
        count_label = ttk.Label(main_frame, textvariable=self.count_var, style='Count.TLabel')
        count_label.grid(row=7, column=0, sticky='w', pady=(0,5))

        ttk.Label(main_frame, text="Messages:", style='Header.TLabel').grid(row=8, column=0, sticky='w', pady=(0,5))
        output_frame = ttk.Frame(main_frame)
        output_frame.grid(row=9, column=0, sticky='nsew', pady=(0,10))
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

        self.output_text = tk.Text(
            output_frame, wrap=tk.WORD, font=self.output_font,
            bg='#ffffff', fg='#202124', padx=12, pady=8,
            relief='flat', borderwidth=1, highlightthickness=1,
            highlightbackground='#dadce0', highlightcolor='#1a73e8'
        )
        scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        self.output_text.configure(yscrollcommand=scrollbar.set)
        self.output_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        self.output_text.tag_configure('rtl', justify='right', spacing3=8, lmargin1=10, lmargin2=10, rmargin=10)
        self.output_text.tag_configure('ltr', justify='left', spacing3=8, lmargin1=10, lmargin2=10, rmargin=10)

        # Button frame for extra actions
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=10, column=0, sticky='ew', pady=(0,5))
        action_frame.columnconfigure(0, weight=1)
        ttk.Button(action_frame, text="📁 Export to File", command=self.export_messages).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="📋 Copy All", command=self.copy_messages).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="🗑 Clear", command=self.clear_output).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="ℹ About", command=self.about_dialog).pack(side=tk.LEFT, padx=5)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(9, weight=1)
        channel_entry.focus_set()

        # Internal storage for fetched messages with timestamps
        self.last_fetched_data = []  # list of (text, timestamp)

    def start_fetch(self):
        self.fetch_btn.config(state=tk.DISABLED)
        self.output_text.delete(1.0, tk.END)
        self.progress.start(10)
        self.status_var.set("Fetching...")
        thread = threading.Thread(target=self._fetch_worker, daemon=True)
        thread.start()

    def _fetch_worker(self):
        channel = self.channel_var.get().strip().lstrip('@')
        if not channel:
            self.root.after(0, self._on_fetch_done, [], "Channel name cannot be empty")
            return
        max_msgs = self.max_var.get()
        def update_status(msg):
            self.root.after(0, lambda: self.status_var.set(msg))
        messages_with_ts = fetch_messages(channel, max_msgs, status_callback=update_status)
        self.root.after(0, self._on_fetch_done, messages_with_ts)

    def _insert_message(self, index, message):
        """Insert a single message with proper RTL/LTR formatting."""
        msg = message.strip()
        if not msg:
            return
        formatted = f"{index}. {msg}"
        if has_rtl_chars(msg):
            isolated_msg = f"\u2067{formatted}\u2069"
            self.output_text.insert(tk.END, isolated_msg + "\n\n", 'rtl')
        else:
            self.output_text.insert(tk.END, formatted + "\n\n", 'ltr')

    def _on_fetch_done(self, messages_with_ts, error_msg=None):
        self.progress.stop()
        self.fetch_btn.config(state=tk.NORMAL)
        if error_msg:
            self.status_var.set(f"Error: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return
        if not messages_with_ts:
            self.status_var.set("No messages found. Check channel name or Google Translate IP.")
            messagebox.showwarning("No messages", "Could not retrieve any messages.\nCheck if the channel is public or your custom IP is correct.")
            self.last_fetched_data = []
            self.count_var.set("0 messages")
            return
        self.last_fetched_data = messages_with_ts
        self.output_text.delete(1.0, tk.END)
        for i, (msg, _) in enumerate(messages_with_ts, 1):
            self._insert_message(i, msg)
        self.status_var.set(f"Fetched {len(messages_with_ts)} messages.")
        self.count_var.set(f"{len(messages_with_ts)} messages")
        self.output_text.see(tk.END)

    def export_messages(self):
        """Export current messages (with timestamps if available) to a text file."""
        if not self.last_fetched_data:
            messagebox.showinfo("No data", "No messages to export. Please fetch messages first.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Messages"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"Telegram Channel: @{self.channel_var.get().strip().lstrip('@')}\n")
                f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n\n")
                for idx, (text, timestamp) in enumerate(self.last_fetched_data, 1):
                    if timestamp:
                        f.write(f"[{idx}] {timestamp}\n")
                    else:
                        f.write(f"[{idx}]\n")
                    f.write(f"{text}\n\n")
            messagebox.showinfo("Export Complete", f"Messages exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not save file:\n{str(e)}")

    def copy_messages(self):
        """Copy all displayed messages (plain text) to clipboard."""
        if not self.output_text.get(1.0, tk.END).strip():
            messagebox.showinfo("Nothing to copy", "No messages to copy.")
            return
        text_content = self.output_text.get(1.0, tk.END).strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(text_content)
        self.status_var.set(f"Copied {len(self.last_fetched_data)} messages to clipboard.")

    def clear_output(self):
        """Clear the output text area and reset stored data."""
        self.output_text.delete(1.0, tk.END)
        self.last_fetched_data = []
        self.count_var.set("0 messages")
        self.status_var.set("Cleared.")

    def about_dialog(self):
        """Show about information."""
        about_text = (
            "Telegram Channel Reader\n"
            "Version 2.0\n\n"
            "Fetches public Telegram channel messages via Google Translate proxy.\n"
            "Features:\n"
            "RTL support for Persian/Arabic\n"
            "Uses curl_cffi + Playwright fallback."
        )
        messagebox.showinfo("About", about_text)

def main():
    root = tk.Tk()
    app = TelegramFetcherGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()