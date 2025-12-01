import streamlit as st
import sqlite3
import pandas as pd
import datetime as dt
import random
import hashlib
from streamlit_searchbox import st_searchbox
#from fpdf import FPDF

# Page configuration
st.set_page_config(
    page_title="Billing Software",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
#st.markdown("""
#<style>
    
#</style>
#""", unsafe_allow_html=True)

#===========Upload CSS File=================
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>",unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_role' not in st.session_state:
    st.session_state.user_role = ""
if 'cart_items' not in st.session_state:
    st.session_state.cart_items = []
if 'invoice_no' not in st.session_state:
    
    conn = sqlite3.connect('billing_app.db')
    cur = conn.cursor()
    cur.execute("SELECT MAX(rowid),* FROM invoicedata")
    eg = cur.fetchmany()
    print(eg)
    for v in eg:    
        st.session_state.invoice_no=(v[6]+1)
if 'customer_name' not in st.session_state:
    st.session_state.customer_name = ""
if 'customer_mobile' not in st.session_state:
    st.session_state.customer_mobile = ""
if 'payment_mode' not in st.session_state:
    st.session_state.payment_mode = "CASH"

# Database functions
def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect('billing_app.db')
    cur = conn.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'cashier'
        )
    """)
    
    # Check if default users exist, if not create them
    cur.execute("SELECT COUNT(*) FROM user_data")
    if cur.fetchone()[0] == 0:
        # Hash passwords
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        cashier_pass = hashlib.sha256("cashier123".encode()).hexdigest()
        manager_pass = hashlib.sha256("manager123".encode()).hexdigest()
        
        default_users = [
            ("admin", admin_pass, "admin"),
            ("cashier", cashier_pass, "cashier"),
            ("manager", manager_pass, "manager")
        ]
        cur.executemany("INSERT INTO user_data (username, password, role) VALUES (?, ?, ?)", default_users)
    
    # Create items table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS itemadd (
            item_code INTEGER PRIMARY KEY,
            item_name TEXT,
            qty INTEGER DEFAULT 1,
            rate REAL,
            gstin REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            soh INTEGER DEFAULT 0,
            cost INTEGER,
            catagory TEXT,
            sub_catagory TEXT,
            brand TEXT,
            expiry_date TEXT,
            store_code INTEGER,
            store_name TEXT,
            vendor_name TEXT,
            vendor_gst TEXT
        )
    """)
    
    # Create customer table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS billdata (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            bill_no TEXT,
            amount REAL,
            cust_name TEXT,
            cust_mobile TEXT,
            payment_mode TEXT,
            cashier TEXT
        )
    """)
    
    # Create sales details table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS saledetails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            bill_no TEXT,
            item_code INTEGER,
            item_name TEXT,
            qty INTEGER,
            rate REAL,
            gstin REAL,
            gst_amount REAL,
            discount REAL,
            dis_amount REAL,
            gross_amount REAL,
            net_amount REAL,
            soh INTEGER,
            cost INTEGER,
            catagory TEXT,
            sub_catagory TEXT,
            brand TEXT,
            expiry_date TEXT,
            store_code INTEGER,
            store_name TEXT,
            vendor_name TEXT,
            vendor_gst TEXT
        )
    """)
    
    # Insert sample items if table is empty
    cur.execute("SELECT COUNT(*) FROM itemadd")
    if cur.fetchone()[0] == 0:
        sample_items = [
            (1001, "White Bread", 1, 150, 5, 0, 50,140,"Bakery","Bread","Raja","20-6-2026",7001,"Alam Cellular Relling","Jupiter Enterprise","CDFX65567FCC575Z"),
            (1002, "Brown Brade", 1, 100, 5, 0, 100,90,"Bakery","Bread","Raja","20-6-2026",7001,"Alam Cellular Relling","Jupiter Enterprise","CDFX65567FCC575Z"),
            #(1003, "Phone Case", 1, 500, 12, 5, 200),
            #(1004, "Screen Protector", 1, 300, 12, 0, 150),
            #(1005, "Power Bank 10000mAh", 1, 1500, 18, 8, 75),
            #(1006, "USB Cable Type-C", 1, 250, 12, 5, 300),
            #(1007, "Wall Charger Fast", 1, 800, 18, 10, 120),
            #(1008, "Bluetooth Speaker", 1, 3500, 18, 15, 60)
        ]
        cur.executemany("""
            INSERT INTO itemadd (item_code, item_name, qty, rate, gstin, discount, soh,cost,catagory,sub_catagory,brand,expiry_date,store_code,store_name,vendor_name,vendor_gst)
            VALUES (?, ?, ?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?)
        """, sample_items)
    
    conn.commit()
    conn.close()

