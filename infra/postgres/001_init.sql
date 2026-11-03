-- Initial transactional ERP source schema.
CREATE TABLE suppliers (
    supplier_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country CHAR(2) NOT NULL,
    lead_time_days INTEGER NOT NULL CHECK (lead_time_days > 0)
);
CREATE TABLE materials (
    material_id INTEGER PRIMARY KEY,
    sku TEXT UNIQUE NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    unit_of_measure VARCHAR(3) NOT NULL
);
CREATE TABLE warehouses (
    warehouse_id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE purchase_orders (
    order_id INTEGER PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(supplier_id),
    order_date DATE NOT NULL,
    promised_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN', 'PARTIAL', 'CLOSED')),
    CHECK (promised_date >= order_date)
);
CREATE TABLE purchase_order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES purchase_orders(order_id),
    material_id INTEGER NOT NULL REFERENCES materials(material_id),
    ordered_qty INTEGER NOT NULL CHECK (ordered_qty > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0)
);
CREATE TABLE goods_receipts (
    receipt_id INTEGER PRIMARY KEY,
    order_item_id INTEGER NOT NULL REFERENCES purchase_order_items(order_item_id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
    receipt_date DATE NOT NULL,
    received_qty INTEGER NOT NULL CHECK (received_qty > 0)
);
CREATE TABLE inventory_movements (
    movement_id INTEGER PRIMARY KEY,
    receipt_id INTEGER UNIQUE NOT NULL REFERENCES goods_receipts(receipt_id),
    material_id INTEGER NOT NULL REFERENCES materials(material_id),
    warehouse_id INTEGER NOT NULL REFERENCES warehouses(warehouse_id),
    movement_date DATE NOT NULL,
    quantity_delta INTEGER NOT NULL CHECK (quantity_delta > 0),
    movement_type TEXT NOT NULL CHECK (movement_type = 'RECEIPT')
);
CREATE INDEX ix_po_supplier ON purchase_orders(supplier_id);
CREATE INDEX ix_po_items_order ON purchase_order_items(order_id);
CREATE INDEX ix_receipts_item ON goods_receipts(order_item_id);
CREATE INDEX ix_movements_date ON inventory_movements(movement_date);
