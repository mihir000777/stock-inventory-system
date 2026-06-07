import os
# pyrefly: ignore [missing-import]
from flask import Flask, render_template, request, redirect, url_for, flash, session
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nexus_auth_secret_key_998877")

# Initialize ThreadedConnectionPool
db_url = os.environ.get("DATABASE_URL")
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    try:
        db_pool = ThreadedConnectionPool(1, 20, dsn=db_url)
    except Exception as e:
        print(f"Failed to initialize Connection Pool: {e}")
        db_pool = None
else:
    db_pool = None

# Database Connection Context Manager
@contextmanager
def get_db_cursor():
    if not db_pool:
        # Fallback to direct connection if pool is not initialized
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is not set. Please configure it.")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = None
        try:
            conn = psycopg2.connect(db_url)
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    else:
        conn = None
        try:
            conn = db_pool.getconn()
            conn.autocommit = False
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                db_pool.putconn(conn)

# Decorators for Authentication & Access Control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access the system.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please log in to access the system.", "warning")
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash("Access denied. Admin privileges required.", "danger")
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Custom Filters
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime(format)

@app.template_filter('dateformat')
def dateformat(value, format='%Y-%m-%d'):
    if value is None:
        return "N/A"
    if isinstance(value, str):
        return value
    return value.strftime(format)

@app.template_filter('currency')
def currency_filter(value):
    if value is None:
        return "$0.00"
    try:
        return f"${float(value):,.2f}"
    except (ValueError, TypeError):
        return value

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()

        if not name or not email or not password:
            flash("Name, Email, and Password are required.", "danger")
            return redirect(url_for('register'))

        password_hash = generate_password_hash(password)

        try:
            with get_db_cursor() as cur:
                # Check if email exists
                cur.execute("SELECT User_ID FROM Users WHERE Email = %s", (email,))
                if cur.fetchone():
                    flash("Email address is already registered.", "danger")
                    return redirect(url_for('register'))
                
                # Insert pending staff user
                cur.execute(
                    "INSERT INTO Users (Name, Email, Password_Hash, Role, Status) VALUES (%s, %s, %s, 'staff', 'pending')",
                    (name, email, password_hash)
                )
                
                # Automatically insert into employee registry for reference if department provided
                cur.execute(
                    "INSERT INTO Employee (Name, Email, Department) VALUES (%s, %s, %s)",
                    (name, email, department if department else 'Staff')
                )
                
            flash("Registration successful. Your account is awaiting admin approval.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"Registration error: {str(e)}", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return redirect(url_for('login'))

        try:
            with get_db_cursor() as cur:
                cur.execute("SELECT * FROM Users WHERE Email = %s", (email,))
                user = cur.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                if user['status'] == 'pending':
                    flash("Your account is awaiting admin approval.", "warning")
                    return redirect(url_for('login'))
                elif user['status'] == 'inactive':
                    flash("Your account has been deactivated.", "danger")
                    return redirect(url_for('login'))

                # Set session variables
                session['user_id'] = user['user_id']
                session['name'] = user['name']
                session['email'] = user['email']
                session['role'] = user['role']
                
                flash(f"Welcome back, {user['name']}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password.", "danger")
        except Exception as e:
            flash(f"Login error: {str(e)}", "danger")

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for('login'))

# --- Main App Routes ---