def verify_login(username, password):
    """Verify user credentials"""
    conn = sqlite3.connect('billing_app.db')
    cur = conn.cursor()
    
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    cur.execute("SELECT username, role FROM user_data WHERE username = ? AND password = ?", 
                (username, hashed_password))
    result = cur.fetchone()
    conn.close()
    
    return result

def search_item(search_term):
    """Search for item by code or name"""
    conn = sqlite3.connect('billing_app.db')
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM itemadd 
        WHERE item_code = ? OR item_name LIKE ?
    """, (search_term, f"%{search_term}%"))
    result= cur.fetchone()      
    conn.close()
    return result

def search_items(searchterm: str):
    """Search function for streamlit-searchbox"""
    if not searchterm:
        return []
    
    conn = sqlite3.connect('billing_app.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT item_name FROM itemadd 
        WHERE item_name LIKE ? 
        ORDER BY item_name 
        LIMIT 20
    ''', (f'%{searchterm}%',))
    
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    return results

def get_all_items():
    """Get all items from database"""
    conn = sqlite3.connect('billing_app.db')
    df = pd.read_sql_query("SELECT * FROM itemadd", conn)
    conn.close()
    return df

def save_bill(bill_data, cart_items):
    """Save bill to database"""
    conn = sqlite3.connect('billing_app.db')
    cur = conn.cursor()
    
    # Save main bill
    cur.execute("""
        INSERT INTO billdata (date, time, bill_no, amount, cust_name, cust_mobile, payment_mode, cashier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, bill_data)
    
    #SOH Update
    for x in cart_items:
        global sohup
        sohup=[]
        sohin=(x[3])
        cur.execute("SELECT * FROM itemadd WHERE item_code=("+str(x[3])+")")
        sohup=cur.fetchone()
        data=(sohup[6]-x[5],sohup[0])
        sohupdate=("""UPDATE itemadd SET soh=? WHERE item_code=?""")
        cur.execute(sohupdate,data)
        conn.commit()
        print("SOH Update")
    # Save sale details
    for item in cart_items:
        #print(item)
        cur.execute("""
            INSERT INTO saledetails 
            (date, time, bill_no, item_code, item_name, qty, rate, gstin, gst_amount, 
             discount, dis_amount, gross_amount, net_amount, soh,cost,catagory,sub_catagory,brand,expiry_date,store_code,store_name,vendor_name,vendor_gst)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?)
        """, item)     


    
    conn.commit()
    conn.close()

def logout():
    """Logout user"""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_role = ""
    st.session_state.cart_items = []
    st.rerun()

# Initialize database
init_database()

