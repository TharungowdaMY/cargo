from flask import Flask, render_template, request, redirect, session, jsonify
from database import get_db, init_db
from werkzeug.security import generate_password_hash, check_password_hash
RATE_CARD = {
    "General": 12,            # ₹12 per kg
    "Pharma": 20,
    "Dangerous Goods": 35,
    "High Value": 50,
    "Perishables": 18,
    "Animals": 40
}

app = Flask(__name__)
app.secret_key = "secret123"

#init_db()


# --------------------------
# AUTH HELPERS
# --------------------------
def is_logged_in():
    return "user_id" in session


def current_role():
    return session.get("role")


# --------------------------
# HOME
# --------------------------
@app.route("/")
def home():
    return render_template("index.html")


# --------------------------
# REGISTER
# --------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

        db = get_db()
        try:
            db.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)",
                       (username, password, role))
            db.commit()
            return redirect("/login")
        except:
            return "User already exists"

    return render_template("register.html")


# --------------------------
# LOGIN
# --------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            return redirect("/")
        return "Invalid credentials"

    return render_template("login.html")


# --------------------------
# LOGOUT
# --------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# --------------------------
# AIRLINE: Upload flight
# --------------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if current_role() != "airline":
        return "Unauthorized"

    if request.method == "POST":
        db = get_db()
        db.execute(
            """
            INSERT INTO flights(airline, flight_no, origin, destination, date, capacity, cargo_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.form["airline"],
                request.form["flight_no"],
                request.form["origin"],
                request.form["destination"],
                request.form["date"],
                request.form["capacity"],
                request.form["cargo_type"]
            )
        )
        db.commit()
        return render_template("upload.html", message="Flight uploaded!")

    return render_template("upload.html")

import csv
from werkzeug.utils import secure_filename
import os

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route("/upload_csv", methods=["GET", "POST"])
def upload_csv():
    if current_role() != "airline":
        return "Unauthorized"

    if request.method == "POST":
        if "csvfile" not in request.files:
            return "No file uploaded"

        file = request.files["csvfile"]
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        db = get_db()

        with open(filepath, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                date = row["date"].replace("/", "-").strip()

                # Convert DD-MM-YYYY to YYYY-MM-DD if needed
                parts = date.split("-")
                if len(parts[0]) == 2:
                    date = f"{parts[2]}-{parts[1]}-{parts[0]}"

                db.execute("""
                    INSERT INTO flights(airline, flight_no, origin, destination, date, capacity)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    row["airline"],
                    row["flight_no"],
                    row["origin"],
                    row["destination"],
                    date,
                    row["capacity"]
                ))

        db.commit()

        return render_template("upload_csv.html", message="CSV uploaded successfully!")

    return render_template("upload_csv.html")


# --------------------------
# SEARCH (AIRLINE view)
# --------------------------
@app.route("/search", methods=["GET", "POST"])
def search():
    if not is_logged_in():
        return redirect("/login")

    results = []
    interline = []

    if request.method == "POST":
        db = get_db()
        origin = request.form["origin"]
        dest = request.form["destination"]
        date = request.form["date"]
        cargo_type = request.form["cargo_type"]

        query = """
            SELECT * FROM flights 
            WHERE origin=? AND destination=? AND date=?
        """
        params = [origin, dest, date]

        if cargo_type:
            query += " AND cargo_type=?"
            params.append(cargo_type)

        results = db.execute(query, params).fetchall()

        first_legs = db.execute(
            "SELECT * FROM flights WHERE origin=? AND date=?",
            (origin, date)
        ).fetchall()

        second_legs = db.execute(
            "SELECT * FROM flights WHERE destination=? AND date=?",
            (dest, date)
        ).fetchall()

        for f1 in first_legs:
            for f2 in second_legs:
                if f1["destination"] == f2["origin"]:

                    if f1["cargo_type"] != f2["cargo_type"]:
                        continue

                    interline.append({
                        "legs": [f1, f2],
                        "capacity": min(f1["capacity"], f2["capacity"]),
                        "cargo_type": f1["cargo_type"]
                    })

    # remove duplicate interline routes
    unique = []
    seen = set()

    for r in interline:
        key = (r["legs"][0]["origin"], r["legs"][0]["destination"], r["legs"][1]["destination"], r["capacity"])
        if key not in seen:
            unique.append(r)
            seen.add(key)

    return render_template("search.html", results=results, interline=unique)


@app.route("/interline", methods=["GET", "POST"])
def interline():
    db = get_db()
    routes = []

    if request.method == "POST":
        origin = request.form["origin"].upper()
        destination = request.form["destination"].upper()
        date = request.form["date"]


        # Get all possible first-leg flights
        first_legs = db.execute(
            "SELECT * FROM flights WHERE origin=? AND date=?",
            (origin, date)
        ).fetchall()

        # Get all possible second-leg flights
        second_legs = db.execute(
            "SELECT * FROM flights WHERE destination=? AND date=?",
            (destination, date)
        ).fetchall()

        # MATCH INTERLINE CONNECTIONS
        for f1 in first_legs:
            for f2 in second_legs:
                if f1["destination"] == f2["origin"]:
                    routes.append({
                        "legs": [f1, f2],
                        "capacity": min(f1["capacity"], f2["capacity"])
                    })

    return render_template("interline.html", routes=routes)

