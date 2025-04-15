from flask import Flask, render_template, request, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Admin credentials
ADMIN_EMAIL = 'admin@pharma.com'
ADMIN_PASSWORD = 'adminpass'

# Connect to PostgreSQL

def get_db_connection():
    return psycopg2.connect(
        dbname='pharma_db',
        user='postgres',
        password='Prerana123',
        host='localhost',
        port='5432'
    )

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not role:
            flash("Please select a role.")
            return render_template('login.html')

        if role == 'admin':
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                session['user_id'] = 'admin'
                session['role'] = 'admin'
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials')
                return render_template('login.html')
        else:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE email = %s AND password = %s AND role = %s AND is_approved = TRUE", (email, password, role))
            user = cur.fetchone()
            cur.close()
            conn.close()

            if user:
                session['user_id'] = user[0]
                session['email'] = user[1] 
                session['role'] = user[5]
                if role == 'pharmacy':
                    return redirect(url_for('pharmacy_dashboard'))
                elif role == 'wholesaler':
                    return redirect(url_for('wholesaler_dashboard'))
            else:
                flash('Invalid credentials or not approved yet.')
                return render_template('login.html')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        license_number = request.form.get('license_number')
        password = request.form.get('password')
        role = request.form.get('role')

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO users (name, email, phone, license_number, password, role, is_approved)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (name, email, phone, license_number, password, role, None))
            conn.commit()
            flash("Signup successful. Awaiting admin approval.")
        except Exception as e:
            print("Signup Error:", e)
            flash("Error occurred during signup. Please try again.")
        finally:
            cur.close()
            conn.close()

        return redirect(url_for('home'))

    return render_template('signup.html')

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    conn = get_db_connection()
    cur = conn.cursor()

    if request.method == 'POST':
        user_id = request.form.get('user_id')
        action = request.form.get('action')

        cur.execute("SELECT is_approved FROM users WHERE id = %s", (user_id,))
        current_status = cur.fetchone()[0]

        if current_status is None:
            if action == 'approve':
                cur.execute("UPDATE users SET is_approved = TRUE WHERE id = %s", (user_id,))
            elif action == 'reject':
                cur.execute("UPDATE users SET is_approved = FALSE WHERE id = %s", (user_id,))
            conn.commit()

    cur.execute("SELECT id, name, email, role, is_approved FROM users ORDER BY id")
    all_users = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('admin_dashboard.html', all_users=all_users)

@app.route('/pharmacy/dashboard')
def pharmacy_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone()

    cur.execute("SELECT id, medicine, quantity, status FROM orders WHERE pharmacy_id = %s", (user_id,))
    orders = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('pharmacy_dashboard.html', user=user, orders=orders)

@app.route('/pharmacy/catalog')
def pharmacy_catalog():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT product_name, company, category FROM catalog")
    catalog = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pharmacy_catalog.html', catalog=catalog)

@app.route('/pharmacy/orders')
def pharmacy_orders():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, medicine, quantity, status FROM orders WHERE pharmacy_id = %s", (user_id,))
    orders = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pharmacy_orders.html', orders=[{'id': o[0], 'medicine': o[1], 'quantity': o[2], 'status': o[3]} for o in orders])

@app.route('/pharmacy/inventory')
def pharmacy_inventory():
    user_id = session.get('user_id')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT medicine, quantity, category FROM pharmacy_inventory WHERE pharmacy_id = %s", (user_id,))
    inventory = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pharmacy_inventory.html', inventory=[{'medicine': i[0], 'quantity': i[1], 'category': i[2]} for i in inventory])

@app.route('/pharmacy/analytics')
def pharmacy_analytics():
    user_email = session.get('email')  # Get email, not user_id
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*), COALESCE(SUM(total_price), 0), MAX(category)
        FROM transactions
        WHERE user_email = %s
    """, (user_email,))
    total_orders, total_spent, top_category = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('pharmacy_analytics.html',
                           total_orders=total_orders,
                           total_spent=total_spent,
                           top_category=top_category)


@app.route('/wholesaler_dashboard')
def wholesaler_dashboard():
    return 'Wholesaler Dashboard (to be implemented)'

if __name__ == '__main__':
    app.run(debug=True)