# 1. Dashboard
@app.route('/')
@login_required
def dashboard():
    try:
        with get_db_cursor() as cur:
            # Aggregate stats
            cur.execute("SELECT COUNT(*) as count FROM Product")
            total_products = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM Product WHERE Quantity < 10")
            low_stock_count = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM Purchase")
            total_purchases = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM Sales")
            total_sales = cur.fetchone()['count']
            
            # Recent 5 purchases
            cur.execute("""
                SELECT p.Purchase_ID, pr.Name as Product_Name, s.Name as Supplier_Name, p.Quantity, p.Purchase_Date
                FROM Purchase p 
                LEFT JOIN Product pr ON p.Product_ID = pr.Product_ID 
                LEFT JOIN Supplier s ON p.Supplier_ID = s.Supplier_ID 
                ORDER BY p.Purchase_ID DESC LIMIT 5
            """)
            recent_purchases = cur.fetchall()
            
            # Recent 5 sales
            cur.execute("""
                SELECT s.Sales_ID, pr.Name as Product_Name, s.Qty_Sold, s.Sales_Date
                FROM Sales s 
                LEFT JOIN Product pr ON s.Product_ID = pr.Product_ID 
                ORDER BY s.Sales_ID DESC LIMIT 5
            """)
            recent_sales = cur.fetchall()

            # Suppliers for the quick add product form (Admins only)
            cur.execute("SELECT Supplier_ID, Name FROM Supplier ORDER BY Name ASC")
            suppliers = cur.fetchall()
            
        return render_template(
            'dashboard.html',
            total_products=total_products,
            low_stock_count=low_stock_count,
            total_purchases=total_purchases,
            total_sales=total_sales,
            recent_purchases=recent_purchases,
            recent_sales=recent_sales,
            suppliers=suppliers
        )
    except Exception as e:
        flash(f"Database loading error: {str(e)}", "danger")
        return render_template(
            'dashboard.html',
            total_products=0,
            low_stock_count=0,
            total_purchases=0,
            total_sales=0,
            recent_purchases=[],
            recent_sales=[],
            suppliers=[]
        )

