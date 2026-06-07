# NEXUS Command Center
### Terminal-Style Inventory Management System

NEXUS is a next-generation, high-performance web terminal designed for real-time inventory metrics, transactional ledgers, and operator access control. Styled around the modern, high-contrast, dark-mode design system from Google Stitch ("Nexus Terminal"), NEXUS provides an interactive, glassmorphic layout backed by robust PostgreSQL transaction checking and Flask routing mechanisms.

---

## ⚡ Core Features

*   **Bento-Grid Telemetry Dashboard**: Get instant access to real-time stats including total registered SKUs, low-stock warnings, total purchase volumes, sales, recent inbound logs, and active outbound telemetry records.
*   **Dynamic Low-Stock Diagnostics**: The top header notification bell polls active inventory levels in the background (every 30 seconds). If any SKU drops below 10 units, a red warning badge triggers, and the dropdown populates with details and direct links to update the critical assets.
*   **Dual-Role Access Control**: Protect the database with secure password hashing (`werkzeug.security`).
    *   **Admins**: Full permissions to register/demote staff, add/edit/delete product assets, configure directories (Employees, Suppliers, Customers), and view valuation reports.
    *   **Staff**: Log transactions (Purchases and Sales) and browse live inventory directories.
*   **Automated Ledgers & Transactions**: Purchases and Sales registries dynamically balance quantities, validate stock level constraints, and record operator logs.
*   **Mobile-Optimized Command Center**: Responsive design that scales down to mobile viewports with a persistent bottom navigator and quick signout triggers in the header.

---

## 🗄️ Relational Database Schema (PostgreSQL)

NEXUS runs on a relational PostgreSQL database schema with strict constraints and automated triggers to enforce data integrity:

### 1. Table Definitions
*   **`Users`**: Holds system login credentials (`Email` is UNIQUE, password hashes, approval status, and `Role` either `'admin'` or `'staff'`).
*   **`Product`**: Tracks registered inventory assets, categories, unit prices, and quantity in stock (constrained by a `CHECK (Quantity >= 0)`).
*   **`Supplier`**: Directory of manufacturers and product suppliers.
*   **`Employee`**: Database of active company workers linked to transaction logs.
*   **`Customer`**: Registry of outbound purchasers.
*   **`Purchase`**: Ledger of inbound stock deliveries (linked to `Product`, `Supplier`, and `Employee`).
*   **`Sales`**: Ledger of outbound customer transactions (linked to `Product`, `Customer`, and `Employee`).

### 2. Automated PostgreSQL Triggers
*   **`purchase_inserted`** (`AFTER INSERT ON Purchase`): Automatically increments the `Quantity` in the `Product` table when a new purchase ledger is recorded.
*   **`sale_inserted`** (`BEFORE INSERT ON Sales`): Validates stock level constraints. If the requested purchase quantity (`Qty_Sold`) exceeds current stock, the transaction is aborted and a custom database exception is raised:
    `RAISE EXCEPTION 'Insufficient stock for product. Available: %, requested: %'`
    Otherwise, it decrements the stock quantity automatically.

---

## 🏎️ Performance Optimizations

*   **Threaded Database Connection Pooling**: Uses psycopg2's `ThreadedConnectionPool` to manage active database connections dynamically. Instead of creating and closing a TCP database socket on every request, connections are fetched from a pool and reused, reducing Render-to-PostgreSQL handshake latencies from **~300ms** to **<15ms**.
*   **Jinja2 Templating Architecture**: All views extend a shared layout shell (`base.html`), ensuring uniform styling, stateful notification drawers, and responsive sidebar menus across the entire application.

---

## 🚀 Local Installation & Setup

### 1. Prerequisites
Ensure you have the following installed on your machine:
*   [Python 3.8+](https://www.python.org/downloads/)
*   [PostgreSQL Database](https://www.postgresql.org/download/)

### 2. Clone and Setup Environment
1. Clone the project repository.
2. In the project root, create a virtual environment and activate it:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Initialize the Database
1. Run PostgreSQL locally or connect to a remote instance.
2. Set up the schema and insert mock dataset:
   ```bash
   psql -U your_postgres_user -d your_database -f schema.sql
   psql -U your_postgres_user -d your_database -f sample_data.sql
   ```

### 4. Configure Environment Variables
Create a `.env` file in the root directory or configure your system variables:
```env
DATABASE_URL=postgresql://your_postgres_user:your_password@localhost:5400/your_database
SECRET_KEY=your_secure_encryption_key
```

### 5. Launch the Server
Start the Flask development server:
```bash
python app.py
```
The console will initialize, and the application will be hosted locally at `http://127.0.0.1:5000`.

---

## 🛡️ Default Mock Login Accounts

For local testing after importing `sample_data.sql`, use the following credentials:
*   **Administrator**:
    *   **Email**: `admin@nexus.system`
    *   **Password**: `admin123`
*   **Staff Operator**:
    *   **Email**: `operator@nexus.system`
    *   **Password**: `staff123`

---

## 📂 Project Structure

```
├── static/
│   └── logo.svg               # Vector N Logo asset and Favicon
├── templates/
│   ├── base.html              # Core Layout Shell (Sidebar, Header, Alerts Dropdown)
│   ├── login.html             # Authorization Entry Terminal
│   ├── register.html          # Registration Portal
│   ├── dashboard.html         # Live Analytics & Bento Grid
│   ├── products.html          # SKU Inventory Catalog and Edit modal
│   ├── purchase.html          # Inbound Transactions Ledger
│   ├── sale.html              # Outbound Transactions Ledger
│   ├── suppliers.html         # Suppliers Directory
│   ├── employees.html         # Employee Registry
│   ├── customers.html         # Customer Database
│   ├── report.html            # Asset Valuation Ledger
│   └── admin.html             # User controls panel
├── app.py                     # Central Flask router and DB pooling core
├── schema.sql                 # SQL tables schema definitions & stock triggers
├── sample_data.sql            # Core startup dataset (operators, mock catalog)
└── requirements.txt           # Active python packages definitions
```

---

## 🎨 UI Reference & Design

NEXUS interface uses **Tailwind CSS** styled under a customized color system:
*   **Primary Accent**: Neon Lime (`#c8f050`)
*   **Secondary Accent**: Violet Glow (`#3f29bc`)
*   **Surface darks**: Charcoal Grey (`#13131a` to `#1f1f26`)
*   **Typography**: *Syne* (for header titles) & *JetBrains Mono* (for data tables and reports).
