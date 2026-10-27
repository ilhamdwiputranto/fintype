import os
import database as db

def run_seed():
    db.init_db()
    print("=" * 58)
    print(" 🌱 FinType Pro - Seeding Data Dummy ")
    print("=" * 58)
    
    # 1. Create Users
    try:
        u1_id = db.create_user("budi", "password123", "Budi Santoso")
        print("  [✓] User 1 Dibuat  : Username: 'budi' | Password: 'password123'")
    except Exception:
        u1 = db.authenticate_user("budi", "password123")
        u1_id = u1['id'] if u1 else 1
        print("  [✓] User 1 Sudah Ada : 'budi'")

    try:
        u2_id = db.create_user("siti", "password123", "Siti Aminah")
        print("  [✓] User 2 Dibuat  : Username: 'siti' | Password: 'password123'")
    except Exception:
        u2 = db.authenticate_user("siti", "password123")
        u2_id = u2['id'] if u2 else 2
        print("  [✓] User 2 Sudah Ada : 'siti'")

    # 2. Create Shared Ledger
    ledgers = db.get_user_ledgers(u1_id)
    shared_l = next((l for l in ledgers if not l['invite_code'].startswith('PRIV')), None)
    
    if not shared_l:
        l_id = db.create_shared_ledger(u1_id, "Keuangan Rumah & Usaha")
        db.join_ledger_by_code(u2_id, db.get_user_ledgers(u1_id)[-1]['invite_code'])
        db.update_ledger_budget(l_id, 10000000.0)
        print(f"  [✓] Shared Ledger Dibuat : 'Keuangan Rumah & Usaha' (Budget: Rp 10.000.000)")
    else:
        l_id = shared_l['id']
        db.update_ledger_budget(l_id, 10000000.0)

    # 3. Add Sample Goals
    goals = db.get_goals_by_ledger(l_id)
    if not goals:
        db.add_goal(l_id, "Rumah Impian 2027", 100000000.0, 5000000.0, "2027-12-31", "rumah, beli rumah, dp rumah", "")
        db.add_goal(l_id, "Dana Darurat 6 Bulan", 30000000.0, 10000000.0, "2026-12-31", "dana darurat, darurat, simpanan", "")
        print("  [✓] Sample Goals Dibuat : 'Rumah Impian 2027' & 'Dana Darurat 6 Bulan'")

    # 4. Add Sample Transactions
    txns = db.get_transactions_by_ledger(l_id)
    if not txns:
        sample_data = [
            ("Gaji bulan ini 8jt masuk ke BCA", "Pemasukan", "Pendapatan", "Pendapatan", "Gaji Bulanan", 8000000, "BCA", "-", "-", "2026-10-01", "Gaji Pokok Budi"),
            ("Transfer 2jt dari BCA ke ShopeePay", "Transfer", "Transfer", "Transfer Antar Kas", "Transfer Bca ➔ Shopeepay", 2000000, "BCA", "ShopeePay", "-", "2026-10-02", "Topup ShopeePay"),
            ("Beli miayam 25rb pake ShopeePay di warung bu atun", "Pengeluaran", "Membeli", "Makanan", "Miayam Bu Atun", 25000, "ShopeePay", "-", "Warung Bu Atun", "2026-10-05", "Makan siang"),
            ("Menabung 500rb untuk goal rumah pakai BCA", "Goal Savings", "Tabungan Goal", "Investasi & Tabungan", "Alokasi Goal: Rumah Impian 2027", 500000, "BCA", "Goal (Rumah Impian 2027)", "-", "2026-10-10", "Alokasi Bulanan"),
            ("Beli bensin 50rb pake Dompetku di pertamina", "Pengeluaran", "Membeli", "Transportasi", "Bensin Pertamax", 50000, "Dompetku", "-", "SPBU Pertamina", "2026-10-12", "Bensin Motor"),
            ("Beli kopi seblak", "Pengeluaran", "Membeli", "Lain-lain", "Pengeluaran General", 15000, "Dompetku", "-", "-", "2026-10-15", "Need Action Item")
        ]
        
        for raw, ttype, aksi, cat, item, nom, sf, tf, loc, dt, notes in sample_data:
            db.add_transaction(
                ledger_id=l_id,
                user_id=u1_id,
                user_name="Budi Santoso",
                raw_text=raw,
                t_type=ttype,
                aksi=aksi,
                category=cat,
                item=item,
                nominal=nom,
                source_fund=sf,
                target_fund=tf,
                location=loc,
                date_time=dt,
                notes=notes
            )
        print("  [✓] Sample Transactions Dibuat : 6 transaksi dimasukkan ke Shared Ledger")

    print("=" * 58)
    print(" 🎉 Seeding Data Dummy Selesai!")
    print("=" * 58)
    print("📌 Kredensial Login Dummy:")
    print("   1. Username: budi  | Password: password123")
    print("   2. Username: siti  | Password: password123")
    print("📌 Silakan buka http://localhost:5000 di browser untuk mencoba!")

if __name__ == "__main__":
    run_seed()