# 2. Products Catalog
@app.route('/products', methods=['GET', 'POST'])
@login_required
def products():
    if request.method == 'POST':
        # ONLY admin can POST (add)
        if session.get('role') != 'admin':
            flash("Permission denied. Admins only.", "danger")
            return redirect(url_for('products'))
            
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        price_str = request.form.get('price', '0')
        quantity_str = request.form.get('quantity', '0')
        supplier_id_str = request.form.get('supplier_id', '')

        if not name:
            flash("Product name is required.", "danger")
            return redirect(url_for('products'))
        
        try:
            price = float(price_str)
            quantity = int(quantity_str)
            if price < 0 or quantity < 0:
                raise ValueError
        except ValueError:
            flash("Price and quantity must be valid non-negative numbers.", "danger")
            return redirect(url_for('products'))

        supplier_id = int(supplier_id_str) if supplier_id_str else None

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Product (Name, Category, Price, Quantity, Supplier_ID) VALUES (%s, %s, %s, %s, %s)",
                    (name, category, price, quantity, supplier_id)
                )
            flash("Product added successfully!", "success")
        except Exception as e:
            flash(f"Error adding product: {str(e)}", "danger")
        return redirect(url_for('products'))

    # GET request
    edit_product = None
    edit_id = request.args.get('edit_id')
    
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT p.Product_ID, p.Name, p.Category, p.Price, p.Quantity, s.Name as Supplier_Name, p.Supplier_ID
                FROM Product p
                LEFT JOIN Supplier s ON p.Supplier_ID = s.Supplier_ID
                ORDER BY p.Product_ID DESC
            """)
            products_list = cur.fetchall()
            
            cur.execute("SELECT Supplier_ID, Name FROM Supplier ORDER BY Name ASC")
            suppliers_list = cur.fetchall()

            if edit_id and session.get('role') == 'admin':
                cur.execute("SELECT * FROM Product WHERE Product_ID = %s", (int(edit_id),))
                edit_product = cur.fetchone()
                
        return render_template(
            'products.html',
            products=products_list,
            suppliers=suppliers_list,
            edit_product=edit_product
        )
    except Exception as e:
        flash(f"Error loading products: {str(e)}", "danger")
        return render_template('products.html', products=[], suppliers=[], edit_product=None)

# Edit product handler (Admin only)
@app.route('/products/edit/<int:product_id>', methods=['POST'])
@admin_required
def edit_product(product_id):
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    price_str = request.form.get('price', '0')
    quantity_str = request.form.get('quantity', '0')
    supplier_id_str = request.form.get('supplier_id', '')

    if not name:
        flash("Product name is required.", "danger")
        return redirect(url_for('products'))

    try:
        price = float(price_str)
        quantity = int(quantity_str)
        if price < 0 or quantity < 0:
            raise ValueError
    except ValueError:
        flash("Invalid price or quantity.", "danger")
        return redirect(url_for('products'))

    supplier_id = int(supplier_id_str) if supplier_id_str else None

    try:
        with get_db_cursor() as cur:
            cur.execute(
                "UPDATE Product SET Name = %s, Category = %s, Price = %s, Quantity = %s, Supplier_ID = %s WHERE Product_ID = %s",
                (name, category, price, quantity, supplier_id, product_id)
            )
        flash("Product updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating product: {str(e)}", "danger")
    
    return redirect(url_for('products'))

# Delete product handler (Admin only)
@app.route('/products/delete/<int:product_id>', methods=['POST'])
@admin_required
def delete_product(product_id):
    try:
        with get_db_cursor() as cur:
            cur.execute("DELETE FROM Product WHERE Product_ID = %s", (product_id,))
        flash("Product deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting product: {str(e)}", "danger")
    return redirect(url_for('products'))

# 3. Purchases Route (Both roles)
@app.route('/purchase', methods=['GET', 'POST'])
@login_required
def purchase():
    if request.method == 'POST':
        product_id_str = request.form.get('product_id')
        supplier_id_str = request.form.get('supplier_id')
        quantity_str = request.form.get('quantity')
        date_str = request.form.get('purchase_date')

        if not product_id_str or not quantity_str:
            flash("Product and Quantity are required.", "danger")
            return redirect(url_for('purchase'))

        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be greater than zero.", "danger")
            return redirect(url_for('purchase'))

        product_id = int(product_id_str)
        supplier_id = int(supplier_id_str) if supplier_id_str else None
        purchase_date = date_str if date_str else datetime.now().date().isoformat()

        try:
            with get_db_cursor() as cur:
                # Pull staff/employee linked details based on current logged in user
                cur.execute("SELECT Employee_ID FROM Employee WHERE Email = %s", (session.get('email'),))
                emp = cur.fetchone()
                employee_id = emp['employee_id'] if emp else None

                # Trigger updates stock
                cur.execute(
                    "INSERT INTO Purchase (Product_ID, Supplier_ID, Quantity, Purchase_Date, Employee_ID) VALUES (%s, %s, %s, %s, %s)",
                    (product_id, supplier_id, quantity, purchase_date, employee_id)
                )
            flash("Purchase recorded successfully! Product stock increased.", "success")
        except Exception as e:
            flash(f"Error recording purchase: {str(e)}", "danger")
            
        return redirect(url_for('purchase'))

    # GET request
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT p.Purchase_ID, pr.Name as Product_Name, s.Name as Supplier_Name, p.Quantity, p.Purchase_Date, e.Name as Employee_Name
                FROM Purchase p
                LEFT JOIN Product pr ON p.Product_ID = pr.Product_ID
                LEFT JOIN Supplier s ON p.Supplier_ID = s.Supplier_ID
                LEFT JOIN Employee e ON p.Employee_ID = e.Employee_ID
                ORDER BY p.Purchase_ID DESC
            """)
            purchases_list = cur.fetchall()

            cur.execute("SELECT Product_ID, Name FROM Product ORDER BY Name ASC")
            products_list = cur.fetchall()

            cur.execute("SELECT Supplier_ID, Name FROM Supplier ORDER BY Name ASC")
            suppliers_list = cur.fetchall()

        return render_template(
            'purchase.html',
            purchases=purchases_list,
            products=products_list,
            suppliers=suppliers_list
        )
    except Exception as e:
        flash(f"Error fetching purchases: {str(e)}", "danger")
        return render_template('purchase.html', purchases=[], products=[], suppliers=[])

