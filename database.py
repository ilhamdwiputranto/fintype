import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_NAME = "fintype_pro.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT NOT NULL,
        current_ledger_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledgers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        invite_code TEXT UNIQUE NOT NULL,
        owner_id INTEGER NOT NULL,
        budget_limit REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ledger_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT DEFAULT 'member',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ledger_id, user_id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL DEFAULT 0,
        target_date TEXT,
        keywords TEXT DEFAULT '',
        image_url TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        user_name TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        type TEXT NOT NULL,
        aksi TEXT NOT NULL,
        category TEXT NOT NULL,
        item TEXT NOT NULL,
        nominal REAL NOT NULL,
        source_fund TEXT DEFAULT '-',
        target_fund TEXT DEFAULT '-',
        location TEXT DEFAULT '-',
        date_time TEXT NOT NULL,
        notes TEXT DEFAULT '',
        receipt_image TEXT DEFAULT '',
        goal_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ledger_id INTEGER NOT NULL,
        rule_key TEXT NOT NULL,
        rule_value TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()

    # Migration checks
    migrations = [
        "ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''",
        "ALTER TABLE users ADD COLUMN current_ledger_id INTEGER",
        "ALTER TABLE ledgers ADD COLUMN budget_limit REAL DEFAULT 0",
        "ALTER TABLE goals ADD COLUMN keywords TEXT DEFAULT ''",
        "ALTER TABLE goals ADD COLUMN image_url TEXT DEFAULT ''",
        "ALTER TABLE transactions ADD COLUMN notes TEXT DEFAULT ''",
        "ALTER TABLE transactions ADD COLUMN receipt_image TEXT DEFAULT ''"
    ]
    for stmt in migrations:
        try:
            cursor.execute(stmt)
        except Exception:
            pass

    conn.commit()
    conn.close()

def create_user(username, password, full_name):
    conn = get_db()
    cursor = conn.cursor()
    pwd_hash = generate_password_hash(password)
    try:
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (username, pwd_hash, full_name)
        )
        user_id = cursor.lastrowid
        
        invite_code = f"PRIV-{user_id}-{os.urandom(3).hex().upper()}"
        cursor.execute(
            "INSERT INTO ledgers (name, invite_code, owner_id) VALUES (?, ?, ?)",
            (f"Buku Pribadi {full_name}", invite_code, user_id)
        )
        ledger_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO ledger_members (ledger_id, user_id, role) VALUES (?, ?, 'owner')",
            (ledger_id, user_id)
        )
        
        cursor.execute(
            "UPDATE users SET current_ledger_id = ? WHERE id = ?",
            (ledger_id, user_id)
        )
        conn.commit()
        return user_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None

def update_user_profile(user_id, full_name, new_password=None):
    conn = get_db()
    cursor = conn.cursor()
    if new_password:
        pwd_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET full_name = ?, password_hash = ? WHERE id = ?", (full_name, pwd_hash, user_id))
    else:
        cursor.execute("UPDATE users SET full_name = ? WHERE id = ?", (full_name, user_id))
    conn.commit()
    conn.close()

