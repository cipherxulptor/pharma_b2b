from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

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
                session['role'] = user[6]
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
    cur.execute("SELECT id, product_name, price, company, pack_size FROM catalog")
    products = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('pharmacy_catalog.html', catalog=products)

# Route to handle cart and generate invoice
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    selected_ids = request.form.getlist('selected_products')
    user_email = session.get('email')

    conn = get_db_connection()
    cur = conn.cursor()

    for product_id in selected_ids:
        quantity = request.form.get(f'quantity_{product_id}')
        if not quantity or int(quantity) < 10:
            continue
        cur.execute("SELECT product_name, price FROM catalog WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if product:
            product_name, price = product
            cur.execute("""
                INSERT INTO order_cart (user_email, product_name, quantity, price, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_email, product_name, quantity, price, 'pending'))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('pharmacy_cart'))

@app.route('/pharmacy/view_catalog')
def pharmacy_view_catalog():
    cur = get_db_connection().cursor()
    cur.execute("SELECT id, product_name, price, company, pack_size FROM catalog")
    products = cur.fetchall()
    cur.close()
    return render_template('pharmacy_view_catalog.html', products=products)


# 🟦 PHARMACY ORDERS

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

@app.route('/confirm_order', methods=['POST'])
def confirm_order():
    selected_ids = request.form.getlist('product_ids')
    orders = []

    for product_id in selected_ids:
        quantity = request.form.get(f'quantity_{product_id}')
        orders.append({'product_id': product_id, 'quantity': quantity})

    # Save orders to database with "pending" status
    # Wholesaler will later Approve/Reject it

    # Example: insert into orders table...

    return "Order request sent for approval!"  # or redirect to pharmacy_dashboard


# 🟦 PHARMACY INVENTORY

@app.route('/pharmacy/inventory')
def pharmacy_inventory():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pharmacy_inventory WHERE pharmacy_id = %s", (user_id,))
    inventory = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('pharmacy_inventory.html', inventory=inventory)

# 🟦 PHARMACY ANALYTICS

@app.route('/pharmacy/analytics')
def pharmacy_analytics():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    user_id = session['user_id']
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT medicine, SUM(quantity) AS total_quantity_sold, SUM(total_price) AS total_sales
        FROM Transactions
        WHERE user_email = %s
        GROUP BY medicine
    """, (session['email'],))
    analytics_data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('pharmacy_analytics.html', analytics_data=analytics_data)

@app.route('/pharmacy/invoices')
def pharmacy_invoices():
    if 'email' not in session or session.get('role') != 'pharmacy':
        return redirect(url_for('login'))

    user_email = session['email']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM transactions WHERE user_email = %s ORDER BY order_date DESC", (user_email,))
    invoices = cursor.fetchall()
    cursor.close()

    return render_template('pharmacy_invoices.html', invoices=invoices)

@app.route('/generate_invoice', methods=['POST'])
def generate_invoice():
    data = request.get_json()
    user_email = data['user_email']
    items = data['items']

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        for item in items:
            cur.execute("""
                INSERT INTO Transactions (user_email, medicine, category, quantity, unit_price, total_price, order_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                user_email,
                item['product_name'],
                item['category'],
                item['quantity'],
                item['price_per_unit'],
                item['total_price'],
                datetime.now()
            ))
        conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        conn.rollback()
        print("Invoice Error:", e)
        return jsonify({'status': 'error', 'message': str(e)})
    finally:
        cur.close()
        conn.close()

@app.route('/download_invoice/<int:order_id>')
def download_invoice(order_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch the approved order
    cur.execute("SELECT * FROM wholesaler_orders WHERE id = %s AND status = 'approved'", (order_id,))
    order = cur.fetchone()

    if order:
        # Generate invoice PDF (you can use a library like ReportLab or fpdf for PDF generation)
        # Placeholder: Generating a simple invoice as a text file
        invoice = f"Invoice for Order {order_id}\n"
        invoice += f"Product Name: {order['product_name']}\n"
        invoice += f"Quantity: {order['quantity']}\n"
        invoice += f"Total Price: ₹{order['total_price']}\n"
        invoice += f"Status: {order['status']}\n"

        # Save the invoice to a file
        filename = f"invoice_{order_id}.txt"
        with open(f"static/invoices/{filename}", "w") as f:
            f.write(invoice)

        return send_from_directory('static/invoices', filename)

    return "Invoice not found", 404

# 🟦 
# 
# 
# R DASHBOARD

@app.route('/wholesaler/dashboard')
def wholesaler_dashboard():
    print("Session role:", session.get('role'))
    print("Session user_id:", session.get('user_id'))

    if 'user_id' not in session or session.get('role') != 'wholesaler':
        return redirect(url_for('home'))

    return render_template('wholesaler_dashboard.html')  # ✅ No inventory data here


@app.route('/wholesaler/analytics')
def wholesaler_analytics():
    return "<h2>Analytics Page Coming Soon</h2>"


@app.route('/wholesaler/inventory')
def wholesaler_inventory():
    if 'user_id' not in session or session.get('role') != 'wholesaler':
        return redirect(url_for('home'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM wholesaler_inventory ORDER BY product_name ASC")
    inventory_items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('wholesaler_inventory.html', inventory=inventory_items)


@app.route('/wholesaler/orders')
def wholesaler_orders():
    conn = psycopg2.connect(
    database="pharma_db",
    user="postgres",
    password="Prerana123",
    host="localhost",
    port="5432"
)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("SELECT * FROM order_cart WHERE status = 'pending'")
    pending_orders = cursor.fetchall()
    cursor.close()
    return render_template('wholesaler_orders.html', pending_orders=pending_orders)

@app.route('/request_order/<int:item_id>', methods=['POST'])
def request_order(item_id):
    quantity = request.form['quantity']
    user_email = session.get('email')  # Assuming the user is logged in
    user_id = session.get('user_id')  # Pharmacy's user id
    role = session.get('role')

    if role != 'pharmacy':
        return redirect(url_for('home'))  # Ensure the user is a pharmacy

    conn = get_db_connection()
    cur = conn.cursor()

    # Get the details of the item from the catalog
    cur.execute("SELECT product_name, price, company FROM catalog WHERE id = %s", (item_id,))
    item = cur.fetchone()

    # Insert the request order into wholesaler_orders table
    cur.execute('''INSERT INTO wholesaler_orders (pharmacy_email, status, product_name, quantity, unit_price, total_price)
                    VALUES (%s, %s, %s, %s, %s, %s)''', 
                (user_email, 'pending', item['product_name'], quantity, item['price'], int(quantity) * int(item['price'])))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for('pharmacy_dashboard'))  # Redirect back to the pharmacy dashboard

@app.route('/submit_order', methods=['POST'])
def submit_order():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']

    # Directly get form data
    product_name = request.form.get('product_name')
    price_str = request.form.get('price')
    quantity_str = request.form.get('quantity')

    # Validate price and quantity
    if not price_str or not price_str.isdigit():
        return "Error: Invalid or missing price", 400
    if not quantity_str or not quantity_str.isdigit():
        return "Error: Invalid or missing quantity", 400

    try:
        price = float(price_str)
        quantity = int(quantity_str)
        total = price * quantity

        conn = psycopg2.connect(
            dbname="pharma_db", user="postgres", password="Prerana123", host="localhost", port="5432"
        )
        cur = conn.cursor()

        # Insert into orders table (adjust according to your table structure)
        cur.execute("""
            INSERT INTO orders (pharmacy_email, product_name, quantity, price, total, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (email, product_name, quantity, price, total, 'pending'))

        conn.commit()
        cur.close()
        conn.close()

        return redirect(url_for('pharmacy_catalog'))  # or dashboard page

    except Exception as e:
        print("Order submission error:", e)
        return "Internal Server Error", 500




@app.route('/reject_order/<int:order_id>', methods=['POST'])
def reject_order(order_id):
    conn = get_db_connection()
    cur = conn.cursor()

    # Update order status to rejected
    cur.execute("UPDATE wholesaler_orders SET status = 'rejected' WHERE id = %s", (order_id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect(url_for('wholesaler_orders'))  # Redirect back to wholesaler orders page


@app.route('/approve_order/<int:order_id>', methods=['POST'])
def approve_order(order_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # 1. Fetch order
    cursor.execute('SELECT * FROM order_cart WHERE id = %s', (order_id,))
    order = cursor.fetchone()

    if not order:
        cursor.close()
        return "Order not found", 404

    product_name = order['product_name']
    quantity = order['quantity']

    # 2. Check inventory
    cursor.execute('SELECT * FROM wholesaler_inventory WHERE product_name = %s', (product_name,))
    inventory = cursor.fetchone()

    if inventory and inventory['quantity'] >= quantity:
        new_quantity = inventory['quantity'] - quantity
        cursor.execute('UPDATE wholesaler_inventory SET quantity = %s WHERE id = %s', (new_quantity, inventory['id']))

        # 3. Insert into transactions
        total_price = quantity * order['price']
        cursor.execute('''INSERT INTO transactions (user_email, medicine, quantity, unit_price, total_price, order_date)
                          VALUES (%s, %s, %s, %s, %s, NOW())''',
                       (order['user_email'], product_name, quantity, order['price'], total_price))

        # 4. Update order status
        cursor.execute('UPDATE order_cart SET status = %s WHERE id = %s', ('approved', order_id))

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('wholesaler_orders'))
    else:
        cursor.close()
        return "Insufficient stock", 400

@app.route('/invoice/<int:invoice_id>')
def invoice(invoice_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM transactions WHERE id = %s', (invoice_id,))
    invoice = cursor.fetchone()
    cursor.close()

    if not invoice:
        return "Invoice not found", 404

    return render_template('invoice.html', invoice=invoice)


from xhtml2pdf import pisa
from io import BytesIO
from flask import make_response

@app.route('/download_invoice/<int:invoice_id>')
def download_invoice_pdf(invoice_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM transactions WHERE id = %s', (invoice_id,))
    invoice = cursor.fetchone()
    cursor.close()

    if not invoice:
        return "Invoice not found", 404

    rendered = render_template('invoice.html', invoice=invoice)
    pdf = BytesIO()
    pisa.CreatePDF(BytesIO(rendered.encode("utf-8")), pdf)

    response = make_response(pdf.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice_id}.pdf'

    return response



@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    data = request.form
    product_id = data.get('product_id')
    quantity = data.get('quantity')

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE Inventory SET quantity = %s WHERE id = %s", (quantity, product_id))
        conn.commit()
        flash("Inventory updated successfully.")
    except Exception as e:
        conn.rollback()
        print("Inventory Update Error:", e)
        flash("Failed to update inventory.")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('wholesaler_inventory'))

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