# 4. Sales Route (Both roles)
@app.route('/sale', methods=['GET', 'POST'])
@login_required
def sale():
    if request.method == 'POST':
        product_id_str = request.form.get('product_id')
        customer_id_str = request.form.get('customer_id')
        qty_sold_str = request.form.get('qty_sold')
        date_str = request.form.get('sales_date')

        if not product_id_str or not qty_sold_str:
            flash("Product and Quantity are required.", "danger")
            return redirect(url_for('sale'))

        try:
            qty_sold = int(qty_sold_str)
            if qty_sold <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity sold must be greater than zero.", "danger")
            return redirect(url_for('sale'))

        product_id = int(product_id_str)
        customer_id = int(customer_id_str) if customer_id_str else None
        sales_date = date_str if date_str else datetime.now().date().isoformat()

        try:
            with get_db_cursor() as cur:
                # Find current employee ID
                cur.execute("SELECT Employee_ID FROM Employee WHERE Email = %s", (session.get('email'),))
                emp = cur.fetchone()
                employee_id = emp['employee_id'] if emp else None

                # Trigger checks stock levels and updates
                cur.execute(
                    "INSERT INTO Sales (Product_ID, Qty_Sold, Sales_Date, Employee_ID, Customer_ID) VALUES (%s, %s, %s, %s, %s)",
                    (product_id, qty_sold, sales_date, employee_id, customer_id)
                )
            flash("Sale recorded successfully! Product stock decreased.", "success")
        except psycopg2.Error as err:
            error_msg = err.diag.message_primary if (err.diag and err.diag.message_primary) else str(err)
            if "EXCEPTION:" in error_msg:
                error_msg = error_msg.split("EXCEPTION:")[-1].strip()
            flash(f"Transaction Blocked: {error_msg}", "danger")
        except Exception as e:
            flash(f"Error recording sale: {str(e)}", "danger")

        return redirect(url_for('sale'))

    # GET request
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT s.Sales_ID, pr.Name as Product_Name, s.Qty_Sold, s.Sales_Date, e.Name as Employee_Name, c.Name as Customer_Name
                FROM Sales s
                LEFT JOIN Product pr ON s.Product_ID = pr.Product_ID
                LEFT JOIN Employee e ON s.Employee_ID = e.Employee_ID
                LEFT JOIN Customer c ON s.Customer_ID = c.Customer_ID
                ORDER BY s.Sales_ID DESC
            """)
            sales_list = cur.fetchall()

            cur.execute("SELECT Product_ID, Name, Quantity FROM Product ORDER BY Name ASC")
            products_list = cur.fetchall()

            cur.execute("SELECT Customer_ID, Name FROM Customer ORDER BY Name ASC")
            customers_list = cur.fetchall()

        return render_template(
            'sale.html',
            sales=sales_list,
            products=products_list,
            customers=customers_list
        )
    except Exception as e:
        flash(f"Error loading sales data: {str(e)}", "danger")
        return render_template('sale.html', sales=[], products=[], customers=[])

# 5. Report (Admin only)
@app.route('/report')
@admin_required
def report():
    try:
        with get_db_cursor() as cur:
            cur.execute("""
                SELECT Name, Category, Quantity, Price, (Price * Quantity) as Total_Value
                FROM Product ORDER BY Name ASC
            """)
            report_data = cur.fetchall()
            
            total_items = sum(item['quantity'] for item in report_data)
            total_value = sum(float(item['total_value']) for item in report_data)
            
        return render_template(
            'report.html',
            report_data=report_data,
            total_items=total_items,
            total_value=total_value
        )
    except Exception as e:
        flash(f"Error generating report: {str(e)}", "danger")
        return render_template('report.html', report_data=[], total_items=0, total_value=0)

# 6. Suppliers (Admin only)
@app.route('/suppliers', methods=['GET', 'POST'])
@admin_required
def suppliers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone_no = request.form.get('phone_no', '').strip()
        address = request.form.get('address', '').strip()
        email = request.form.get('email', '').strip()
        city = request.form.get('city', '').strip()

        if not name:
            flash("Supplier name is required.", "danger")
            return redirect(url_for('suppliers'))

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Supplier (Name, Phone_No, Address, Email, City) VALUES (%s, %s, %s, %s, %s)",
                    (name, phone_no, address, email, city)
                )
            flash("Supplier added successfully!", "success")
        except Exception as e:
            flash(f"Error saving supplier: {str(e)}", "danger")
        return redirect(url_for('suppliers'))

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM Supplier ORDER BY Supplier_ID DESC")
            suppliers_list = cur.fetchall()
        return render_template('suppliers.html', suppliers=suppliers_list)
    except Exception as e:
        flash(f"Error loading suppliers: {str(e)}", "danger")
        return render_template('suppliers.html', suppliers=[])

# 7. Employees (Admin only)
@app.route('/employees', methods=['GET', 'POST'])
@admin_required
def employees():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()

        if not name:
            flash("Employee name is required.", "danger")
            return redirect(url_for('employees'))

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Employee (Name, Email, Phone, Department) VALUES (%s, %s, %s, %s)",
                    (name, email, phone, department)
                )
            flash("Employee registered successfully!", "success")
        except Exception as e:
            flash(f"Error saving employee: {str(e)}", "danger")
        return redirect(url_for('employees'))

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM Employee ORDER BY Employee_ID DESC")
            employees_list = cur.fetchall()
        return render_template('employees.html', employees=employees_list)
    except Exception as e:
        flash(f"Error loading employees: {str(e)}", "danger")
        return render_template('employees.html', employees=[])

# 8. Customers (Admin only)
@app.route('/customers', methods=['GET', 'POST'])
@admin_required
def customers():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        address = request.form.get('address', '').strip()

        if not name:
            flash("Customer name is required.", "danger")
            return redirect(url_for('customers'))

        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "INSERT INTO Customer (Name, Phone, Email, Address) VALUES (%s, %s, %s, %s)",
                    (name, phone, email, address)
                )
            flash("Customer registered successfully!", "success")
        except Exception as e:
            flash(f"Error saving customer: {str(e)}", "danger")
        return redirect(url_for('customers'))

    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT * FROM Customer ORDER BY Customer_ID DESC")
            customers_list = cur.fetchall()
        return render_template('customers.html', customers=customers_list)
    except Exception as e:
        flash(f"Error loading customers: {str(e)}", "danger")
        return render_template('customers.html', customers=[])

# --- API Endpoints ---

@app.route('/api/low-stock')
@login_required
def api_low_stock():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT Product_ID, Name, Quantity FROM Product WHERE Quantity < 10 ORDER BY Quantity ASC")
            low_stock_items = cur.fetchall()
        return {"status": "success", "items": low_stock_items}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

# --- Admin Panel Route ---

@app.route('/admin')
@admin_required
def admin_panel():
    try:
        with get_db_cursor() as cur:
            cur.execute("SELECT User_ID, Name, Email, Role, Status, Created_At FROM Users ORDER BY Created_At DESC")
            users_list = cur.fetchall()
        return render_template('admin.html', users=users_list)
    except Exception as e:
        flash(f"Error loading admin panel: {str(e)}", "danger")
        return redirect(url_for('dashboard'))

@app.route('/admin/user/<int:user_id>/<string:action>', methods=['POST'])
@admin_required
def admin_user_action(user_id, action):
    # Security check: cannot demote or deactivate yourself
    if user_id == session.get('user_id'):
        flash("Action denied. You cannot modify your own administrative status or role.", "danger")
        return redirect(url_for('admin_panel'))

    try:
        with get_db_cursor() as cur:
            if action == 'approve':
                cur.execute("UPDATE Users SET Status = 'active' WHERE User_ID = %s", (user_id,))
                # Also ensure the approved user is listed as an active employee
                cur.execute("SELECT Name, Email FROM Users WHERE User_ID = %s", (user_id,))
                u = cur.fetchone()
                if u:
                    cur.execute("SELECT Employee_ID FROM Employee WHERE Email = %s", (u['email'],))
                    if not cur.fetchone():
                        cur.execute("INSERT INTO Employee (Name, Email, Department) VALUES (%s, %s, 'Staff')", (u['name'], u['email']))
                flash("User approved and status set to active.", "success")
            elif action == 'deactivate':
                cur.execute("UPDATE Users SET Status = 'inactive' WHERE User_ID = %s", (user_id,))
                flash("User account deactivated.", "success")
            elif action == 'make_admin':
                cur.execute("UPDATE Users SET Role = 'admin' WHERE User_ID = %s", (user_id,))
                flash("User role set to Admin.", "success")
            elif action == 'make_staff':
                cur.execute("UPDATE Users SET Role = 'staff' WHERE User_ID = %s", (user_id,))
                flash("User role set to Staff.", "success")
            else:
                flash("Invalid administrative action requested.", "danger")
    except Exception as e:
        flash(f"Failed to execute administrative action: {str(e)}", "danger")

    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)
