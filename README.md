# DAMANOLA PTY LTD — Render / GitHub Project

Professional Flask business website for Damanola Pty Ltd.

## GitHub folder structure

damanola-pty-ltd/
├── app.py
├── requirements.txt
├── render.yaml
├── README.md
├── .gitignore
├── templates/
│   ├── index.html
│   ├── sitemap.xml
│   └── admin/
│       ├── login.html
│       └── dashboard.html
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│       └── company-poster.png
└── instance/

## Website features
- Responsive professional design
- Hero section based on the supplied poster
- Services section
- Company/about section
- Project/work showcase
- Free quote form
- WhatsApp quote integration
- Click-to-call
- Email contact
- FAQ
- Mobile floating WhatsApp button
- SEO metadata
- robots.txt
- sitemap.xml
- Health-check API
- SQLite quote database
- Admin dashboard
- Admin quote/lead status management
- Admin service management
- Render deployment configuration
- GitHub-ready structure

## Run on Pydroid 3

Install:
pip install -r requirements.txt

Run:
python app.py

Open:
http://127.0.0.1:5000

## Deploy on Render

Push the whole folder to GitHub.

Render Build Command:
pip install -r requirements.txt

Render Start Command:
gunicorn app:app

The included render.yaml can also be used.

## Admin

Open:
https://YOUR-RENDER-DOMAIN/admin/login

Set an environment variable on Render:
ADMIN_PASSWORD = your strong admin password

Do NOT use the fallback password in production.

## Important database note

The SQLite database is included for simple deployment and testing. Render's free web service filesystem is not intended for permanent database storage. For a production site where quote records must survive deployments/restarts, connect the app to a managed PostgreSQL database.
