import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = 'pos-kasir-hendra-media-tech-2026'

DB_PATH = os.path.join(os.path.dirname(__file__), 'pos_toko.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabel Produk
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS produk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT NOT NULL,
            harga INTEGER NOT NULL,
            stok INTEGER NOT NULL
        )
    ''')
    # Tabel Transaksi Penjualan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT NOT NULL,
            total INTEGER NOT NULL,
            bayar INTEGER NOT NULL,
            kembali INTEGER NOT NULL,
            detail_items TEXT NOT NULL
        )
    ''')
    
    # Isi data contoh awal jika masih kosong
    cursor.execute('SELECT COUNT(*) FROM produk')
    if cursor.fetchone()[0] == 0:
        cursor.executemany('''
            INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)
        ''', [
            ('Kopi Hitam Robusta', 8000, 25),
            ('Es Teh Manis', 5000, 40),
            ('Roti Bakar Cokelat', 12000, 4),  # Stok menipis
            ('Mie Goreng Spesial', 15000, 15),
            ('Air Mineral 600ml', 4000, 3)     # Stok menipis
        ])
    conn.commit()
    conn.close()

init_db()

# Halaman Kasir Utama (Point of Sale)
@app.route('/')
def halaman_kasir():
    conn = get_db_connection()
    produk_list = conn.execute('SELECT * FROM produk ORDER BY nama ASC').fetchall()
    conn.close()
    return render_template('kasir.html', produk_list=produk_list)

# Proses Simpan Transaksi Penjualan
@app.route('/checkout', methods=['POST'])
def checkout():
    data = request.get_json()
    items = data.get('items', [])
    total = int(data.get('total', 0))
    bayar = int(data.get('bayar', 0))
    kembali = bayar - total

    if not items or bayar < total:
        return jsonify({'status': 'error', 'message': 'Pembayaran tidak valid!'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    # Potong Stok Produk
    detail_str_list = []
    for item in items:
        p_id = item['id']
        qty = int(item['qty'])
        
        # Ambil nama & update stok
        p = cursor.execute('SELECT nama, stok FROM produk WHERE id = ?', (p_id,)).fetchone()
        if p and p['stok'] >= qty:
            cursor.execute('UPDATE produk SET stok = stok - ? WHERE id = ?', (qty, p_id))
            detail_str_list.append(f"{p['nama']} x{qty}")
        else:
            conn.close()
            return jsonify({'status': 'error', 'message': f"Stok {item['nama']} tidak mencukupi!"}), 400

    # Simpan Transaksi
    tgl_now = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
    detail_items = ", ".join(detail_str_list)
    cursor.execute('''
        INSERT INTO transaksi (tanggal, total, bayar, kembali, detail_items)
        VALUES (?, ?, ?, ?, ?)
    ''', (tgl_now, total, bayar, kembali, detail_items))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Transaksi berhasil!'})

# Halaman Kelola Stok & Produk
@app.route('/produk', methods=['GET', 'POST'])
def kelola_produk():
    conn = get_db_connection()
    if request.method == 'POST':
        nama = request.form.get('nama')
        harga = int(request.form.get('harga', 0))
        stok = int(request.form.get('stok', 0))
        
        if nama and harga > 0:
            conn.execute('INSERT INTO produk (nama, harga, stok) VALUES (?, ?, ?)', (nama, harga, stok))
            conn.commit()
            flash('Produk baru berhasil ditambahkan!', 'success')
        return redirect(url_for('kelola_produk'))

    produk_list = conn.execute('SELECT * FROM produk ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('produk.html', produk_list=produk_list)

@app.route('/produk/hapus/<int:id>', methods=['POST'])
def hapus_produk(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM produk WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Produk berhasil dihapus!', 'info')
    return redirect(url_for('kelola_produk'))

# Halaman Laporan Penjualan
@app.route('/laporan')
def laporan_penjualan():
    conn = get_db_connection()
    transaksi_list = conn.execute('SELECT * FROM transaksi ORDER BY id DESC').fetchall()
    total_omzet = sum(t['total'] for t in transaksi_list)
    conn.close()
    return render_template('laporan', transaksi_list=transaksi_list, total_omzet=total_omzet)

if __name__ == '__main__':
    app.run(debug=True)
