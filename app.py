from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_from_directory
)
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey" 

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "risha"
app.config["MYSQL_DB"] = "lost_found_db"

mysql = MySQL(app)

BASE_STATIC = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_LOST   = os.path.join(BASE_STATIC, "uploads", "lost")
UPLOAD_FOUND  = os.path.join(BASE_STATIC, "uploads", "found")
UPLOAD_PROOFS = os.path.join(BASE_STATIC, "uploads", "proofs")

for folder in (UPLOAD_LOST, UPLOAD_FOUND, UPLOAD_PROOFS):
    os.makedirs(folder, exist_ok=True)

ALLOWED_IMAGES = {"jpg", "jpeg", "png", "gif", "webp"}
ALLOWED_PROOF  = {"jpg", "jpeg", "png", "gif", "webp", "pdf"}

def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

# Small helper so templates can easily build image URLs (and show a placeholder)
@app.template_filter("imgurl")
def imgurl_filter(rel_path):
    if rel_path:
        return url_for("static", filename=rel_path)
    return url_for("static", filename="placeholder.png")


# 1) First page → info.html
@app.route("/")
def project_info():
    return render_template("info.html")

# 2) Landing page → index.html
@app.route("/home")
def index():
    return render_template("index.html")

# 3) Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM User WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

       
        if user and user["password"] == password:
            session["user_id"]  = user["user_id"]
            session["name"]     = user["name"]
            session["is_admin"] = int(user.get("is_admin", 0))
            flash(f"Welcome, {user['name']}!", "success")
            return redirect(url_for("index"))

        flash("Incorrect email or password!", "danger")

    return render_template("login.html")

# 4) Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("project_info"))

