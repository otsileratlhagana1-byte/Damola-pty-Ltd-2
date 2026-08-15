import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-in-render")

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "instance", "damanola.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

COMPANY = {
    "name": "Damanola Pty Ltd",
    "location": "Pretoria, South Africa",
    "phone": "067 030 0655",
    "whatsapp": "27670300655",
    "email": "Mcdbarber@outlook.com",
    "facebook": "Damanola Pty ltd",
}

DEFAULT_SERVICES = [
    ("Steel & Wood Furniture", "Custom tables, counters, shelving, frames and furniture.", "01"),
    ("Security Fencing", "Strong fencing solutions designed around your property.", "02"),
    ("Security Gates", "Custom steel gates with a durable professional finish.", "03"),
    ("Stall Erection", "Fabrication and erection of stalls and structures.", "04"),
    ("Signage Boards", "Custom fabricated signage boards for businesses and events.", "05"),
]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT,
        service TEXT, location TEXT, message TEXT, status TEXT DEFAULT 'New',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, description TEXT NOT NULL, number TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )""")
    count = conn.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    if count == 0:
        conn.executemany("INSERT INTO services(name,description,number) VALUES(?,?,?)", DEFAULT_SERVICES)
    conn.commit()
    conn.close()

init_db()

def admin_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_company():
    return {"company": COMPANY}

@app.route("/")
def home():
    conn = db()
    services = conn.execute("SELECT * FROM services WHERE active=1 ORDER BY id").fetchall()
    conn.close()
    return render_template("index.html", services=services)

@app.route("/quote", methods=["POST"])
def quote():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    service = request.form.get("service", "").strip()
    location = request.form.get("location", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not phone or not message:
        flash("Please complete your name, phone number and project details.", "error")
        return redirect(url_for("home") + "#quote")

    conn = db()
    conn.execute(
        "INSERT INTO quotes(name,phone,email,service,location,message) VALUES(?,?,?,?,?,?)",
        (name, phone, email, service, location, message)
    )
    conn.commit()
    conn.close()

    text = (
        "Hello Damanola Pty Ltd,%0A%0A"
        "I would like a FREE QUOTE.%0A"
        f"Name: {name}%0APhone: {phone}%0A"
        f"Service: {service}%0ALocation: {location}%0A"
        f"Project details: {message}"
    )
    return redirect(f"https://wa.me/{COMPANY['whatsapp']}?text={quote(text)}")

@app.route("/contact", methods=["POST"])
def contact():
    return redirect(url_for("home") + "#quote")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form.get("password", "")
        expected = os.environ.get("ADMIN_PASSWORD", "change-me")
        if secrets.compare_digest(password, expected):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("Invalid password.", "error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db()
    quotes = conn.execute("SELECT * FROM quotes ORDER BY id DESC").fetchall()
    services = conn.execute("SELECT * FROM services ORDER BY id").fetchall()
    stats = {
        "quotes": conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0],
        "new": conn.execute("SELECT COUNT(*) FROM quotes WHERE status='New'").fetchone()[0],
        "services": conn.execute("SELECT COUNT(*) FROM services WHERE active=1").fetchone()[0],
    }
    conn.close()
    return render_template("admin/dashboard.html", quotes=quotes, services=services, stats=stats)

@app.route("/admin/quote/<int:quote_id>/status", methods=["POST"])
@admin_required
def quote_status(quote_id):
    status = request.form.get("status", "New")
    if status not in {"New", "Contacted", "Quoted", "Won", "Closed"}:
        status = "New"
    conn = db()
    conn.execute("UPDATE quotes SET status=? WHERE id=?", (status, quote_id))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/service/add", methods=["POST"])
@admin_required
def service_add():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    if name and description:
        conn = db()
        conn.execute("INSERT INTO services(name,description,number) VALUES(?,?,?)",
                     (name, description, f"{conn.execute('SELECT COUNT(*) FROM services').fetchone()[0]+1:02d}"))
        conn.commit()
        conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/service/<int:service_id>/delete", methods=["POST"])
@admin_required
def service_delete(service_id):
    conn = db()
    conn.execute("UPDATE services SET active=0 WHERE id=?", (service_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "service": "Damanola Pty Ltd website"})

@app.route("/robots.txt")
def robots():
    return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n", 200, {"Content-Type": "text/plain"}

@app.route("/sitemap.xml")
def sitemap():
    return render_template("sitemap.xml"), 200, {"Content-Type": "application/xml"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
