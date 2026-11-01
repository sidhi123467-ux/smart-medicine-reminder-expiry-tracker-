import streamlit as st
import sqlite3, hashlib, re, csv, io
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / 'medicine_reminder.db'

st.set_page_config(page_title='Smart Medicine Reminder', page_icon='💊', layout='wide')


# BLUE THEME CUSTOMIZATION
st.markdown("""
<style>
:root { --navy:#123B70; --blue:#1976D2; --pale:#EAF3FF; --ink:#172B4D; }
.stApp { background:#F3F7FD; color:var(--ink); }
[data-testid="stHeader"] { background:rgba(243,247,253,.96); }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#123B70 0%,#174B86 100%); }
[data-testid="stSidebar"] * { color:#fff !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { padding:8px 10px; border-radius:9px; margin:3px 0; background:rgba(255,255,255,.07); }
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover { background:rgba(255,255,255,.18); }
[data-testid="stSidebar"] button { background:#fff !important; color:#123B70 !important; border:0 !important; }
h1,h2,h3 { color:#123B70 !important; font-weight:750 !important; }
p, label, [data-testid="stMarkdownContainer"] { color:inherit; }
[data-testid="stMetric"] { background:#fff; border:1px solid #C9DDF7; border-left:5px solid #1976D2; border-radius:13px; padding:16px 18px; box-shadow:0 3px 12px rgba(18,59,112,.06); }
[data-testid="stMetricLabel"] { color:#45617F !important; font-weight:600; }
[data-testid="stMetricValue"] { color:#123B70 !important; }
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button { background:#1976D2 !important; color:#fff !important; border:1px solid #1976D2 !important; border-radius:9px !important; font-weight:650 !important; min-height:42px; }
.stButton>button:hover,.stFormSubmitButton>button:hover,.stDownloadButton>button:hover { background:#125EAC !important; border-color:#125EAC !important; color:#fff !important; }
.stButton>button:focus,.stFormSubmitButton>button:focus { box-shadow:0 0 0 3px rgba(25,118,210,.22) !important; }
input,textarea,[data-baseweb="select"]>div { border-radius:8px !important; }
[data-testid="stDataFrame"],[data-testid="stTable"] { border:1px solid #C9DDF7; border-radius:10px; overflow:hidden; }
div[data-testid="stExpander"] { background:#fff; border:1px solid #C9DDF7; border-radius:10px; }
[data-testid="stAlert"] { border-radius:10px; }
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { color:#125EAC !important; border-bottom-color:#1976D2 !important; }
[data-testid="stForm"] { background:#fff; border:1px solid #D5E7FF; border-radius:12px; padding:18px; }
/* Centered, clean login/register panel */
[data-testid="stVerticalBlock"]:has(> [data-testid="stTabs"]) { gap:1rem; }
[data-testid="stTabs"] { background:#fff; border:1px solid #D5E7FF; border-radius:14px; padding:14px 18px; box-shadow:0 8px 28px rgba(18,59,112,.07); }
@media(max-width:700px) { .block-container{padding-top:1.1rem;padding-left:1rem;padding-right:1rem;} [data-testid="stMetric"]{padding:11px;} }
</style>
""", unsafe_allow_html=True)