# 5) Register
@app.route("/register", methods=["POST"])
def register():
    name     = request.form.get("name", "").strip()
    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    contact  = request.form.get("contact_number", "").strip()
    branch   = request.form.get("branch", "").strip()
    semester = request.form.get("semester", "").strip() or None
    street   = request.form.get("address_street", "").strip()
    city     = request.form.get("address_city", "").strip()
    pin      = request.form.get("address_pincode", "").strip()

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        flash("Invalid email!", "danger")
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT 1 FROM User WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        flash("Email already exists!", "danger")
        return redirect(url_for("login"))

    cur.execute("""
        INSERT INTO User
        (name, email, contact_number, password, branch, semester, address_street, address_city, address_pincode)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (name, email, contact, password, branch, semester, street, city, pin))
    mysql.connection.commit()
    cur.close()

    flash("Account created! Please login.", "success")
    return redirect(url_for("login"))

# 6) Report Lost Item
@app.route("/lost", methods=["GET", "POST"])
def lost():
    if request.method == "POST":
        category   = request.form.get("category", "").strip()
        desc       = request.form.get("description", "").strip()
        date_lost  = request.form.get("date_lost", "").strip()
        location   = request.form.get("location_lost", "").strip()
        user_id    = session.get("user_id", 1)  # demo fallback

        image_rel = None
        file = request.files.get("image")
        if file and file.filename:
            if not allowed_file(file.filename, ALLOWED_IMAGES):
                flash("Invalid image format!", "danger")
                return redirect(url_for("lost"))
            fname = f"lost_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_LOST, fname))
            image_rel = f"uploads/lost/{fname}"

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            INSERT INTO Lost_Item (category, description, date_lost, location_lost, image_path, user_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (category, desc, date_lost, location, image_rel, user_id))
        mysql.connection.commit()
        cur.close()

        flash("Lost item reported!", "success")
        return redirect(url_for("lost_list"))

    return render_template("lost.html")

# 7) Report Found Item
@app.route("/found", methods=["GET", "POST"])
def found():
    if request.method == "POST":
        category   = request.form.get("category", "").strip()
        desc       = request.form.get("description", "").strip()
        date_found = request.form.get("date_found", "").strip()
        location   = request.form.get("location_found", "").strip()
        status     = request.form.get("status", "unclaimed")
        user_id    = session.get("user_id", 1)

        image_rel = None
        file = request.files.get("image")
        if file and file.filename:
            if not allowed_file(file.filename, ALLOWED_IMAGES):
                flash("Invalid image format!", "danger")
                return redirect(url_for("found"))
            fname = f"found_{int(datetime.now().timestamp())}_{secure_filename(file.filename)}"
            file.save(os.path.join(UPLOAD_FOUND, fname))
            image_rel = f"uploads/found/{fname}"

        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("""
            INSERT INTO Found_Item (category, description, date_found, location_found, status, image_path, user_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (category, desc, date_found, location, status, image_rel, user_id))
        mysql.connection.commit()
        cur.close()

        flash("Found item posted!", "success")
        return redirect(url_for("found_list"))

    return render_template("found.html")

# 8) View Lost Items + Search
@app.route("/lost-items")
def lost_list():
    q = request.args.get("q", "").strip()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if q:
        like = f"%{q}%"
        cur.execute("""
            SELECT * FROM Lost_Item
            WHERE category LIKE %s
               OR description LIKE %s
               OR location_lost LIKE %s
            ORDER BY date_lost DESC, created_at DESC
        """, (like, like, like))
    else:
        cur.execute("SELECT * FROM Lost_Item ORDER BY date_lost DESC, created_at DESC")
    items = cur.fetchall()
    cur.close()
    return render_template("lost_list.html", items=items, q=q)

# 9) View Found Items + Search
@app.route("/found-items")
def found_list():
    q = request.args.get("q", "").strip()
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    if q:
        like = f"%{q}%"
        cur.execute("""
            SELECT * FROM Found_Item
            WHERE category LIKE %s
               OR description LIKE %s
               OR location_found LIKE %s
            ORDER BY date_found DESC, created_at DESC
        """, (like, like, like))
    else:
        cur.execute("SELECT * FROM Found_Item ORDER BY date_found DESC, created_at DESC")
    items = cur.fetchall()
    cur.close()
    return render_template("found_list.html", items=items, q=q)
@app.template_filter("imgurl")
def imgurl_filter(path):
    if not path or path.strip() == "":
        return url_for("static", filename="placeholder.png")

    p = path.replace("\\", "/")

    if p.startswith("static/"):
        return url_for("static", filename=p[7:])

    if p.startswith("/static/"):
        return url_for("static", filename=p[8:])

    return url_for("static", filename=p)

# 10) Matches page
@app.route("/matches")
def matches():
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            mr.match_id,
            mr.match_status,
            mr.matched_date,
            mr.created_at,
            l.category  AS lost_category,
            l.description AS lost_description,
            l.location_lost,
            l.image_path AS lost_image,
            f.found_id,
            f.description AS found_description,
            f.location_found,
            f.image_path AS found_image
        FROM Match_Record mr
        JOIN Lost_Item  l ON mr.lost_id = l.lost_id
        JOIN Found_Item f ON mr.found_id = f.found_id
        ORDER BY mr.matched_date DESC, mr.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    return render_template("matches.html", matches=rows)

# 11) Start claim (from a match)
# 11) Start claim (from a match)
@app.route("/claim", methods=["POST"])
def claim():
    match_id = request.form.get("match_id")

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT found_id FROM Match_Record WHERE match_id=%s", (match_id,))
    rec = cur.fetchone()
    cur.close()

    if not rec:
        flash("Invalid match.", "danger")
        return redirect(url_for("matches"))

    return render_template("claim_form.html", found_id=rec["found_id"])


# 12) Submit claim
@app.route("/submit_claim", methods=["POST"])
def submit_claim():
    name     = request.form.get("name", "").strip()
    found_id = request.form.get("found_id")
    proof    = request.files.get("proof")

    if not proof or not proof.filename:
        flash("Upload a proof file.", "danger")
        return redirect(url_for("matches"))

    if not allowed_file(proof.filename, ALLOWED_PROOF):
        flash("Invalid proof format!", "danger")
        return redirect(url_for("matches"))

    fname = f"proof_{int(datetime.now().timestamp())}_{secure_filename(proof.filename)}"
    proof.save(os.path.join(UPLOAD_PROOFS, fname))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        INSERT INTO Claim (claimant_name, proof_document, claim_status, found_id)
        VALUES (%s, %s, %s, %s)
    """, (name, f"uploads/proofs/{fname}", "pending", found_id))
    mysql.connection.commit()
    cur.close()

    flash("Claim submitted! Waiting for approval.", "success")
    return redirect(url_for("matches"))

# 13) Admin dashboard
def admin_only():
    return session.get("is_admin", 0) == 1

@app.route("/admin")
def admin_page():
    if not admin_only():
        flash("Admin only!", "danger")
        return redirect(url_for("login"))

    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("""
        SELECT 
            c.claim_id, c.claimant_name, c.claim_status, c.proof_document, c.created_at,
            f.found_id, f.description AS found_description, f.status AS found_status,
            f.image_path AS found_image
        FROM Claim c
        JOIN Found_Item f ON c.found_id = f.found_id
        ORDER BY c.created_at DESC
    """)
    claims = cur.fetchall()
    cur.close()
    return render_template("admin.html", claims=claims)
@app.route("/admin/approve/<int:claim_id>", methods=["POST"])
def approve_claim(claim_id):
    if not admin_only():
        return redirect(url_for("login"))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Claim SET claim_status='approved' WHERE claim_id=%s", (claim_id,))
    mysql.connection.commit()
    cur.close()
    flash("Claim approved.", "success")
    return redirect(url_for("admin_page"))  


@app.route("/admin/reject/<int:claim_id>", methods=["POST"])
def reject_claim(claim_id):
    if not admin_only():
        return redirect(url_for("login"))
    cur = mysql.connection.cursor()
    cur.execute("UPDATE Claim SET claim_status='rejected' WHERE claim_id=%s", (claim_id,))
    mysql.connection.commit()
    cur.close()
    flash("Claim rejected.", "info")
    return redirect(url_for("admin_page"))

@app.route("/static/uploads/<path:filename>")
def uploads(filename):
    return send_from_directory(os.path.join(BASE_STATIC, "uploads"), filename)

# Run
if __name__ == "__main__":
    app.run(debug=True, port=8000)
