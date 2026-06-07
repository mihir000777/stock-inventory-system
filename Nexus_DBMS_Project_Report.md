# NEXUS: Stock Inventory Management System
### DBMS Mini-Project Report (IV Semester B.E. CSBS)

---

## 1. ABSTRACT
Modern enterprise logistics require robust systems to track inventories, balance stocks, and log transactional histories accurately. This project, entitled NEXUS, implements a Stock Inventory Management System designed to address these business concerns through a relational database system. The system is built on a PostgreSQL database hosted via Supabase, with a Python Flask application serving as the web interface, hosted on Render. The database consists of six highly normalized tables: Product, Supplier, Customer, Employee, Purchase, and Sales, along with a secure Users table. To enforce data integrity and automate operations, PostgreSQL trigger functions written in PL/pgSQL are implemented. A purchase trigger automatically increments stock quantity when procurement is recorded, while a sales trigger validates and decrements stock, raising exceptions to block out-of-stock checkouts. Additionally, a secure session-based authentication system provides role-based access control (RBAC), dividing users into Administrators (who maintain directories, approve accounts, and view valuation reports) and Staff (who record purchases and sales). This architectural division ensures transaction reliability, operational security, and database consistency, which is crucial for modern inventory operations.

## 2. INTRODUCTION
### 2.1 Project Overview
NEXUS is a web-based Stock Inventory Management System built as a relational database application. In modern commercial retail and warehouse settings, tracking physical stock, procurement from suppliers, and client sales manually is highly error-prone. This project introduces a centralized system that models these components using a strict relational model, where every operational record updates stock amounts automatically. The system has been developed with a clear separation of concerns: Supabase (PostgreSQL) acts as the secure relational database engine, Flask handles the backend routing and security check controllers, and custom CSS provides a premium user interface.

### 2.2 Purpose & Problem Statement
Traditional spreadsheet inventory records face severe data management issues: lack of transaction isolation, failure to enforce constraints, and zero record traceability. For example, a sales clerk could accidentally record a sale of ten laptops when only three are physically present in the warehouse, resulting in database inconsistency. The primary purpose of NEXUS is to demonstrate how these business constraints can be handled natively inside the database engine using SQL constraints and stored procedures. Additionally, the project aims to implement Role-Based Access Control (RBAC) to restrict staff operators from modifying base records (such as product pricing, employee registries, and supplier profiles) while allowing them to execute purchases and sales transactions.

## 3. SYSTEM REQUIREMENTS
### 3.1 Functional Requirements
• Registration & Login: Users must register with Name, Email, Password, and Department. Newly registered users cannot log in until approved by an Admin.
• Administrator Control: Admins can approve pending signups, deactivate active accounts, promote staff to admin, add new products/suppliers/employees/customers, and delete entries.
• Staff Transactions: Staff members can view product lists, current stock levels, and record new purchases and sales. They are strictly blocked from adding, editing, or deleting database assets.
• Real-Time Stock Sync: When a purchase is registered, the product's quantity must increase immediately. When a sale is registered, the quantity must decrease. If a sale quantity exceeds the available stock, the database must abort the transaction and display an error to the user.

### 3.2 Software Tech Stack
| Component | Detail |
| --- | --- |
| Database Server | Supabase (PostgreSQL 15+) cloud hosting |
| Backend Framework | Python 3.11.9, Flask 3.0.3 Web Framework |
| Database Driver | psycopg2-binary 2.9.9 |
| Web Server hosting | Render (Free Tier container service) |

## 4. SYSTEM DESIGN
### 4.1 Schema Mapping
* Supplier(Supplier_ID [PK], Name, Phone_No, Address, Email, City)
* Product(Product_ID [PK], Name, Category, Price, Quantity, Supplier_ID [FK -> Supplier.Supplier_ID])
* Employee(Employee_ID [PK], Name, Email, Phone, Department)
* Customer(Customer_ID [PK], Name, Phone, Email, Address)
* Purchase(Purchase_ID [PK], Product_ID [FK -> Product.Product_ID], Supplier_ID [FK -> Supplier.Supplier_ID], Quantity, Purchase_Date, Employee_ID [FK -> Employee.Employee_ID])
* Sales(Sales_ID [PK], Product_ID [FK -> Product.Product_ID], Qty_Sold, Sales_Date, Employee_ID [FK -> Employee.Employee_ID], Customer_ID [FK -> Customer.Customer_ID])
* Users(User_ID [PK], Name, Email, Password_Hash, Role, Status, Created_At)

### 4.2 Normalization Analysis
• **1NF**: All attributes are atomic (indivisible) and contain no repeating groups. All tables contain primary keys.
• **2NF**: Tables are in 1NF and have single-attribute primary keys (surrogate keys), eliminating any partial dependencies. All non-prime attributes depend fully on the primary key.
• **3NF**: Tables are in 2NF and contain no transitive dependencies of non-prime attributes. Attributes like Department or Category depend directly on their primary key, not via intermediate attributes.

## 5. DATABASE TRIGGER FUNCTIONS (PL/pgSQL)
#### Inbound Purchase Sync:
```sql
CREATE OR REPLACE FUNCTION update_stock_on_purchase()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE Product
    SET Quantity = Quantity + NEW.Quantity
    WHERE Product_ID = NEW.Product_ID;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER purchase_inserted
AFTER INSERT ON Purchase
FOR EACH ROW EXECUTE FUNCTION update_stock_on_purchase();
```

#### Outbound Sales Stock Check:
```sql
CREATE OR REPLACE FUNCTION update_stock_on_sale()
RETURNS TRIGGER AS $$
DECLARE
    current_stock INTEGER;
BEGIN
    SELECT Quantity INTO current_stock FROM Product WHERE Product_ID = NEW.Product_ID;

    IF current_stock IS NULL THEN
        RAISE EXCEPTION 'Product with ID % does not exist.', NEW.Product_ID;
    ELSIF current_stock < NEW.Qty_Sold THEN
        RAISE EXCEPTION 'Insufficient stock. Available: %, requested: %', current_stock, NEW.Qty_Sold;
    ELSE
        UPDATE Product SET Quantity = Quantity - NEW.Qty_Sold WHERE Product_ID = NEW.Product_ID;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sale_inserted
BEFORE INSERT ON Sales
FOR EACH ROW EXECUTE FUNCTION update_stock_on_sale();
```

## 6. TESTING SCENARIOS
| Scenario | Input | Expected Outcome | Status |
| --- | --- | --- | --- |
| Register Staff | Email: clerk@store.com, Dept: Sales | Account registered in pending status | PASS |
| Admin User Action | Approve clerk@store.com | Status updates to active, Employee record created | PASS |
| Access Admin Route | Staff tries to load /admin | Blocked, redirect to dashboard with access denied alert | PASS |
| Record Purchase | Procure Laptop (Qty: 5) | Purchase saved. Product stock increments by 5 units | PASS |
| Record Out of Stock Sale | Sell Laptop (Qty: 100) | Database throws error, transaction aborted, error alert displayed | PASS |


## 7. CONCLUSION
NEXUS establishes that relational databases combined with transactional web frameworks provide reliable and secure inventory automation. Incorporating procedures directly into the database engine ensures complete data consistency and prevents invalid states, fulfilling the key objectives of the university database laboratory curriculum.
