

# 📡 Telegram Channel Reader

A Python GUI application that fetches and displays text messages from public Telegram channels using Google Translate as a proxy. Works without modifying your hosts file by using custom IP mapping.

![Screenshot](screenshot.png) <!-- optional: add a screenshot later -->

## ✨ Features

- 🚀 **Two fetch methods** – `curl_cffi` (fast, no browser) with fallback to `playwright`
- 🧩 **Custom DNS mapping** – you define IP→domain rules directly in the code
- ⚡ **Asynchronous fetching**

## 🔧 Requirements

- Python 3.7 or higher
- The following Python packages (install via pip):

```bash
pip install curl_cffi beautifulsoup4 playwright
playwright install chromium