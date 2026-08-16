import os, sqlite3, secrets
from functools import wraps
from urllib.parse import quote as urlquote
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

app=Flask(__name__)
app.secret_key=os.environ.get("SECRET_KEY","change-this-secret")
BASE=os.path.dirname(os.path.abspath(__file__))
DB_PATH=os.environ.get("DB_PATH",os.path.join(BASE,"instance","damanola.db"))
UPLOAD=os.path.join(BASE,"static","uploads","products")
os.makedirs(os.path.dirname(DB_PATH),exist_ok=True); os.makedirs(UPLOAD,exist_ok=True)

COMPANY={"name":"Damanola Pty Ltd","phone":"067 030 0655","whatsapp":"27670300655",
"email":"Mcdbarber@outlook.com","location":"Pretoria, South Africa","facebook":"Damanola Pty ltd"}

def db():
    c=sqlite3.connect(DB_PATH); c.row_factory=sqlite3.Row; return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS quotes(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,phone TEXT NOT NULL,email TEXT,
      service TEXT,location TEXT,message TEXT NOT NULL,status TEXT DEFAULT 'New',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,category TEXT,description TEXT,
      tag TEXT,image TEXT NOT NULL,active INTEGER DEFAULT 1,created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
    c.execute("""CREATE TABLE IF NOT EXISTS services(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT NOT NULL,
      active INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS site_settings(
      id INTEGER PRIMARY KEY CHECK(id=1),maintenance INTEGER DEFAULT 0)""")
    c.execute("INSERT OR IGNORE INTO site_settings(id,maintenance) VALUES(1,0)")
    if c.execute("SELECT COUNT(*) FROM services").fetchone()[0]==0:
        c.executemany("INSERT INTO services(name,description) VALUES(?,?)",[
        ("Steel & Wood Furniture","Custom furniture, counters, shelving, frames and fabrication."),
        ("Security Fencing","Strong, practical fencing solutions for homes and businesses."),
        ("Security Gates","Custom steel gates designed around your property."),
        ("Stall Erection","Fabrication and erection of stalls and structures."),
        ("Signage Boards","Custom fabricated boards for businesses, events and projects.")])
    c.commit(); c.close()
init_db()

def admin_required(f):
    @wraps(f)
    def w(*a,**k):
        if not session.get("admin"): return redirect(url_for("admin_login"))
        return f(*a,**k)
    return w

@app.context_processor
def inject(): return {"company":COMPANY}

@app.before_request
def maintenance_guard():
    if request.path.startswith("/admin") or request.path.startswith("/static") or request.path=="/api/health": return
    c=db(); s=c.execute("SELECT maintenance FROM site_settings WHERE id=1").fetchone(); c.close()
    if s and s["maintenance"]: return render_template("maintenance.html"),503

@app.route("/")
def index():
    c=db(); services=c.execute("SELECT * FROM services WHERE active=1").fetchall()
    products=c.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall(); c.close()
    return render_template("index.html",services=services,products=products)

@app.route("/quote",methods=["POST"])
def quote():
    name=request.form.get("name","").strip(); phone=request.form.get("phone","").strip()
    email=request.form.get("email","").strip(); service=request.form.get("service","").strip()
    location=request.form.get("location","").strip(); message=request.form.get("message","").strip()
    if not name or not phone or not message:
        flash("Please complete your name, phone number and project details.","error")
        return redirect(url_for("index")+"#quote")
    c=db(); c.execute("INSERT INTO quotes(name,phone,email,service,location,message) VALUES(?,?,?,?,?,?)",
                      (name,phone,email,service,location,message)); c.commit(); c.close()
    text=f"""Hello Damanola Pty Ltd,

I would like a FREE QUOTE.

Name: {name}
Phone: {phone}
Service: {service}
Location: {location}
Project details: {message}"""
    return redirect("https://wa.me/"+COMPANY["whatsapp"]+"?text="+urlquote(text))

@app.route("/api/health")
def health(): return jsonify(status="ok")

@app.route("/admin/login",methods=["GET","POST"])
def admin_login():
    if request.method=="POST":
        if secrets.compare_digest(request.form.get("password",""),os.environ.get("ADMIN_PASSWORD","change-me")):
            session["admin"]=True; return redirect(url_for("admin_dashboard"))
        flash("Incorrect password.","error")
    return render_template("admin/login.html")

@app.route("/admin/logout")
def admin_logout(): session.clear(); return redirect(url_for("admin_login"))

@app.route("/admin")
@app.route("/dashboard")
@admin_required
def admin_dashboard():
    c=db()
    quotes=c.execute("SELECT * FROM quotes ORDER BY id DESC").fetchall()
    products=c.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    services=c.execute("SELECT * FROM services WHERE active=1 ORDER BY id").fetchall()
    settings=c.execute("SELECT * FROM site_settings WHERE id=1").fetchone()
    stats={"quotes":c.execute("SELECT COUNT(*) FROM quotes").fetchone()[0],
           "new":c.execute("SELECT COUNT(*) FROM quotes WHERE status='New'").fetchone()[0],
           "products":c.execute("SELECT COUNT(*) FROM products WHERE active=1").fetchone()[0],
           "services":c.execute("SELECT COUNT(*) FROM services WHERE active=1").fetchone()[0]}
    c.close()
    return render_template("admin/dashboard.html",quotes=quotes,products=products,services=services,settings=settings,stats=stats)

@app.route("/admin/settings/maintenance",methods=["POST"])
@admin_required
def maintenance():
    enabled=1 if request.form.get("enabled")=="1" else 0
    c=db(); c.execute("UPDATE site_settings SET maintenance=? WHERE id=1",(enabled,)); c.commit(); c.close()
    flash("Maintenance mode updated."); return redirect(url_for("admin_dashboard"))

@app.route("/admin/quote/<int:q>/status",methods=["POST"])
@admin_required
def quote_status(q):
    status=request.form.get("status","New")
    if status not in {"New","Contacted","Quoted","Won","Closed"}: status="New"
    c=db(); c.execute("UPDATE quotes SET status=? WHERE id=?",(status,q)); c.commit(); c.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/product/add",methods=["POST"])
@admin_required
def add_product():
    name=request.form.get("name","").strip(); image=request.files.get("image")
    if not name or not image or not image.filename:
        flash("Product name and picture are required.","error"); return redirect(url_for("admin_dashboard"))
    ext=image.filename.rsplit(".",1)[-1].lower() if "." in image.filename else ""
    if ext not in {"png","jpg","jpeg","webp"}:
        flash("Use PNG, JPG, JPEG or WEBP.","error"); return redirect(url_for("admin_dashboard"))
    filename=secrets.token_hex(12)+"."+ext; image.save(os.path.join(UPLOAD,filename))
    c=db(); c.execute("INSERT INTO products(name,category,description,tag,image) VALUES(?,?,?,?,?)",
                      (name,request.form.get("category",""),request.form.get("description",""),
                       request.form.get("tag",""),filename)); c.commit(); c.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/product/<int:p>/delete",methods=["POST"])
@admin_required
def delete_product(p):
    c=db(); row=c.execute("SELECT image FROM products WHERE id=?",(p,)).fetchone()
    c.execute("UPDATE products SET active=0 WHERE id=?",(p,)); c.commit(); c.close()
    if row:
        path=os.path.join(UPLOAD,row["image"])
        if os.path.exists(path): os.remove(path)
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/service/add",methods=["POST"])
@admin_required
def add_service():
    name=request.form.get("name","").strip(); desc=request.form.get("description","").strip()
    if name and desc:
        c=db(); c.execute("INSERT INTO services(name,description) VALUES(?,?)",(name,desc)); c.commit(); c.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/service/<int:s>/delete",methods=["POST"])
@admin_required
def delete_service(s):
    c=db(); c.execute("UPDATE services SET active=0 WHERE id=?",(s,)); c.commit(); c.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/robots.txt")
def robots(): return "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n",200,{"Content-Type":"text/plain"}

@app.route("/sitemap.xml")
def sitemap(): return render_template("sitemap.xml"),200,{"Content-Type":"application/xml"}

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
