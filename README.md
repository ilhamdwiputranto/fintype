<div align="center">

# ⚡ FinType

### Zero-Friction Financial Ledger Application

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%20v3.0%2B-green.svg)](https://flask.palletsprojects.org/)
[![Frontend](https://img.shields.io/badge/frontend-Tailwind%20CSS%20%7C%20Alpine.js-38bdf8.svg)](https://tailwindcss.com/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)

**FinType** adalah aplikasi pencatatan keuangan modern berbasis _Natural Language Processing (NLP)_ dan _Regex Engine_ yang memungkinkan pengguna mencatat transaksi secara natural, instan, dan _zero-friction_. Dilengkapi fitur **Shared Ledger**, pemantauan target keuangan (_Financial Goals_), serta _AI Financial Coach_.

[Fitur Utama](#-fitur-utama) • [Teknologi](#-teknologi-yang-digunakan) • [Instalasi](#-cara-instalasi--memulai) • [Panduan Penggunaan](#-panduan-kalimat-parser-nlp) • [Struktur Proyek](#-struktur-direktori)

</div>

---

## 🌟 Fitur Utama

### 🤖 1. Zero-Friction Natural Language Processing (NLP) & Speech-to-Text

- **Pencatatan Kalimat Alami**: Cukup tulis kalimat seperti `"Beli kopi 25rb di alfamart pake dompet kemarin"`, parser akan otomatis mengekstrak Nominal (`Rp 25.000`), Kategori (`Makanan/Minuman`), Sumber Dana (`Dompet`), Lokasi (`Alfamart`), dan Tanggal (`Kemarin`).
- **Live Parser Preview & Wallet Balance Estimator**: Preview hasil parsing secara real-time sebelum disimpan beserta simulasi dampak ke saldo dompet.
- **Dukungan Suara (Speech-to-Text)**: Catat transaksi langsung melalui perintah suara menggunakan Web Speech API.

### 👥 2. Multi-Ledger & Shared Budgeting

- **Buku Keuangan Bersama (Shared Ledger)**: Buat atau gabung ke ledger keluarga/usaha dengan kode undangan unik.
- **Budget Monitoring**: Atur batas anggaran bulanan ledger dengan indikator visual dan peringatan otomatis jika terjadi _over-budget_.
- **Role System**: Pembagian akses antara _Owner_ dan _Member_.

### 📊 3. Otomatisasi Kantong (Wallets), Kategori & Financial Goals

- **Auto-Generated Wallets**: Saldo dompet (BCA, ShopeePay, Cash, dll.) terhitung secara otomatis berdasarkan alokasi arus kas transaksi.
- **Financial Goals Progress Tracker**: Tetapkan target tabungan (misal: _Rumah Impian_, _Dana Darurat_) dan hubungkan dengan kata kunci transaksi untuk akumulasi progres otomatis.
- **Proporsi Kategori Interactive**: Visualisasi diagram proporsi pengeluaran/pemasukan dengan fitur klik-untuk-filter ke riwayat.

### 💡 4. AI Financial Coach & Smart Action

- **AI Financial Insights**: Menganalisis pola pengeluaran bulanan, rasio tabungan, dan memberikan saran finansial yang relevan.
- **Need Action Handler**: Mendeteksi transaksi yang kurang spesifik atau nominal 0 untuk ditinjau dan diperbaiki pengguna.

### 📁 5. Manajemen Data & Kustomisasi

- **Import/Export Data CSV**: Ekspor seluruh riwayat pencatatan ke CSV atau impor data historis dengan mudah.
- **Custom Regex Rules (Import/Export JSON)**: Buat aturan pemetaan kata kunci dan kategori sesuai kebutuhan pribadi, lengkap dengan dukungan ekspor/impor JSON.

---

## 🛠️ Teknologi yang Digunakan

- **Backend**: Python 3, Flask, SQLite3, Werkzeug
- **Frontend**: HTML5, Tailwind CSS (via CDN), Alpine.js (Reactive State Management)
- **Iconography**: FontAwesome 6
- **Parser Engine**: Custom Regex & Rule-based Natural Language Processing Engine

---

## 🚀 Cara Instalasi & Memulai

### Prasyarat

Pastikan Anda sudah menginstal **Python 3.8+** di komputer Anda.

### Langkah-Langkah

1. **Clone Repositori**

   ```bash
   git clone https://github.com/username-anda/fintype.git
   cd fintype
   ```

2. **Buat & Aktifkan Virtual Environment (Disarankan)**

   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instal Dependensi**

   ```bash
   pip install -r requirements.txt
   ```

4. **Isi Data Dummy (Opsional)**
   Untuk mencoba aplikasi langsung dengan data sampel (pengguna dummy, transaksi, & goals):

   ```bash
   python seed_dummy.py
   ```

   _Kredensial Akun Dummy:_
   - **User 1**: Username: `budi` | Password: `password123`
   - **User 2**: Username: `siti` | Password: `password123`

5. **Jalankan Aplikasi**

   ```bash
   python app.py
   ```

6. **Buka Aplikasi di Browser**
   Akses `http://localhost:5000` pada peramban Anda.

---

## 📝 Panduan Kalimat Parser (NLP)

FinType mendukung berbagai pola format kalimat alami berikut:

| Tipe Transaksi   | Contoh Kalimat Input                                          | Hasil Parsing Otomatis                                                                     |
| :--------------- | :------------------------------------------------------------ | :----------------------------------------------------------------------------------------- |
| **Pengeluaran**  | `"Beli miayam 25rb pake ShopeePay di warung bu atun kemarin"` | Nom: **25.000** \| Kat: **Makanan** \| Sumber: **ShopeePay** \| Lokasi: **Warung Bu Atun** |
| **Pemasukan**    | `"Gaji bulan ini 8jt masuk ke BCA"`                           | Nom: **8.000.000** \| Kat: **Pendapatan** \| Sumber: **BCA**                               |
| **Transfer**     | `"Transfer 2jt dari BCA ke ShopeePay"`                        | Nom: **2.000.000** \| Sumber: **BCA** \| Tujuan: **ShopeePay**                             |
| **Goal Savings** | `"Menabung 500rb untuk goal rumah pakai BCA"`                 | Nom: **500.000** \| Goal: **Rumah** \| Sumber: **BCA**                                     |

---

## 📂 Struktur Direktori

```text
.
├── app.py                # Flask Web Server & API Endpoints
├── database.py           # SQLite Database Abstraction Layer & Migrations
├── parser.py             # Custom Regex & NLP Parser Engine
├── seed_dummy.py         # Database Seeder (Data Contoh & Akun Tester)
├── requirements.txt      # Daftar Dependensi Python
├── static/
│   └── uploads/          # Folder Penyimpanan Struk & Cover Goal
├── templates/
│   ├── index.html        # Single Page Application Dashboard (Alpine.js + Tailwind)
│   ├── login.html        # Halaman Login
│   └── register.html     # Halaman Registrasi User
└── README.md             # Dokumentasi Proyek
```

---

## 📄 Lisensi

Proyek ini didistribusikan di bawah lisensi **MIT**. Silakan gunakan, modifikasi, dan kembangkan sesuai kebutuhan Anda.
