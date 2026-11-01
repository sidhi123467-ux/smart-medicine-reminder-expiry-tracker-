import os
import csv
import shutil
import sqlite3
import hashlib
import re
from datetime import datetime, date
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
DB = os.path.join(DATA_DIR, "medicine_reminder.db")
os.makedirs(DATA_DIR, exist_ok=True)


def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def hp(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    c = con(); q = c.cursor()
    q.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT UNIQUE, password TEXT, created TEXT)""")
    q.execute("""CREATE TABLE IF NOT EXISTS medicines(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, name TEXT, dosage TEXT, frequency TEXT, time TEXT,
        quantity INTEGER DEFAULT 0, expiry TEXT, notes TEXT)""")
    q.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, medicine_id INTEGER, medicine TEXT,
        status TEXT, marked TEXT)""")
    # Safe upgrades for databases created by the earlier version.
    existing = {r[1] for r in q.execute("PRAGMA table_info(medicines)").fetchall()}
    upgrades = {
        "category": "TEXT DEFAULT 'General'",
        "instructions": "TEXT DEFAULT ''",
        "doctor": "TEXT DEFAULT ''",
        "batch_no": "TEXT DEFAULT ''",
        "low_stock": "INTEGER DEFAULT 5",
        "active": "INTEGER DEFAULT 1",
    }
    for col, definition in upgrades.items():
        if col not in existing:
            q.execute(f"ALTER TABLE medicines ADD COLUMN {col} {definition}")
    c.commit(); c.close()


def email_ok(x):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x) is not None