# ---------- Database ----------
def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, created TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS medicines(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            name TEXT NOT NULL, dosage TEXT, frequency TEXT, time TEXT,
            quantity INTEGER DEFAULT 0, expiry TEXT, notes TEXT,
            category TEXT DEFAULT 'General', instructions TEXT DEFAULT '',
            doctor TEXT DEFAULT '', batch_no TEXT DEFAULT '',
            low_stock INTEGER DEFAULT 5, active INTEGER DEFAULT 1)''')
        c.execute('''CREATE TABLE IF NOT EXISTS history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            medicine_id INTEGER, medicine TEXT, status TEXT, marked TEXT)''')

def pw_hash(p):
    return hashlib.sha256(p.encode('utf-8')).hexdigest()

def email_ok(x):
    return re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', x or '') is not None

init_db()
if 'user' not in st.session_state: st.session_state.user = None
if 'page' not in st.session_state: st.session_state.page = 'Dashboard'
uid = st.session_state.user['id'] if st.session_state.user else None

# ---------- Login / Registration ----------
if not st.session_state.user:
    st.markdown("<div style='text-align:center;font-size:48px'>💊</div><h1 style='text-align:center;color:#173b73'>Smart Medicine Reminder</h1><p style='text-align:center;color:#667085'>Medicine schedules • Expiry tracking • Stock alerts</p>", unsafe_allow_html=True)
    left, center, right = st.columns([1,1.2,1])
    with center:
        tab1, tab2 = st.tabs(['Login', 'Create account'])
        with tab1:
            em = st.text_input('Email address', key='login_email')
            pw = st.text_input('Password', type='password', key='login_pw')
            if st.button('Login', use_container_width=True, type='primary'):
                with db() as c:
                    u = c.execute('SELECT * FROM users WHERE email=? AND password=?', (em.strip().lower(), pw_hash(pw))).fetchone()
                if u:
                    st.session_state.user = dict(u); st.rerun()
                else: st.error('Incorrect email or password.')
        with tab2:
            nm = st.text_input('Full name', key='reg_name')
            reml = st.text_input('Email address', key='reg_email')
            rp = st.text_input('Password (minimum 6 characters)', type='password', key='reg_pw')
            rc = st.text_input('Confirm password', type='password', key='reg_confirm')
            if st.button('Create account', use_container_width=True, type='primary'):
                if not nm.strip() or not email_ok(reml.strip()): st.error('Enter your name and a valid email address.')
                elif len(rp) < 6: st.error('Password must contain at least 6 characters.')
                elif rp != rc: st.error('Passwords do not match.')
                else:
                    try:
                        with db() as c:
                            c.execute('INSERT INTO users(name,email,password,created) VALUES(?,?,?,?)', (nm.strip(), reml.strip().lower(), pw_hash(rp), datetime.now().isoformat()))
                        st.success('Account created. Please log in.')
                    except sqlite3.IntegrityError: st.error('This email is already registered.')
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown('## 💊 Smart Medicine')
    st.caption('Welcome, ' + st.session_state.user['name'])
    pages = ['Dashboard','My Medicines','Add Medicine','Reminders','Expiry & Stock','Dose History','Analytics','About']
    st.session_state.page = st.radio('Navigation', pages, index=pages.index(st.session_state.page) if st.session_state.page in pages else 0)
    st.divider()
    if st.button('Logout', use_container_width=True):
        st.session_state.user = None; st.session_state.page = 'Dashboard'; st.rerun()

page = st.session_state.page

def medicines(active_only=True):
    with db() as c:
        sql = 'SELECT * FROM medicines WHERE user_id=?'
        if active_only: sql += ' AND active=1'
        return c.execute(sql + ' ORDER BY name COLLATE NOCASE', (uid,)).fetchall()

def counts():
    ms = medicines()
    today = date.today().isoformat(); now = datetime.now().strftime('%H:%M')
    expired = sum(1 for m in ms if m['expiry'] and m['expiry'] < today)
    low = sum(1 for m in ms if (m['quantity'] or 0) <= (m['low_stock'] if m['low_stock'] is not None else 5))
    due = sum(1 for m in ms if now in [z.strip() for z in (m['time'] or '').split(',')])
    with db() as c:
        h = c.execute('SELECT status FROM history WHERE user_id=?', (uid,)).fetchall()
    taken = sum(1 for x in h if x['status']=='TAKEN')
    missed = sum(1 for x in h if x['status']=='MISSED')
    return len(ms), expired, low, due, taken, missed

def save_medicine(values, mid=None):
    with db() as c:
        if mid:
            c.execute('''UPDATE medicines SET name=?,dosage=?,frequency=?,time=?,quantity=?,expiry=?,notes=?,category=?,instructions=?,doctor=?,batch_no=?,low_stock=? WHERE id=? AND user_id=?''', (*values, mid, uid))
        else:
            c.execute('''INSERT INTO medicines(user_id,name,dosage,frequency,time,quantity,expiry,notes,category,instructions,doctor,batch_no,low_stock) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''', (uid, *values))

def medicine_form(existing=None):
    m = existing
    with st.form('medicine_form', clear_on_submit=not bool(m)):
        a,b = st.columns(2)
        name = a.text_input('Medicine name *', value=m['name'] if m else '')
        dosage = b.text_input('Dosage (e.g. 1 tablet)', value=m['dosage'] if m else '')
        frequency = a.selectbox('Frequency', ['Once a day','Twice a day','Three times a day','As needed','Weekly','Other'], index=(['Once a day','Twice a day','Three times a day','As needed','Weekly','Other'].index(m['frequency']) if m and m['frequency'] in ['Once a day','Twice a day','Three times a day','As needed','Weekly','Other'] else 0))
        times = b.text_input('Reminder times (HH:MM, comma separated)', value=m['time'] if m else '', placeholder='08:00, 14:00, 20:00')
        c1,c2 = st.columns(2)
        qty = c1.number_input('Current quantity', min_value=0, step=1, value=int(m['quantity'] or 0) if m else 0)
        low = c2.number_input('Low-stock alert level', min_value=0, step=1, value=int(m['low_stock'] or 5) if m else 5)
        default_expiry = date.fromisoformat(m['expiry']) if m and m['expiry'] else None
        exp = st.date_input('Expiry date (optional)', value=default_expiry)
        cat = st.text_input('Category', value=m['category'] if m and m['category'] else 'General')
        doctor = st.text_input('Doctor name', value=m['doctor'] if m else '')
        batch = st.text_input('Batch number', value=m['batch_no'] if m else '')
        instructions = st.text_input('Instructions', value=m['instructions'] if m else '', placeholder='After food / Before food')
        notes = st.text_area('Notes', value=m['notes'] if m else '')
        submitted = st.form_submit_button('Update medicine' if m else 'Save medicine', type='primary', use_container_width=True)
    if submitted:
        if not name.strip(): st.error('Medicine name is required.')
        else:
            valid = True
            for t in [x.strip() for x in times.split(',') if x.strip()]:
                try: datetime.strptime(t,'%H:%M')
                except ValueError: valid=False
            if not valid: st.error('Enter reminder times in HH:MM format, such as 08:00, 20:00.')
            else:
                values=(name.strip(),dosage.strip(),frequency,times.strip(),int(qty),exp.isoformat() if exp else '',notes.strip(),cat.strip(),instructions.strip(),doctor.strip(),batch.strip(),int(low))
                save_medicine(values, m['id'] if m else None)
                st.success('Medicine saved successfully.'); st.session_state.page='My Medicines'; st.rerun()

# ---------- Pages ----------
if page == 'Dashboard':
    st.title('🏠 Dashboard'); st.caption('Overview of your medicines, reminders, expiry and stock.')
    vals = counts(); labels=['Medicines','Expired','Low Stock','Due Now','Doses Taken']
    cols=st.columns(5)
    for col,label,val in zip(cols,labels,vals[:5]): col.metric(label,val)
    st.subheader('Quick actions')
    q1,q2,q3=st.columns(3)
    if q1.button('➕ Add medicine',use_container_width=True): st.session_state.page='Add Medicine'; st.rerun()
    if q2.button('⏰ View reminders',use_container_width=True): st.session_state.page='Reminders'; st.rerun()
    if q3.button('⚠ Expiry & stock',use_container_width=True): st.session_state.page='Expiry & Stock'; st.rerun()
    st.info('Tip: Enter multiple reminder times separated by commas, for example 08:00, 14:00, 20:00.')
    ms=medicines()
    if ms:
        st.subheader('Your active medicines')
        st.dataframe([{'Medicine':m['name'],'Dosage':m['dosage'],'Time':m['time'],'Quantity':m['quantity'],'Expiry':m['expiry']} for m in ms],use_container_width=True,hide_index=True)
elif page == 'Add Medicine':
    st.title('➕ Add Medicine'); medicine_form()
elif page == 'My Medicines':
    st.title('💊 My Medicines'); st.caption('Search, edit, refill or remove medicine records.')
    term=st.text_input('Search medicines by name or category')
    ms=[m for m in medicines() if term.lower() in (m['name']+' '+(m['category'] or '')).lower()]
    if ms:
        st.dataframe([{'ID':m['id'],'Medicine':m['name'],'Dosage':m['dosage'],'Frequency':m['frequency'],'Reminder(s)':m['time'],'Qty':m['quantity'],'Expiry':m['expiry'],'Category':m['category']} for m in ms],use_container_width=True,hide_index=True)
        options={f"{m['name']} (ID {m['id']})":m for m in ms}
        selected=st.selectbox('Select a medicine to manage',list(options))
        chosen=options[selected]
        with st.expander('Edit selected medicine'):
            medicine_form(chosen)
        x,y=st.columns(2)
        refill=x.number_input('Add stock quantity',min_value=1,step=1,key='refill_qty')
        if x.button('↻ Refill selected medicine'):
            with db() as c: c.execute('UPDATE medicines SET quantity=quantity+? WHERE id=? AND user_id=?',(int(refill),chosen['id'],uid))
            st.success('Stock updated.'); st.rerun()
        if y.button('🗑 Delete selected medicine'):
            with db() as c: c.execute('UPDATE medicines SET active=0 WHERE id=? AND user_id=?',(chosen['id'],uid))
            st.success('Medicine removed.'); st.rerun()
    else: st.info('No medicines found. Add a medicine to get started.')
elif page == 'Reminders':
    st.title('⏰ Reminders'); st.caption('Check today’s schedule and record each dose.')
    now=datetime.now().strftime('%H:%M'); st.write('Current time:',now)
    ms=medicines(); today=date.today().isoformat()
    rows=[]
    for m in ms:
        for tm in [z.strip() for z in (m['time'] or '').split(',') if z.strip()]: rows.append((tm,m))
    rows.sort(key=lambda z:z[0])
    if not rows: st.info('No reminder times added yet.')
    for tm,m in rows:
        with st.container(border=True):
            c1,c2,c3=st.columns([2,1,2]); c1.markdown('**'+m['name']+'**'); c1.caption(m['dosage'] or '')
            c2.write('🕒 '+tm)
            c3.write('')
            a,b=c3.columns(2)
            if a.button('Taken',key=f"taken_{m['id']}_{tm}"):
                with db() as c: c.execute('INSERT INTO history(user_id,medicine_id,medicine,status,marked) VALUES(?,?,?,?,?)',(uid,m['id'],m['name'],'TAKEN',datetime.now().isoformat()))
                st.success('Dose marked as taken.'); st.rerun()
            if b.button('Missed',key=f"missed_{m['id']}_{tm}"):
                with db() as c: c.execute('INSERT INTO history(user_id,medicine_id,medicine,status,marked) VALUES(?,?,?,?,?)',(uid,m['id'],m['name'],'MISSED',datetime.now().isoformat()))
                st.warning('Dose marked as missed.'); st.rerun()
    st.warning('Browser reminders are shown when you open this page. This demo does not send background notifications when the browser is closed.')
elif page == 'Expiry & Stock':
    st.title('⚠ Expiry & Stock Alerts'); today=date.today().isoformat(); ms=medicines()
    expired=[m for m in ms if m['expiry'] and m['expiry']<today]
    soon=[m for m in ms if m['expiry'] and today<=m['expiry']<=(date.today()).isoformat()]
    low=[m for m in ms if (m['quantity'] or 0)<=(m['low_stock'] or 5)]
    a,b,c=st.columns(3); a.metric('Expired',len(expired)); b.metric('Low stock',len(low)); c.metric('Active medicines',len(ms))
    if expired:
        st.subheader('Expired medicines')
        st.dataframe([{'Medicine':m['name'],'Expiry':m['expiry'],'Quantity':m['quantity']} for m in expired],use_container_width=True,hide_index=True)
    if low:
        st.subheader('Low stock medicines')
        st.dataframe([{'Medicine':m['name'],'Available quantity':m['quantity'],'Refill alert at':m['low_stock']} for m in low],use_container_width=True,hide_index=True)
    if not expired and not low: st.success('No expired or low-stock medicines found.')
elif page == 'Dose History':
    st.title('📜 Dose History')
    with db() as c: hs=c.execute('SELECT medicine,status,marked FROM history WHERE user_id=? ORDER BY marked DESC',(uid,)).fetchall()
    if hs:
        st.dataframe([{'Medicine':h['medicine'],'Status':h['status'],'Date & time':h['marked'].replace('T',' ')} for h in hs],use_container_width=True,hide_index=True)
        buf=io.StringIO(); w=csv.writer(buf); w.writerow(['Medicine','Status','Date & time'])
        for h in hs: w.writerow([h['medicine'],h['status'],h['marked']])
        st.download_button('⬇ Download history as CSV',buf.getvalue(),'dose_history.csv','text/csv')
        if st.button('Clear dose history'):
            with db() as c: c.execute('DELETE FROM history WHERE user_id=?',(uid,))
            st.success('History cleared.'); st.rerun()
    else: st.info('No dose history recorded yet.')
elif page == 'Analytics':
    st.title('📊 Analytics'); vals=counts(); a,b=st.columns(2); a.metric('Doses marked taken',vals[4]); b.metric('Doses marked missed',vals[5])
    if vals[4]+vals[5]:
        st.progress(vals[4]/(vals[4]+vals[5]),text=f"Recorded dose completion: {round(vals[4]/(vals[4]+vals[5])*100)}%")
    else: st.info('Mark doses as Taken or Missed to see adherence analytics.')
elif page == 'About':
    st.title('ℹ About this project')
    st.markdown('''**Smart Medicine Reminder & Expiry Tracker** helps users organize medicine schedules, record doses, monitor expiry dates and track available stock.\n\n**Main features**\n- User registration and login\n- Add, search, edit and remove medicine records\n- Multiple daily reminder times\n- Taken / missed dose history\n- Expiry and low-stock alerts\n- Basic adherence analytics\n\n**Important:** This is an educational project and is not a substitute for medical advice. Always follow instructions from a qualified healthcare professional.''')
