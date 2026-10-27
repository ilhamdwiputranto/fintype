import os
import csv
import io
import json
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_file
from werkzeug.utils import secure_filename

import database as db
from parser import FinTypeParser

app = Flask(__name__)
app.secret_key = 'fintype_secret_pro_key_v4_6_blue'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Max Upload

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db.init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    user_id = session.get('user_id')
    if user_id:
        return db.get_user_by_id(user_id)
    return None

# --- AUTH ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = db.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            return redirect(url_for('index'))
        return render_template('login.html', error='Username atau Password salah')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not full_name or not username or not password or not confirm_password:
            return render_template('register.html', error='Semua kolom wajib diisi!')
            
        if password != confirm_password:
            return render_template('register.html', error='Konfirmasi password tidak cocok!')
            
        if len(password) < 6:
            return render_template('register.html', error='Password minimal 6 karakter!')
            
        try:
            db.create_user(username, password, full_name)
            return render_template('login.html', success='Pendaftaran berhasil! Silakan masuk dengan akun baru Anda.')
        except db.sqlite3.IntegrityError:
            return render_template('register.html', error='Username sudah digunakan, silakan gunakan username lain.')
        except Exception as e:
            return render_template('register.html', error=f'Gagal mendaftar: {str(e)}')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

# --- MAIN DASHBOARD ROUTE ---
@app.route('/')
@login_required
def index():
    user = get_current_user()
    if not user or not user['current_ledger_id']:
        return redirect(url_for('login_page'))
    return render_template('index.html', user=user)

# --- USER & PROFILE API ---
@app.route('/api/user-data', methods=['GET'])
@login_required
def api_user_data():
    user = get_current_user()
    ledgers = db.get_user_ledgers(user['id'])
    current_ledger = next((l for l in ledgers if l['id'] == user['current_ledger_id']), None)
    members = db.get_ledger_members(user['current_ledger_id']) if current_ledger else []
    
    return jsonify({
        'user': dict(user),
        'current_ledger': dict(current_ledger) if current_ledger else None,
        'ledgers': [dict(l) for l in ledgers],
        'ledger_members': [dict(m) for m in members]
    })

@app.route('/api/profile', methods=['PUT'])
@login_required
def api_update_profile():
    user = get_current_user()
    data = request.json or {}
    full_name = data.get('full_name', '').strip()
    old_password = data.get('old_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not full_name:
        return jsonify({'success': False, 'message': 'Nama lengkap tidak boleh kosong'})
        
    if new_password:
        if not old_password or not db.check_password_hash(user['password_hash'], old_password):
            return jsonify({'success': False, 'message': 'Password lama tidak sesuai'})
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'Password baru minimal 6 karakter'})
        db.update_user_profile(user['id'], full_name, new_password)
    else:
        db.update_user_profile(user['id'], full_name)
        
    return jsonify({'success': True, 'message': 'Profil berhasil diperbarui'})

# --- PARSER API ---
@app.route('/api/parse', methods=['POST'])
@login_required
def api_parse_text():
    data = request.json or {}
    text = data.get('text', '')
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    goals = db.get_goals_by_ledger(ledger_id)
    rules = db.get_custom_rules(ledger_id)
    
    parser = FinTypeParser(custom_rules=rules)
    result = parser.parse(text, existing_goals=goals)
    return jsonify(result)