# --------------------------
# FORWARDER SEARCH & BOOKING
# --------------------------
@app.route("/forwarder_search", methods=["GET", "POST"])
def forwarder_search():
    if current_role() != "forwarder":
        return "Unauthorized"

    db = get_db()
    results = []
    interline = []

    if request.method == "POST":
        origin = request.form["origin"]
        dest = request.form["destination"]
        date = request.form["date"]

        results = db.execute(
            "SELECT * FROM flights WHERE origin=? AND destination=? AND date=?",
            (origin, dest, date)).fetchall()

        first_legs = db.execute("SELECT * FROM flights WHERE origin=? AND date=?",
                                (origin, date)).fetchall()
        second_legs = db.execute("SELECT * FROM flights WHERE destination=? AND date=?",
                                 (dest, date)).fetchall()

        for f1 in first_legs:
            for f2 in second_legs:
                if f1["destination"] == f2["origin"]:
                    interline.append({
                        "legs": [f1, f2],
                        "capacity": min(f1["capacity"], f2["capacity"])
                    })

    unique = []
    seen = set()

    for r in interline:
        key = (r["legs"][0]["origin"], r["legs"][0]["destination"], r["legs"][1]["destination"], r["capacity"])
        if key not in seen:
            unique.append(r)
            seen.add(key)

    return render_template("forwarder_search.html", results=results, interline=unique)


