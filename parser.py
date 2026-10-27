import re
from datetime import datetime, timedelta

class FinTypeParser:
    def __init__(self, custom_rules=None):
        self.rules = custom_rules or []

    def parse_amount(self, text):
        text_lower = text.lower()
        jt_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:jt|juta)', text_lower)
        if jt_match:
            num = float(jt_match.group(1).replace(',', '.'))
            return int(num * 1000000)
            
        rb_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:rb|ribu|k)', text_lower)
        if rb_match:
            num = float(rb_match.group(1).replace(',', '.'))
            return int(num * 1000)
            
        std_match = re.search(r'(?:rp\.?\s*)?(\d{1,3}(?:[.,]\d{3})+|\d+)', text_lower)
        if std_match:
            num_str = std_match.group(1).replace('.', '').replace(',', '')
            try:
                return int(num_str)
            except ValueError:
                return 0
        return 0

    def parse_date(self, text):
        text_lower = text.lower()
        today = datetime.now()
        
        if 'kemarin' in text_lower:
            target_date = today - timedelta(days=1)
        elif '2 hari lalu' in text_lower or 'dua hari lalu' in text_lower:
            target_date = today - timedelta(days=2)
        elif 'besok' in text_lower:
            target_date = today + timedelta(days=1)
        else:
            target_date = today
            
        return target_date.strftime('%Y-%m-%d')

    def parse(self, text, existing_goals=None):
        if not text or not text.strip():
            return {
                "type": "Pengeluaran",
                "raw_text": "",
                "aksi": "Membeli",
                "nominal": 0,
                "formatted_nominal": "Rp 0",
                "category": "Lain-lain",
                "item": "-",
                "source_fund": "Dompetku",
                "target_fund": "-",
                "location": "-",
                "date_time": datetime.now().strftime('%Y-%m-%d'),
                "goal_title": "-",
                "goal_id": None,
                "is_complete": False
            }

        raw_text = text.strip()
        text_lower = raw_text.lower()
        nominal = self.parse_amount(text_lower)
        date_str = self.parse_date(text_lower)
        
        # Check custom rules for category overriding
        override_category = None
        for r in self.rules:
            key = r.get('rule_key', '').lower().strip()
            val = r.get('rule_value', '').strip()
            if key and key in text_lower:
                override_category = val
                break

        # 1. GOAL SAVINGS PARSER PATTERN
        goal_keywords = ["menabung", "tabung", "simpan", "alokasi", "buat goal", "untuk goal", "demi goal"]
        if any(kw in text_lower for kw in goal_keywords):
            goal_title = "Tabungan Umum"
            goal_id = None
            
            if existing_goals:
                for g in existing_goals:
                    kws = [k.strip().lower() for k in g.get('keywords', '').split(',') if k.strip()]
                    kws.append(g['title'].strip().lower())
                    if any(kw in text_lower for kw in kws if kw):
                        goal_title = g['title']
                        goal_id = g['id']
                        break
                        
            if goal_title == "Tabungan Umum":
                m_goal = re.search(r'(?:goal|buat|untuk|demi)\s+([a-zA-Z0-9_\-\s]+)', text_lower)
                if m_goal:
                    goal_title = m_goal.group(1).title().strip()

            sumber = "Dompetku"
            sumber_match = re.search(r'(?:dari|pake|pakai|via)\s+([a-zA-Z0-9_\-]+)', text_lower)
            if sumber_match:
                sumber = sumber_match.group(1).title()

            is_comp = (nominal > 0)
            return {
                "type": "Goal Savings",
                "raw_text": raw_text,
                "aksi": "Tabungan Goal",
                "nominal": nominal,
                "formatted_nominal": f"Rp {nominal:,}".replace(',', '.'),
                "category": override_category or "Investasi & Tabungan",
                "item": f"Alokasi Goal: {goal_title}",
                "source_fund": sumber,
                "target_fund": f"Goal ({goal_title})",
                "location": "-",
                "date_time": date_str,
                "goal_title": goal_title,
                "goal_id": goal_id,
                "is_complete": is_comp
            }

        # 2. TRANSFER PARSER PATTERN
        transfer_keywords = ["transfer", "trf", "pindah", "kirim", "topup", "top up"]
        if any(kw in text_lower for kw in transfer_keywords):
            sumber = "Dompetku"
            tujuan = "Rekening Tujuan"
            
            m_sumber = re.search(r'dari\s+([a-zA-Z0-9_\-]+)', text_lower)
            if m_sumber:
                sumber = m_sumber.group(1).title()
                
            m_tujuan = re.search(r'(?:ke|untuk)\s+([a-zA-Z0-9_\-\s]+)', text_lower)
            if m_tujuan:
                tujuan = m_tujuan.group(1).title().strip()

            is_comp = (nominal > 0 and (m_sumber is not None or m_tujuan is not None))
            return {
                "type": "Transfer",
                "raw_text": raw_text,
                "aksi": "Transfer",
                "nominal": nominal,
                "formatted_nominal": f"Rp {nominal:,}".replace(',', '.'),
                "category": override_category or "Transfer Antar Kas",
                "item": f"Transfer {sumber} ➔ {tujuan}",
                "source_fund": sumber,
                "target_fund": tujuan,
                "location": "-",
                "date_time": date_str,
                "goal_title": "-",
                "goal_id": None,
                "is_complete": is_comp
            }

        # 3. PEMASUKAN PARSER PATTERN
        income_keywords = ["dapat", "jual", "gaji", "terima", "masuk", "bonus", "untung", "cair", "klaim", "terisi", "diisi", "pemasukan"]
        if any(kw in text_lower for kw in income_keywords):
            item_name = "Pemasukan Umum"
            words = text_lower.split()
            if len(words) > 1:
                item_name = ' '.join([w for w in words[:3] if not any(c.isdigit() for c in w)]).title()
                
            sumber = "BCA"
            m_sumber = re.search(r'(?:ke|masuk ke|di|terisi)\s+([a-zA-Z0-9_\-]+)', text_lower)
            if m_sumber:
                sumber = m_sumber.group(1).title()

            is_comp = (nominal > 0)
            return {
                "type": "Pemasukan",
                "raw_text": raw_text,
                "aksi": "Pendapatan",
                "nominal": nominal,
                "formatted_nominal": f"Rp {nominal:,}".replace(',', '.'),
                "category": override_category or "Pendapatan",
                "item": item_name if item_name else "Pemasukan Cash",
                "source_fund": sumber,
                "target_fund": "-",
                "location": "-",
                "date_time": date_str,
                "goal_title": "-",
                "goal_id": None,
                "is_complete": is_comp
            }

        # 4. PENGELUARAN PARSER PATTERN (DEFAULT)
        sumber_dana = "Dompetku"
        sumber_match = re.search(r'(?:dari|pake|pakai|via)\s+([a-zA-Z0-9_\-]+)', text_lower)
        if sumber_match:
            sumber_dana = sumber_match.group(1).title()

        lokasi = "-"
        lokasi_match = re.search(r'(?:di|at)\s+([a-zA-Z0-9_\-\s]+?)(?=\s+(?:dari|pake|pakai|kemarin|hari ini|besok|tadi|\d+|$))', text_lower)
        if lokasi_match:
            lokasi = lokasi_match.group(1).title().strip()

        # Category mapping
        cat_map = {
            "Makanan": ["miayam", "mie ayam", "nasi", "bakso", "sate", "makan", "roti", "soto", "rendang", "snack", "warung", "seblak"],
            "Minuman": ["kopi", "es teh", "jus", "susu", "air", "minum", "boba", "teh"],
            "Transportasi": ["bensin", "gojek", "grab", "parkir", "tol", "servis", "angkot", "tiket"],
            "Kebutuhan": ["sabun", "shampoo", "minyak", "beras", "token", "listrik", "pulsa", "kuota", "belanja"],
            "Hiburan": ["bioskop", "game", "netflix", "spotify", "nonton", "liburan"]
        }
        
        detected_cat = "Lain-lain"
        if override_category:
            detected_cat = override_category
        else:
            for cat, keywords in cat_map.items():
                if any(kw in text_lower for kw in keywords):
                    detected_cat = cat
                    break
                
        # Item extraction
        item_words = []
        skip_words = ["beli", "bayar", "sewa", "di", "dari", "pake", "pakai", "via", "kemarin", "besok", "hari", "ini"]
        for w in raw_text.split():
            clean_w = re.sub(r'[^a-zA-Z0-9]', '', w.lower())
            if clean_w not in skip_words and not any(c.isdigit() for c in clean_w) and len(clean_w) > 1:
                item_words.append(w)
                
        item = ' '.join(item_words[:3]).title() if item_words else "Pengeluaran General"

        # Completeness check
        is_comp = (nominal > 0 and detected_cat != "Lain-lain" and item != "Pengeluaran General")

        return {
            "type": "Pengeluaran",
            "raw_text": raw_text,
            "aksi": "Membeli",
            "nominal": nominal,
            "formatted_nominal": f"Rp {nominal:,}".replace(',', '.'),
            "category": detected_cat,
            "item": item,
            "source_fund": sumber_dana,
            "target_fund": "-",
            "location": lokasi,
            "date_time": date_str,
            "goal_title": "-",
            "goal_id": None,
            "is_complete": is_comp
        }
