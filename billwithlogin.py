import streamlit as st
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
# Import MongoDB utilities
import mongo_db as db_ops

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
    invoice_no = db_ops.get_max_invoice_no()
    st.session_state.invoice_no = invoice_no
if 'customer_name' not in st.session_state:
    st.session_state.customer_name = ""
if 'customer_mobile' not in st.session_state:
    st.session_state.customer_mobile = ""
if 'payment_mode' not in st.session_state:
    st.session_state.payment_mode = "CASH"

# Database functions
def init_database():
    """Initialize MongoDB database with required collections"""
    db_ops.init_database()

def verify_login(username, password):
    """Verify user credentials"""
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    result = db_ops.verify_login(username, hashed_password)
    
    if result:
        return (result.get('username'), result.get('role'))
    return None

def search_item(search_term):
    """Search for item by code or name"""
    result = db_ops.search_item(search_term)
    return result

def search_items(searchterm: str):
    """Search function for streamlit-searchbox"""
    return db_ops.search_items(searchterm)

def get_all_items():
    """Get all items from database"""
    items = db_ops.get_all_items()
    if items:
        return pd.DataFrame(items)
    return pd.DataFrame()

def save_bill(bill_data, cart_items):
    """Save bill to database"""
    # Prepare bill document
    bill_doc = {
        'date': bill_data[0],
        'time': bill_data[1],
        'bill_no': bill_data[2],
        'amount': bill_data[3],
        'cust_name': bill_data[4],
        'cust_mobile': bill_data[5],
        'payment_mode': bill_data[6],
        'cashier': bill_data[7]
    }
    
    # Convert cart items to sale details documents
    sale_details = []
    for item in cart_items:
        sale_detail = {
            'date': bill_doc['date'],
            'time': bill_doc['time'],
            'bill_no': bill_doc['bill_no'],
            'item_code': item[3],
            'item_name': item[4],
            'qty': item[5],
            'rate': item[6],
            'gstin': item[7],
            'gst_amount': item[8],
            'discount': item[9],
            'dis_amount': item[10],
            'gross_amount': item[11],
            'net_amount': item[12],
            'soh': item[13],
            'cost': item[14],
            'catagory': item[15],
            'sub_catagory': item[16],
            'brand': item[17],
            'expiry_date': item[18],
            'store_code': item[19],
            'store_name': item[20],
            'vendor_name': item[21],
            'vendor_gst': item[22]
        }
        sale_details.append(sale_detail)
    
    # Save to MongoDB
    db_ops.save_bill(bill_doc, sale_details)
    
    # Update SOH (Stock on Hand)
    for item in cart_items:
        item_code = item[3]
        qty_sold = item[5]
        
        # Get current item
        current_item = db_ops.search_item(str(item_code))
        if current_item:
            new_soh = current_item.get('soh', 0) - qty_sold
            db_ops.update_item_soh(item_code, new_soh)
            print(f"SOH Updated for item {item_code}: {new_soh}")

def search_catagory_func(searchc: str):
    """Search function for category"""
    return db_ops.search_catagory(searchc)

def search_subcatagory_func(searchs: str):
    """Search function for sub-category"""
    return db_ops.search_subcatagory(searchs)

def search_brand_func(searchb: str):
    """Search function for brand"""
    return db_ops.search_brand(searchb)

def search_vendor_func(searchv: str):
    """Search function for vendor"""
    return db_ops.search_vendor(searchv)

