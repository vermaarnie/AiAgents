from flask import Flask, request, jsonify, render_template, redirect, url_for, session, send_file
import sqlite3
import google.generativeai as genai
import os
from werkzeug.security import generate_password_hash, check_password_hash


# Initialize Flask app
app = Flask(__name__)
app.secret_key = "AIzaSyAUe5NcRRE0PaXRHYJSVyk3MM33wtXZZ4c"  # Required for using sessions

# Configure Gemini API
API_KEY = "AIzaSyAUe5NcRRE0PaXRHYJSVyk3MM33wtXZZ4c"  # Replace with your actual API key
genai.configure(api_key=API_KEY)

# Function to initialize the SQLite database
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL
                    )''')
    conn.commit()
    conn.close()

# Initialize database when the app starts
init_db()

# Function to get a response from Gemini AI
def get_gemini_response(user_input):
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(f"Provide only official government schemes in India for: {user_input}. Give eligibility, benefits, and links. No general information, only official schemes.")
        
        if not response or not response.text:
            return f"SchemeAI: I apologize, but there are no government schemes in India relevant to \"{user_input}\"."

        # Convert Markdown-style bold text and links to HTML
        formatted_response = response.text.replace("**", "<b>").replace("**", "</b>")
        
        # Corrected Link Formatting
        formatted_response = formatted_response.replace("](", '" target="_blank">').replace("[", '<a href="')
        formatted_response = formatted_response.replace(")", "</a>")

        return formatted_response.replace("\n", "<br>")

    except Exception as e:
        return f"Error: {str(e)}"


# **🔹 Route: Home Page (Login Page)**
@app.route("/")
def home():
    return render_template("login.html")

# **🔹 Route: Sign Up Page**

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)  # Hash password before saving

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for("home"))  # Redirect to login page after signup
        except sqlite3.IntegrityError:
            return "Error: Username already exists!"
    
    return render_template("signup.html")  # Ensure signup page renders correctly



# **🔹 Route: Login Authentication**
@app.route("/login", methods=["GET", "POST"])

def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):  # Verify hashed password
            session["username"] = username
            return redirect(url_for("chatbot_dashboard"))  # Redirect to chatbot
        else:
            return "Invalid username or password! <a href='/'>Try again</a>"

    return render_template("login.html")  # If method is GET, render login page

# **🔹 Route: Chatbot Dashboard**
@app.route("/chatbot")
def chatbot_dashboard():
    if "username" not in session:
        return redirect(url_for("home"))  # Redirect if not logged in
    return render_template("chatbot.html")

# **🔹 Route: Logout**
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

# **🔹 Route: Handle User Messages**
@app.route("/chat", methods=["POST"])
def chat():
    if "chat_history" not in session:
        session["chat_history"] = []

    user_input = request.json.get("message")
    response = get_gemini_response(user_input)
    session["chat_history"].append({"user": user_input, "schemeAI": response})
    session.modified = True

    return jsonify({"reply": response})

# **🔹 Route: Download Chat History**
@app.route("/download_chat", methods=["GET"])
def download_chat():
    file_path = "chat_history.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        if "chat_history" in session:
            for chat in session["chat_history"]:
                f.write(f"You: {chat['user']}\n")
                f.write(f"SchemeAI: {chat['schemeAI']}\n\n")

    return send_file(file_path, as_attachment=True)

# **✅ APP START ✅**
if __name__ == "__main__":
    app.run(debug=True)
