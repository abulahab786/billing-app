import streamlit as st
import sqlite3
import pandas as pd
import datetime as dt
import hashlib
from streamlit_searchbox import st_searchbox
import os
import io
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except Exception:
    FPDF_AVAILABLE = False
from zoneinfo import ZoneInfo

# India timezone
INDIA_TZ = ZoneInfo("Asia/Kolkata")

def now_in_india():
    return dt.datetime.now(INDIA_TZ)

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
            (1001, "White Bread", 1, 150, 5, 0, 50,140,"Bakery","Bread","Raja","20-6-2026",7001,"Alam Megastore Relling","Jupiter Enterprise","CDFX65567FCC575Z"),
            (1002, "Brown Brade", 1, 100, 5, 0, 100,90,"Bakery","Bread","Raja","20-6-2026",7001,"Alam Megastore Relling","Jupiter Enterprise","CDFX65567FCC575Z"),
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


def generate_pdf(bill: dict, return_bytes: bool = False, force_ascii: bool = False):
    """Generate a professional, multi-page-capable PDF invoice. Returns bytes when `return_bytes=True`.

    bill: dict with keys: bill_no, date, time, customer_name, customer_mobile, items, totals
    """
    bill_no = str(bill.get('bill_no', 'invoice'))
    pdf_path = None
    if not return_bytes:
        os.makedirs('bills', exist_ok=True)
        pdf_path = os.path.join('bills', f"{bill_no}.pdf")

    # Text fallback
    if not FPDF_AVAILABLE:
        txt = []
        txt.append('Alam Megastore\n')
        txt.append(f"Bill No: {bill.get('bill_no')}  Date: {bill.get('date')} {bill.get('time')}\n")
        txt.append(f"Customer: {bill.get('customer_name')}  Mobile: {bill.get('customer_mobile')}\n\n")
        txt.append('Description\tQty\tRate\tAmount\n')
        for it in bill.get('items', []):
            txt.append(f"{it.get('item_name')}\t{it.get('qty')}\t{it.get('rate')}\t{it.get('amount')}\n")
        # total quantity for text fallback
        try:
            total_qty_txt = sum(int(float(it.get('qty', 0) or 0)) for it in bill.get('items', []))
        except Exception:
            total_qty_txt = 0
        t = bill.get('totals', {})
        txt.append(f"\nTotal Quantity: {total_qty_txt}\n")
        txt.append(f"Subtotal: {t.get('subtotal')}  Discount: {t.get('discount')}  Total: {t.get('total')}\n")
        txt_str = ''.join(txt)
        if return_bytes:
            return txt_str.encode('utf-8')
        if pdf_path is None:
            os.makedirs('bills', exist_ok=True)
            txt_path = os.path.join('bills', f"{bill_no}.txt")
        else:
            txt_path = os.path.join(os.path.dirname(pdf_path), f"{bill_no}.txt")
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(txt_str)
        return txt_path

    # Initialize PDF
    pdf = FPDF(unit='pt', format='A4')
    pdf.add_page()
    pdf.set_auto_page_break(False)

    # Try to register Unicode TTF for ₹ support
    unicode_font = False
    font_candidates = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/usr/share/fonts/truetype/freefont/FreeSans.ttf',
        'DejaVuSans.ttf',
    ]
    font_path = None
    for p in font_candidates:
        if os.path.exists(p):
            font_path = p
            break
    if font_path:
        try:
            pdf.add_font('DejaVu', '', fname=font_path, uni=True)
            for style in ('B', 'I', 'BI'):
                try:
                    pdf.add_font('DejaVu', style, fname=font_path, uni=True)
                except Exception:
                    pass
            unicode_font = True
        except Exception:
            unicode_font = False

    # If caller forced ASCII mode, disable unicode font usage
    if force_ascii:
        unicode_font = False

    # Choose base font depending on availability
    base_font = 'DejaVu' if unicode_font else 'Helvetica'

    # Layout settings
    primary = (0,40,30)
    accent = (202, 155, 26)
    header_h = 80
    left_margin = 30
    right_margin = 30
    bottom_margin = 50
    row_h = 18

    logo_path = 'logo.png'

    # Try to import QR libraries (optional)
    try:
        import qrcode
        from PIL import Image
        QR_AVAILABLE = True
    except Exception:
        QR_AVAILABLE = False

    # Helpers
    def header():
        pdf.set_fill_color(*primary)
        pdf.rect(0, 0, pdf.w, header_h, 'F')
        if os.path.exists(logo_path):
            try:
                pdf.image(logo_path, x=90, y=5, w=240, h=60)
            except Exception:
                pass
        pdf.set_text_color(255, 255, 220)
        pdf.set_font(base_font, 'B', 22)
        pdf.set_xy(90, 30)
        #pdf.cell(160, 20, 'Alam Megastore', ln=1)
        pdf.set_x(30)
        pdf.set_font(base_font, 'B', 12)
        pdf.cell(30, 90, 'Relling Bihibaray | Dist-Darjeeling | Mobile: 9832025468', ln=1)
        # Invoice badge
        bw = 150
        bh = 44
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(pdf.w - bw - 30, 20, bw, bh, 'F')
        pdf.set_xy(pdf.w - bw - 30, 28)
        pdf.set_text_color(*primary)
        pdf.set_font(base_font, 'B', 12)
        pdf.cell(bw, 12, 'INVOICE', align='C', ln=1)
        pdf.set_font(base_font, '', 9)
        pdf.set_xy(pdf.w - bw - 30, 44)
        pdf.cell(bw, 10, f"Bill No: {bill_no}", align='C')
        pdf.set_text_color(0, 0, 0)

    def table_header():
        pdf.set_fill_color(*primary)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(base_font, 'B', 11)
        pdf.set_x(left_margin)
        pdf.cell(300, 22, 'Description', border=0, fill=True)
        pdf.set_x(330)
        pdf.cell(60, 22, 'Qty', border=0, align='C', fill=True)
        pdf.set_x(390)
        pdf.cell(80, 22, 'Rate', border=0, align='R', fill=True)
        pdf.set_x(470)
        pdf.cell(80, 22, 'Amount', border=0, align='R', ln=1, fill=True)
        pdf.set_text_color(0, 0, 0)

    def footer():
        # page number
        page_no = pdf.page_no()
        pdf.set_xy(0, pdf.h - bottom_margin + 10)
        pdf.set_font(base_font, 'I', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 10, f'Page {page_no}', align='C')
        pdf.set_text_color(0, 0, 0)

    # Start content
    header()
    pdf.ln(10)
    # Customer & meta
    pdf.set_font(base_font, 'B', 11)
    pdf.set_x(left_margin)
    pdf.cell(80, 70, 'Customer:', ln=0)
    pdf.set_font(base_font, '', 11)
    pdf.cell(260, 70, f"{bill.get('customer_name','')}  {bill.get('customer_mobile','')}", ln=1)
    pdf.set_x(left_margin)
    pdf.set_font(base_font, 'B', 11)
    pdf.cell(80, 2, 'Date & Time:', ln=0)
    pdf.set_font(base_font, '', 11)
    pdf.cell(260, 2, f"{bill.get('date','')}      {bill.get('time','')}", ln=1)
    pdf.ln(6)

    # Items table
    table_header()
    pdf.set_font(base_font, '', 10)
    fill = False
    items = bill.get('items', [])
    # Compute GST total if item gst_amount provided
    gst_total = 0.0
    for it in items:
        try:
            gst_total += float(it.get('gst_amount', 0) or 0)
        except Exception:
            pass

    # Compute total quantity
    total_qty = 0
    for it in items:
        try:
            total_qty += int(float(it.get('qty', 0) or 0))
        except Exception:
            pass

    for it in items:
        # Check page space
        if pdf.get_y() + row_h + bottom_margin > pdf.h:
            footer()
            pdf.add_page()
            header()
            pdf.ln(10)
            table_header()
            pdf.set_font(base_font, '', 10)

        if fill:
            pdf.set_fill_color(*accent)
            fill_flag = True
        else:
            pdf.set_fill_color(255,247,230)
            fill_flag = True

        pdf.set_x(left_margin)
        desc = str(it.get('item_name', ''))[:60]
        pdf.cell(300, row_h, desc, border=0, fill=fill_flag)
        pdf.set_x(330)
        pdf.cell(60, row_h, str(it.get('qty', '')), border=0, align='C', fill=fill_flag)
        # currency
        def fmt(v):
            try:
                val = float(v)
            except Exception:
                val = 0.0
            return (f"₹{val:.2f}") if unicode_font else (f"Rs.{val:.2f}")

        pdf.set_x(390)
        pdf.cell(80, row_h, fmt(it.get('rate', 0)), border=2, align='R', fill=fill_flag)
        pdf.set_x(470)
        pdf.cell(80, row_h, fmt(it.get('amount', 0)), border=2, align='R', ln=1, fill=fill_flag)
        fill = not fill

    # Totals block
    t = bill.get('totals', {})
    # ensure space
    if pdf.get_y() + 140 + bottom_margin > pdf.h:
        footer()
        pdf.add_page()
        header()
        pdf.ln(10)

    right_x = 410
    pdf.set_x(right_x)
    pdf.set_font(base_font, '', 11)
    def fmt_total(v):
        try:
            val = float(v)
        except Exception:
            val = 0.0
        return (f"₹{val:.2f}") if unicode_font else (f"Rs.{val:.2f}")

    pdf.set_x(0)
    pdf.cell(0,18,'______________________________________________________________________________________________',align='C',ln=1)
    pdf.set_x(230)
    pdf.set_fill_color(100,123,23)
    pdf.cell(70, 18, 'Total Qty:', border=0,fill=True)
    pdf.cell(70, 18, str(total_qty), border=0, align='R', ln=0,fill=True)
    pdf.set_x(right_x)
    pdf.cell(70, 18, 'Subtotal:', border=4)    
    pdf.cell(70, 18, fmt_total(t.get('subtotal', 0)), border=0, align='R', ln=1)
    pdf.set_x(right_x)
    pdf.cell(70, 18, 'GST Total:', border=0)
    pdf.cell(70, 18, fmt_total(gst_total), border=4, align='R', ln=1)
    #pdf.set_x(right_x)
    #pdf.cell(70, 18, 'Total Qty:', border=0)
    #pdf.cell(70, 18, str(total_qty), border=0, align='R', ln=1)
    pdf.set_x(right_x)
    pdf.cell(70, 18, 'Discount:', border=0)
    pdf.cell(70, 18, fmt_total(t.get('discount', 0)), border=0, align='R', ln=1)

    # Highlight total
    pdf.set_x(right_x)
    pdf.set_fill_color(*primary)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(base_font, 'B', 13)
    pdf.cell(70, 22, 'Total:', border=0, fill=True)
    pdf.cell(70, 22, fmt_total(t.get('total', 0)), border=0, align='R', ln=1, fill=True)
    pdf.set_text_color(0, 0, 0)

    pdf.set_x(right_x)
    pdf.set_font(base_font, '', 11)
    pdf.cell(70, 18, 'Tender:', border=0)
    pdf.cell(70, 18, fmt_total(t.get('tender', 0)), border=0, align='R', ln=1)
    pdf.set_x(right_x)
    pdf.cell(70, 18, 'Change:', border=0)
    pdf.cell(70, 18, fmt_total(t.get('change', 0)), border=0, align='R', ln=1)
    pdf.ln(12)
    # Signature and bank details
    # Insert QR code image (if available) to left of signature/bank details
    qr_tmp_path = None
    try:
        if QR_AVAILABLE:
            import json, tempfile
            qr_payload = {
                'bill_no': bill_no,
                'date': bill.get('date'),
                'total': t.get('total')
            }
            qr = qrcode.QRCode(box_size=4, border=1)
            qr.add_data(json.dumps(qr_payload))
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            qr_tmp_path = tmp.name
            tmp.close()
            img.save(qr_tmp_path)
            # place QR image
            try:
                pdf.image(qr_tmp_path, x=left_margin, y=pdf.get_y(), w=80)
            except Exception:
                pass
    except Exception:
        qr_tmp_path = None

    # Signature boxes
    pdf.set_x(left_margin + 90)
    pdf.cell(240, 40, 'Received By: ______________________', ln=0)
    pdf.set_x(350)
    pdf.cell(240, 40, 'Authorised Signatory: ______________', ln=1)
    pdf.ln(6)
    pdf.set_x(left_margin)
    pdf.set_font(base_font, '', 9)
    pdf.multi_cell(0, 90, 'Bank Details: ABC Bank, IFSC: ABCD0123456, A/C: 1234567890', align='L')

    # cleanup temporary QR file
    try:
        if qr_tmp_path and os.path.exists(qr_tmp_path):
            os.unlink(qr_tmp_path)
    except Exception:
        pass

    # Footer on last page
    footer()

    # Output
    # Attempt to get PDF bytes. If fpdf fails with UnicodeEncodeError
    # (it tries to encode pages as latin-1), retry in ASCII mode (replace ₹ with Rs.)
    try:
        s = pdf.output(dest='S')
    except UnicodeEncodeError:
        if not force_ascii:
            # Retry generation forcing ASCII currency (no ₹)
            return generate_pdf(bill, return_bytes=return_bytes, force_ascii=True)
        raise

    if isinstance(s, (bytes, bytearray)):
        pdf_bytes = bytes(s)
    else:
        try:
            pdf_bytes = s.encode('latin-1')
        except Exception:
            pdf_bytes = s.encode('utf-8', errors='replace')

    if return_bytes:
        return pdf_bytes

    try:
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        return pdf_path
    except Exception:
        return pdf_bytes
        pdf.set_font('Helvetica', '', 11)
    pdf.set_x(totals_x)
    pdf.cell(totals_w_label, 18, 'Tender:', border=0)
    pdf.cell(totals_w_value, 18, (f"₹{float(t.get('tender',0)):.2f}" if unicode_font else f"Rs.{float(t.get('tender',0)):.2f}"), border=0, align='R', ln=1)

    pdf.set_x(totals_x)
    pdf.cell(totals_w_label, 18, 'Change:', border=0)
    pdf.cell(totals_w_value, 18, (f"₹{float(t.get('change',0)):.2f}" if unicode_font else f"Rs.{float(t.get('change',0)):.2f}"), border=0, align='R', ln=1)

    pdf.ln(12)
    # Footer thank you
    pdf.set_font(base_font, 'I', 10)
    pdf.multi_cell(0, 12, 'Thank you for visiting Alam Megastore. Visit again!', align='C')

    # Return PDF bytes (or write to disk if requested)
    s = pdf.output(dest='S')
    if isinstance(s, (bytes, bytearray)):
        pdf_bytes = bytes(s)
    else:
        try:
            pdf_bytes = s.encode('latin-1')
        except Exception:
            pdf_bytes = s.encode('utf-8', errors='replace')

    if return_bytes:
        return pdf_bytes

    # Save file and return path
    try:
        with open(pdf_path, 'wb') as f:
            f.write(pdf_bytes)
        return pdf_path
    except Exception:
        # fallback: return bytes if saving failed
        return pdf_bytes

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
        #st.markdown("""
            #<div style="text-align: center; margin-bottom: 1rem;">
                #<div style="font-size: 6rem;">🛒</div>
            #</div>
        #""", unsafe_allow_html=True)
        col1,col2,col3=st.columns([1,2,1])
        with col2:
            st.image('logo.png')
        #st.markdown('<div class="login-header">Alam Megastore</div>', unsafe_allow_html=True)
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
    st.markdown('<div class="main-header">🛒 Alam Megastore - Billing Software</div>', unsafe_allow_html=True)
    
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
                            ["🏠 Billing", "📦 Inventory", "➕ Add New Items","📊 Reports", "🔍 Search Bills", "👥 User Management","👥 Vendor Management","🗄️ Database Backup" ],
                            label_visibility="collapsed")
        elif st.session_state.user_role == "manager":
            page = st.radio("Navigation", 
                            ["🏠 Billing", "📦 Inventory","➕ Add New Items","📊 Reports", "🔍 Search Bills","👥 Vendor Management"],
                            label_visibility="collapsed")
        else:  # cashier
            page = st.radio("Navigation", 
                            ["🏠 Billing", "🔍 Search Bills"],
                            label_visibility="collapsed")
        
        st.markdown("---")
        st.info(f"**Bill No:** {st.session_state.invoice_no}")
        st.info(f"**Date:** {now_in_india().strftime('%d/%m/%Y')}")
        st.info(f"**Time:** {now_in_india().strftime('%H:%M:%S')}")
    
    # Main content based on page selection
    if page == "🏠 Billing":
        billing_page()
    elif page == "📦 Inventory":
        inventory_page()
    elif page == "➕ Add New Items":
        add_items()    
    elif page == "📊 Reports":
        reports_page()
    elif page == "🔍 Search Bills":
        search_bills_page()
    elif page == "👥 User Management":
        user_management_page()
    elif page == "👥 Vendor Management":
        vendor_add_page()    
    elif page == "🗄️ Database Backup":
        database_backup()    

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
            customer_mobile = st.text_input("📱 Customer Mobile", value=st.session_state.customer_mobile, max_chars=10)
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
                    #st.warning("New customer")
                    @st.dialog("New Customer Entry")
                    def addcust():
                        st.text_input("",value=customer_mobile)
                        customer_name=st.text_input("",placeholder="Enter Customer Name")
                        if st.button("Add Customer"):
                            st.session_state.customer_name = customer_name
                            st.success(f"Customer added: {customer_name}")
                            st.rerun()                        
                    addcust()
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
            tender_amount = st.number_input("💵 Enter Tender Amount", min_value=0.0, value=float(total_amount))
            #st.subheader("💳 Payment Mode")
            #payment_mode = st.selectbox("Select Mode", ["CASH", "CARD", "UPI", "GC CARD"])
            #st.session_state.payment_mode = payment_mode
        
        with btn_col3:
            if st.button("💾 Save & Print Bill", type="primary", width='stretch'):
                if not st.session_state.cart_items:
                    st.error("Cart is empty!")
                else:
                    # Generate bill
                    current_date = now_in_india().strftime('%d/%m/%Y')
                    current_time = now_in_india().strftime('%H:%M:%S')
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
                Alam Megastore
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
    Thank You for visit Alam Megastore
    =====================================
    """
                    
                    st.success("✅ Bill saved successfully!")

                    # Prepare structured bill data and generate PDF (or fallback to text file if FPDF not available)
                    bill_struct = {
                        'bill_no': bill_no,
                        'date': current_date,
                        'time': current_time,
                        'customer_name': st.session_state.customer_name,
                        'customer_mobile': st.session_state.customer_mobile,
                        'cashier': st.session_state.username,
                        'items': [
                            {
                                'item_name': it.get('item_name'),
                                'qty': it.get('qty'),
                                'rate': it.get('rate'),
                                'amount': it.get('amount')
                            } for it in st.session_state.cart_items
                        ],
                        'totals': {
                            'subtotal': sum(it.get('gross_amount', 0) for it in st.session_state.cart_items),
                            'discount': total_discount,
                            'total': total_amount,
                            'tender': tender_amount,
                            'change': tender_amount - total_amount
                        }
                    }

                    # Generate PDF/text bytes in-memory and show preview + download button
                    file_bytes = generate_pdf(bill_struct, return_bytes=True)

                    @st.dialog('Bill Test')
                    def billprint():
                        st.code(bill_text, language=None)
                        try:
                            # Detect whether bytes look like a PDF (starts with %PDF)
                            is_pdf = isinstance(file_bytes, (bytes, bytearray)) and file_bytes[:4] == b"%PDF"
                            file_label = f"{bill_no}.{'pdf' if is_pdf else 'txt'}"
                            mime = 'application/pdf' if is_pdf else 'text/plain'
                            if st.download_button(label=f"Download Invoice ({file_label})", data=file_bytes, file_name=file_label, mime=mime)==True:
                                downfile= st.progress(100)                                
                                st.success("Invoice Download Completed!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Could not prepare download: {e}")
                        
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
                    st.session_state.payment_mode = "CASH"
                    conn.close()
                    st.session_state.item_search=""
                    st.session_state.selected_item=[]
                    st.session_state.quantity=1
                    st.session_state.selected_item=[""]
                    

                    

                    
                    st.balloons()
                    
                   
                    
    else:
        st.info("🛒 Cart is empty. Add items to start billing.")

def inventory_page():      
    st.subheader("📦 Inventory Management")
         
    itemsearch=st.text_input("",placeholder="Type the Item Code")
    
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
                        st.info("   Need to Add from \n \n➕ Add New Item Tab from SidebarMenu")
                        
                    # Add new item

                    #with st.expander("➕ Add New Item Tab"):
                            

                    #with st.form("add_item_form"):
                                                        
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
    
    
def add_items():
    #================Functions For Item Add=======================================
    def search_catagory(searchc: str):
        """Search function for streamlit-searchbox"""
        if not searchc:
            return []
        
        conn = sqlite3.connect('billing_app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT catagory FROM catagory
            WHERE catagory LIKE ? 
            ORDER BY catagory 
            LIMIT 20
        ''', (f'%{searchc}%',))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    def search_subcatagory(searchs: str):
        """Search function for streamlit-searchbox"""
        if not searchs:
            return []
        
        conn = sqlite3.connect('billing_app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT sub_catagory FROM sub_catagory 
            WHERE sub_catagory LIKE ? 
            ORDER BY sub_catagory 
            LIMIT 20
        ''', (f'%{searchs}%',))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    def search_brand(searchb: str):
        """Search function for streamlit-searchbox"""
        if not searchb:
            return []
        
        conn = sqlite3.connect('billing_app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT brand FROM brand 
            WHERE brand LIKE ? 
            ORDER BY brand
            LIMIT 20
        ''', (f'%{searchb}%',))
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results
    def search_vendor(searchv: str):
        """Search function for streamlit-searchbox"""
        if not searchv:
            return []
        
        conn = sqlite3.connect('billing_app.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT vendor_name FROM vendor_details 
            WHERE vendor_name LIKE ? 
            ORDER BY vendor_name 
            LIMIT 20
        ''', (f'%{searchv}%',))
        
        results = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT vendor_gst FROM vendor_details WHERE vendor_name LIKE ? ORDER BY vendor_name LIMIT 1", (f'%{searchv}%',))
        gstget= cursor.fetchall()
        print(gstget)
        st.session_state.vendorgst=gstget[0][0] if gstget else 0.0
        
        conn.close()
        
        return results
    #========================================================================
    st.subheader("➕ Add New Items")

    col1, col2 = st.columns(2)
    with col1:
        new_code = st.text_input("Item Code")
        new_name = st.text_input("Item Name")
        new_rate = st.number_input("Rate", min_value=0.0, step=0.01)
        new_gstin = st.number_input("GST %", min_value=0.0, max_value=100.0, value=0.0)
        new_discount = st.number_input("Discount %", min_value=0.0, max_value=100.0, value=0.0)
        new_soh = st.number_input("Stock on Hand", min_value=0, value=0)
        cost = st.number_input("Purchase Cost", min_value=0.0, step=0.01)
        catag =st_searchbox(search_catagory,clear_on_submit=False,label="Search Catagory",key="searchc")
    with col2:
        scatag = st_searchbox(search_subcatagory,clear_on_submit=False,label="Search Sub-Catagory",key="searchs")
        brand = st_searchbox(search_brand,clear_on_submit=False,label="Search Brand Name",key="searchb")
        expiry = st.date_input("Select Expiry Date")
        storecode = st.number_input("Store Code", min_value=0, value=7001)
        storename = st.selectbox("Store Name", ("Alam Megastore Relling","Alam Megastore Siliguri"))
        vendorname = st_searchbox(search_vendor,clear_on_submit=False,label="Search Vendor",key="searchv")
        vendorgst=st.text_input("Vendor GSTNO",value=st.session_state.get('vendorgst',''))                                
                                    
                                
    if st.button("Add Item"):
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

    st.subheader("Category, Sub-Category and Brand Update Below ") 
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    with cat_col1:
        new_catagory = st.text_input("New Catagory")
        if st.button("Add Catagory"):
            conn = sqlite3.connect('billing_app.db')
            cur = conn.cursor()
            cur.execute("SELECT catagory FROM catagory WHERE catagory=?", (new_catagory,))   
            result = cur.fetchone()
            if result and result[0] == new_catagory:
                st.error("❌ Catagory already exists!")
                conn.close()
            
            else:
                cur.execute("INSERT INTO catagory (catagory) VALUES (?)", (new_catagory,))
                conn.commit()
                st.success("✅ Catagory added successfully!")
           
                conn.close()    
    with cat_col2:
        new_subcatagory = st.text_input("New Sub-Catagory")
        if st.button("Add Sub-Catagory"):
            conn = sqlite3.connect('billing_app.db')
            cur = conn.cursor()
            cur.execute("SELECT sub_catagory FROM sub_catagory WHERE sub_catagory=?", (new_subcatagory,))   
            result = cur.fetchone()
            if result and result[0] == new_subcatagory:
                st.error("❌ Sub-Catagory already exists!")
                conn.close()
            else:
                cur.execute("INSERT INTO sub_catagory (sub_catagory) VALUES (?)", (new_subcatagory,))
                conn.commit()
                st.success("✅ Sub-Catagory added successfully!")
            
                conn.close()    
    with cat_col3:
        new_brand = st.text_input("New Brand")
        if st.button("Add Brand"):
            conn = sqlite3.connect('billing_app.db')
            cur = conn.cursor()
            cur.execute("SELECT brand FROM brand WHERE brand=?", (new_brand,))
            result = cur.fetchone()
            if result and result[0] == new_brand:
                st.error("❌ Brand already exists!")
                conn.close()
            else:
                cur.execute("INSERT OR IGNORE INTO brand (brand) VALUES (?)", (new_brand,))
                conn.commit()
                st.success("✅ Brand added successfully!")
            
                conn.close()
def vendor_add_page():
    st.subheader("Vendor Add Dashboard")
    st.write("This is the Vendor Add Dashboard.")
    col1,col2=st.columns(2)
    with col1:
        vendor_id= st.text_input("Vendor ID")
        vendor_name= st.text_input("Vendor Name")
        vendor_mobile= st.text_input("Vendor Mobile")
        vendor_gst= st.text_input("Vendor GST No")
        vendor_address= st.text_area("Vendor Address")
    with col2:
        bank_name= st.text_input("Bank Name")
        account_no= st.text_input("Account No")
        ifsc_code= st.text_input("IFSC Code")
        branch= st.text_input("Branch")
    if st.button("Add Vendor"):
        conn=sqlite3.connect("billing_app.db")
        cur=conn.cursor()
        cur.execute("INSERT INTO vendor_details (vendor_id,vendor_name,vendor_mobile,vendor_gst,vendor_address,bank_name,bank_ac_no,bank_ifsc,bank_branch) VALUES(?,?,?,?,?,?,?,?,?)",(vendor_id,vendor_name,vendor_mobile,vendor_gst,vendor_address,bank_name,account_no,ifsc_code,branch))
        conn.commit()
        conn.close()
        st.success("Vendor Added Successfully!")

def reports_page():
    st.subheader("📊 Sales Reports")
    
    # Get sales data
    current_date = now_in_india().strftime('%d/%m/%Y')
    conn = sqlite3.connect('billing_app.db')
    sales_df = pd.read_sql_query("SELECT * FROM billdata ORDER BY id DESC LIMIT 50", conn)
    sale_details=pd.read_sql_query("SELECT * FROM saledetails",conn)
    daysale=pd.read_sql_query("SELECT * FROM saledetails WHERE date='"+current_date+"'",conn)
    conn.close()    
    
    if not sales_df.empty:
        # Summary metrics
        #st.metric("Total Revenue", f"₹{sales_df['amount'].sum():.2f}")
        current_date = now_in_india().strftime('%d/%m/%Y')
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
                sales_df[['bill_no', 'date', 'time', 'cust_name','cust_mobile', 'amount', 'payment_mode', 'cashier']],
                width='stretch',
                hide_index=True,
                column_config={
                    'bill_no': 'Bill No',
                    'date': 'Date',
                    'time': 'Time',
                    'cust_name': 'Customer',
                    'cust_mobile':'Customer Mobile',
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

def database_backup():
    st.subheader("🗄️ Database Backup")
    #===============
    def backupdata(source_path,backup_path):
        src_conn=sqlite3.connect(source_path)
        bck_conn=sqlite3.connect(backup_path)
        with bck_conn:
            src_conn.backup(
                bck_conn,
                pages=0,
                progress=progress_callback
            )
        print("Backup Success")   
        bck_conn.close()
        src_conn.close()
    def progress_callback(status,remaining,total):
        st.success(f"Copied {total - remaining} of {total} pages....")
    if st.button("Backup DB"):
        backupdata("billing_app.db","billing_app_backup.db") 
        file_path="billing_app_backup.db" 
        with open(file_path,"rb") as f:
            st.download_button(
                label="Download DB Backup",
                data=f,
                file_name="billing_app_bak.db",
                )
             

    # Display all users
    conn = sqlite3.connect('billing_app.db')
    #cur=conn.cursor()
    billd=pd.read_sql_query("SELECT * FROM billdata",conn)
    inv=pd.read_sql_query("SELECT * FROM invoicedata",conn)
    item=pd.read_sql_query("SELECT * FROM itemadd",conn)
    saled=pd.read_sql_query("SELECT * FROM saledetails",conn)
    usrd=pd.read_sql_query("SELECT * FROM user_data",conn)
    if st.button("Dowload all Tables Data in CSV"):
        billd.to_csv("billdata.csv",index=None)
        inv.to_csv("invoicedata.csv",index=None)
        item.to_csv("itemadd.csv",index=None)
        saled.to_csv("saledetails.csv",index=None)
        usrd.to_csv("user_data.csv",index=None)
          
    
    st.subheader("Import Item Data From CSV file as example showing below")
    conn=sqlite3.connect("billing_app.db") 
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
          
                    
# Main execution
if not st.session_state.logged_in:
    login_page()
else:
    main_app()                   