def generate_pdf(bill: dict, return_bytes: bool = False, force_ascii: bool = False):
    """Generate a professional PDF invoice. Returns bytes when `return_bytes=True`."""
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
        os.makedirs('bills', exist_ok=True)
        txt_path = os.path.join('bills', f"{bill_no}.txt")
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

    if force_ascii:
        unicode_font = False

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

    try:
        import qrcode
        from PIL import Image
        QR_AVAILABLE = True
    except Exception:
        QR_AVAILABLE = False

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
        pdf.set_x(30)
        pdf.set_font(base_font, 'B', 12)
        pdf.cell(30, 90, 'Relling Bihibaray | Dist-Darjeeling | Mobile: 9832025468', ln=1)
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
        page_no = pdf.page_no()
        pdf.set_xy(0, pdf.h - bottom_margin + 10)
        pdf.set_font(base_font, 'I', 8)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 10, f'Page {page_no}', align='C')
        pdf.set_text_color(0, 0, 0)

    header()
    pdf.ln(10)
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

    table_header()
    pdf.set_font(base_font, '', 10)
    fill = False
    items = bill.get('items', [])
    
    gst_total = 0.0
    for it in items:
        try:
            gst_total += float(it.get('gst_amount', 0) or 0)
        except Exception:
            pass

    total_qty = 0
    for it in items:
        try:
            total_qty += int(float(it.get('qty', 0) or 0))
        except Exception:
            pass

    for it in items:
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

    t = bill.get('totals', {})
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
    pdf.set_x(right_x)
    pdf.cell(70, 18, 'Discount:', border=0)
    pdf.cell(70, 18, fmt_total(t.get('discount', 0)), border=0, align='R', ln=1)

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
            try:
                pdf.image(qr_tmp_path, x=left_margin, y=pdf.get_y(), w=80)
            except Exception:
                pass
    except Exception:
        qr_tmp_path = None

    pdf.set_x(left_margin + 90)
    pdf.cell(240, 40, 'Received By: ______________________', ln=0)
    pdf.set_x(350)
    pdf.cell(240, 40, 'Authorised Signatory: ______________', ln=1)
    pdf.ln(6)
    pdf.set_x(left_margin)
    pdf.set_font(base_font, '', 9)
    pdf.multi_cell(0, 90, 'Bank Details: ABC Bank, IFSC: ABCD0123456, A/C: 1234567890', align='L')

    try:
        if qr_tmp_path and os.path.exists(qr_tmp_path):
            os.unlink(qr_tmp_path)
    except Exception:
        pass

    footer()

    try:
        s = pdf.output(dest='S')
    except UnicodeEncodeError:
        if not force_ascii:
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
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        col1,col2,col3=st.columns([1,2,1])
        with col2:
            st.image('logo.png')
        st.markdown('<div class="login-subheader">Billing Management System</div>', unsafe_allow_html=True)
        
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
        
        with st.expander("ℹ️ Demo Credentials"):
            st.markdown("""
            **Username:** admin | **Password:** admin123
            **Username:** cashier | **Password:** cashier123
            **Username:** manager | **Password:** manager123
            """)