# --- TRANSACTIONS API ---
@app.route('/api/transactions', methods=['GET', 'POST'])
@login_required
def api_transactions():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if request.method == 'GET':
        search = request.args.get('search', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        txns = db.get_transactions_by_ledger(ledger_id, search, start_date, end_date)
        return jsonify(txns)
        
    if request.method == 'POST':
        data = request.form if request.form else (request.json or {})
        raw_text = data.get('raw_text', '')
        notes = data.get('notes', '')
        
        receipt_url = ""
        if 'receipt_image' in request.files:
            file = request.files['receipt_image']
            if file and file.filename != '':
                fname = secure_filename(file.filename)
                timestamp = int(datetime.now().timestamp())
                save_name = f"receipt_{timestamp}_{fname}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
                receipt_url = f"/static/uploads/{save_name}"
        elif data.get('receipt_image_url'):
            receipt_url = data.get('receipt_image_url')
            
        rules = db.get_custom_rules(ledger_id)
        parser = FinTypeParser(custom_rules=rules)
        goals = db.get_goals_by_ledger(ledger_id)
        parsed = parser.parse(raw_text, existing_goals=goals)
        
        t_type = data.get('type') or parsed['type']
        aksi = data.get('aksi') or parsed['aksi']
        category = data.get('category') or parsed['category']
        item = data.get('item') or parsed['item']
        nominal = float(data.get('nominal') or parsed['nominal'])
        source_fund = data.get('source_fund') or parsed['source_fund']
        target_fund = data.get('target_fund') or parsed['target_fund']
        location = data.get('location') or parsed['location']
        date_time = data.get('date_time') or parsed['date_time']
        goal_id = data.get('goal_id') or parsed['goal_id']
        
        txn_id = db.add_transaction(
            ledger_id=ledger_id,
            user_id=user['id'],
            user_name=user['full_name'],
            raw_text=raw_text,
            t_type=t_type,
            aksi=aksi,
            category=category,
            item=item,
            nominal=nominal,
            source_fund=source_fund,
            target_fund=target_fund,
            location=location,
            date_time=date_time,
            notes=notes,
            receipt_image=receipt_url,
            goal_id=goal_id
        )
        return jsonify({'success': True, 'id': txn_id})

@app.route('/api/transactions/<int:txn_id>', methods=['PUT', 'DELETE'])
@login_required
def api_transaction_detail(txn_id):
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if request.method == 'DELETE':
        db.delete_transaction(txn_id, ledger_id)
        return jsonify({'success': True, 'message': 'Transaksi dihapus'})
        
    if request.method == 'PUT':
        data = request.form if request.form else (request.json or {})
        raw_text = data.get('raw_text', '')
        notes = data.get('notes', '')
        
        receipt_url = data.get('existing_receipt_image', '')
        if 'receipt_image' in request.files:
            file = request.files['receipt_image']
            if file and file.filename != '':
                fname = secure_filename(file.filename)
                timestamp = int(datetime.now().timestamp())
                save_name = f"receipt_{timestamp}_{fname}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
                receipt_url = f"/static/uploads/{save_name}"
                
        rules = db.get_custom_rules(ledger_id)
        parser = FinTypeParser(custom_rules=rules)
        goals = db.get_goals_by_ledger(ledger_id)
        parsed = parser.parse(raw_text, existing_goals=goals)
        
        t_type = data.get('type') or parsed['type']
        aksi = data.get('aksi') or parsed['aksi']
        category = data.get('category') or parsed['category']
        item = data.get('item') or parsed['item']
        nominal = float(data.get('nominal') or parsed['nominal'])
        source_fund = data.get('source_fund') or parsed['source_fund']
        target_fund = data.get('target_fund') or parsed['target_fund']
        location = data.get('location') or parsed['location']
        date_time = data.get('date_time') or parsed['date_time']
        
        db.update_transaction(
            txn_id=txn_id,
            ledger_id=ledger_id,
            raw_text=raw_text,
            t_type=t_type,
            aksi=aksi,
            category=category,
            item=item,
            nominal=nominal,
            source_fund=source_fund,
            target_fund=target_fund,
            location=location,
            date_time=date_time,
            notes=notes,
            receipt_image=receipt_url
        )
        return jsonify({'success': True, 'message': 'Transaksi diperbarui'})

# --- CATEGORIES & WALLETS API ---
@app.route('/api/categories', methods=['GET'])
@login_required
def api_categories():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    txns = db.get_transactions_by_ledger(ledger_id)
    
    pengeluaran_cats = {}
    pemasukan_cats = {}
    transfer_cats = {}
    
    for t in txns:
        c = t['category'] or 'Lain-lain'
        nom = t['nominal']
        if t['type'] == 'Pengeluaran':
            if c not in pengeluaran_cats:
                pengeluaran_cats[c] = {'total': 0, 'count': 0, 'items': []}
            pengeluaran_cats[c]['total'] += nom
            pengeluaran_cats[c]['count'] += 1
            pengeluaran_cats[c]['items'].append(t['item'])
        elif t['type'] == 'Pemasukan':
            if c not in pemasukan_cats:
                pemasukan_cats[c] = {'total': 0, 'count': 0, 'items': []}
            pemasukan_cats[c]['total'] += nom
            pemasukan_cats[c]['count'] += 1
            pemasukan_cats[c]['items'].append(t['item'])
        elif t['type'] in ['Transfer', 'Goal Savings']:
            if c not in transfer_cats:
                transfer_cats[c] = {'total': 0, 'count': 0, 'items': []}
            transfer_cats[c]['total'] += nom
            transfer_cats[c]['count'] += 1
            transfer_cats[c]['items'].append(t['item'])
            
    out_pengeluaran = [{'name': k, 'total': v['total'], 'count': v['count'], 'items': list(set(v['items']))} for k, v in pengeluaran_cats.items()]
    out_pemasukan = [{'name': k, 'total': v['total'], 'count': v['count'], 'items': list(set(v['items']))} for k, v in pemasukan_cats.items()]
    out_transfer = [{'name': k, 'total': v['total'], 'count': v['count'], 'items': list(set(v['items']))} for k, v in transfer_cats.items()]
    
    return jsonify({
        'pengeluaran': out_pengeluaran,
        'pemasukan': out_pemasukan,
        'transfer': out_transfer
    })

@app.route('/api/wallets', methods=['GET'])
@login_required
def api_wallets():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    wallets = db.get_wallets_summary(ledger_id)
    return jsonify(wallets)

# --- GOALS API ---
@app.route('/api/goals', methods=['GET', 'POST'])
@login_required
def api_goals():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if request.method == 'GET':
        goals = db.get_goals_by_ledger(ledger_id)
        return jsonify(goals)
        
    if request.method == 'POST':
        data = request.form if request.form else (request.json or {})
        title = data.get('title', '').strip()
        target_amount = float(data.get('target_amount', 0))
        current_amount = float(data.get('current_amount', 0))
        target_date = data.get('target_date', '')
        keywords = data.get('keywords', '').strip()
        image_url = data.get('image_url', '').strip()
        
        if 'goal_image' in request.files:
            file = request.files['goal_image']
            if file and file.filename != '':
                fname = secure_filename(file.filename)
                timestamp = int(datetime.now().timestamp())
                save_name = f"goal_{timestamp}_{fname}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
                image_url = f"/static/uploads/{save_name}"
                
        goal_id = db.add_goal(ledger_id, title, target_amount, current_amount, target_date, keywords, image_url)
        return jsonify({'success': True, 'id': goal_id})

@app.route('/api/goals/<int:goal_id>', methods=['PUT', 'DELETE'])
@login_required
def api_goal_detail(goal_id):
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if request.method == 'DELETE':
        db.delete_goal(goal_id, ledger_id)
        return jsonify({'success': True, 'message': 'Goal dihapus'})
        
    if request.method == 'PUT':
        data = request.form if request.form else (request.json or {})
        title = data.get('title', '').strip()
        target_amount = float(data.get('target_amount', 0))
        current_amount = float(data.get('current_amount', 0))
        target_date = data.get('target_date', '')
        keywords = data.get('keywords', '').strip()
        image_url = data.get('image_url', '').strip()
        
        if 'goal_image' in request.files:
            file = request.files['goal_image']
            if file and file.filename != '':
                fname = secure_filename(file.filename)
                timestamp = int(datetime.now().timestamp())
                save_name = f"goal_{timestamp}_{fname}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], save_name))
                image_url = f"/static/uploads/{save_name}"
                
        db.update_goal(goal_id, ledger_id, title, target_amount, current_amount, target_date, keywords, image_url)
        return jsonify({'success': True, 'message': 'Goal diperbarui'})

# --- CUSTOM RULES (REGEX) API ---
@app.route('/api/custom-rules', methods=['GET', 'POST'])
@login_required
def api_custom_rules():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if request.method == 'GET':
        rules = db.get_custom_rules(ledger_id)
        return jsonify(rules)
        
    if request.method == 'POST':
        data = request.json or {}
        key = data.get('rule_key', '').strip()
        val = data.get('rule_value', '').strip()
        if not key or not val:
            return jsonify({'success': False, 'message': 'Kata kunci dan Kategori wajib diisi'})
        db.add_custom_rule(ledger_id, key, val)
        return jsonify({'success': True})

@app.route('/api/custom-rules/<int:rule_id>', methods=['DELETE'])
@login_required
def api_delete_custom_rule(rule_id):
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    db.delete_custom_rule(rule_id, ledger_id)
    return jsonify({'success': True})

@app.route('/api/custom-rules/export', methods=['GET'])
@login_required
def api_export_custom_rules():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    rules = db.get_custom_rules(ledger_id)
    
    data_out = json.dumps(rules, indent=2)
    return Response(
        data_out,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment;filename=fintype_custom_rules_ledger_{ledger_id}.json"}
    )

@app.route('/api/custom-rules/import', methods=['POST'])
@login_required
def api_import_custom_rules():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if 'rules_file' not in request.files:
        return jsonify({'success': False, 'message': 'File JSON tidak ditemukan'})
        
    file = request.files['rules_file']
    try:
        content = json.load(file)
        imported_count = 0
        for item in content:
            k = item.get('rule_key')
            v = item.get('rule_value')
            if k and v:
                db.add_custom_rule(ledger_id, k, v)
                imported_count += 1
        return jsonify({'success': True, 'message': f'Berhasil mengimpor {imported_count} kata kunci kustom'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Gagal membaca file JSON: {str(e)}'})

# --- LEDGERS API ---
@app.route('/api/ledgers/switch', methods=['POST'])
@login_required
def api_switch_ledger():
    data = request.json or {}
    ledger_id = data.get('ledger_id')
    user = get_current_user()
    db.update_user_ledger(user['id'], ledger_id)
    return jsonify({'success': True})

@app.route('/api/ledgers/create', methods=['POST'])
@login_required
def api_create_ledger():
    data = request.json or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Nama ledger wajib diisi'})
    user = get_current_user()
    ledger_id = db.create_shared_ledger(user['id'], name)
    return jsonify({'success': True, 'ledger_id': ledger_id})

@app.route('/api/ledgers/budget', methods=['POST'])
@login_required
def api_update_ledger_budget():
    data = request.json or {}
    budget = float(data.get('budget_limit', 0))
    user = get_current_user()
    db.update_ledger_budget(user['current_ledger_id'], budget)
    return jsonify({'success': True})

@app.route('/api/ledgers/join', methods=['POST'])
@login_required
def api_join_ledger():
    data = request.json or {}
    code = data.get('invite_code', '').strip()
    user = get_current_user()
    ledger_id, message = db.join_ledger_by_code(user['id'], code)
    if ledger_id:
        return jsonify({'success': True, 'message': message})
    return jsonify({'success': False, 'message': message})

@app.route('/api/ledgers/leave', methods=['POST'])
@login_required
def api_leave_ledger():
    data = request.json or {}
    ledger_id = data.get('ledger_id')
    user = get_current_user()
    db.leave_ledger(user['id'], ledger_id)
    return jsonify({'success': True})

# --- AI ANALYSIS ROUTE ---
@app.route('/api/ai-analysis', methods=['GET'])
@login_required
def api_ai_analysis():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    txns = db.get_transactions_by_ledger(ledger_id)
    goals = db.get_goals_by_ledger(ledger_id)
    
    total_pemasukan = sum(t['nominal'] for t in txns if t['type'] == 'Pemasukan')
    total_pengeluaran = sum(t['nominal'] for t in txns if t['type'] == 'Pengeluaran')
    net_balance = total_pemasukan - total_pengeluaran
    
    cat_totals = {}
    for t in txns:
        if t['type'] == 'Pengeluaran' and t['category']:
            cat_totals[t['category']] = cat_totals.get(t['category'], 0) + t['nominal']
            
    top_cat = max(cat_totals.items(), key=lambda x: x[1])[0] if cat_totals else "Belum Ada Data"
    
    insights = []
    if total_pengeluaran > total_pemasukan and total_pemasukan > 0:
        insights.append(f"⚠️ Pengeluaran Anda (Rp {total_pengeluaran:,.0f}) melebihi Pemasukan (Rp {total_pemasukan:,.0f}). Kurangi alokasi {top_cat}.")
    elif total_pemasukan > 0:
        savings_rate = int(((total_pemasukan - total_pengeluaran) / total_pemasukan) * 100)
        insights.append(f"🎉 Rasio Tabungan Ledger: {savings_rate}%. Arus kas Anda dan anggota ledger sangat sehat!")
    else:
        insights.append("💡 Belum ada data pemasukan tercatat. Tambahkan catatan pemasukan untuk analisis yang presisi.")
        
    if top_cat != "Belum Ada Data":
        insights.append(f"📊 Pengeluaran terbesar ledger saat ini adalah **{top_cat}** sebesar Rp {cat_totals[top_cat]:,.0f}.")
        
    if goals:
        completed_goals = [g for g in goals if g.get('calculated_amount', 0) >= g['target_amount']]
        insights.append(f"🎯 Progress Goals: {len(completed_goals)} dari {len(goals)} target keuangan telah tercapai!")

    return jsonify({
        'success': True,
        'summary': {
            'pemasukan': total_pemasukan,
            'pengeluaran': total_pengeluaran,
            'net_balance': net_balance,
            'top_category': top_cat
        },
        'insights': insights
    })

# --- EXPORT & IMPORT ROUTE ---
@app.route('/export/csv')
@login_required
def export_csv():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    txns = db.get_transactions_by_ledger(ledger_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Tanggal', 'Dicatat Oleh', 'Tipe', 'Aksi', 'Kategori', 'Item', 'Nominal', 'Sumber Dana', 'Tujuan Dana', 'Lokasi', 'Catatan', 'Kalimat Asli'])
    
    for t in txns:
        writer.writerow([
            t['id'], t['date_time'], t['user_name'], t['type'], t['aksi'], 
            t['category'], t['item'], t['nominal'], t['source_fund'], 
            t['target_fund'], t['location'], t.get('notes', ''), t['raw_text']
        ])
        
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=fintype_ledger_{ledger_id}_export.csv"}
    )

@app.route('/import/csv', methods=['POST'])
@login_required
def import_csv():
    user = get_current_user()
    ledger_id = user['current_ledger_id']
    
    if 'csv_file' not in request.files:
        return jsonify({'success': False, 'message': 'File CSV tidak ditemukan'})
        
    file = request.files['csv_file']
    if not file or file.filename == '':
        return jsonify({'success': False, 'message': 'Pilih file CSV yang valid'})
        
    try:
        stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
        reader = csv.DictReader(stream)
        
        imported_count = 0
        rules = db.get_custom_rules(ledger_id)
        parser = FinTypeParser(custom_rules=rules)
        goals = db.get_goals_by_ledger(ledger_id)
        
        for row in reader:
            raw_text = row.get('Kalimat Asli') or row.get('raw_text') or row.get('Item') or row.get('item') or ''
            if not raw_text.strip():
                continue
                
            parsed = parser.parse(raw_text, existing_goals=goals)
            
            t_type = row.get('Tipe') or row.get('type') or parsed['type']
            aksi = row.get('Aksi') or row.get('aksi') or parsed['aksi']
            category = row.get('Kategori') or row.get('category') or parsed['category']
            item = row.get('Item') or row.get('item') or parsed['item']
            
            try:
                nominal = float(row.get('Nominal') or row.get('nominal') or parsed['nominal'])
            except ValueError:
                nominal = parsed['nominal']
                
            source_fund = row.get('Sumber Dana') or row.get('source_fund') or parsed['source_fund']
            target_fund = row.get('Tujuan Dana') or row.get('target_fund') or parsed['target_fund']
            location = row.get('Lokasi') or row.get('location') or parsed['location']
            date_time = row.get('Tanggal') or row.get('date_time') or parsed['date_time']
            notes = row.get('Catatan') or row.get('notes') or ''
            
            db.add_transaction(
                ledger_id=ledger_id,
                user_id=user['id'],
                user_name=user['full_name'],
                raw_text=raw_text,
                t_type=t_type,
                aksi=aksi,
                category=category,
                item=item,
                nominal=nominal,
                source_fund=source_fund,
                target_fund=target_fund,
                location=location,
                date_time=date_time,
                notes=notes,
                receipt_image=""
            )
            imported_count += 1
            
        return jsonify({'success': True, 'message': f'Berhasil mengimpor {imported_count} transaksi ke Ledger!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Gagal memproses file CSV: {str(e)}'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
