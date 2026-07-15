import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "QueueNova123"

DATABASE = os.path.join("database", "queue.db")


# ================= DATABASE =================

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            token_number INTEGER NOT NULL,
            status TEXT DEFAULT 'Waiting'
        )
    """)

    conn.commit()
    conn.close()


# ================= HOME =================

@app.route("/")
def home():
    return render_template("index.html")


# ================= REGISTER =================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )

        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ================= LOGIN =================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()

        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        print("Email:", email)
        print("Password:", password)
        print("User:", user)

        conn.close()

        if user:
            session["user_email"] = user["email"]
            return redirect(url_for("dashboard"))
        else:
            return "Invalid Email or Password"

    return render_template("login.html")

# ================= LOGOUT =================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ================= USER DASHBOARD =================

@app.route("/dashboard")
def dashboard():

    if "user_email" not in session:
        return redirect(url_for("login"))

    return render_template("user_dashboard.html")


# ================= BOOK TOKEN =================
@app.route("/book-token")
def book_token():

    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    # Check if user already has a waiting token
    existing = conn.execute(
        """
        SELECT *
        FROM tokens
        WHERE user_email=? AND status='Waiting'
        """,
        (session["user_email"],)
    ).fetchone()

    if existing:
        conn.close()
        return f"You already have Token Q{existing['token_number']:03d}"

    # Get last token number
    last_token = conn.execute(
        "SELECT MAX(token_number) FROM tokens"
    ).fetchone()[0]

    if last_token is None:
        next_token = 1
    else:
        next_token = last_token + 1

    # Insert new token
    conn.execute(
        "INSERT INTO tokens (user_email, token_number) VALUES (?, ?)",
        (session["user_email"], next_token)
    )

    conn.commit()
    conn.close()

    return f"Your Token Number is Q{next_token:03d}"




# ================= MY TOKENS =================
 

@app.route("/my-tokens")
def my_tokens():

    if "user_email" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    tokens = conn.execute(
        "SELECT * FROM tokens WHERE user_email=?",
        (session["user_email"],)
    ).fetchall()

    conn.close()

    return render_template("my_tokens.html", tokens=tokens)


# ================= ADMIN DASHBOARD =================

@app.route("/admin")
def admin():

    conn = get_db_connection()

    total = conn.execute(
        "SELECT COUNT(*) FROM tokens"
    ).fetchone()[0]

    waiting = conn.execute(
        "SELECT COUNT(*) FROM tokens WHERE status='Waiting'"
    ).fetchone()[0]

    called = conn.execute(
        "SELECT COUNT(*) FROM tokens WHERE status='Called'"
    ).fetchone()[0]

    completed = conn.execute(
        "SELECT COUNT(*) FROM tokens WHERE status='Completed'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        total=total,
        waiting=waiting,
        called=called,
        completed=completed
    )

# ================= ALL TOKENS =================

@app.route("/all-tokens")
def all_tokens():

    conn = get_db_connection()

    tokens = conn.execute(
        "SELECT * FROM tokens ORDER BY token_number"
    ).fetchall()

    conn.close()

    return render_template("all_tokens.html", tokens=tokens)


# ================= NEXT TOKEN =================

@app.route("/next-token")
def next_token():

    conn = get_db_connection()

    token = conn.execute("""
        SELECT *
        FROM tokens
        WHERE status='Waiting'
        ORDER BY token_number
        LIMIT 1
    """).fetchone()

    if token:

        conn.execute("""
            UPDATE tokens
            SET status='Called'
            WHERE id=?
        """, (token["id"],))

        conn.commit()

        message = f"Now Calling Token Q{token['token_number']:03d}"

    else:

        message = "No Waiting Tokens"

    conn.close()

    return message

@app.route("/complete-token")
def complete_token():

    conn = get_db_connection()

    token = conn.execute("""
        SELECT *
        FROM tokens
        WHERE status='Called'
        ORDER BY token_number
        LIMIT 1
    """).fetchone()

    if token:

        conn.execute("""
            UPDATE tokens
            SET status='Completed'
            WHERE id=?
        """, (token["id"],))

        conn.commit()

        message = f"Token Q{token['token_number']:03d} Completed"

    else:
        message = "No Called Token"

    conn.close()

    return message


@app.route("/reset-queue")
def reset_queue():

    conn = get_db_connection()

    conn.execute("DELETE FROM tokens")

    conn.commit()
    conn.close()

    return "Queue Reset Successfully"
# ================= QUEUE STATUS =================

@app.route("/queue-status")
def queue_status():

    conn = get_db_connection()

    current = conn.execute("""
        SELECT *
        FROM tokens
        WHERE status='Called'
        ORDER BY token_number DESC
        LIMIT 1
    """).fetchone()

    conn.close()

    return render_template("queue_status.html", current=current)


# ================= RUN =================

if __name__ == "__main__":
    create_table()
    app.run(debug=True)