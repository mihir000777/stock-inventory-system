-- Database Schema: Stock Inventory Management System (with Users & Authentication)

-- 1. Supplier Table
CREATE TABLE Supplier (
    Supplier_ID SERIAL PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Phone_No VARCHAR(50),
    Address TEXT,
    Email VARCHAR(255),
    City VARCHAR(100)
);

-- 2. Product Table
CREATE TABLE Product (
    Product_ID SERIAL PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Category VARCHAR(100),
    Price NUMERIC(10, 2) NOT NULL CHECK (Price >= 0),
    Quantity INTEGER NOT NULL DEFAULT 0 CHECK (Quantity >= 0),
    Supplier_ID INTEGER,
    CONSTRAINT fk_product_supplier 
        FOREIGN KEY (Supplier_ID) 
        REFERENCES Supplier(Supplier_ID) 
        ON DELETE SET NULL
);

-- 3. Employee Table
CREATE TABLE Employee (
    Employee_ID SERIAL PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Email VARCHAR(255),
    Phone VARCHAR(50),
    Department VARCHAR(100)
);

-- 4. Customer Table
CREATE TABLE Customer (
    Customer_ID SERIAL PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Phone VARCHAR(50),
    Email VARCHAR(255),
    Address TEXT
);

-- 5. Purchase Table
CREATE TABLE Purchase (
    Purchase_ID SERIAL PRIMARY KEY,
    Product_ID INTEGER NOT NULL,
    Supplier_ID INTEGER,
    Quantity INTEGER NOT NULL CHECK (Quantity > 0),
    Purchase_Date DATE DEFAULT CURRENT_DATE,
    Employee_ID INTEGER,
    CONSTRAINT fk_purchase_product 
        FOREIGN KEY (Product_ID) 
        REFERENCES Product(Product_ID) 
        ON DELETE CASCADE,
    CONSTRAINT fk_purchase_supplier 
        FOREIGN KEY (Supplier_ID) 
        REFERENCES Supplier(Supplier_ID) 
        ON DELETE SET NULL,
    CONSTRAINT fk_purchase_employee 
        FOREIGN KEY (Employee_ID) 
        REFERENCES Employee(Employee_ID) 
        ON DELETE SET NULL
);

-- 6. Sales Table
CREATE TABLE Sales (
    Sales_ID SERIAL PRIMARY KEY,
    Product_ID INTEGER NOT NULL,
    Qty_Sold INTEGER NOT NULL CHECK (Qty_Sold > 0),
    Sales_Date DATE DEFAULT CURRENT_DATE,
    Employee_ID INTEGER,
    Customer_ID INTEGER,
    CONSTRAINT fk_sales_product 
        FOREIGN KEY (Product_ID) 
        REFERENCES Product(Product_ID) 
        ON DELETE CASCADE,
    CONSTRAINT fk_sales_employee 
        FOREIGN KEY (Employee_ID) 
        REFERENCES Employee(Employee_ID) 
        ON DELETE SET NULL,
    CONSTRAINT fk_sales_customer 
        FOREIGN KEY (Customer_ID) 
        REFERENCES Customer(Customer_ID) 
        ON DELETE SET NULL
);

-- 7. Users Table (for Authentication and Authorization)
CREATE TABLE Users (
    User_ID SERIAL PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Email VARCHAR(255) UNIQUE NOT NULL,
    Password_Hash VARCHAR(255) NOT NULL,
    Role VARCHAR(50) DEFAULT 'staff',
    Status VARCHAR(50) DEFAULT 'pending',
    Created_At TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to Automatically Update Stock on Purchase
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
FOR EACH ROW
EXECUTE FUNCTION update_stock_on_purchase();

-- Trigger to Automatically Check and Update Stock on Sale
CREATE OR REPLACE FUNCTION update_stock_on_sale()
RETURNS TRIGGER AS $$
DECLARE
    current_stock INTEGER;
BEGIN
    -- Fetch the current stock quantity for the product
    SELECT Quantity INTO current_stock
    FROM Product
    WHERE Product_ID = NEW.Product_ID;

    -- If product doesn't exist, raise exception
    IF current_stock IS NULL THEN
        RAISE EXCEPTION 'Product with ID % does not exist.', NEW.Product_ID;
    -- If stock is insufficient, block sale and raise exception
    ELSIF current_stock < NEW.Qty_Sold THEN
        RAISE EXCEPTION 'Insufficient stock for product. Available: %, requested: %', current_stock, NEW.Qty_Sold;
    -- Otherwise, decrease the stock
    ELSE
        UPDATE Product
        SET Quantity = Quantity - NEW.Qty_Sold
        WHERE Product_ID = NEW.Product_ID;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sale_inserted
BEFORE INSERT ON Sales
FOR EACH ROW
EXECUTE FUNCTION update_stock_on_sale();