# Login Page
def login_page():
    # Center content
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        #st.markdown('<div class="login-container">', unsafe_allow_html=True)
        #st.markdown('<div class="login-box">', unsafe_allow_html=True)
        
        # Logo/Icon
        st.markdown("""
            <div style="text-align: center; margin-bottom: 1rem;">
                <div style="font-size: 6rem;">🛒</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="login-header">Alam Cellular</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subheader">Billing Management System</div>', unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form") :
            username = st.text_input("👤 Username", placeholder="Enter your username")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
            
            submit = st.form_submit_button("🔐 Login", width='stretch')
            
            if submit:
                if username and password:
                    result = verify_login(username, password)
                    if result:
                        st.session_state.logged_in = True
                        st.session_state.username = result[0]
                        st.session_state.user_role = result[1]
                        st.success(f"✅ Welcome {result[0]}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password!")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Demo credentials info
        with st.expander("ℹ️ Demo Credentials"):
            st.markdown("""
            NONE
            """)

# Main App (after login)
def main_app():
    # Header
    st.markdown('<div class="main-header">🛒 Alam Cellular - Billing Software</div>', unsafe_allow_html=True)
    
    # Sidebar for navigation
    with st.sidebar:
        st.image('logo.png', width=190)
        
        # User info
        st.markdown("---")
        st.success(f"👤 **User:** {st.session_state.username}")
        st.info(f"🎭 **Role:** {st.session_state.user_role.upper()}")
        
        if st.button("🚪 Logout", width='stretch'):
            logout()
        
        st.markdown("---")
        
        # Navigation based on role
        if st.session_state.user_role == "admin":
            page = st.radio("Navigation", 
                            ["🏠 Billing", "📦 Inventory", "📊 Reports", "🔍 Search Bills", "👥 User Management"],
                            label_visibility="collapsed")
        elif st.session_state.user_role == "manager":
            page = st.radio("Navigation", 
                            ["🏠 Billing", "📦 Inventory", "📊 Reports", "🔍 Search Bills"],
                            label_visibility="collapsed")
        else:  # cashier
            page = st.radio("Navigation", 
                            ["🏠 Billing", "🔍 Search Bills"],
                            label_visibility="collapsed")
        
        st.markdown("---")
        st.info(f"**Bill No:** {st.session_state.invoice_no}")
        st.info(f"**Date:** {dt.datetime.now().strftime('%d/%m/%Y')}")
        st.info(f"**Time:** {dt.datetime.now().strftime('%H:%M:%S')}")
    
    # Main content based on page selection
    if page == "🏠 Billing":
        billing_page()
    elif page == "📦 Inventory":
        inventory_page()
    elif page == "📊 Reports":
        reports_page()
    elif page == "🔍 Search Bills":
        search_bills_page()
    elif page == "👥 User Management":
        user_management_page()

def item_reset():
    #st.session_state.quantity=1
    st.session_state.item_search=""
    st.session_state.selected_item=[]

def billing_page():
    # Customer Information
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.subheader("👤 Customer Information")
        cust_col1, cust_col2 = st.columns(2)
        with cust_col1:
            customer_mobile = st.text_input("📱 Customer Mobile", value=st.session_state.customer_mobile)
            if st.button("🔍 Search Customer"):
                conn = sqlite3.connect('billing_app.db')
                cur = conn.cursor()
                cur.execute("SELECT cust_name, cust_mobile FROM billdata WHERE cust_mobile = ?", (customer_mobile,))
                result = cur.fetchone()
                conn.close()
                if result:
                    st.session_state.customer_name = result[0]
                    st.session_state.customer_mobile = result[1]
                    st.success(f"Customer found: {result[0]}")
                else:
                    st.warning("New customer")
        
        with cust_col2:
            customer_name = st.text_input("👤 Customer Name", value=st.session_state.customer_name)
            st.session_state.customer_name = customer_name
            st.session_state.customer_mobile = customer_mobile
    
    with col2:
        st.subheader("💳 Payment Mode")
        payment_mode = st.selectbox("Select Mode", ["CASH", "CARD", "UPI", "GC CARD"])
        st.session_state.payment_mode = payment_mode
    
    st.markdown("---")
    
   
    st.subheader("🔍 Add Items to Cart")
    search_col1, search_col2 = st.columns([3, 1])
   
    with search_col1:        
        item_search = st.text_input("",placeholder="Type item code or EAN No")
        # Item Search
        selected_item = st_searchbox(
        search_items,
        key="item_searchbox",
        placeholder="Search items...with Names",
        #label="🔍 Search for an item with Names",
        clear_on_submit=False,
        #clearable=False
        )
    
    with search_col2:
        quantity = st.number_input("Quantity", min_value=1, value=1)
    
    with search_col2:
        #st.write("")
        #st.write("")
        if st.button("➕ Add to Cart", width='stretch'):
            if item_search:
                i = search_item(item_search)
                #item=(i[0],i[1],i[2],i[3],i[4],i[5],i[6])
                if i:
                    item_code, item_name, _, rate, gstin, discount, soh,cost,catagory,sub_catagory,brand = (i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7],i[8],i[9],i[10])
                    
                    # Calculate amounts
                    total_rate = rate * quantity
                    dis_amount = total_rate * discount / 100
                    amount = total_rate - dis_amount
                    gst_amount = amount * gstin / 100
                    gross_amount = amount
                    net_amount = amount-gst_amount
                    costnew=(i[7]*quantity)
                    
                    # Add to cart
                    cart_item = {
                        'item_code': item_code,
                        'item_name': item_name,
                        'qty': quantity,
                        'rate': rate,
                        'gstin':i[4],
                        'gst_amount':gst_amount,
                        'discount': discount,
                        'dis_amount': dis_amount,
                        'gross_amount': gross_amount,
                        'amount': net_amount,
                        'cost':costnew,
                        'catagory':i[8],
                        'sub_catagory':i[9],
                        'brand':i[10],
                        'expiry_date':i[11],
                        'store_code':i[12],
                        'store_name':i[13],
                        'vendor_name':i[14],
                        'vendor_gst':i[15]
                    }
                    st.session_state.cart_items.append(cart_item)
                    st.success(f"✅ Added {item_name} to cart!") 
                    item_reset()
                    
                    #st.session_state.item_search=['']                                   
                    st.rerun()
                  
                else:
                    st.error("❌ Item not found!")
    
            elif selected_item:
                i = search_item(selected_item)
                #item=(i[0],i[1],i[2],i[3],i[4],i[5],i[6])
                if i:
                    item_code, item_name, _, rate, gstin, discount, soh,cost,catagory,sub_catagory,brand = (i[0],i[1],i[2],i[3],i[4],i[5],i[6],i[7],i[8],i[9],i[10])
                    
                    # Calculate amounts
                    total_rate = rate * quantity
                    dis_amount = total_rate * discount / 100
                    amount = total_rate - dis_amount
                    gst_amount = amount * gstin / 100
                    gross_amount = amount
                    net_amount = amount-gst_amount
                    costnew=(i[7]*quantity)
                    
                    # Add to cart
                    cart_item = {
                        'item_code': item_code,
                        'item_name': item_name,
                        'qty': quantity,
                        'rate': rate,
                        'gstin':i[4],
                        'gst_amount':gst_amount,
                        'discount': discount,
                        'dis_amount': dis_amount,
                        'gross_amount': gross_amount,
                        'amount': net_amount,
                        'cost':costnew,
                        'catagory':i[8],
                        'sub_catagory':i[9],
                        'brand':i[10],
                        'expiry_date':i[11],
                        'store_code':i[12],
                        'store_name':i[13],
                        'vendor_name':i[14],
                        'vendor_gst':i[15]
                    }
                    st.session_state.cart_items.append(cart_item)
                    st.success(f"✅ Added {item_name} to cart!") 
                    #st.session_state.item_search == ['']  
                    item_reset()                                 
                    st.rerun()                    
                else:
                    st.error("❌ Item not found!")
    # Display Cart
    st.markdown("---")
    st.subheader("🛒 Shopping Cart")
    
    if st.session_state.cart_items:
        # Create DataFrame for display
        cart_df = pd.DataFrame(st.session_state.cart_items)
        
        # Display table
        st.dataframe(
            cart_df[['item_code', 'item_name', 'qty', 'rate', 'gst_amount','discount', 'amount']],
            width='stretch',
            hide_index=True,
            column_config={
                'item_code': 'Code',
                'item_name': 'Item Name',
                'qty': 'Qty',
                'rate': st.column_config.NumberColumn('Rate', format="₹%.2f"),
                'gst_amount':st.column_config.NumberColumn('Gst',format="₹%.2f"),
                'discount': st.column_config.NumberColumn('Disc %', format="%.1f%%"),
                'amount': st.column_config.NumberColumn('Net-Amount', format="₹%.2f")
            }
        )
        
        # Totals
        total_qty = sum(item['qty'] for item in st.session_state.cart_items)
        total_discount = sum(item['dis_amount'] for item in st.session_state.cart_items)
        total_amount = sum(item['gross_amount'] for item in st.session_state.cart_items)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Items", total_qty)
        with col2:
            st.metric("Sub Total", f"₹{sum(item['gross_amount'] for item in st.session_state.cart_items):.2f}")
        with col3:
            st.metric("Discount", f"₹{total_discount:.2f}")
        with col4:
            st.markdown(f'<div class="total-box"> ₹{total_amount:.2f}</div>', unsafe_allow_html=True)
        
        # Action buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        st.session_state.item_search =""
        
        with btn_col1:
            if st.button("🗑️ Clear Cart", width='stretch'):
                st.session_state.cart_items = []
                st.rerun()
        
        with btn_col2:
            tender_amount = st.number_input("💵 Tender Amount", min_value=0.0, value=float(total_amount))
            #st.subheader("💳 Payment Mode")
            #payment_mode = st.selectbox("Select Mode", ["CASH", "CARD", "UPI", "GC CARD"])
            #st.session_state.payment_mode = payment_mode
        
        with btn_col3:
            if st.button("💾 Save & Print Bill", type="primary", width='stretch'):
                if not st.session_state.cart_items:
                    st.error("Cart is empty!")
                else:
                    # Generate bill
                    current_date = dt.datetime.now().strftime('%d/%m/%Y')
                    current_time = dt.datetime.now().strftime('%H:%M:%S')
                    bill_no = f"{st.session_state.invoice_no}"
                    conn=sqlite3.connect('billing_app.db')
                    cur=conn.cursor()
                    cur.execute("INSERT INTO invoicedata (reg_no,cm_no,bill_no) VALUES(null,null,'"+(bill_no)+"')")
                    conn.commit()
                    
                    # Prepare bill data
                    bill_data = (
                        current_date, current_time, bill_no, total_amount,
                        st.session_state.customer_name, st.session_state.customer_mobile,
                        st.session_state.payment_mode, st.session_state.username
                    )
                    
                    # Prepare sale details
                    sale_details = []
                    for item in st.session_state.cart_items:
                        sale_detail = (
                            current_date, current_time, bill_no,
                            item['item_code'], item['item_name'], item['qty'],
                            item['rate'], item['gstin'], item['gst_amount'], item['discount'],
                            item['dis_amount'], item['gross_amount'], item['amount'], 0,
                            item['cost'],item['catagory'],item['sub_catagory'],item['brand'],item['expiry_date'],
                            item['store_code'],item['store_name'],item['vendor_name'],item['vendor_gst']
                        )
                        sale_details.append(sale_detail)
                    
                    # Save to database
                    save_bill(bill_data, sale_details)
                    
                    
                    # Generate bill text
                    bill_text = f"""
    =====================================
                Alam Cellular
              Relling Bihibaray
               Dist-Darjeeling
              Mobile-9832025468
    =====================================
    Bill No: {bill_no}
    Date: {current_date}  Time: {current_time}
    Customer: {st.session_state.customer_name}
    Mobile: {st.session_state.customer_mobile}
    Cashier: {st.session_state.username}
    =====================================
    Item Name         Qty   Rate   Amount
    =====================================
    """
                    
                    for item in st.session_state.cart_items:
                        bill_text += f"\n   {item['item_name'][:20]:20}{item['qty']:3} {item['rate']:7.2f} {item['amount']:8.2f}"
                    
                    bill_text += f"""
    =====================================
    Total Qty: {total_qty}
    Discount: ₹{total_discount:.2f}
    Total Amount: ₹{total_amount:.2f}
    Tender: ₹{tender_amount:.2f}
    Change: ₹{tender_amount - total_amount:.2f}
    Payment Mode: {st.session_state.payment_mode}
    =====================================
    Thank You for visit Alam Cellular
    =====================================
    """
                    
                    st.success("✅ Bill saved successfully!")
                    #PDF GENERATE=======================================================
                    
                    #file1=open("bills/"+str(bill_no)+".txt",'w')
                    #file1.write(bill_text)
                    #file1.close()

                    
                    @st.dialog('Bill Test')
                    def billprint():
                        st.code(bill_text, language=None)
                        if st.button("Next Bill"):
                            search_item=''
                            st.rerun()
                    billprint()
                    # Reset for next bill
                    conn = sqlite3.connect('billing_app.db')
                    cur = conn.cursor()
                    cur.execute("SELECT MAX(rowid),* FROM invoicedata")
                    eg = cur.fetchmany()
                    print(eg)
                    for v in eg:    
                        st.session_state.invoice_no=(v[6]+1)
                    st.session_state.cart_items = []
                    #st.session_state.invoice_no = bill_no
                    st.session_state.customer_name = ""
                    st.session_state.customer_mobile = ""
                    st.session_state.item_search = ""
                    

                    
                    st.balloons()
                    
                   
                    
    else:
        st.info("🛒 Cart is empty. Add items to start billing.")

def inventory_page():
    conn=sqlite3.connect("billing_app.db")
    st.subheader("📦 Inventory Management") 
    st.text("Sample Format for Making CSV file (Ensure all row should be their with proper Heading)")
    sampledata=pd.read_sql_query("SELECT * FROM itemadd LIMIT 2",conn)
    st.dataframe(sampledata,width="stretch",hide_index=True)
    upload_csv=st.file_uploader("Choose CSV File to import")
    
    
    #item=[]
    if st.button("import Item Data",width=300):
        if upload_csv==upload_csv:

            df=pd.read_csv(upload_csv)
            df.columns=df.columns.str.strip()
            
            #head=next(df)
            data=[]
            
            #data.append(x)
            #print(x)
            conn=sqlite3.connect("billing_app.db")
            cur=conn.cursor()
            df.to_sql("itemadd",conn, if_exists="replace",index=0)
            conn.commit()
            conn.close()
            st.success("Data Imported Successfully")
        else:
            st.info("Please Upload the CSV File")    
          
        
    itemsearch=st.text_input("",placeholder="Type the Item Code")
    #if st.button("Take Item from Camera"):
        #caminput=st.camera_input("Cam Input")
    if st.button("Search",width=200):
        if itemsearch:
                i = search_item(itemsearch)
                if i:
                    item_code, item_name, rate, gstin, discount, soh ,cost,expiry_date,vendorname,vendorgst= (i[0],i[1],i[3],i[4],i[5],i[6],i[7],i[8],i[11],i[12])
                    @st.dialog("Item Details")
                    def itemd():
                        st.form("ITEM DETAILS")
                        
                        col1,col2=st.columns(2)
                        with col1:
                            itemc=st.text_input("Item Code",value=(i[0]))
                            itemn=st.text_input("Item name",value=(i[1]))
                            mrp=st.text_input("MRP",value=(i[3]))
                            gstv=st.text_input("Gstin%",value=(i[4]))
                            dis=st.text_input("Discount%",value=(i[5]))
                            sohinhand=st.number_input("SOH",value=(i[6]))
                            costp=st.number_input("COST",value=(i[7]))
                        with col2:
                            cat=st.text_input("catagory",value=(i[8]))
                            subc=st.text_input("Sub Catagory",value=(i[9]))
                            brd=st.text_input("Brand",value=(i[10]))
                            exd=st.text_input("Expiry Date",value=(i[11]))
                            vdn=st.text_input("Vendor Name",value=(i[14]))
                            vdg=st.text_input("Vendor GST",value=(i[15]))

                        sohin=st.number_input("SOH INPUT",value=0)
                        def sohinword():
                            conn=sqlite3.connect("billing_app.db")
                            cur=conn.cursor()
                            data=(sohin+sohinhand,(i[0]))
                            cur.execute("""UPDATE itemadd SET item_name='"+str(itemn)+"',rate='"+str(mrp)+"',gstin='"+str(gstv)+"',discount='"+str(dis)+"',
                                            cost='"+str(costp)+"',catagory='"+str(cat)+"',sub_catagory='"+str(subc)+"',brand='"+str(brd)+"',expiry_date='"+str(exd)+"',vendor_name='"+str(vdn)+"',vendor_gst='"+str(vdg)+"' WHERE item_code='"+str(itemc)+"'""")        
                            conn.commit()
                            query=("""UPDATE itemadd SET soh=? WHERE item_code=?""")
                            cur.execute(query,data)
                            conn.commit()
                            print("SOH IN DONE")
                        if st.button("Click to Update Item Details"):
                            sohinword()
                            st.rerun()


                    itemd()
                else:
                    @st.dialog("Information")
                    def itemaddtab():
                        st.error("Item Not Found")
                        st.info("   Need to Add from \n \n➕ Add New Item Tab Below")
                        
                    # Add new item
                        with st.expander("➕ Add New Item Tab"):
                            with st.form("add_item_form"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_code = st.text_input("Item Code",value=(itemsearch))
                                    new_name = st.text_input("Item Name")
                                    new_rate = st.number_input("Rate", min_value=0.0, step=0.01)
                                    new_gstin = st.number_input("GST %", min_value=0.0, max_value=100.0, value=0.0)
                                    new_discount = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0)
                                    new_soh = st.number_input("Stock on Hand", min_value=0, value=0)
                                    cost = st.number_input("Purchase Cost", min_value=0.0, step=0.01)
                                    catag = st.text_input("Catagory")
                                with col2:
                                    scatag = st.text_input("Sub-Catagory")
                                    brand = st.text_input("Brand")
                                    expiry = st.date_input("Select Expiry Date")
                                    storecode = st.number_input("Store Code", min_value=0, value=7001)
                                    storename = st.selectbox("Store Name", ("Alam Cellular Relling","Alam Cellular Siliguri"))
                                    vendorname = st.text_input("Vendor Name")
                                    vendorgst=st.text_input("Vendor GSTNO")
                                    
                                
                                if st.form_submit_button("Add Item"):
                                    conn = sqlite3.connect('billing_app.db')
                                    cur = conn.cursor()
                                    try:
                                        cur.execute("""
                                            INSERT INTO itemadd (item_code, item_name, qty, rate, gstin, discount, soh,cost,catagory,sub_catagory,brand,expiry_date,store_code,store_name,vendor_name,vendor_gst)
                                            VALUES (?, ?, 1, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?)
                                        """, (new_code, new_name, new_rate, new_gstin, new_discount, new_soh,cost,catag,scatag,brand,expiry,storecode,storename,vendorname,vendorgst))
                                        conn.commit()
                                        st.success("✅ Item added successfully!")
                                        #st.rerun()
                                    except sqlite3.IntegrityError:
                                        st.error("❌ Item code already exists!")
                                    finally:
                                        conn.close()
                                    
                    itemaddtab()
                    
    # Display all items
    items_df = get_all_items()
    
    if not items_df.empty:
        st.dataframe(
            items_df,
            width='stretch',
            hide_index=True,
            column_config={
                'item_code': 'Item Code',
                'item_name': 'Item Name',
                'qty': 'Default Qty',
                'rate': st.column_config.NumberColumn('Rate', format="₹%.2f"),
                'gstin': st.column_config.NumberColumn('GST %', format="%.1f%%"),
                'discount': st.column_config.NumberColumn('Discount %', format="%.1f%%"),
                'soh': 'Stock on Hand'
            }
        )
    else:
        st.info("No items in inventory")
    
    

   

        

def reports_page():
    st.subheader("📊 Sales Reports")
    
    # Get sales data
    current_date = dt.datetime.now().strftime('%d/%m/%Y')
    conn = sqlite3.connect('billing_app.db')
    sales_df = pd.read_sql_query("SELECT * FROM billdata ORDER BY id DESC LIMIT 50", conn)
    sale_details=pd.read_sql_query("SELECT * FROM saledetails",conn)
    daysale=pd.read_sql_query("SELECT * FROM saledetails WHERE date='"+current_date+"'",conn)
    conn.close()
    
    if not sales_df.empty:
        # Summary metrics
        #st.metric("Total Revenue", f"₹{sales_df['amount'].sum():.2f}")
        current_date = dt.datetime.now().strftime('%d/%m/%Y')
        co1,co2=st.columns(2)
        total_Revenue=sales_df['amount'].sum()
        total_day=sales_df[sales_df['date']== current_date]['amount'].sum()
        with co1:
            st.markdown(f'<div class="total-rev">Total Revenue = ₹{total_Revenue:.2f}</div>', unsafe_allow_html=True)
        with co2:
            st.markdown(f'<div class="total-rev">Today Sale = ₹{total_day:.2f}</div>', unsafe_allow_html=True)    
        st.markdown("---")
        col1, col2, col3, col4,col5= st.columns(5)
        with col1:
            st.metric("Total Bills", len(sales_df))        
        with col2:
            st.metric("Avg Bill Value", f"₹{sales_df['amount'].mean():.2f}")
        with col3:
            cash_sales = sales_df[sales_df['payment_mode'] == 'CASH']['amount'].sum()
            st.metric("Cash Sales", f"₹{cash_sales:.2f}")
        with col4:
            card_sales = sales_df[sales_df['payment_mode'] == 'CARD']['amount'].sum()
            st.metric("Card Sales", f"₹{card_sales:.2f}")
        with col5:
            upi_sales = sales_df[sales_df['payment_mode'] == 'UPI']['amount'].sum()
            st.metric("UPI Sales", f"₹{upi_sales:.2f}")    
        
        st.markdown("---")
        if st.button("Show Sale Invoice Data"):
            if st.button("Hide Sale Data"):
                st.rerun()
            # Display sales table
            st.dataframe(
                sales_df[['bill_no', 'date', 'time', 'cust_name', 'amount', 'payment_mode', 'cashier']],
                width='stretch',
                hide_index=True,
                column_config={
                    'bill_no': 'Bill No',
                    'date': 'Date',
                    'time': 'Time',
                    'cust_name': 'Customer',
                    'amount': st.column_config.NumberColumn('Amount', format="₹ %.2f"),
                    #'amount':'Amount',
                    'payment_mode': 'Payment',
                    'cashier': 'Cashier'
                }
            )
        elif st.button("Show Todays Sale"):
            if st.button("Hide Sale Data"):
                st.rerun()
            # Display sales table
            st.dataframe(daysale,
                
                width='stretch',
                hide_index=True,
                
            )
        elif st.button("Show Sale Details All"):
            if st.button("Hide Sale Data"):
                st.rerun()
            # Display sales table
            st.dataframe(sale_details,
                
                width='stretch',
                hide_index=True,
                
            )    
    else:
        st.info("No sales data available")

def search_bills_page():
    st.subheader("🔍 Search Bills")
    
    search_bill = st.text_input("Enter Bill Number", placeholder="e.g., 101123456")
    
    if st.button("Search"):
        if search_bill:
            conn = sqlite3.connect('billing_app.db')
            
            # Get bill header
            bill_df = pd.read_sql_query(
                "SELECT * FROM billdata WHERE bill_no = ?", 
                conn, 
                params=(search_bill,)
            )
            
            if not bill_df.empty:
                # Display bill info
                bill_info = bill_df.iloc[0]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Bill No:** {bill_info['bill_no']}")
                    st.info(f"**Customer:** {bill_info['cust_name']}")
                with col2:
                    st.info(f"**Date:** {bill_info['date']}")
                    st.info(f"**Time:** {bill_info['time']}")
                with col3:
                    st.info(f"**Amount:** ₹{bill_info['amount']:.2f}")
                    st.info(f"**Payment:** {bill_info['payment_mode']}")
                
                # Get bill items
                items_df = pd.read_sql_query(
                    "SELECT * FROM saledetails WHERE bill_no = ?", 
                    conn, 
                    params=(search_bill,)
                )
                
                if not items_df.empty:
                    st.markdown("### Items")
                    st.dataframe(
                        items_df[['item_code', 'item_name', 'qty', 'rate', 'discount', 'gross_amount']],
                        width='stretch',
                        hide_index=True
                    )
            else:
                st.warning("Bill not found!")
            
            conn.close()

def user_management_page():
    st.subheader("👥 User Management")
    
    # Display all users
    conn = sqlite3.connect('billing_app.db')
    users_df = pd.read_sql_query("SELECT id, username, role FROM user_data", conn)
    conn.close()
    
    if not users_df.empty:
        st.dataframe(
            users_df,
            width='stretch',
            hide_index=True,
            column_config={
                'id': 'ID',
                'username': 'Username',
                'role': 'Role'
            }
        )
    
    # Add new user
    with st.expander("➕ Add New User"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                has_password=hashlib.sha256(new_password.strip().encode()).hexdigest()
            with col2:
                new_role = st.selectbox("Role", ["cashier", "manager", "admin"])
            
            if st.form_submit_button("Add User"):
                if new_username and new_password:
                    conn = sqlite3.connect('billing_app.db')
                    cur = conn.cursor()
                    try:
                        cur.execute("INSERT INTO user_data (username,password,role) VALUES ('"+str(new_username)+"','"+str(has_password)+"','"+str(new_role)+"')")
                        st.success("User Added Successfully")
                    except sqlite3.IntegrityError:
                        #cur.execute("UPDATE user_data SET username='"+str(new_username)+"',password='"+str(has_password)+"',role='"+str(new_role)+"'")
                        st.error("❌ USER Already Available")
                    finally:
                        conn.commit()
                        conn.close() 

    with st.expander("➕ UPDATE AND DELETE USER"):
        with st.form("update & ❌Delete user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
                has_password=hashlib.sha256(new_password.strip().encode()).hexdigest()
            with col2:
                new_role = st.selectbox("Role", ["cashier", "manager", "admin"])                      
            if st.form_submit_button("Update User"):
                if new_username and new_password:
                    conn = sqlite3.connect('billing_app.db')
                    cur = conn.cursor()
                    cur.execute("UPDATE user_data SET username='"+str(new_username)+"',password='"+str(has_password)+"',role='"+str(new_role)+"' WHERE username='"+str(new_username)+"'")
                    st.success("User Updated Successfully")
                    conn.commit()
                    conn.close()
            if st.form_submit_button("❌Delete User"):
                if new_username:
                    conn = sqlite3.connect('billing_app.db')
                    cur = conn.cursor()
                    cur.execute("DELETE from user_data WHERE username='"+str(new_username)+"'")
                    st.error("User Deleted Successfully")
                    conn.commit()
                    conn.close()          


                    
# Main execution
if not st.session_state.logged_in:
    login_page()
else:
    main_app()                   
