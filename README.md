# RTL_Reader

# 📡 Telegram Channel Reader

A beautiful Python GUI application that fetches and displays text messages from public Telegram channels using Google Translate as a proxy. Works without modifying your hosts file by using custom IP mapping. **Automatically detects Persian/Arabic (RTL) text and renders it correctly**, handling numbers, English words, and emojis within RTL messages.

![Screenshot](screenshot.png) <!-- optional: add a screenshot later -->

## ✨ Features

- 🖥️ **Clean, modern GUI** based on `tkinter` with Calibri font
- 🔄 **Automatic RTL detection** – Persian, Arabic, and mixed‑script messages displayed right‑aligned and correctly ordered
- 💡 **Channel suggestions** displayed as hints next to the input field
- 🚀 **Two fetch methods** – `curl_cffi` (fast, no browser) with fallback to `playwright`
- 🧩 **Custom DNS mapping** – you define IP→domain rules directly in the code (no system hosts file required)
- 🔘 **Handles “Preview channel” button** automatically for channels that need it
- 📝 **Numbered messages** for easy reference
- ⚡ **Asynchronous fetching** – GUI stays responsive

## 🔧 Requirements

- Python 3.7 or higher
- The following Python packages (install via pip):

```bash
pip install curl_cffi beautifulsoup4 playwright
playwright install chromium