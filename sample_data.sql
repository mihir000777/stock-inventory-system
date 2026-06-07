-- Sample Data: Stock Inventory Management System (with Users & Authentication)

-- 1. Insert Users (with Werkzeug-compatible hashed passwords)
-- Admin User: admin@store.com / admin123
-- Active Staff User: staff@store.com / staff123
-- Pending Staff User: pending@store.com / pending123
INSERT INTO Users (Name, Email, Password_Hash, Role, Status) VALUES
('System Administrator', 'admin@store.com', 'scrypt:32768:8:1$FT6dCeVayBco5qOZ$76ae1e33bc12dbd5d9c8f29c8629e4a073c9c7de07fa87a99a1107895e1a4696869adc28846c9b706d2f1d3962c3591551dae600a8ba1d588cc57ee7a1ce869d', 'admin', 'active'),
('Active Staff Operator', 'staff@store.com', 'scrypt:32768:8:1$J9xKFCOmkKfbyLu1$c09aaabdf23b7de56986059855a3cf6820e32a7dde79738f93733e52ec1d9230d238442bc2872aea7d36b32f9109f7c5de05c5cc35e2ac6ef16e02f9cd6f35ce', 'staff', 'active'),
('Pending Staff Clerk', 'pending@store.com', 'scrypt:32768:8:1$txxFEoypvsXR8M7Q$8e3738044422b836ce4af07caa0be4f1cba38e1d6e652a50bc3a42ad82e17e1ab74297a1b31a1c1165114660c596edc137a2c10c4e49ff21cd133d21a7b02d5c', 'staff', 'pending');

-- 2. Insert Suppliers
INSERT INTO Supplier (Name, Phone_No, Address, Email, City) VALUES
('Tech Distributors', '+1-555-0199', '100 Tech Way', 'sales@techdist.com', 'San Francisco'),
('Office Essentials', '+1-555-0120', '456 Paper Rd', 'info@officeessentials.com', 'New York'),
('Global Furniture Co', '+1-555-0144', '789 Oak Ave', 'support@globalfurn.com', 'Chicago');

-- 3. Insert Employees
INSERT INTO Employee (Name, Email, Phone, Department) VALUES
('John Doe', 'john.doe@inventory.com', '+1-555-9011', 'Sales'),
('Jane Smith', 'jane.smith@inventory.com', '+1-555-9022', 'Procurement');

-- 4. Insert Customers
INSERT INTO Customer (Name, Phone, Email, Address) VALUES
('Alice Johnson', '+1-555-4433', 'alice.j@gmail.com', '12 Main St, San Jose'),
('Bob Miller', '+1-555-8877', 'bob.miller@yahoo.com', '34 Pine Rd, Brooklyn');

-- 5. Insert Products
INSERT INTO Product (Name, Category, Price, Quantity, Supplier_ID) VALUES
('Quantum Laptop', 'Electronics', 899.99, 10, 1),
('Ergonomic Office Chair', 'Furniture', 149.99, 2, 3),
('Wireless Mouse', 'Electronics', 24.99, 15, 1),
('Hardcover Notebook', 'Office Supplies', 8.50, 5, 2),
('Classic Cotton T-Shirt', 'Apparel', 19.99, 30, 2);

-- 6. Insert Purchases (Trigger will increase product stock automatically)
-- Purchase 1: Laptop (Product_ID 1) - Quantity 5. Stock: 10 + 5 = 15
INSERT INTO Purchase (Product_ID, Supplier_ID, Quantity, Purchase_Date, Employee_ID) VALUES
(1, 1, 5, '2026-06-01', 2);

-- Purchase 2: Office Chair (Product_ID 2) - Quantity 4. Stock: 2 + 4 = 6
INSERT INTO Purchase (Product_ID, Supplier_ID, Quantity, Purchase_Date, Employee_ID) VALUES
(2, 3, 4, '2026-06-02', 2);

-- Purchase 3: Notebook (Product_ID 4) - Quantity 10. Stock: 5 + 10 = 15
INSERT INTO Purchase (Product_ID, Supplier_ID, Quantity, Purchase_Date, Employee_ID) VALUES
(4, 2, 10, '2026-06-03', 2);

-- 7. Insert Sales (Trigger will decrease product stock automatically)
-- Sale 1: Laptop (Product_ID 1) - Qty_Sold 3. Stock: 15 - 3 = 12
INSERT INTO Sales (Product_ID, Qty_Sold, Sales_Date, Employee_ID, Customer_ID) VALUES
(1, 3, '2026-06-04', 1, 1);

-- Sale 2: Notebook (Product_ID 4) - Qty_Sold 7. Stock: 15 - 7 = 8
INSERT INTO Sales (Product_ID, Qty_Sold, Sales_Date, Employee_ID, Customer_ID) VALUES
(4, 7, '2026-06-05', 1, 2);

-- Sale 3: T-Shirt (Product_ID 5) - Qty_Sold 12. Stock: 30 - 12 = 18
INSERT INTO Sales (Product_ID, Qty_Sold, Sales_Date, Employee_ID, Customer_ID) VALUES
(5, 12, '2026-06-06', 1, 1);
