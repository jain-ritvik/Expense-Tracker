from flask import Flask, render_template, request, redirect, session
from datetime import datetime
import sqlite3
import database

app = Flask(__name__)
app.secret_key = "your-secret-key"

def get_connection():
    conn = sqlite3.connect("pyspend.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/login', methods = ["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("usersession.html")

    email = request.form["email"]
    password = request.form["password"]

    conn = get_connection()
    
    user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email,password)).fetchone()

    conn.close()

    if not user:
        return "Invalid credentials"
    
    session["user_id"] = user["id"]
    session["user_name"] = user["name"]

    return redirect("/")

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form["name"]
    email = request.form["email"]
    password = request.form["password"]
    confirm = request.form["confirm_password"]

    conn = get_connection()

    if password != confirm:
        return "Passwords do not match"
      
    try:
        conn.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, password)
        )
        conn.commit()

    except:
        return "User already exists"

    finally:
        conn.close()

    return redirect('/login')

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    # session.clear()     both do the same work
    return redirect("/login")

@app.route('/')
def home():
    if "user_id" not in session:
        return redirect('/login')
    
    current_monthYear = datetime.now().strftime("%B %Y")
    conn = get_connection()
    budget_percentage = 0
    
    income = conn.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM transactions
    WHERE transaction_type='income'
    AND user_id=?
    """,(session["user_id"],)).fetchone()[0]

    expenses = conn.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM transactions
    WHERE transaction_type='expense'
    AND user_id=?
    """, (session["user_id"],)).fetchone()[0]

    budget_row = conn.execute("""
    SELECT amount
    FROM budget
    WHERE user_id=?
    """, (session["user_id"],)).fetchone()

    transactions = conn.execute("""
    SELECT *
    FROM transactions
    WHERE user_id=?
    ORDER BY created_at DESC
    LIMIT 5
    """, (session["user_id"],)).fetchall()

    category_data = conn.execute("""
    SELECT category, SUM(amount) as total
    FROM transactions
    WHERE transaction_type='expense'
    AND user_id=?
    GROUP BY category
    """, (session["user_id"],)).fetchall()

    category_data = [dict(row) for row in category_data]

    monthly_data = conn.execute("""
    SELECT category,
        SUM(amount) as total
    FROM transactions
    WHERE transaction_type='expense'
    AND user_id=?
    GROUP BY category
    ORDER BY total DESC
    """, (session["user_id"],)).fetchall()

    monthly_data = [dict(row) for row in monthly_data]

    budget = float(budget_row["amount"]) if budget_row else 0.0
    budget = float(budget)

    conn.close()

    if budget == 0:
            budget_percentage = 0
            budget_color = "secondary"
            budget_message = "Set a budget first"

    else:
        budget_percentage = min((expenses / budget) * 100, 100)
        
        if budget_percentage < 70:
            budget_color = "success"
            budget_message = "Healthy spending"
        elif budget_percentage < 90:
            budget_color = "warning"
            budget_message = "Approaching budget limit"
        else:
            budget_color = "danger"
            budget_message = "Budget exceeded"

    savings = income - expenses

    if expenses > income:
        insight = "⚠️ Your expenses exceed your income."

    elif budget_percentage > 90:
        insight = "⚠️ You are close to your budget limit."

    else:
        insight = "✅ Your spending is under control."

    return render_template(
        "home.html",
        current_monthYear = current_monthYear,
        income=income,
        expenses=expenses,
        budget=budget,
        budgetPercentage=round(budget_percentage, 2),
        transactions=transactions,
        category_data=category_data,
        monthly_data=monthly_data,
        budgetColor=budget_color,
        budgetMessage=budget_message,
        insight = insight
    )

@app.route('/add-income', methods=['POST'])
def add_income():
    if "user_id" not in session:
        return redirect("/login")
    
    amount = request.form.get('amount')
    category = request.form.get('category')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO transactions
        (user_id, transaction_type, amount, category)
        VALUES (?, ?, ?, ?)
        """,
        (session["user_id"], "income", amount, category)
    )

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/add-expense', methods=['POST'])
def add_expense():
    if "user_id" not in session:
        return redirect("/login")

    amount = request.form.get('amount')
    category = request.form.get('category')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO transactions
        (user_id, transaction_type, amount, category)
        VALUES (?, ?, ?, ?)
        """,
        (session["user_id"], "expense", amount, category)
    )

    conn.commit()
    conn.close()

    # later: store in DB
    return redirect('/')

@app.route('/setBudget', methods = ['POST'])
def setBudget():
    if "user_id" not in session:
        return redirect("/login")

    amount = request.form.get('amount')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO budget
        (user_id, amount)
        VALUES (?, ?)
        """, (session["user_id"], amount)
    )

    conn.commit()
    conn.close()
    
    return redirect('/')

@app.route('/edit/<int:id>')
def edit_transaction(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()

    transaction = conn.execute(
        """
        SELECT *    
        FROM transactions
        WHERE id=?
        AND user_id=?
        """,
        (id, session["user_id"])
    ).fetchone()

    conn.close()

    return render_template(
        "edit.html",
        transaction=transaction
    )

@app.route('/delete/<int:id>', methods = ['POST'])
def delete_transaction(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_connection()

    conn.execute(
        "DELETE FROM transactions WHERE id=? AND user_id=?",
        (id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect(request.referrer or '/')

@app.route('/update/<int:id>', methods=['POST'])
def update_transaction(id):
    if "user_id" not in session:
        return redirect("/login")

    amount = request.form.get("amount")
    category = request.form.get("category")

    conn = get_connection()

    conn.execute(
        """
        UPDATE transactions
        SET amount=?, category=?
        WHERE id=? AND user_id=?
        """,
        (amount, category, id, session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect('/')

@app.route('/transactions', methods = ["POST", "GET"])
def transactions():
    user_id = session.get('user_id')

    conn = sqlite3.connect('pyspend.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM transactions      
        WHERE user_id = ? 
        ORDER BY created_at DESC                 
        ''' , (user_id,))

    transactions = cursor.fetchall()
    conn.close()

    return render_template('transactions.html', transactions=transactions)

# print(session.get("user_id"))

if __name__ == "__main__":
    app.run(debug=True)
