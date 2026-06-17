from flask import Flask, render_template, request, redirect
from datetime import datetime
import sqlite3

app = Flask(__name__)

def get_connection():
    conn = sqlite3.connect("spendly.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    current_monthYear = datetime.now().strftime("%B %Y")
    conn = get_connection()
    budget_percentage = 0
    
    income = conn.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM transactions
    WHERE transaction_type='income'
    """).fetchone()[0]

    expenses = conn.execute("""
    SELECT COALESCE(SUM(amount),0)
    FROM transactions
    WHERE transaction_type='expense'
    """).fetchone()[0]

    budget_row = conn.execute("""
    SELECT amount
    FROM budget
    WHERE id=1
    """).fetchone()

    transactions = conn.execute("""
    SELECT *
    FROM transactions
    ORDER BY created_at DESC
    LIMIT 5
    """).fetchall()

    category_data = conn.execute("""
    SELECT category, SUM(amount) as total
    FROM transactions
    WHERE transaction_type='expense'
    GROUP BY category
    """).fetchall()

    category_data = [dict(row) for row in category_data]

    monthly_data = conn.execute("""
    SELECT category,
        SUM(amount) as total
    FROM transactions
    WHERE transaction_type='expense'
    GROUP BY category
    ORDER BY total DESC
    """).fetchall()

    monthly_data = [dict(row) for row in monthly_data]

    budget = budget_row["amount"] if budget_row else 0
    budget = float(budget)

    conn.close()

    if budget:
        budget_percentage = min((expenses / budget) * 100, 100)

    return render_template(
        "home.html",
        current_monthYear = current_monthYear,
        income=income,
        expenses=expenses,
        budget=budget,
        budgetPercentage=round(budget_percentage, 2),
        transactions=transactions,
        category_data=category_data,
        monthly_data=monthly_data
    )

@app.route('/add-income', methods=['POST'])
def add_income():
    amount = request.form.get('amount')
    category = request.form.get('category')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO transactions
        (transaction_type, amount, category)
        VALUES (?, ?, ?)
        """,
        ("income", amount, category)
    )

    conn.commit()
    conn.close()

    # later: store in DB
    return redirect('/')

@app.route('/add-expense', methods=['POST'])
def add_expense():
    amount = request.form.get('amount')
    category = request.form.get('category')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT INTO transactions
        (transaction_type, amount, category)
        VALUES (?, ?, ?)
        """,
        ("expense", amount, category)
    )

    conn.commit()
    conn.close()

    # later: store in DB
    return redirect('/')

@app.route('/setBudget', methods = ['POST'])
def setBudget():
    amount = request.form.get('amount')
    amount = float(amount)

    conn = get_connection()

    conn.execute(
        """
        INSERT OR REPLACE INTO budget
        (id, amount)
        VALUES (1, ?)
        """,
        (amount,)
    )

    conn.commit()
    conn.close()
    
    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)