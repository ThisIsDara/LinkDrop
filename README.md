# LinkDrop

A lightweight private web app for queueing and downloading URLs. Friends can submit URLs to a queue, and you can review and download them from an admin panel using your `dl` command.

## Features

- **Public Submit Page**: Friends can paste a URL and optional note to queue for download
- **Admin Dashboard**: Password-protected panel to view, filter, and manage submitted links
- **One-Click Download**: Trigger downloads using your existing `dl` command
- **Status Tracking**: Track pending, downloading, done, and failed status
- **Download Logs**: View stdout/stderr from each download attempt
- **Dark Mode UI**: Modern dark theme admin interface
- **Rate Limiting**: Protect against spam submissions
- **SQLite Database**: Lightweight, no external database required

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure

Copy `.env` and update with your settings:

```bash
cp .env .env.local
```

Key settings:
- `ADMIN_USERNAME` / `ADMIN_PASSWORD` - Admin login credentials
- `SECRET_KEY` - Flask secret key (change this!)

### 3. Run

```bash
python app.py
```

The app will start on `http://0.0.0.0:5000`.

## Usage

### Submit a Link

1. Open `http://your-server:5000`
2. Paste a URL
3. Optionally add a note
4. Click Submit

### Admin Panel

1. Go to `http://your-server:5000/login`
2. Enter admin credentials
3. View all submitted links
4. Use action buttons:
   - **DL** - Download Now (runs `dl URL`)
   - **OK** - Mark Done manually
   - **RT** - Retry (reset to pending)
   - **LG** - View Download Log
   - **X** - Delete link

## Deployment

### Systemd Service

Create `/etc/systemd/system/linkdrop.service`:

```ini
[Unit]
Description=LinkDrop URL Download Queue
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/linkdrop
ExecStart=/usr/bin/python /path/to/linkdrop/app.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable linkdrop
sudo systemctl start linkdrop
```

### nginx Reverse Proxy

Example config for `/etc/nginx/sites-available/linkdrop`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/linkdrop /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Production Considerations

1. Use a strong `SECRET_KEY`
2. Enable HTTPS with let's encrypt or valid cert
3. Consider running behind a VPN or authentication proxy
4. Monitor logs: `journalctl -u linkdrop -f`

## The `dl` Command

This app assumes you have a `dl` command available on your system that takes a URL as an argument.

Example wrapper script (`/usr/local/bin/dl`):

```bash
#!/bin/bash
# Your custom download logic
yt-dlp "$1"
```

Make it executable:

```bash
chmod +x /usr/local/bin/dl
```

## Project Structure

```
linkdrop/
├── app.py           # Main Flask application
├── requirements.txt # Python dependencies
├── .env            # Environment configuration
├── linkdrop.db     # SQLite database (created on first run)
├── templates/
│   ├── submit.html # Public submit page
│   ├── login.html # Admin login page
│   └── admin.html  # Admin dashboard
└── static/
    ├─�� style.css   # Styles
    └── admin.js    # Admin JavaScript
```

## Security Notes

- Change default admin credentials
- Use a strong SECRET_KEY
- Consider restricting access to local network or VPN
- Rate limiting is enabled by default (10 submissions/hour per IP)