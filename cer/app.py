from flask import Flask, request, jsonify, send_file, render_template
import mysql.connector
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os

app = Flask(__name__)

# ---------------- MySQL Connection ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="0000",  # replace with your MySQL password
    database="certificate_portal"
)
cursor = db.cursor(dictionary=True)

# ---------------- Serve HTML Files ----------------
@app.route("/")
def home_page():
    return render_template("index.html")  # index.html inside /templates

@app.route("/student")
def student_page():
    return render_template("student.html")

@app.route("/staff")
def staff_page():
    return render_template("staff.html")
@app.route("/login")
def login_page():
    return render_template("login.html")


# ---------------- Student APIs ----------------
@app.route("/api/request_certificate", methods=["POST"])
def request_certificate():
    data = request.get_json()
    name = data.get("name", "").strip()
    if name:
        cursor.execute("INSERT INTO requests (student_name) VALUES (%s)", (name,))
        db.commit()
        return jsonify({"message": "Request submitted successfully."})
    return jsonify({"error": "Name is required."}), 400


@app.route("/api/check_status", methods=["POST"])
def check_status():
    data = request.get_json()
    name = data.get("name", "").strip()
    cursor.execute(
        "SELECT * FROM requests WHERE student_name=%s ORDER BY id DESC LIMIT 1",
        (name,)
    )
    req = cursor.fetchone()
    if req:
        return jsonify(req)
    return jsonify({"error": "No request found."}), 404


# ---------------- Staff APIs ----------------
@app.route("/api/get_requests")
def get_requests():
    cursor.execute("SELECT * FROM requests ORDER BY created_at DESC")
    requests = cursor.fetchall()
    return jsonify(requests)


@app.route("/api/approve/<int:req_id>", methods=["POST"])
def approve_request(req_id):
    cursor.execute("UPDATE requests SET status='approved' WHERE id=%s", (req_id,))
    db.commit()
    return jsonify({"message": "Approved"})


@app.route("/api/reject/<int:req_id>", methods=["POST"])
def reject_request(req_id):
    cursor.execute("UPDATE requests SET status='rejected' WHERE id=%s", (req_id,))
    db.commit()
    return jsonify({"message": "Rejected"})


# ---------------- Certificate Download ----------------
@app.route("/api/download/<int:req_id>")
def download_certificate(req_id):
    cursor.execute("SELECT * FROM requests WHERE id=%s", (req_id,))
    req = cursor.fetchone()
    if not req or req["status"] != "approved":
        return "Certificate not available."

    # Certificate template path
    cert_path = os.path.join("static", "assets", "img", "certificate_template.png")
    if not os.path.exists(cert_path):
        return "Template not found. Please check static/assets/img/certificate_template.png"

    img = Image.open(cert_path)
    draw = ImageDraw.Draw(img)

    # Font path
    font_path = os.path.join("static", "fonts", "arial.ttf")
    if not os.path.exists(font_path):
        return "Font not found. Please add arial.ttf to static/fonts."

    font = ImageFont.truetype(font_path, 48)

    # Student name
    text = req["student_name"]
    w, h = draw.textsize(text, font=font)
    img_width, img_height = img.size
    draw.text(((img_width - w) / 2, img_height - 200), text, fill="black", font=font)

    # Save as PDF in memory
    pdf_bytes = BytesIO()
    img.save(pdf_bytes, format="PDF")
    pdf_bytes.seek(0)

    return send_file(pdf_bytes, as_attachment=True, download_name="certificate.pdf")


# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
