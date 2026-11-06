"""
MongoDB database utilities for Billing App
Replaces SQLite3 database operations
"""

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection string (update with your MongoDB URI)
#MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://abulahabslm_db_admin:Passw0rd@alammegastore.pzlbxsw.mongodb.net/?appName=alammegastore")
DB_NAME = "billing_app"

def get_db():
    """Get MongoDB database instance"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db, client

def close_connection(client):
    """Close MongoDB connection"""
    client.close()

def init_database():
    """Initialize MongoDB collections with required indexes and sample data"""
    db, client = get_db()
    
    try:
        # Create collections if they don't exist
        collections = {
            'user_data': 'username',
            'invoicedata': None,
            'itemadd': 'item_code',
            'billdata': 'bill_no',
            'saledetails': None,
            'catagory': 'catagory',
            'sub_catagory': 'sub_catagory',
            'brand': 'brand',
            'vendor_details': 'vendor_id'
        }
        
        for collection_name, unique_field in collections.items():
            if collection_name not in db.list_collection_names():
                db.create_collection(collection_name)
                
            # Create unique indexes
            if unique_field:
                try:
                    db[collection_name].create_index([(unique_field, ASCENDING)], unique=True)
                except:
                    pass
        
        # Add default users if none exist
        if db.user_data.count_documents({}) == 0:
            import hashlib
            default_users = [
                {
                    "username": "admin",
                    "password": hashlib.sha256("admin123".encode()).hexdigest(),
                    "role": "admin"
                },
                {
                    "username": "cashier",
                    "password": hashlib.sha256("cashier123".encode()).hexdigest(),
                    "role": "cashier"
                },
                {
                    "username": "manager",
                    "password": hashlib.sha256("manager123".encode()).hexdigest(),
                    "role": "manager"
                }
            ]
            db.user_data.insert_many(default_users)
        
        # Add sample items if none exist
        if db.itemadd.count_documents({}) == 0:
            sample_items = [
                {
                    "item_code": 1001,
                    "item_name": "White Bread",
                    "qty": 1,
                    "rate": 150,
                    "gstin": 5,
                    "discount": 0,
                    "soh": 50,
                    "cost": 140,
                    "catagory": "Bakery",
                    "sub_catagory": "Bread",
                    "brand": "Raja",
                    "expiry_date": "20-6-2026",
                    "store_code": 7001,
                    "store_name": "Alam Megastore Relling",
                    "vendor_name": "Jupiter Enterprise",
                    "vendor_gst": "CDFX65567FCC575Z"
                },
                {
                    "item_code": 1002,
                    "item_name": "Brown Bread",
                    "qty": 1,
                    "rate": 100,
                    "gstin": 5,
                    "discount": 0,
                    "soh": 100,
                    "cost": 90,
                    "catagory": "Bakery",
                    "sub_catagory": "Bread",
                    "brand": "Raja",
                    "expiry_date": "20-6-2026",
                    "store_code": 7001,
                    "store_name": "Alam Megastore Relling",
                    "vendor_name": "Jupiter Enterprise",
                    "vendor_gst": "CDFX65567FCC575Z"
                }
            ]
            db.itemadd.insert_many(sample_items)
        
        print("MongoDB initialized successfully!")
        
    finally:
        close_connection(client)

# User operations
def verify_login(username, password):
    """Verify user credentials"""
    db, client = get_db()
    try:
        user = db.user_data.find_one({
            "username": username,
            "password": password
        })
        return user
    finally:
        close_connection(client)

def get_all_users():
    """Get all users"""
    db, client = get_db()
    try:
        users = list(db.user_data.find({}, {"password": 0}))
        return users
    finally:
        close_connection(client)

def insert_user(username, password, role):
    """Insert new user"""
    db, client = get_db()
    try:
        result = db.user_data.insert_one({
            "username": username,
            "password": password,
            "role": role
        })
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Username already exists!")
    finally:
        close_connection(client)

def update_user(username, password, role):
    """Update user"""
    db, client = get_db()
    try:
        result = db.user_data.update_one(
            {"username": username},
            {"$set": {"password": password, "role": role}}
        )
        return result.modified_count
    finally:
        close_connection(client)

def delete_user(username):
    """Delete user"""
    db, client = get_db()
    try:
        result = db.user_data.delete_one({"username": username})
        return result.deleted_count
    finally:
        close_connection(client)

# Item operations
def search_item(search_term):
    """Search for item by code or name"""
    db, client = get_db()
    try:
        # Try to convert to integer for item_code search
        try:
            item_code = int(search_term)
            item = db.itemadd.find_one({"item_code": item_code})
            if item:
                return item
        except ValueError:
            pass
        
        # Search by name
        item = db.itemadd.find_one({"item_name": {"$regex": search_term, "$options": "i"}})
        return item
    finally:
        close_connection(client)

def search_items(search_term):
    """Search function for streamlit-searchbox - returns item names"""
    if not search_term:
        return []
    
    db, client = get_db()
    try:
        results = db.itemadd.find(
            {"item_name": {"$regex": search_term, "$options": "i"}},
            {"item_name": 1}
        ).limit(20)
        return [item['item_name'] for item in results]
    finally:
        close_connection(client)

def get_all_items():
    """Get all items from database"""
    db, client = get_db()
    try:
        items = list(db.itemadd.find({}))
        return items
    finally:
        close_connection(client)

def insert_item(item_data):
    """Insert new item"""
    db, client = get_db()
    try:
        result = db.itemadd.insert_one(item_data)
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Item code already exists!")
    finally:
        close_connection(client)

def update_item_soh(item_code, new_soh):
    """Update stock on hand"""
    db, client = get_db()
    try:
        result = db.itemadd.update_one(
            {"item_code": item_code},
            {"$set": {"soh": new_soh}}
        )
        return result.modified_count
    finally:
        close_connection(client)

def update_item(item_code, update_data):
    """Update item details"""
    db, client = get_db()
    try:
        result = db.itemadd.update_one(
            {"item_code": item_code},
            {"$set": update_data}
        )
        return result.modified_count
    finally:
        close_connection(client)

# Bill operations
def save_bill(bill_data, sale_details):
    """Save bill and sale details"""
    db, client = get_db()
    try:
        # Insert main bill
        bill_result = db.billdata.insert_one(bill_data)
        
        # Insert sale details
        if sale_details:
            db.saledetails.insert_many(sale_details)
        
        return bill_result.inserted_id
    finally:
        close_connection(client)

def search_bill(bill_no):
    """Search for bill by bill number"""
    db, client = get_db()
    try:
        bill = db.billdata.find_one({"bill_no": str(bill_no)})
        return bill
    finally:
        close_connection(client)

def get_bill_items(bill_no):
    """Get items for a specific bill"""
    db, client = get_db()
    try:
        items = list(db.saledetails.find({"bill_no": str(bill_no)}))
        return items
    finally:
        close_connection(client)

def get_all_bills():
    """Get all bills"""
    db, client = get_db()
    try:
        bills = list(db.billdata.find({}).sort("_id", -1).limit(50))
        return bills
    finally:
        close_connection(client)

def get_all_sale_details():
    """Get all sale details"""
    db, client = get_db()
    try:
        details = list(db.saledetails.find({}))
        return details
    finally:
        close_connection(client)

def get_day_sales(date):
    """Get sales for a specific date"""
    db, client = get_db()
    try:
        sales = list(db.saledetails.find({"date": date}))
        return sales
    finally:
        close_connection(client)

# Invoice operations
def get_max_invoice_no():
    """Get the maximum invoice number"""
    db, client = get_db()
    try:
        invoice = db.invoicedata.find_one(sort=[("bill_no", -1)])
        if invoice:
            bill_no = invoice.get('bill_no', 0)
            # Convert to int if it's a string
            if isinstance(bill_no, str):
                try:
                    bill_no = int(bill_no)
                except (ValueError, TypeError):
                    bill_no = 0
            return bill_no + 1
        return 1
    finally:
        close_connection(client)

def insert_invoice(invoice_data):
    """Insert invoice record"""
    db, client = get_db()
    try:
        # Ensure bill_no is stored as integer
        if 'bill_no' in invoice_data and isinstance(invoice_data['bill_no'], str):
            try:
                invoice_data['bill_no'] = int(invoice_data['bill_no'])
            except (ValueError, TypeError):
                pass
        result = db.invoicedata.insert_one(invoice_data)
        return result.inserted_id
    finally:
        close_connection(client)

# Category operations
def search_catagory(search_term):
    """Search categories"""
    if not search_term:
        return []
    
    db, client = get_db()
    try:
        results = db.catagory.find(
            {"catagory": {"$regex": search_term, "$options": "i"}},
            {"catagory": 1}
        ).limit(20)
        return [item['catagory'] for item in results]
    finally:
        close_connection(client)

def insert_catagory(catagory_name):
    """Insert new category"""
    db, client = get_db()
    try:
        result = db.catagory.insert_one({"catagory": catagory_name})
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Category already exists!")
    finally:
        close_connection(client)

# Sub-Category operations
def search_subcatagory(search_term):
    """Search sub-categories"""
    if not search_term:
        return []
    
    db, client = get_db()
    try:
        results = db.sub_catagory.find(
            {"sub_catagory": {"$regex": search_term, "$options": "i"}},
            {"sub_catagory": 1}
        ).limit(20)
        return [item['sub_catagory'] for item in results]
    finally:
        close_connection(client)

def insert_subcatagory(subcatagory_name):
    """Insert new sub-category"""
    db, client = get_db()
    try:
        result = db.sub_catagory.insert_one({"sub_catagory": subcatagory_name})
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Sub-category already exists!")
    finally:
        close_connection(client)

# Brand operations
def search_brand(search_term):
    """Search brands"""
    if not search_term:
        return []
    
    db, client = get_db()
    try:
        results = db.brand.find(
            {"brand": {"$regex": search_term, "$options": "i"}},
            {"brand": 1}
        ).limit(20)
        return [item['brand'] for item in results]
    finally:
        close_connection(client)

def insert_brand(brand_name):
    """Insert new brand"""
    db, client = get_db()
    try:
        result = db.brand.insert_one({"brand": brand_name})
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Brand already exists!")
    finally:
        close_connection(client)

# Vendor operations
def search_vendor(search_term):
    """Search vendors"""
    if not search_term:
        return []
    
    db, client = get_db()
    try:
        results = db.vendor_details.find(
            {"vendor_name": {"$regex": search_term, "$options": "i"}},
            {"vendor_name": 1, "vendor_gst": 1}
        ).limit(20)
        return [item['vendor_name'] for item in results]
    finally:
        close_connection(client)

def get_vendor_gst(vendor_name):
    """Get vendor GST"""
    db, client = get_db()
    try:
        vendor = db.vendor_details.find_one(
            {"vendor_name": {"$regex": vendor_name, "$options": "i"}},
            {"vendor_gst": 1}
        )
        return vendor.get('vendor_gst', '') if vendor else ''
    finally:
        close_connection(client)

def insert_vendor(vendor_data):
    """Insert new vendor"""
    db, client = get_db()
    try:
        result = db.vendor_details.insert_one(vendor_data)
        return result.inserted_id
    except DuplicateKeyError:
        raise Exception("Vendor ID already exists!")
    finally:
        close_connection(client)

# Customer operations
def search_customer_by_mobile(mobile):
    """Search customer by mobile"""
    db, client = get_db()
    try:
        customer = db.billdata.find_one(
            {"cust_mobile": mobile},
            {"cust_name": 1, "cust_mobile": 1}
        )
        return customer
    finally:
        close_connection(client)
