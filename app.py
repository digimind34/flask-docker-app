from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
from psycopg2 import errors
import os
import time

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

DB_HOST = os.getenv("DB_HOST", "db")
DB_NAME = os.getenv("DB_NAME", "mydatabase")
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "mypassword")


def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


@app.route("/")
def home():
    retries = 5
    while retries > 0:
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT version();")
            db_version = cur.fetchone()[0]
            cur.close()
            conn.close()

            return render_template("home.html", db_version=db_version)

        except Exception as e:
            retries -= 1
            time.sleep(2)
            if retries == 0:
                return f"Database connection failed: {e}"


@app.route("/users")
def users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, email FROM users ORDER BY id;")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return render_template("users.html", users=rows)
    except Exception as e:
        return f"Error fetching users: {e}"


@app.route("/add-user", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()

        if not name or not email:
            flash("Name and email are required.", "error")
            return render_template("add_user.html", name=name, email=email)

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s)",
                (name, email)
            )
            conn.commit()
            cur.close()
            conn.close()

            flash("User added successfully.", "success")
            return redirect(url_for("users"))

        except Exception as e:
            if "duplicate key value violates unique constraint" in str(e):
                flash("That email already exists. Use a different email.", "error")
                return render_template("add_user.html", name=name, email=email)

            flash(f"Error adding user: {e}", "error")
            return render_template("add_user.html", name=name, email=email)

    return render_template("add_user.html", name="", email="")


@app.route("/delete-user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()

        flash("User deleted successfully.", "success")
        return redirect(url_for("users"))
    except Exception as e:
        flash(f"Error deleting user: {e}", "error")
        return redirect(url_for("users"))


@app.route("/edit-user/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        if request.method == "POST":
            name = request.form["name"].strip()
            email = request.form["email"].strip()

            if not name or not email:
                flash("Name and email are required.", "error")
                cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                cur.close()
                conn.close()
                return render_template("edit_user.html", user=user)

            try:
                cur.execute(
                    "UPDATE users SET name = %s, email = %s WHERE id = %s",
                    (name, email, user_id)
                )
                conn.commit()
                cur.close()
                conn.close()

                flash("User updated successfully.", "success")
                return redirect(url_for("users"))

            except Exception as e:
                conn.rollback()

                if "duplicate key value violates unique constraint" in str(e):
                    flash("That email already exists. Use a different email.", "error")
                else:
                    flash(f"Error updating user: {e}", "error")

                cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
                cur.close()
                conn.close()
                return render_template("edit_user.html", user=user)

        cur.execute("SELECT id, name, email FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user is None:
            return "User not found."

        return render_template("edit_user.html", user=user)

    except Exception as e:
        return f"Error editing user: {e}"


@app.route("/health")
def health():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1;")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "healthy"}, 200
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 500

if __name__ == "__main__":
    app.run()