# Main App (after login)
def main_app():
    st.markdown('<div class="main-header">🛒 Alam Megastore - Billing Software</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.image('logo.png', width=190)
        
        st.markdown("---")
        st.success(f"👤 **User:** {st.session_state.username}")
        st.info(f"🎭 **Role:** {st.session_state.user_role.upper()}")
        
        if st.button("🚪 Logout", width='stretch'):
            logout()
        
        st.markdown("---")
        
        if st.session_state.user_role == "admin":
            page = st.radio("Navigation", 
                            ["🏠 Billing", "📦 Inventory", "➕ Add New Items","📊 Reports", "🔍 Search Bills", "👥 User Management","👥 Vendor Management"],
                            label_visibility="collapsed")
        elif st.session_state.user_role == "manager":
            page = st.radio("Navigation", 
                            ["🏠 Billing", "📦 Inventory","➕ Add New Items","📊 Reports", "🔍 Search Bills","👥 Vendor Management"],
                            label_visibility="collapsed")
        else:
            page = st.radio("Navigation", 
                            ["🏠 Billing", "🔍 Search Bills"],
                            label_visibility="collapsed")
        
        st.markdown("---")
        st.info(f"**Bill No:** {st.session_state.invoice_no}")
        st.info(f"**Date:** {now_in_india().strftime('%d/%m/%Y')}")
        st.info(f"**Time:** {now_in_india().strftime('%H:%M:%S')}")
    
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

def item_reset():
    st.session_state.item_search=""
    st.session_state.selected_item=[]

def billing_page():
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.subheader("👤 Customer Information")
        cust_col1, cust_col2 = st.columns(2)
        with cust_col1:
            customer_mobile = st.text_input("📱 Customer Mobile", value=st.session_state.customer_mobile, max_chars=10)
            if st.button("🔍 Search Customer"):
                result = db_ops.search_customer_by_mobile(customer_mobile)
                if result:
                    st.session_state.customer_name = result.get('cust_name', '')
                    st.session_state.customer_mobile = result.get('cust_mobile', '')
                    st.success(f"Customer found: {result.get('cust_name', '')}")
                else:
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
        selected_item = st_searchbox(
            search_items,
            key="item_searchbox",
            placeholder="Search items...with Names",
            clear_on_submit=False,
        )
    
    with search_col2:
        quantity = st.number_input("Quantity", min_value=1, value=1)
    
    with search_col2:
        if st.button("➕ Add to Cart", width='stretch'):
            if item_search or selected_item:
                search_term = item_search or selected_item
                i = search_item(search_term)
                if i:
                    item_code = i.get('item_code')
                    item_name = i.get('item_name')
                    rate = i.get('rate')
                    gstin = i.get('gstin')
                    discount = i.get('discount')
                    soh = i.get('soh')
                    cost = i.get('cost')
                    
                    # Calculate amounts
                    total_rate = rate * quantity
                    dis_amount = total_rate * discount / 100
                    amount = total_rate - dis_amount
                    gst_amount = amount * gstin / 100
                    gross_amount = amount
                    net_amount = amount - gst_amount
                    costnew = (cost * quantity)
                    
                    # Add to cart
                    cart_item = {
                        'item_code': item_code,
                        'item_name': item_name,
                        'qty': quantity,
                        'rate': rate,
                        'gstin': gstin,
                        'gst_amount': gst_amount,
                        'discount': discount,
                        'dis_amount': dis_amount,
                        'gross_amount': gross_amount,
                        'amount': net_amount,
                        'cost': costnew,
                        'catagory': i.get('catagory'),
                        'sub_catagory': i.get('sub_catagory'),
                        'brand': i.get('brand'),
                        'expiry_date': i.get('expiry_date'),
                        'store_code': i.get('store_code'),
                        'store_name': i.get('store_name'),
                        'vendor_name': i.get('vendor_name'),
                        'vendor_gst': i.get('vendor_gst')
                    }
                    st.session_state.cart_items.append(cart_item)
                    st.success(f"✅ Added {item_name} to cart!") 
                    item_reset()
                    st.rerun()
                else:
                    st.error("❌ Item not found!")
    
    # Display Cart
    st.markdown("---")
    st.subheader("🛒 Shopping Cart")
    
    if st.session_state.cart_items:
        cart_df = pd.DataFrame(st.session_state.cart_items)
        
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
        
        with btn_col3:
            if st.button("💾 Save & Print Bill", type="primary", width='stretch'):
                if not st.session_state.cart_items:
                    st.error("Cart is empty!")
                else:
                    # Generate bill
                    current_date = now_in_india().strftime('%d/%m/%Y')
                    current_time = now_in_india().strftime('%H:%M:%S')
                    bill_no = f"{st.session_state.invoice_no}"
                    
                    # Insert invoice
                    invoice_data = {'bill_no': bill_no}
                    db_ops.insert_invoice(invoice_data)
                    
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

                    file_bytes = generate_pdf(bill_struct, return_bytes=True)

                    @st.dialog('Bill Test')
                    def billprint():
                        st.code(bill_text, language=None)
                        try:
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
                    st.session_state.invoice_no = db_ops.get_max_invoice_no()
                    st.session_state.cart_items = []
                    st.session_state.customer_name = ""
                    st.session_state.customer_mobile = ""
                    st.session_state.item_search = ""
                    st.session_state.payment_mode = "CASH"
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
                    @st.dialog("Item Details")
                    def itemd():
                        col1,col2=st.columns(2)
                        with col1:
                            itemc=st.text_input("Item Code",value=i.get('item_code'))
                            itemn=st.text_input("Item name",value=i.get('item_name'))
                            mrp=st.text_input("MRP",value=str(i.get('rate')))
                            gstv=st.text_input("Gstin%",value=str(i.get('gstin')))
                            dis=st.text_input("Discount%",value=str(i.get('discount')))
                            sohinhand=st.number_input("SOH",value=i.get('soh',0))
                            costp=st.number_input("COST",value=i.get('cost',0))
                        with col2:
                            cat=st.text_input("catagory",value=i.get('catagory',''))
                            subc=st.text_input("Sub Catagory",value=i.get('sub_catagory',''))
                            brd=st.text_input("Brand",value=i.get('brand',''))
                            exd=st.text_input("Expiry Date",value=i.get('expiry_date',''))
                            vdn=st.text_input("Vendor Name",value=i.get('vendor_name',''))
                            vdg=st.text_input("Vendor GST",value=i.get('vendor_gst',''))

                        sohin=st.number_input("SOH INPUT",value=0)
                        if st.button("Click to Update Item Details"):
                            new_soh = sohin + sohinhand
                            update_data = {
                                'item_name': itemn,
                                'rate': float(mrp),
                                'gstin': float(gstv),
                                'discount': float(dis),
                                'soh': new_soh,
                                'cost': int(costp),
                                'catagory': cat,
                                'sub_catagory': subc,
                                'brand': brd,
                                'expiry_date': exd,
                                'vendor_name': vdn,
                                'vendor_gst': vdg
                            }
                            db_ops.update_item(i['item_code'], update_data)
                            st.success("Item updated successfully!")
                            st.rerun()

                    itemd()
                else:
                    @st.dialog("Information")
                    def itemaddtab():
                        st.error("Item Not Found")
                        st.info("   Need to Add from \n \n➕ Add New Item Tab from SidebarMenu")
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
        catag = st_searchbox(search_catagory_func, clear_on_submit=False, label="Search Catagory", key="searchc")
    with col2:
        scatag = st_searchbox(search_subcatagory_func, clear_on_submit=False, label="Search Sub-Catagory", key="searchs")
        brand = st_searchbox(search_brand_func, clear_on_submit=False, label="Search Brand Name", key="searchb")
        expiry = st.date_input("Select Expiry Date")
        storecode = st.number_input("Store Code", min_value=0, value=7001)
        storename = st.selectbox("Store Name", ("Alam Megastore Relling","Alam Megastore Siliguri"))
        vendorname = st_searchbox(search_vendor_func, clear_on_submit=False, label="Search Vendor", key="searchv")
        vendorgst=st.text_input("Vendor GSTNO", value=st.session_state.get('vendorgst',''))                                
                                    
    if st.button("Add Item"):
        try:
            item_data = {
                'item_code': int(new_code),
                'item_name': new_name,
                'qty': 1,
                'rate': new_rate,
                'gstin': new_gstin,
                'discount': new_discount,
                'soh': new_soh,
                'cost': int(cost),
                'catagory': catag,
                'sub_catagory': scatag,
                'brand': brand,
                'expiry_date': str(expiry),
                'store_code': storecode,
                'store_name': storename,
                'vendor_name': vendorname,
                'vendor_gst': vendorgst
            }
            db_ops.insert_item(item_data)
            st.success("✅ Item added successfully!")
        except Exception as e:
            st.error(f"❌ Error: {e}")

    st.subheader("Category, Sub-Category and Brand Update Below ") 
    cat_col1, cat_col2, cat_col3 = st.columns(3)
    
    with cat_col1:
        new_catagory = st.text_input("New Catagory")
        if st.button("Add Catagory"):
            try:
                db_ops.insert_catagory(new_catagory)
                st.success("✅ Catagory added successfully!")
            except Exception as e:
                st.error(f"❌ {e}")
    
    with cat_col2:
        new_subcatagory = st.text_input("New Sub-Catagory")
        if st.button("Add Sub-Catagory"):
            try:
                db_ops.insert_subcatagory(new_subcatagory)
                st.success("✅ Sub-Catagory added successfully!")
            except Exception as e:
                st.error(f"❌ {e}")
    
    with cat_col3:
        new_brand = st.text_input("New Brand")
        if st.button("Add Brand"):
            try:
                db_ops.insert_brand(new_brand)
                st.success("✅ Brand added successfully!")
            except Exception as e:
                st.error(f"❌ {e}")

def vendor_add_page():
    st.subheader("Vendor Add Dashboard")
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
        vendor_data = {
            'vendor_id': vendor_id,
            'vendor_name': vendor_name,
            'vendor_mobile': vendor_mobile,
            'vendor_gst': vendor_gst,
            'vendor_address': vendor_address,
            'bank_name': bank_name,
            'bank_ac_no': account_no,
            'bank_ifsc': ifsc_code,
            'bank_branch': branch
        }
        try:
            db_ops.insert_vendor(vendor_data)
            st.success("✅ Vendor Added Successfully!")
        except Exception as e:
            st.error(f"❌ Error: {e}")

def reports_page():
    st.subheader("📊 Sales Reports")
    
    current_date = now_in_india().strftime('%d/%m/%Y')
    sales_data = db_ops.get_all_bills()
    sale_details = db_ops.get_all_sale_details()
    daysale = db_ops.get_day_sales(current_date)
    
    if sales_data:
        sales_df = pd.DataFrame(sales_data)
        sale_details_df = pd.DataFrame(sale_details)
        daysale_df = pd.DataFrame(daysale)
        
        co1,co2=st.columns(2)
        total_Revenue=sales_df['amount'].sum()
        total_day=sales_df[sales_df['date']== current_date]['amount'].sum()
        with co1:
            st.markdown(f'<div class="total-rev">Total Revenue = ₹{total_Revenue:.2f}</div>', unsafe_allow_html=True)
        with co2:
            st.markdown(f'<div class="total-rev">Today Sale = ₹{total_day:.2f}</div>', unsafe_allow_html=True)    
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns(5)
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
                    'payment_mode': 'Payment',
                    'cashier': 'Cashier'
                }
            )
        elif st.button("Show Todays Sale"):
            st.dataframe(daysale_df, width='stretch', hide_index=True)
        elif st.button("Show Sale Details All"):
            st.dataframe(sale_details_df, width='stretch', hide_index=True)
    else:
        st.info("No sales data available")