def valid_date(x):
    if not x:
        return True
    try:
        datetime.strptime(x, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def valid_times(value):
    if not value.strip():
        return True
    for item in value.split(","):
        item = item.strip()
        try:
            datetime.strptime(item, "%H:%M")
        except ValueError:
            return False
    return True


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Smart Medicine Reminder & Expiry Tracker")
        self.geometry("1180x760")
        self.minsize(980, 640)
        self.user = None
        self.content = None
        self.reminders_enabled = True
        self.last_popup_keys = set()
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass
        self.style.configure("TButton", font=("Segoe UI", 10), padding=8)
        self.style.configure("Treeview", rowheight=30, font=("Segoe UI", 10))
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        self.configure(bg="#f4f7fb")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.login()

    def clear(self):
        for w in self.winfo_children():
            w.destroy()

    def login(self):
        self.clear()
        card = tk.Frame(self, bg="white", bd=1, relief="solid")
        card.place(relx=.5, rely=.5, anchor="center", width=450, height=490)
        tk.Label(card, text="💊", font=("Segoe UI Emoji", 42), bg="white").pack(pady=(22, 0))
        tk.Label(card, text="Smart Medicine Reminder", font=("Segoe UI", 21, "bold"), fg="#173b73", bg="white").pack()
        tk.Label(card, text="Login to your account", fg="#667085", bg="white").pack(pady=(3, 22))
        f = tk.Frame(card, bg="white"); f.pack(fill="x", padx=45)
        tk.Label(f, text="Email", bg="white").pack(anchor="w")
        self.e = ttk.Entry(f); self.e.pack(fill="x", pady=(3, 14), ipady=5)
        tk.Label(f, text="Password", bg="white").pack(anchor="w")
        self.p = ttk.Entry(f, show="*"); self.p.pack(fill="x", pady=(3, 18), ipady=5)
        ttk.Button(f, text="Login", command=self.do_login).pack(fill="x")
        tk.Button(f, text="Create Account", command=self.register, bd=0, bg="white", fg="#2563eb", font=("Segoe UI", 10, "underline")).pack(pady=14)
        tk.Label(card, text="Desktop application • No server required", bg="white", fg="#98a2b3").pack(side="bottom", pady=15)
        self.e.focus()
        self.p.bind("<Return>", lambda e: self.do_login())

    def register(self):
        self.clear()
        card = tk.Frame(self, bg="white", bd=1, relief="solid")
        card.place(relx=.5, rely=.5, anchor="center", width=470, height=560)
        tk.Label(card, text="Create Account", font=("Segoe UI", 23, "bold"), fg="#173b73", bg="white").pack(pady=(25, 5))
        tk.Label(card, text="Register using your email ID", fg="#667085", bg="white").pack(pady=(0, 20))
        f = tk.Frame(card, bg="white"); f.pack(fill="x", padx=45)
        es = []
        for lab, show in [("Full Name", False), ("Email ID", False), ("Password", True), ("Confirm Password", True)]:
            tk.Label(f, text=lab, bg="white").pack(anchor="w")
            x = ttk.Entry(f, show="*" if show else "")
            x.pack(fill="x", pady=(3, 12), ipady=5); es.append(x)
        self.rn, self.re, self.rp, self.rc = es
        ttk.Button(f, text="Create Account", command=self.do_register).pack(fill="x", pady=5)
        tk.Button(f, text="Back to Login", command=self.login, bd=0, bg="white", fg="#2563eb", font=("Segoe UI", 10, "underline")).pack(pady=12)

    def do_register(self):
        n, e, p, c = self.rn.get().strip(), self.re.get().strip().lower(), self.rp.get(), self.rc.get()
        if not n or not e or not p:
            return messagebox.showwarning("Missing details", "Please fill all fields.")
        if not email_ok(e):
            return messagebox.showwarning("Email", "Enter a valid email ID.")
        if len(p) < 6:
            return messagebox.showwarning("Password", "Use at least 6 characters.")
        if p != c:
            return messagebox.showwarning("Password", "Passwords do not match.")
        x = con()
        try:
            x.execute("INSERT INTO users(name,email,password,created) VALUES(?,?,?,?)", (n, e, hp(p), datetime.now().isoformat()))
            x.commit(); messagebox.showinfo("Success", "Account created. Please login."); self.login()
        except sqlite3.IntegrityError:
            messagebox.showerror("Already registered", "This email is already registered.")
        finally:
            x.close()

    def do_login(self):
        e, p = self.e.get().strip().lower(), self.p.get()
        x = con(); r = x.execute("SELECT * FROM users WHERE email=? AND password=?", (e, hp(p))).fetchone(); x.close()
        if not r:
            return messagebox.showerror("Login failed", "Incorrect email or password.")
        self.user = dict(r); self.main()

    def main(self):
        self.clear()
        h = tk.Frame(self, bg="#173b73", height=70); h.pack(fill="x")
        tk.Label(h, text="💊 Smart Medicine Reminder", font=("Segoe UI", 18, "bold"), fg="white", bg="#173b73").pack(side="left", padx=22, pady=18)
        tk.Button(h, text="Logout", command=self.login, bg="#173b73", fg="white", bd=0).pack(side="right", padx=15)
        tk.Label(h, text="Welcome, " + self.user["name"], fg="#dbeafe", bg="#173b73").pack(side="right", padx=8)
        body = tk.Frame(self, bg="#f4f7fb"); body.pack(fill="both", expand=True)
        nav = tk.Frame(body, bg="#eaf0fb", width=205); nav.pack(side="left", fill="y")
        self.content = tk.Frame(body, bg="#f4f7fb"); self.content.pack(side="left", fill="both", expand=True, padx=24, pady=20)
        items = [
            ("🏠 Dashboard", self.dashboard), ("💊 Medicines", self.medicines),
            ("⏰ Reminders", self.reminders), ("⚠ Expiry & Stock", self.expiry),
            ("📜 History", self.history_page), ("📊 Analytics", self.analytics),
            ("⚙ Settings", self.settings), ("ℹ About", self.about)
        ]
        for t, c in items:
            tk.Button(nav, text=t, command=c, anchor="w", bg="#eaf0fb", fg="#243b64", bd=0, font=("Segoe UI", 11), padx=18, pady=12).pack(fill="x")
        self.dashboard()
        self.after(15000, self.check_due_reminders)

    def section_title(self, t, s=""):
        for w in self.content.winfo_children():
            w.destroy()
        tk.Label(self.content, text=t, font=("Segoe UI", 24, "bold"), fg="#172b4d", bg="#f4f7fb").pack(anchor="w")
        if s:
            tk.Label(self.content, text=s, fg="#667085", bg="#f4f7fb").pack(anchor="w", pady=(3, 16))

    def counts(self):
        x = con(); ms = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1", (self.user["id"],)).fetchall(); hs = x.execute("SELECT status FROM history WHERE user_id=?", (self.user["id"],)).fetchall(); x.close()
        today = date.today().isoformat(); now = datetime.now().strftime("%H:%M")
        expired = sum(1 for m in ms if m["expiry"] and m["expiry"] < today)
        low = sum(1 for m in ms if (m["quantity"] or 0) <= (m["low_stock"] if m["low_stock"] is not None else 5))
        due = sum(1 for m in ms if now in [z.strip() for z in (m["time"] or "").split(",")])
        taken = sum(1 for h in hs if h["status"] == "TAKEN")
        missed = sum(1 for h in hs if h["status"] == "MISSED")
        return len(ms), expired, low, due, taken, missed

    def smallcard(self, p, l, v):
        f = tk.Frame(p, bg="white", bd=1, relief="solid"); f.pack(side="left", fill="both", expand=True, padx=4)
        tk.Label(f, text=l, fg="#667085", bg="white").pack(anchor="w", padx=14, pady=(13, 3))
        tk.Label(f, text=str(v), font=("Segoe UI", 20, "bold"), fg="#173b73", bg="white").pack(anchor="w", padx=14, pady=(0, 13))

    def dashboard(self):
        self.section_title("Dashboard", "Overview of medicines, reminders, stock and adherence.")
        a, b, c, d, e, f = self.counts()
        r = tk.Frame(self.content, bg="#f4f7fb"); r.pack(fill="x", pady=5)
        for l, v in [("Medicines", a), ("Expired", b), ("Low Stock", c), ("Due Now", d), ("Taken", e)]: self.smallcard(r, l, v)
        quick = tk.Frame(self.content, bg="white", bd=1, relief="solid"); quick.pack(fill="both", expand=True, pady=18)
        tk.Label(quick, text="Quick Actions", font=("Segoe UI", 15, "bold"), bg="white").pack(anchor="w", padx=20, pady=15)
        for t, c0 in [("➕ Add Medicine", self.add), ("⏰ View Today's Reminders", self.reminders), ("⚠ Check Expiry & Stock", self.expiry), ("📜 View Dose History", self.history_page), ("📊 View Analytics", self.analytics)]:
            ttk.Button(quick, text=t, command=c0).pack(anchor="w", padx=20, pady=4)
        tk.Label(quick, text="Tip: Add multiple reminder times like 08:00, 14:00, 20:00.", bg="white", fg="#667085").pack(anchor="w", padx=20, pady=15)

    def medicines(self):
        self.section_title("My Medicines", "Search, add, edit, refill or delete medicine records.")
        bar = tk.Frame(self.content, bg="#f4f7fb"); bar.pack(fill="x", pady=(0, 10))
        self.search_var = tk.StringVar(); search = ttk.Entry(bar, textvariable=self.search_var, width=32); search.pack(side="left", ipady=5)
        search.bind("<KeyRelease>", lambda e: self.load())
        ttk.Button(bar, text="🔍 Search", command=self.load).pack(side="left", padx=5)
        ttk.Button(bar, text="➕ Add", command=self.add).pack(side="left", padx=5)
        ttk.Button(bar, text="✏ Edit", command=self.edit).pack(side="left", padx=5)
        ttk.Button(bar, text="↻ Refill", command=self.refill).pack(side="left", padx=5)
        ttk.Button(bar, text="🗑 Delete", command=self.delete).pack(side="left", padx=5)
        cols = ("id", "name", "dosage", "frequency", "time", "qty", "expiry", "category")
        self.mt = ttk.Treeview(self.content, columns=cols, show="headings")
        for c, h, w in [("id", "ID", 45), ("name", "Medicine", 170), ("dosage", "Dosage", 90), ("frequency", "Frequency", 105), ("time", "Reminder(s)", 120), ("qty", "Qty", 60), ("expiry", "Expiry", 105), ("category", "Category", 110)]:
            self.mt.heading(c, text=h); self.mt.column(c, width=w, anchor="center")
        self.mt.pack(fill="both", expand=True); self.load()

    def load(self):
        if not hasattr(self, "mt") or not self.mt.winfo_exists(): return
        for i in self.mt.get_children(): self.mt.delete(i)
        term = getattr(self, "search_var", tk.StringVar()).get().strip()
        x = con()
        if term:
            like = "%" + term + "%"
            rows = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1 AND (name LIKE ? OR category LIKE ? OR dosage LIKE ?) ORDER BY name", (self.user["id"], like, like, like)).fetchall()
        else:
            rows = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1 ORDER BY id DESC", (self.user["id"],)).fetchall()
        x.close()
        for m in rows:
            self.mt.insert("", "end", values=(m["id"], m["name"], m["dosage"], m["frequency"], m["time"], m["quantity"], m["expiry"] or "-", m["category"] or "General"))

    def add(self, eid=None):
        w = tk.Toplevel(self); w.title("Medicine Details"); w.geometry("520x680"); w.grab_set(); w.configure(bg="white")
        frame = tk.Frame(w, bg="white"); frame.pack(fill="both", expand=True, padx=28, pady=18)
        fields = [
            ("Medicine Name", ""), ("Dosage", "e.g. 500 mg"), ("Frequency", "e.g. Once daily"),
            ("Reminder Times", "e.g. 08:00, 20:00"), ("Quantity", "e.g. 20"), ("Low Stock Alert At", "e.g. 5"),
            ("Expiry Date", "YYYY-MM-DD"), ("Category", "e.g. Tablet / Syrup"), ("Doctor", "Optional"),
            ("Batch Number", "Optional"), ("Instructions", "e.g. After food"), ("Notes", "Optional")]
        es = []
        for lab, hint in fields:
            tk.Label(frame, text=lab, bg="white", font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(5, 2))
            e = ttk.Entry(frame); e.pack(fill="x", ipady=3); es.append(e)
            if hint: e.insert(0, hint if lab == "Instructions" else "")
        # clear placeholder-like instruction field
        if es[10].get() == "e.g. After food": es[10].delete(0, "end")
        if eid:
            x = con(); m = x.execute("SELECT * FROM medicines WHERE id=? AND user_id=?", (eid, self.user["id"])).fetchone(); x.close()
            vals = [m["name"], m["dosage"], m["frequency"], m["time"], m["quantity"], m["low_stock"], m["expiry"], m["category"], m["doctor"], m["batch_no"], m["instructions"], m["notes"]]
            for a, b in zip(es, vals): a.delete(0, "end"); a.insert(0, "" if b is None else str(b))

        def save():
            vals = [e.get().strip() for e in es]
            if not vals[0]: return messagebox.showwarning("Required", "Medicine name is required.", parent=w)
            try: qty = int(vals[4] or 0); low = int(vals[5] or 5)
            except ValueError: return messagebox.showwarning("Number", "Quantity and low-stock level must be whole numbers.", parent=w)
            if not valid_date(vals[6]): return messagebox.showwarning("Expiry", "Use YYYY-MM-DD for expiry date.", parent=w)
            if not valid_times(vals[3]): return messagebox.showwarning("Reminder time", "Use HH:MM format, separated by commas.", parent=w)
            if qty < 0 or low < 0: return messagebox.showwarning("Number", "Quantity values cannot be negative.", parent=w)
            x = con()
            data = (vals[0], vals[1], vals[2], vals[3], qty, vals[6], vals[11], vals[7] or "General", vals[10], vals[8], vals[9], low)
            if eid:
                x.execute("""UPDATE medicines SET name=?,dosage=?,frequency=?,time=?,quantity=?,expiry=?,notes=?,category=?,instructions=?,doctor=?,batch_no=?,low_stock=? WHERE id=? AND user_id=?""", (*data, eid, self.user["id"]))
            else:
                x.execute("""INSERT INTO medicines(user_id,name,dosage,frequency,time,quantity,expiry,notes,category,instructions,doctor,batch_no,low_stock,active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)""", (self.user["id"], *data))
            x.commit(); x.close(); w.destroy(); self.medicines()
        ttk.Button(frame, text="Save Medicine", command=save).pack(pady=16)

    def selected_id(self):
        s = self.mt.selection()
        if not s: return None
        return int(self.mt.item(s[0], "values")[0])

    def edit(self):
        mid = self.selected_id()
        if not mid: return messagebox.showwarning("Select", "Select a medicine first.")
        self.add(mid)

    def delete(self):
        mid = self.selected_id()
        if not mid: return messagebox.showwarning("Select", "Select a medicine first.")
        if messagebox.askyesno("Confirm", "Delete selected medicine? Its history will be kept."):
            x = con(); x.execute("UPDATE medicines SET active=0 WHERE id=? AND user_id=?", (mid, self.user["id"])); x.commit(); x.close(); self.load()

    def refill(self):
        mid = self.selected_id()
        if not mid: return messagebox.showwarning("Select", "Select a medicine first.")
        q = tk.simpledialog.askinteger("Refill Stock", "How many units are being added?", minvalue=1, parent=self)
        if q:
            x = con(); x.execute("UPDATE medicines SET quantity=quantity+? WHERE id=? AND user_id=?", (q, mid, self.user["id"])); x.commit(); x.close(); self.load()

    def reminders(self):
        self.section_title("Reminders", "Today's schedule. Use multiple times such as 08:00, 14:00, 20:00.")
        x = con(); rows = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1 ORDER BY time,name", (self.user["id"],)).fetchall(); x.close()
        if not rows:
            tk.Label(self.content, text="No medicines added yet. Use Add Medicine.", bg="#f4f7fb", fg="#667085", font=("Segoe UI", 12)).pack(anchor="w")
        now = datetime.now().strftime("%H:%M")
        for m in rows:
            times = [z.strip() for z in (m["time"] or "").split(",") if z.strip()]
            due = now in times
            f = tk.Frame(self.content, bg="white", bd=1, relief="solid"); f.pack(fill="x", pady=5)
            title = "💊 " + m["name"] + ("  •  DUE NOW" if due else "")
            tk.Label(f, text=title, font=("Segoe UI", 12, "bold"), bg="white", fg="#173b73").pack(side="left", padx=15, pady=12)
            tk.Label(f, text=f"{m['dosage'] or ''} • {m['frequency'] or ''} • {m['time'] or 'No time'} • Qty {m['quantity']}", bg="white", fg="#667085").pack(side="left")
            ttk.Button(f, text="✓ Taken", command=lambda z=m: self.mark(z, "TAKEN")).pack(side="right", padx=5)
            ttk.Button(f, text="✕ Missed", command=lambda z=m: self.mark(z, "MISSED")).pack(side="right", padx=5)

    def mark(self, m, status):
        x = con(); x.execute("INSERT INTO history(user_id,medicine_id,medicine,status,marked) VALUES(?,?,?,?,?)", (self.user["id"], m["id"], m["name"], status, datetime.now().isoformat(timespec="seconds")))
        if status == "TAKEN" and (m["quantity"] or 0) > 0:
            x.execute("UPDATE medicines SET quantity=quantity-1 WHERE id=? AND user_id=?", (m["id"], self.user["id"]))
        x.commit(); x.close(); self.reminders()

    def check_due_reminders(self):
        if self.user and self.reminders_enabled:
            now = datetime.now().strftime("%H:%M")
            today_key = date.today().isoformat() + " " + now
            x = con(); rows = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1", (self.user["id"],)).fetchall(); x.close()
            for m in rows:
                times = [z.strip() for z in (m["time"] or "").split(",") if z.strip()]
                if now in times and (m["id"], today_key) not in self.last_popup_keys:
                    self.last_popup_keys.add((m["id"], today_key))
                    self.notify_bell()
                    messagebox.showinfo("Medicine Reminder", f"Time to take: {m['name']}\nDosage: {m['dosage'] or '-'}\nInstructions: {m['instructions'] or '-'}", parent=self)
        self.after(15000, self.check_due_reminders)

    def expiry(self):
        self.section_title("Expiry & Stock", "Expired medicines, expiry-soon warnings and low-stock alerts.")
        x = con(); rows = x.execute("SELECT * FROM medicines WHERE user_id=? AND active=1", (self.user["id"],)).fetchall(); x.close()
        t = ttk.Treeview(self.content, columns=("name", "qty", "expiry", "category", "status"), show="headings")
        for c, h, w in [("name", "Medicine", 190), ("qty", "Quantity", 90), ("expiry", "Expiry", 120), ("category", "Category", 120), ("status", "Status", 260)]: t.heading(c, text=h); t.column(c, width=w)
        t.pack(fill="both", expand=True)
        today = date.today()
        for m in rows:
            st = []
            exp = None
            if m["expiry"]:
                try: exp = datetime.strptime(m["expiry"], "%Y-%m-%d").date()
                except ValueError: pass
            if exp:
                days = (exp - today).days
                if days < 0: st.append("EXPIRED")
                elif days <= 30: st.append(f"EXPIRES IN {days} DAYS")
            if (m["quantity"] or 0) <= (m["low_stock"] if m["low_stock"] is not None else 5): st.append("LOW STOCK")
            if not st: st.append("OK")
            t.insert("", "end", values=(m["name"], m["quantity"], m["expiry"] or "-", m["category"] or "General", " • ".join(st)))

    def history_page(self):
        self.section_title("Dose History", "Track taken/missed doses and export the history as CSV.")
        bar = tk.Frame(self.content, bg="#f4f7fb"); bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="Export CSV", command=self.export_history).pack(side="left")
        ttk.Button(bar, text="Clear My History", command=self.clear_history).pack(side="left", padx=7)
        t = ttk.Treeview(self.content, columns=("medicine", "status", "marked"), show="headings")
        for c, h, w in [("medicine", "Medicine", 260), ("status", "Status", 130), ("marked", "Date / Time", 230)]: t.heading(c, text=h); t.column(c, width=w)
        t.pack(fill="both", expand=True)
        x = con(); rows = x.execute("SELECT medicine,status,marked FROM history WHERE user_id=? ORDER BY id DESC", (self.user["id"],)).fetchall(); x.close()
        for r in rows: t.insert("", "end", values=(r["medicine"], r["status"], r["marked"]))

    def export_history(self):
        path = filedialog.asksaveasfilename(title="Export Dose History", defaultextension=".csv", filetypes=[("CSV file", "*.csv")])
        if not path: return
        x = con(); rows = x.execute("SELECT medicine,status,marked FROM history WHERE user_id=? ORDER BY id DESC", (self.user["id"],)).fetchall(); x.close()
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["Medicine", "Status", "Date / Time"]); w.writerows([[r["medicine"], r["status"], r["marked"]] for r in rows])
        messagebox.showinfo("Export complete", "Dose history exported successfully.")

    def clear_history(self):
        if messagebox.askyesno("Confirm", "Delete all dose history for this account?"):
            x = con(); x.execute("DELETE FROM history WHERE user_id=?", (self.user["id"],)); x.commit(); x.close(); self.history_page()

    def analytics(self):
        self.section_title("Analytics", "Simple adherence and stock overview for your account.")
        a, b, c, d, taken, missed = self.counts(); total = taken + missed; rate = taken / total * 100 if total else 0
        r = tk.Frame(self.content, bg="#f4f7fb"); r.pack(fill="x")
        for l, v in [("Medicines", a), ("Expired", b), ("Low Stock", c), ("Taken", taken), ("Missed", missed), ("Adherence", f"{rate:.1f}%")]: self.smallcard(r, l, v)
        box = tk.Frame(self.content, bg="white", bd=1, relief="solid"); box.pack(fill="both", expand=True, pady=20)
        tk.Label(box, text="How the adherence figure is calculated", font=("Segoe UI", 14, "bold"), bg="white").pack(anchor="w", padx=20, pady=18)
        tk.Label(box, text=f"Taken doses: {taken}\nMissed doses: {missed}\nAdherence = Taken ÷ (Taken + Missed) × 100\n\nThis is a tracking statistic only and is not medical advice.", justify="left", bg="white", fg="#344054", font=("Segoe UI", 11)).pack(anchor="w", padx=20)

    def settings(self):
        self.section_title("Settings", "Local application settings and database backup.")
        box = tk.Frame(self.content, bg="white", bd=1, relief="solid"); box.pack(fill="x", pady=5)
        var = tk.BooleanVar(value=self.reminders_enabled)
        tk.Checkbutton(box, text="Enable popup medicine reminders", variable=var, bg="white", anchor="w", command=lambda: setattr(self, "reminders_enabled", var.get())).pack(fill="x", padx=20, pady=15)
        ttk.Button(box, text="Backup Database", command=self.backup_db).pack(anchor="w", padx=20, pady=6)
        ttk.Button(box, text="Open Data Folder", command=self.open_data_folder).pack(anchor="w", padx=20, pady=6)
        tk.Label(box, text="Your medicines and dose history are stored locally in the data folder. No web server is used.", bg="white", fg="#667085").pack(anchor="w", padx=20, pady=18)

    def backup_db(self):
        path = filedialog.asksaveasfilename(title="Backup Database", initialfile="medicine_reminder_backup.db", defaultextension=".db", filetypes=[("SQLite database", "*.db")])
        if path:
            try:
                shutil.copy2(DB, path); messagebox.showinfo("Backup", "Database backup created successfully.")
            except Exception as ex: messagebox.showerror("Backup error", str(ex))

    def open_data_folder(self):
        try:
            os.startfile(DATA_DIR)
        except Exception:
            messagebox.showinfo("Data Folder", DATA_DIR)

    def notify_bell(self):
        try: super().bell()
        except Exception: pass

    def about(self):
        self.section_title("About Project", "B.Sc. Computer Science final-year desktop application.")
        box = tk.Frame(self.content, bg="white", bd=1, relief="solid"); box.pack(fill="both", expand=True)
        text = ("Smart Medicine Reminder & Expiry Tracker\n\n"
                "Technology: Python Tkinter + SQLite\n\n"
                "Extended features:\n"
                "• Email registration and login\n"
                "• Medicine CRUD with category, doctor, batch and instructions\n"
                "• Multiple daily reminder times\n"
                "• Automatic popup reminders\n"
                "• Taken/Missed dose tracking\n"
                "• Automatic quantity reduction after Taken\n"
                "• Refill stock and low-stock thresholds\n"
                "• Expiry-soon and expired alerts\n"
                "• Search medicines\n"
                "• Dose history and CSV export\n"
                "• Adherence analytics\n"
                "• Local database backup\n"
                "• Desktop shortcut support\n\n"
                "No Flask, browser, localhost, or web server is required.")
        tk.Label(box, text=text, justify="left", anchor="nw", bg="white", font=("Segoe UI", 12), fg="#344054").pack(fill="both", expand=True, padx=30, pady=30)


if __name__ == "__main__":
    init_db()
    App().mainloop()