def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def update_user_ledger(user_id, ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET current_ledger_id = ? WHERE id = ?", (ledger_id, user_id))
    conn.commit()
    conn.close()

def get_user_ledgers(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT l.*, lm.role 
        FROM ledgers l
        JOIN ledger_members lm ON l.id = lm.ledger_id
        WHERE lm.user_id = ?
        ORDER BY l.id ASC
    """, (user_id,))
    ledgers = cursor.fetchall()
    conn.close()
    return ledgers

def create_shared_ledger(user_id, name):
    conn = get_db()
    cursor = conn.cursor()
    try:
        invite_code = f"SHARE-{user_id}-{os.urandom(3).hex().upper()}"
        cursor.execute("INSERT INTO ledgers (name, invite_code, owner_id) VALUES (?, ?, ?)", (name, invite_code, user_id))
        ledger_id = cursor.lastrowid
        cursor.execute("INSERT INTO ledger_members (ledger_id, user_id, role) VALUES (?, ?, 'owner')", (ledger_id, user_id))
        cursor.execute("UPDATE users SET current_ledger_id = ? WHERE id = ?", (ledger_id, user_id))
        conn.commit()
        return ledger_id
    finally:
        conn.close()

def update_ledger_budget(ledger_id, budget_limit):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE ledgers SET budget_limit = ? WHERE id = ?", (budget_limit, ledger_id))
    conn.commit()
    conn.close()

def join_ledger_by_code(user_id, invite_code):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM ledgers WHERE invite_code = ?", (invite_code.strip().upper(),))
        ledger = cursor.fetchone()
        if not ledger:
            return None, "Kode undangan tidak ditemukan."
        
        try:
            cursor.execute("INSERT INTO ledger_members (ledger_id, user_id, role) VALUES (?, ?, 'member')", (ledger['id'], user_id))
            cursor.execute("UPDATE users SET current_ledger_id = ? WHERE id = ?", (ledger['id'], user_id))
            conn.commit()
            return ledger['id'], "Berhasil bergabung dengan Ledger!"
        except sqlite3.IntegrityError:
            cursor.execute("UPDATE users SET current_ledger_id = ? WHERE id = ?", (ledger['id'], user_id))
            conn.commit()
            return ledger['id'], "Anda sudah terdaftar di Ledger ini. Switched ke ledger ini."
    finally:
        conn.close()

def leave_ledger(user_id, ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM ledger_members WHERE user_id = ? AND ledger_id = ?", (user_id, ledger_id))
        cursor.execute("""
            SELECT l.id FROM ledgers l 
            JOIN ledger_members lm ON l.id = lm.ledger_id 
            WHERE lm.user_id = ? ORDER BY l.id ASC LIMIT 1
        """, (user_id,))
        first_ledger = cursor.fetchone()
        next_id = first_ledger['id'] if first_ledger else None
        cursor.execute("UPDATE users SET current_ledger_id = ? WHERE id = ?", (next_id, user_id))
        conn.commit()
    finally:
        conn.close()

def get_ledger_members(ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.id, u.full_name, u.username, lm.role 
        FROM users u
        JOIN ledger_members lm ON u.id = lm.user_id
        WHERE lm.ledger_id = ?
    """, (ledger_id,))
    members = cursor.fetchall()
    conn.close()
    return members

def get_custom_rules(ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_rules WHERE ledger_id = ? ORDER BY id DESC", (ledger_id,))
    rules = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rules

def add_custom_rule(ledger_id, rule_key, rule_value):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO custom_rules (ledger_id, rule_key, rule_value) VALUES (?, ?, ?)", (ledger_id, rule_key.lower().strip(), rule_value.strip()))
    conn.commit()
    conn.close()

def delete_custom_rule(rule_id, ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_rules WHERE id = ? AND ledger_id = ?", (rule_id, ledger_id))
    conn.commit()
    conn.close()

def add_transaction(ledger_id, user_id, user_name, raw_text, t_type, aksi, category, item, nominal, source_fund, target_fund, location, date_time, notes="", receipt_image="", goal_id=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO transactions (
                ledger_id, user_id, user_name, raw_text, type, aksi, category, item, nominal, 
                source_fund, target_fund, location, date_time, notes, receipt_image, goal_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ledger_id, user_id, user_name, raw_text, t_type, aksi, category, item, nominal, source_fund, target_fund, location, date_time, notes, receipt_image, goal_id))
        txn_id = cursor.lastrowid
        
        if goal_id and t_type == "Goal Savings":
            cursor.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ? AND ledger_id = ?", (nominal, goal_id, ledger_id))
            
        conn.commit()
        return txn_id
    finally:
        conn.close()

def update_transaction(txn_id, ledger_id, raw_text, t_type, aksi, category, item, nominal, source_fund, target_fund, location, date_time, notes, receipt_image):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM transactions WHERE id = ? AND ledger_id = ?", (txn_id, ledger_id))
        old_txn = cursor.fetchone()
        if old_txn and old_txn['type'] == 'Goal Savings' and old_txn['goal_id']:
            cursor.execute("UPDATE goals SET current_amount = MAX(0, current_amount - ?) WHERE id = ?", (old_txn['nominal'], old_txn['goal_id']))
            
        cursor.execute("""
            UPDATE transactions 
            SET raw_text = ?, type = ?, aksi = ?, category = ?, item = ?, nominal = ?, 
                source_fund = ?, target_fund = ?, location = ?, date_time = ?, notes = ?, receipt_image = ?
            WHERE id = ? AND ledger_id = ?
        """, (raw_text, t_type, aksi, category, item, nominal, source_fund, target_fund, location, date_time, notes, receipt_image, txn_id, ledger_id))
        
        if old_txn and t_type == 'Goal Savings' and old_txn['goal_id']:
            cursor.execute("UPDATE goals SET current_amount = current_amount + ? WHERE id = ?", (nominal, old_txn['goal_id']))

        conn.commit()
    finally:
        conn.close()

def delete_transaction(txn_id, ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM transactions WHERE id = ? AND ledger_id = ?", (txn_id, ledger_id))
        txn = cursor.fetchone()
        if txn and txn['type'] == 'Goal Savings' and txn['goal_id']:
            cursor.execute("UPDATE goals SET current_amount = MAX(0, current_amount - ?) WHERE id = ?", (txn['nominal'], txn['goal_id']))
            
        cursor.execute("DELETE FROM transactions WHERE id = ? AND ledger_id = ?", (txn_id, ledger_id))
        conn.commit()
    finally:
        conn.close()

def get_transactions_by_ledger(ledger_id, search_query="", start_date="", end_date=""):
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM transactions WHERE ledger_id = ?"
    params = [ledger_id]
    
    if search_query:
        query += " AND (raw_text LIKE ? OR item LIKE ? OR category LIKE ? OR location LIKE ? OR user_name LIKE ? OR notes LIKE ? OR source_fund LIKE ? OR target_fund LIKE ?)"
        sq = f"%{search_query}%"
        params.extend([sq, sq, sq, sq, sq, sq, sq, sq])
        
    if start_date:
        query += " AND date_time >= ?"
        params.append(start_date)
        
    if end_date:
        query += " AND date_time <= ?"
        params.append(end_date)
        
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    txns = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return txns

def get_goals_by_ledger(ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM goals WHERE ledger_id = ? ORDER BY id DESC", (ledger_id,))
    goals = [dict(row) for row in cursor.fetchall()]
    
    cursor.execute("SELECT * FROM transactions WHERE ledger_id = ?", (ledger_id,))
    txns = [dict(row) for row in cursor.fetchall()]
    
    for g in goals:
        kw_list = [k.strip().lower() for k in g.get('keywords', '').split(',') if k.strip()]
        kw_list.append(g['title'].strip().lower())
        
        accumulated = 0
        for t in txns:
            if t.get('goal_id') == g['id']:
                accumulated += t['nominal']
            elif t['type'] in ['Goal Savings', 'Pengeluaran', 'Transfer']:
                t_text = (t['raw_text'] + ' ' + t['item'] + ' ' + t.get('notes', '')).lower()
                if any(kw in t_text for kw in kw_list if kw):
                    accumulated += t['nominal']
        g['calculated_amount'] = max(g['current_amount'], accumulated)
        
    conn.close()
    return goals

def add_goal(ledger_id, title, target_amount, current_amount, target_date, keywords="", image_url=""):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO goals (ledger_id, title, target_amount, current_amount, target_date, keywords, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ledger_id, title, target_amount, current_amount, target_date, keywords, image_url))
        goal_id = cursor.lastrowid
        conn.commit()
        return goal_id
    finally:
        conn.close()

def update_goal(goal_id, ledger_id, title, target_amount, current_amount, target_date, keywords="", image_url=""):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE goals 
            SET title = ?, target_amount = ?, current_amount = ?, target_date = ?, keywords = ?, image_url = ?
            WHERE id = ? AND ledger_id = ?
        """, (title, target_amount, current_amount, target_date, keywords, image_url, goal_id, ledger_id))
        conn.commit()
    finally:
        conn.close()

def delete_goal(goal_id, ledger_id):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM goals WHERE id = ? AND ledger_id = ?", (goal_id, ledger_id))
        conn.commit()
    finally:
        conn.close()

def get_wallets_summary(ledger_id):
    txns = get_transactions_by_ledger(ledger_id)
    wallets = {}
    
    # Standard default wallets if referenced
    for t in txns:
        sf = t['source_fund'].strip().title() if t['source_fund'] and t['source_fund'] != '-' else None
        tf = t['target_fund'].strip().title() if t['target_fund'] and t['target_fund'] != '-' else None
        
        if sf and sf not in ['-', 'Kas/Bank']:
            wallets.setdefault(sf, 0.0)
        if tf and tf not in ['-', 'Rekening Tujuan'] and not tf.startswith('Goal ('):
            wallets.setdefault(tf, 0.0)
            
        nom = t['nominal']
        if t['type'] == 'Pemasukan' and sf:
            wallets[sf] = wallets.get(sf, 0.0) + nom
        elif t['type'] == 'Pengeluaran' and sf:
            wallets[sf] = wallets.get(sf, 0.0) - nom
        elif t['type'] == 'Transfer':
            if sf:
                wallets[sf] = wallets.get(sf, 0.0) - nom
            if tf and not tf.startswith('Goal ('):
                wallets[tf] = wallets.get(tf, 0.0) + nom
        elif t['type'] == 'Goal Savings':
            if sf:
                wallets[sf] = wallets.get(sf, 0.0) - nom

    # Defaults if empty
    if not wallets:
        wallets = {'Dompetku': 0.0, 'Kas Utama': 0.0}

    return [{'name': k, 'balance': v} for k, v in wallets.items()]