# --------------------------
# BOOKING
# --------------------------
@app.route("/book", methods=["POST"])
def book():
    if current_role() != "forwarder":
        return "Unauthorized"

    db = get_db()
    flight_id = request.form["flight_id"]
    weight = int(request.form["weight"])

    # Fetch flight info
    flight = db.execute("SELECT * FROM flights WHERE id=?", (flight_id,)).fetchone()
    if not flight:
        return "Flight not found"

    if weight > flight["capacity"]:
        return "Not enough capacity"

    # PRICE CALCULATION
    cargo_type = flight["cargo_type"] or "General"
    rate = RATE_CARD.get(cargo_type, 15)
    total_price = rate * weight

    # Reduce flight capacity
    new_capacity = flight["capacity"] - weight
    db.execute("UPDATE flights SET capacity=? WHERE id=?", (new_capacity, flight_id))

    import time
    expires_at = int(time.time()) + 120  # 2 minutes

    # Create booking with pricing
    db.execute("""
        INSERT INTO bookings(user_id, flight_id, weight, status, expires_at, price, total, payment_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session["user_id"], flight_id, weight, "HOLD", expires_at, rate, total_price, "UNPAID"))

    db.commit()
    return redirect("/bookings")



# --------------------------
# VIEW BOOKINGS
# --------------------------
@app.route("/bookings")
def bookings_view():
    if not is_logged_in():
        return redirect("/login")

    db = get_db()
    import time
    now = int(time.time())

    # 1️⃣ Find expired HOLD bookings
    expired = db.execute(
        "SELECT * FROM bookings WHERE status='HOLD' AND expires_at < ?",
        (now,)
    ).fetchall()

    # 2️⃣ Auto-expire them + restore capacity
    for b in expired:
        flight = db.execute("SELECT * FROM flights WHERE id=?", (b["flight_id"],)).fetchone()

        # Restore capacity
        restored = flight["capacity"] + b["weight"]
        db.execute("UPDATE flights SET capacity=? WHERE id=?", (restored, b["flight_id"]))

        # Change status to EXPIRED
        db.execute("UPDATE bookings SET status='CANCELLED' WHERE id=?", (b["id"],))

    db.commit()

    bookings = db.execute("SELECT * FROM bookings").fetchall()

    return render_template("booking_management.html", bookings=bookings)




@app.route("/api/emirates")
def api_emirates():
    return jsonify([
        {"airline": "Emirates", "flight_no": "EK215", "origin": "DXB", "destination": "LAX", "date": "2025-12-10", "capacity": 9500, "cargo_type": "Pharma"},
        {"airline": "Emirates", "flight_no": "EK7", "origin": "DXB", "destination": "LHR", "date": "2025-12-10", "capacity": 8000, "cargo_type": "Dangerous Goods"}
    ])
@app.route("/api/qatar")
def api_qatar():
    return jsonify([
        {"airline": "Qatar Airways", "flight_no": "QR17", "origin": "DOH", "destination": "LHR", "date": "2025-12-10", "capacity": 8500, "cargo_type": "Pharma"},
        {"airline": "Qatar Airways", "flight_no": "QR571", "origin": "DEL", "destination": "DOH", "date": "2025-12-10", "capacity": 4800, "cargo_type": "General"}
    ])

@app.route("/api/lufthansa")
def api_lufthansa():
    return jsonify([
        {"airline": "Lufthansa", "flight_no": "LH401", "origin": "FRA", "destination": "JFK", "date": "2025-12-10", "capacity": 9000, "cargo_type": "Perishables"},
        {"airline": "Lufthansa", "flight_no": "LH900", "origin": "FRA", "destination": "LHR", "date": "2025-12-10", "capacity": 5500, "cargo_type": "General"}
    ])
@app.route("/api/klm")
def api_klm():
    return jsonify([
        {"airline": "KLM", "flight_no": "KL641", "origin": "AMS", "destination": "JFK", "date": "2025-12-10", "capacity": 6200, "cargo_type": "General"},
        {"airline": "KLM", "flight_no": "KL871", "origin": "DEL", "destination": "AMS", "date": "2025-12-10", "capacity": 4300, "cargo_type": "Perishables"}
    ])


@app.route("/api/british_airways")
def api_ba():
    return jsonify([
        {"airline": "British Airways", "flight_no": "BA108", "origin": "DXB", "destination": "LHR", "date": "2025-12-10", "capacity": 6500, "cargo_type": "High Value"},
        {"airline": "British Airways", "flight_no": "BA118", "origin": "DOH", "destination": "LHR", "date": "2025-12-10", "capacity": 7800, "cargo_type": "General"}
    ])

import requests

@app.route("/import_all_airlines", methods=["POST"])
def import_all_airlines():
    db = get_db()
    sources = [
        "http://127.0.0.1:5000/api/emirates",
        "http://127.0.0.1:5000/api/qatar",
        "http://127.0.0.1:5000/api/lufthansa",
        "http://127.0.0.1:5000/api/klm",
        "http://127.0.0.1:5000/api/british_airways"
    ]

    for url in sources:
        feed = requests.get(url).json()
        for f in feed:
            db.execute("""
                INSERT INTO flights(airline, flight_no, origin, destination, date, capacity, cargo_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (f["airline"], f["flight_no"], f["origin"], f["destination"], f["date"], f["capacity"], f["cargo_type"]))

    db.commit()
    return redirect("/big_feed")


@app.route("/big_feed")
def big_feed():
    flights = get_db().execute("SELECT * FROM flights WHERE capacity > 6000").fetchall()
    return render_template("big_airline_feed.html", flights=flights)

# --------------------------
# WORKSPACE
# --------------------------
@app.route("/workspace", methods=["GET", "POST"])
def workspace():
    db = get_db()
    if request.method == "POST":
        db.execute("INSERT INTO messages(sender,text) VALUES(?,?)",
                   (request.form["sender"], request.form["text"]))
        db.commit()

    messages = db.execute("SELECT * FROM messages").fetchall()
    return render_template("workspace.html", messages=messages)




@app.route("/confirm_booking", methods=["POST"])
def confirm_booking():
    booking_id = request.form["id"]

    db = get_db()
    b = db.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()

    import time
    now = int(time.time())

    if b["status"] != "HOLD":
        return "Cannot confirm"

    if now > b["expires_at"]:
        return "Hold expired"

    db.execute("UPDATE bookings SET status='CONFIRMED' WHERE id=?", (booking_id,))
    db.commit()

    return redirect("/bookings")


@app.route("/airline_optimizer")
def airline_optimizer():
    if current_role() != "airline":
        return "Unauthorized"

    db = get_db()

    flights = db.execute("SELECT * FROM flights").fetchall()
    bookings = db.execute("SELECT * FROM bookings WHERE status='CONFIRMED'").fetchall()

    total_capacity = sum(f["capacity"] for f in flights)
    total_used = sum(b["weight"] for b in bookings)
    unused_capacity = total_capacity - total_used

    # Per route breakdown
    route_stats = {}
    for f in flights:
        key = f"{f['origin']} → {f['destination']}"
        if key not in route_stats:
            route_stats[key] = {"capacity": 0, "used": 0}

        route_stats[key]["capacity"] += f["capacity"]

    for b in bookings:
        flight = db.execute("SELECT * FROM flights WHERE id=?", (b["flight_id"],)).fetchone()
        key = f"{flight['origin']} → {flight['destination']}"
        route_stats[key]["used"] += b["weight"]

    recommendations = []

    for route, stats in route_stats.items():
        capacity = stats["capacity"]
        used = stats["used"]
        unused = capacity - used

        if unused > capacity * 0.50:
            recommendations.append({
                "route": route,
                "message": "⚠ High unused space. Consider offering discounts or interline partnerships."
            })
        elif used > capacity * 0.90:
            recommendations.append({
                "route": route,
                "message": "🔥 High demand! Increase pricing or add more frequency."
            })

    return render_template("airline_optimizer.html",
                           flights=flights,
                           bookings=bookings,
                           total_capacity=total_capacity,
                           total_used=total_used,
                           unused_capacity=unused_capacity,
                           route_stats=route_stats,
                           recommendations=recommendations)

if __name__ == "__main__":
    with app.app_context():
        init_db()

    app.run(debug=True)