def search_bills_page():
    st.subheader("🔍 Search Bills")
    
    search_bill = st.text_input("Enter Bill Number", placeholder="e.g., 101123456")
    
    if st.button("Search"):
        if search_bill:
            bill = db_ops.search_bill(search_bill)
            
            if bill:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.info(f"**Bill No:** {bill.get('bill_no')}")
                    st.info(f"**Customer:** {bill.get('cust_name')}")
                with col2:
                    st.info(f"**Date:** {bill.get('date')}")
                    st.info(f"**Time:** {bill.get('time')}")
                with col3:
                    st.info(f"**Amount:** ₹{bill.get('amount', 0):.2f}")
                    st.info(f"**Payment:** {bill.get('payment_mode')}")
                
                items = db_ops.get_bill_items(search_bill)
                if items:
                    items_df = pd.DataFrame(items)
                    st.markdown("### Items")
                    st.dataframe(
                        items_df[['item_code', 'item_name', 'qty', 'rate', 'discount', 'gross_amount']],
                        width='stretch',
                        hide_index=True
                    )
            else:
                st.warning("Bill not found!")

def user_management_page():
    st.subheader("👥 User Management")
    
    users = db_ops.get_all_users()
    if users:
        users_df = pd.DataFrame(users)
        st.dataframe(
            users_df[['username', 'role']] if 'username' in users_df.columns else users_df,
            width='stretch',
            hide_index=True
        )
    
    with st.expander("➕ Add New User"):
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username")
                new_password = st.text_input("Password", type="password")
            with col2:
                new_role = st.selectbox("Role", ["cashier", "manager", "admin"])
            
            if st.form_submit_button("Add User"):
                if new_username and new_password:
                    hashed_password = hashlib.sha256(new_password.strip().encode()).hexdigest()
                    try:
                        db_ops.insert_user(new_username, hashed_password, new_role)
                        st.success("✅ User Added Successfully")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    with st.expander("➕ UPDATE AND DELETE USER"):
        with st.form("update_delete_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                upd_username = st.text_input("Username")
                upd_password = st.text_input("Password", type="password")
            with col2:
                upd_role = st.selectbox("Role", ["cashier", "manager", "admin"])                      
            
            col_upd, col_del = st.columns(2)
            with col_upd:
                if st.form_submit_button("Update User"):
                    if upd_username and upd_password:
                        hashed_password = hashlib.sha256(upd_password.strip().encode()).hexdigest()
                        try:
                            db_ops.update_user(upd_username, hashed_password, upd_role)
                            st.success("✅ User Updated Successfully")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
            
            with col_del:
                if st.form_submit_button("❌ Delete User"):
                    if upd_username:
                        try:
                            db_ops.delete_user(upd_username)
                            st.success("✅ User Deleted Successfully")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")

# Main execution
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
