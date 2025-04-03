import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import random
import string
from PIL import Image, ImageTk
from ttkthemes import ThemedTk
import os

class ProductInventorySystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistem Inventaris & POS Produk")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)
        
        # Tentukan path database
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.db_path = os.path.join(current_dir, 'inventory.db')
        
        # Koneksi ke database SQLite
        try:
            self.conn = sqlite3.connect(self.db_path)
            print(f"Database terbuat di: {self.db_path}")
            self.create_tables()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Gagal membuat database: {str(e)}")
            return

        # Buat folder yang diperlukan
        self.create_required_folders()
        
        # Buat notebook untuk tab berbeda
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buat frame untuk setiap tab
        self.inventory_frame = ttk.Frame(self.notebook)
        self.pos_frame = ttk.Frame(self.notebook)
        self.reports_frame = ttk.Frame(self.notebook)
        
        # Tambahkan frame ke notebook
        self.notebook.add(self.inventory_frame, text="Manajemen Inventaris")
        self.notebook.add(self.pos_frame, text="Point of Sale")
        self.notebook.add(self.reports_frame, text="Laporan")
        
        # Buat menu
        self.create_menu()
        
        # Setup tab inventaris
        self.setup_inventory_tab()
        
        # Setup tab POS
        self.setup_pos_tab()
        
        # Setup tab laporan
        self.setup_reports_tab()
        
        # Setup penutupan kamera saat window ditutup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Cek item inventaris yang rendah
        self.check_low_inventory()

    def create_required_folders(self):
        folders = ['struk', 'laporan', 'backup']
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        for folder in folders:
            folder_path = os.path.join(current_dir, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                print(f"Folder {folder} dibuat di: {folder_path}")

    def create_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # Menu File
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database", command=self.backup_database)
        file_menu.add_separator()
        file_menu.add_command(label="Keluar", command=self.on_closing)
        
        # Menu Laporan
        report_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Laporan", menu=report_menu)
        report_menu.add_command(label="Penjualan Harian", 
                              command=lambda: self.generate_report_by_type("Penjualan Harian"))
        report_menu.add_command(label="Penjualan Produk", 
                              command=lambda: self.generate_report_by_type("Penjualan Produk"))
        report_menu.add_command(label="Pergerakan Inventaris", 
                              command=lambda: self.generate_report_by_type("Pergerakan Inventaris"))
        report_menu.add_command(label="Stok Rendah", 
                              command=lambda: self.generate_report_by_type("Stok Rendah"))
        
    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            name TEXT NOT NULL,
            capital_price REAL NOT NULL,
            selling_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            date_added TEXT NOT NULL,
            last_updated TEXT,
            low_stock_threshold INTEGER DEFAULT 3
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            action TEXT,
            previous_qty INTEGER,
            change_qty INTEGER,
            new_qty INTEGER,
            date TEXT,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            date TEXT NOT NULL,
            total_items INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            tax REAL NOT NULL,
            total_amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            customer_name TEXT,
            notes TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            barcode TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount REAL DEFAULT 0,
            total_price REAL NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        self.conn.commit()

    def setup_inventory_tab(self):
        # Variabel untuk inventaris
        self.barcode_var = tk.StringVar()
        self.product_name_var = tk.StringVar()
        self.capital_price_var = tk.StringVar()
        self.selling_price_var = tk.StringVar()
        self.quantity_var = tk.StringVar()
        self.low_stock_threshold_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.edit_mode = False
        self.edit_id = None
        
        # Frame Utama
        main_frame = ttk.Frame(self.inventory_frame)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame Kiri (Form Input)
        left_frame = ttk.LabelFrame(main_frame, text="Manajemen Produk")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame Kanan (Daftar Produk)
        right_frame = ttk.LabelFrame(main_frame, text="Daftar Produk")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Widget Form
        ttk.Label(left_frame, text="Barcode:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.barcode_entry = ttk.Entry(left_frame, textvariable=self.barcode_var, width=30)
        self.barcode_entry.grid(row=0, column=1, padx=10, pady=5, sticky=tk.W)
        
        ttk.Button(left_frame, text="Generate Barcode", command=self.generate_barcode).grid(row=0, column=2, padx=10, pady=5)
        
        ttk.Label(left_frame, text="Nama Produk:").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Entry(left_frame, textvariable=self.product_name_var, width=50).grid(row=2, column=1, columnspan=3, padx=10, pady=5, sticky=tk.W)
        
        # Validasi untuk input numerik
        vcmd = (self.root.register(self.validate_numeric_input), '%P')
        
        ttk.Label(left_frame, text="Harga Modal:").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Entry(left_frame, textvariable=self.capital_price_var, width=30, validate='key', validatecommand=vcmd).grid(row=3, column=1, padx=10, pady=5, sticky=tk.W)
        
        ttk.Label(left_frame, text="Harga Jual:").grid(row=4, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Entry(left_frame, textvariable=self.selling_price_var, width=30, validate='key', validatecommand=vcmd).grid(row=4, column=1, padx=10, pady=5, sticky=tk.W)
        
        ttk.Label(left_frame, text="Jumlah:").grid(row=5, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Entry(left_frame, textvariable=self.quantity_var, width=30, validate='key', validatecommand=vcmd).grid(row=5, column=1, padx=10, pady=5, sticky=tk.W)
        
        ttk.Label(left_frame, text="Batas Stok Rendah:").grid(row=6, column=0, padx=10, pady=5, sticky=tk.W)
        ttk.Entry(left_frame, textvariable=self.low_stock_threshold_var, width=30, validate='key', validatecommand=vcmd).grid(row=6, column=1, padx=10, pady=5, sticky=tk.W)
        ttk.Label(left_frame, text="(Peringatan jika ≤ nilai ini)").grid(row=6, column=2, columnspan=2, padx=10, pady=5, sticky=tk.W)
        
        # Set nilai default untuk batas stok rendah
        self.low_stock_threshold_var.set("3")     
                # Frame Tombol
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=7, column=0, columnspan=4, padx=10, pady=15)
        
        ttk.Button(btn_frame, text="Tambah Produk", width=15, command=self.add_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Update Produk", width=15, command=self.update_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Hapus Produk", width=15, command=self.delete_product).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Bersihkan Form", width=15, command=self.clear_fields).pack(side=tk.LEFT, padx=5)
        
        # Setup frame pencarian dan daftar produk
        self.setup_product_list_frame(right_frame)

    def setup_product_list_frame(self, parent):
        # Frame untuk pencarian
        search_frame = ttk.LabelFrame(parent, text="Pencarian Produk", padding=10)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Search box dan tombol
        ttk.Label(search_frame, text="Cari:").pack(side=tk.LEFT)
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, padx=5)  # Perbaikan disini: entry -> Entry
        ttk.Button(search_frame, text="Cari", command=self.search_products).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="Tampilkan Semua", command=self.display_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Stok Rendah", command=self.display_low_stock).pack(side=tk.LEFT)
        
        # Frame untuk tabel produk
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview untuk menampilkan produk
        self.product_tree = ttk.Treeview(
            table_frame,
            columns=('ID', 'Nama', 'Barcode', 'Harga', 'Stok', 'Updated'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        
        # Konfigurasi scrollbar
        scrollbar.config(command=self.product_tree.yview)
        
        # Konfigurasi kolom
        self.product_tree.heading('ID', text='ID')
        self.product_tree.heading('Nama', text='Nama Produk')
        self.product_tree.heading('Barcode', text='Barcode')
        self.product_tree.heading('Harga', text='Harga')
        self.product_tree.heading('Stok', text='Stok')
        self.product_tree.heading('Updated', text='Terakhir Diupdate')
        
        # Atur lebar kolom
        self.product_tree.column('ID', width=50)
        self.product_tree.column('Nama', width=200)
        self.product_tree.column('Barcode', width=100)
        self.product_tree.column('Harga', width=100)
        self.product_tree.column('Stok', width=70)
        self.product_tree.column('Updated', width=150)
        
        self.product_tree.pack(fill=tk.BOTH, expand=True)

    def setup_pos_tab(self):
        # Variabel POS
        self.pos_barcode_var = tk.StringVar()
        self.pos_qty_var = tk.StringVar()
        self.pos_qty_var.set("1")  # Jumlah default adalah 1
        self.customer_name_var = tk.StringVar()
        self.notes_var = tk.StringVar()
        self.payment_method_var = tk.StringVar()
        self.payment_method_var.set("Tunai")  # Metode pembayaran default
        self.cart_items = []  # List untuk menyimpan item di keranjang
        
        # Frame utama untuk POS
        pos_main_frame = ttk.Frame(self.pos_frame)
        pos_main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Frame kiri untuk input barcode dan keranjang
        pos_left_frame = ttk.Frame(pos_main_frame)
        pos_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Frame kanan untuk pembayaran dan total
        pos_right_frame = ttk.Frame(pos_main_frame)
        pos_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5, ipadx=10) 
                # Frame Input Produk
        entry_frame = ttk.LabelFrame(pos_left_frame, text="Input Produk")
        entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Input barcode atau keyword
        ttk.Label(entry_frame, text="Barcode/Keyword:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.pos_search_var = tk.StringVar()
        search_entry = ttk.Entry(entry_frame, textvariable=self.pos_search_var, width=30)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        search_entry.bind("<Return>", lambda e: self.search_product_pos())
        
        ttk.Button(entry_frame, text="Cari", command=self.search_product_pos).grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(entry_frame, text="Jumlah:").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(entry_frame, textvariable=self.pos_qty_var, width=5).grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(entry_frame, text="Tambah ke Keranjang", command=self.add_to_cart).grid(row=0, column=5, padx=5, pady=5)

        # Frame hasil pencarian
        self.search_result_frame = ttk.LabelFrame(entry_frame, text="Hasil Pencarian")
        self.search_result_frame.grid(row=1, column=0, columnspan=6, padx=5, pady=5, sticky='nsew')

        # Treeview untuk hasil pencarian
        self.search_tree = ttk.Treeview(self.search_result_frame,
                                      columns=("id", "barcode", "name", "price", "stock"),
                                      show="headings",
                                      height=4)
        
        self.search_tree.heading("id", text="ID")
        self.search_tree.heading("barcode", text="Barcode")
        self.search_tree.heading("name", text="Nama Produk")
        self.search_tree.heading("price", text="Harga")
        self.search_tree.heading("stock", text="Stok")
        
        self.search_tree.column("id", width=50)
        self.search_tree.column("barcode", width=100)
        self.search_tree.column("name", width=200)
        self.search_tree.column("price", width=100)
        self.search_tree.column("stock", width=70)
        
        self.search_tree.pack(fill=tk.BOTH, expand=True)
        self.search_tree.bind("<Double-1>", self.select_search_result)

        # Frame Keranjang Belanja
        cart_frame = ttk.LabelFrame(pos_left_frame, text="Keranjang Belanja")
        cart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview keranjang
        cart_tree_frame = ttk.Frame(cart_frame)
        cart_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        cart_scroll_y = ttk.Scrollbar(cart_tree_frame)
        cart_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        cart_scroll_x = ttk.Scrollbar(cart_tree_frame, orient="horizontal")
        cart_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.cart_tree = ttk.Treeview(cart_tree_frame,
                                     columns=("id", "barcode", "name", "price", "qty", "total"),
                                     show="headings",
                                     yscrollcommand=cart_scroll_y.set,
                                     xscrollcommand=cart_scroll_x.set)
        
        cart_scroll_y.config(command=self.cart_tree.yview)
        cart_scroll_x.config(command=self.cart_tree.xview)
        
        # Definisi kolom keranjang
        self.cart_tree.heading("id", text="ID")
        self.cart_tree.heading("barcode", text="Barcode")
        self.cart_tree.heading("name", text="Produk")
        self.cart_tree.heading("price", text="Harga Satuan")
        self.cart_tree.heading("qty", text="Jumlah")
        self.cart_tree.heading("total", text="Total")
        
        # Konfigurasi lebar kolom
        self.cart_tree.column("id", width=50)
        self.cart_tree.column("barcode", width=100)
        self.cart_tree.column("name", width=200)
        self.cart_tree.column("price", width=100)
        self.cart_tree.column("qty", width=60)
        self.cart_tree.column("total", width=100)
        
        self.cart_tree.pack(fill=tk.BOTH, expand=True)
        
        # Tombol keranjang
        cart_btn_frame = ttk.Frame(cart_frame)
        cart_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(cart_btn_frame, text="Hapus Item", command=self.remove_from_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btn_frame, text="Kosongkan Keranjang", command=self.clear_cart).pack(side=tk.LEFT, padx=5)

        # Frame Pembayaran
        payment_frame = ttk.LabelFrame(pos_right_frame, text="Pembayaran")
        payment_frame.pack(fill=tk.BOTH, expand=False, padx=5, pady=5)
        
        # Tampilan subtotal, pajak, total
        ttk.Label(payment_frame, text="Subtotal:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.subtotal_label = ttk.Label(payment_frame, text="Rp 0", font=("Arial", 12))
        self.subtotal_label.grid(row=0, column=1, padx=5, pady=5, sticky=tk.E)
        
        ttk.Label(payment_frame, text="PPN (11%):").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.tax_label = ttk.Label(payment_frame, text="Rp 0", font=("Arial", 12))
        self.tax_label.grid(row=1, column=1, padx=5, pady=5, sticky=tk.E)

        ttk.Separator(payment_frame, orient='horizontal').grid(row=2, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        
        ttk.Label(payment_frame, text="TOTAL:", font=("Arial", 12, "bold")).grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.total_label = ttk.Label(payment_frame, text="Rp 0", font=("Arial", 14, "bold"))
        self.total_label.grid(row=3, column=1, padx=5, pady=5, sticky=tk.E)
        
        # Metode pembayaran
        ttk.Label(payment_frame, text="Metode Pembayaran:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        payment_methods = ["Tunai", "Kartu Kredit", "Kartu Debit", "QRIS"]
        payment_combo = ttk.Combobox(payment_frame, textvariable=self.payment_method_var, values=payment_methods, state="readonly")
        payment_combo.grid(row=4, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Info pelanggan
        ttk.Label(payment_frame, text="Nama Pelanggan:").grid(row=5, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(payment_frame, textvariable=self.customer_name_var).grid(row=5, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        ttk.Label(payment_frame, text="Catatan:").grid(row=6, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(payment_frame, textvariable=self.notes_var).grid(row=6, column=1, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Tombol proses pembayaran
        process_btn = ttk.Button(payment_frame, text="Proses Pembayaran", command=self.process_payment)
        process_btn.grid(row=7, column=0, columnspan=2, padx=5, pady=15, sticky=tk.W+tk.E)

    def search_product_pos(self):
        search_term = self.pos_search_var.get()
        if not search_term:
            messagebox.showwarning("Peringatan", "Masukkan barcode atau kata kunci")
            return
            
        # Bersihkan hasil pencarian sebelumnya
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, barcode, name, selling_price, quantity
                FROM products
                WHERE barcode LIKE ? OR name LIKE ?
                ORDER BY name
            ''', (f'%{search_term}%', f'%{search_term}%'))
            
            results = cursor.fetchall()
            
            if not results:
                messagebox.showinfo("Info", "Tidak ada produk yang ditemukan")
                return
                
            for row in results:
                # Format harga ke format rupiah
                formatted_price = f"Rp {row[3]:,.2f}"
                values = (row[0], row[1], row[2], formatted_price, row[4])
                self.search_tree.insert('', 'end', values=values)
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencari produk: {str(e)}")

    def select_search_result(self, event):
        selected_item = self.search_tree.selection()
        if not selected_item:
            return
            
        # Ambil data produk yang dipilih
        values = self.search_tree.item(selected_item[0])['values']
        
        # Set nilai untuk penambahan ke keranjang
        self.pos_barcode_var.set(values[1])  # Barcode
        
        # Tambahkan ke keranjang
        self.add_to_cart()

    def add_to_cart(self):
        barcode = self.pos_barcode_var.get()
        if not barcode:
            messagebox.showwarning("Peringatan", "Silakan pilih produk terlebih dahulu")
            return
            
        try:
            qty = int(self.pos_qty_var.get())
            if qty <= 0:
                raise ValueError("Jumlah harus lebih dari 0")
        except ValueError as e:
            messagebox.showwarning("Peringatan", str(e))
            return
            
        # Cek produk di database
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, name, selling_price, quantity 
            FROM products 
            WHERE barcode = ?
        ''', (barcode,))
        product = cursor.fetchone()
        
        if not product:
            messagebox.showwarning("Peringatan", "Produk tidak ditemukan")
            return
            
        product_id, name, price, stock = product
        
        if qty > stock:
            messagebox.showwarning("Peringatan", f"Stok tidak mencukupi. Stok tersedia: {stock}")
            return
            
        # Cek apakah produk sudah ada di keranjang
        for item in self.cart_tree.get_children():
            values = self.cart_tree.item(item)['values']
            if values[0] == product_id:  # Jika produk sudah ada
                new_qty = values[4] + qty
                if new_qty > stock:
                    messagebox.showwarning("Peringatan", f"Total quantity melebihi stok. Stok tersedia: {stock}")
                    return
                # Update quantity dan total
                new_total = price * new_qty
                self.cart_tree.item(item, values=(product_id, barcode, name, price, new_qty, new_total))
                self.update_totals()
                return
            
        # Jika produk belum ada di keranjang
        total = price * qty
        self.cart_tree.insert('', 'end', values=(product_id, barcode, name, price, qty, total))
        
        # Update total
        self.update_totals()
        
        # Reset input
        self.pos_search_var.set('')
        self.pos_qty_var.set('1')

    def update_totals(self):
        subtotal = sum(float(self.cart_tree.item(item)['values'][5]) for item in self.cart_tree.get_children())
        tax = subtotal * 0.11  # PPN 11%
        total = subtotal + tax
        
        self.subtotal_label.config(text=f"Rp {subtotal:,.2f}")
        self.tax_label.config(text=f"Rp {tax:,.2f}")
        self.total_label.config(text=f"Rp {total:,.2f}")

    def remove_from_cart(self):
        selected_item = self.cart_tree.selection()
        if not selected_item:
            messagebox.showwarning("Peringatan", "Pilih item yang akan dihapus")
            return
            
        self.cart_tree.delete(selected_item)
        self.update_totals()

    def clear_cart(self):
        if not self.cart_tree.get_children():
            messagebox.showwarning("Peringatan", "Keranjang sudah kosong")
            return
            
        if messagebox.askyesno("Konfirmasi", "Yakin ingin mengosongkan keranjang?"):
            for item in self.cart_tree.get_children():
                self.cart_tree.delete(item)
            self.update_totals()
            
            # Reset form pembayaran
            self.customer_name_var.set('')
            self.notes_var.set('')
            self.payment_method_var.set('Tunai')


    def display_products(self):
        """Menampilkan semua produk di treeview"""
        # Reset search field
        self.search_var.set('')
        
        # Tampilkan semua produk
        self.load_products()

    def process_payment(self):
        if not self.cart_tree.get_children():
            messagebox.showwarning("Peringatan", "Keranjang belanja kosong")
            return
            
        try:
            # Hitung total
            subtotal = sum(float(self.cart_tree.item(item)['values'][5]) for item in self.cart_tree.get_children())
            tax = subtotal * 0.11
            total = subtotal + tax
            
            # Generate transaction ID
            transaction_id = datetime.datetime.now().strftime('TRX%Y%m%d%H%M%S')
            
            # Simpan transaksi ke database
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO sales (
                    transaction_id, date, total_items, subtotal, tax, 
                    total_amount, payment_method, customer_name, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction_id,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                len(self.cart_tree.get_children()),
                subtotal,
                tax,
                total,
                self.payment_method_var.get(),
                self.customer_name_var.get(),
                self.notes_var.get()
            ))
            
            # Simpan item transaksi dan update stok
            for item in self.cart_tree.get_children():
                values = self.cart_tree.item(item)['values']
                product_id, barcode, name, price, qty, item_total = values
                
                cursor.execute('''
                    INSERT INTO sale_items (
                        transaction_id, product_id, product_name, barcode,
                        quantity, unit_price, total_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    transaction_id, product_id, name, barcode,
                    qty, price, item_total
                ))
                
                cursor.execute('''
                    UPDATE products 
                    SET quantity = quantity - ?,
                        last_updated = ?
                    WHERE id = ?
                ''', (qty, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), product_id))
                
            self.conn.commit()
            
            # Tampilkan struk
            self.print_receipt(transaction_id)
            
            # Bersihkan keranjang dan reset form
            self.clear_cart()
            self.customer_name_var.set('')
            self.notes_var.set('')
            self.payment_method_var.set('Tunai')
            
            messagebox.showinfo("Sukses", "Transaksi berhasil")
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Terjadi kesalahan: {str(e)}")

    def print_receipt(self, transaction_id):
        try:
            # Buat folder struk jika belum ada
            if not os.path.exists('struk'):
                os.makedirs('struk')
            
            filename = os.path.join('struk', f"struk_{transaction_id}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=" * 40 + "\n")
                f.write("TOKO SAYA\n")
                f.write("Jl. Contoh No. 123\n")
                f.write("Telp: 021-1234567\n")
                f.write("=" * 40 + "\n\n")
                
                f.write(f"No: {transaction_id}\n")
                f.write(f"Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Kasir: Admin\n\n")
                
                f.write("-" * 40 + "\n")
                for item in self.cart_tree.get_children():
                    values = self.cart_tree.item(item)['values']
                    name = values[2]
                    qty = values[4]
                    price = values[3]
                    total = values[5]
                    f.write(f"{name[:20]:<20}\n")
                    f.write(f"{qty:>3} x {price:>10,.2f} = {total:>10,.2f}\n")
                
                f.write("-" * 40 + "\n\n")
                
                subtotal = float(self.subtotal_label.cget("text").replace("Rp ", "").replace(",", ""))
                tax = float(self.tax_label.cget("text").replace("Rp ", "").replace(",", ""))
                total = float(self.total_label.cget("text").replace("Rp ", "").replace(",", ""))
                
                f.write(f"Subtotal: {subtotal:>28,.2f}\n")
                f.write(f"PPN 11%: {tax:>28,.2f}\n")
                f.write(f"TOTAL  : {total:>28,.2f}\n\n")
                
                f.write("=" * 40 + "\n")
                f.write("Terima kasih atas kunjungan Anda\n")
                f.write("=" * 40 + "\n")
            
            messagebox.showinfo("Sukses", f"Struk tersimpan sebagai {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan struk: {str(e)}")


    def display_low_stock(self):
        """Menampilkan produk dengan stok di bawah 10"""
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, barcode, price, quantity, last_updated 
                FROM products 
                WHERE quantity < 10
                ORDER BY quantity ASC
            ''')
            
            # Tampilkan hasil di treeview
            for row in cursor.fetchall():
                self.product_tree.insert('', 'end', values=(
                    row[0],  # ID
                    row[1],  # Nama
                    row[2],  # Barcode
                    f"{row[3]:,.2f}",  # Harga
                    row[4],  # Jumlah
                    row[5]   # Terakhir diupdate
                ), tags=('low_stock',) if row[4] < 5 else ())
            
            # Konfigurasi warna untuk stok rendah
            self.product_tree.tag_configure('low_stock', foreground='red')
                
            if not self.product_tree.get_children():
                messagebox.showinfo("Info", "Tidak ada produk dengan stok rendah")
                self.load_products()  # Tampilkan kembali semua produk
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat data stok rendah: {str(e)}")

    def generate_barcode(self):
        # Generate barcode 13 digit: 
        # 2 digit prefix + 10 digit random + 1 digit checksum
        prefix = "20"  # Bisa disesuaikan dengan kebutuhan
        random_numbers = ''.join(random.choices(string.digits, k=10))
        barcode = f"{prefix}{random_numbers}"
        
        # Hitung checksum
        total = 0
        for i in range(12):
            digit = int(barcode[i])
            if i % 2 == 0:
                total += digit
            else:
                total += digit * 3
        
        checksum = (10 - (total % 10)) % 10
        barcode = f"{barcode}{checksum}"
        
        self.barcode_var.set(barcode)

    def validate_numeric_input(self, P):
        if P == "" or P == ".":
            return True
        try:
            float(P)
            return True
        except ValueError:
            return False

    def backup_database(self):
        try:
            # Buat nama file backup dengan timestamp
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join('backup', f'inventory_backup_{timestamp}.db')
            
            # Buat backup
            backup_conn = sqlite3.connect(backup_path)
            self.conn.backup(backup_conn)
            backup_conn.close()
            
            messagebox.showinfo("Sukses", f"Database berhasil dibackup ke:\n{backup_path}")
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Gagal backup database: {str(e)}")

    def add_product(self):
        # Validasi input
        if not all([
            self.name_var.get().strip(),
            self.barcode_var.get().strip(),
            self.price_var.get().strip(),
            self.quantity_var.get().strip()
        ]):
            messagebox.showwarning("Peringatan", "Semua field harus diisi!")
            return

        try:
            # Ambil data dari form
            name = self.name_var.get().strip()
            barcode = self.barcode_var.get().strip()
            price = float(self.price_var.get())
            quantity = int(self.quantity_var.get())
            
            # Cek apakah barcode sudah ada
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM products WHERE barcode = ?", (barcode,))
            if cursor.fetchone():
                messagebox.showerror("Error", "Barcode sudah terdaftar!")
                return
            
            # Tambah produk ke database
            cursor.execute('''
                INSERT INTO products (name, barcode, price, quantity, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                name,
                barcode,
                price,
                quantity,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            self.conn.commit()
            messagebox.showinfo("Sukses", "Produk berhasil ditambahkan!")
            
            # Reset form
            self.name_var.set('')
            self.barcode_var.set('')
            self.price_var.set('')
            self.quantity_var.set('')
            
            # Refresh tabel produk
            self.load_products()
            
        except ValueError:
            messagebox.showerror("Error", "Harga dan jumlah harus berupa angka!")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Gagal menambah produk: {str(e)}")

    def load_products(self):
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            # Ambil data dari database
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name, barcode, price, quantity, last_updated 
                FROM products 
                ORDER BY name
            ''')
            
            # Tampilkan di treeview
            for row in cursor.fetchall():
                self.product_tree.insert('', 'end', values=(
                    row[0],  # ID
                    row[1],  # Nama
                    row[2],  # Barcode
                    f"{row[3]:,.2f}",  # Harga
                    row[4],  # Jumlah
                    row[5]   # Terakhir diupdate
                ))
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat data produk: {str(e)}")

    def update_product(self):
        selected_item = self.product_tree.selection()
        if not selected_item:
            messagebox.showwarning("Peringatan", "Pilih produk yang akan diupdate!")
            return
            
        # Validasi input
        if not all([
            self.name_var.get().strip(),
            self.barcode_var.get().strip(),
            self.price_var.get().strip(),
            self.quantity_var.get().strip()
        ]):
            messagebox.showwarning("Peringatan", "Semua field harus diisi!")
            return
            
        try:
            # Ambil data dari form
            name = self.name_var.get().strip()
            barcode = self.barcode_var.get().strip()
            price = float(self.price_var.get())
            quantity = int(self.quantity_var.get())
            
            # Ambil ID produk dari item yang dipilih
            product_id = self.product_tree.item(selected_item)['values'][0]
            
            # Cek apakah barcode sudah digunakan produk lain
            cursor = self.conn.cursor()
            cursor.execute("SELECT id FROM products WHERE barcode = ? AND id != ?", 
                         (barcode, product_id))
            if cursor.fetchone():
                messagebox.showerror("Error", "Barcode sudah digunakan produk lain!")
                return
            
            # Update produk di database
            cursor.execute('''
                UPDATE products 
                SET name = ?, 
                    barcode = ?, 
                    price = ?, 
                    quantity = ?,
                    last_updated = ?
                WHERE id = ?
            ''', (
                name,
                barcode,
                price,
                quantity,
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                product_id
            ))
            
            self.conn.commit()
            messagebox.showinfo("Sukses", "Produk berhasil diupdate!")
            
            # Reset form
            self.name_var.set('')
            self.barcode_var.set('')
            self.price_var.set('')
            self.quantity_var.set('')
            
            # Refresh tabel produk
            self.load_products()
            
        except ValueError:
            messagebox.showerror("Error", "Harga dan jumlah harus berupa angka!")
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Gagal mengupdate produk: {str(e)}")

    def select_product(self, event):
        selected_item = self.product_tree.selection()
        if selected_item:
            # Ambil data produk yang dipilih
            values = self.product_tree.item(selected_item)['values']
            
            # Isi form dengan data produk
            self.name_var.set(values[1])      # Nama
            self.barcode_var.set(values[2])   # Barcode
            self.price_var.set(values[3])     # Harga
            self.quantity_var.set(values[4])  # Jumlah

    def delete_product(self):
        selected_item = self.product_tree.selection()
        if not selected_item:
            messagebox.showwarning("Peringatan", "Pilih produk yang akan dihapus!")
            return
            
        if not messagebox.askyesno("Konfirmasi", "Yakin ingin menghapus produk ini?"):
            return
            
        try:
            # Ambil ID produk dari item yang dipilih
            product_id = self.product_tree.item(selected_item)['values'][0]
            
            # Hapus produk dari database
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            self.conn.commit()
            
            messagebox.showinfo("Sukses", "Produk berhasil dihapus!")
            
            # Reset form
            self.name_var.set('')
            self.barcode_var.set('')
            self.price_var.set('')
            self.quantity_var.set('')
            
            # Refresh tabel produk
            self.load_products()
            
        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Error", f"Gagal menghapus produk: {str(e)}")

    def clear_fields(self):
        """Bersihkan semua field input di form inventory"""
        self.name_var.set('')
        self.barcode_var.set('')
        self.price_var.set('')
        self.quantity_var.set('')
        
        # Hapus seleksi di treeview jika ada
        if self.product_tree.selection():
            self.product_tree.selection_remove(self.product_tree.selection())


    def setup_reports_tab(self):
        """Setup tab untuk laporan penjualan"""
        # Frame utama
        main_frame = ttk.Frame(self.reports_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame untuk filter
        filter_frame = ttk.LabelFrame(main_frame, text="Filter Laporan", padding=10)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tanggal mulai
        ttk.Label(filter_frame, text="Dari:").pack(side=tk.LEFT)
        self.start_date = DateEntry(filter_frame, width=12, background='darkblue',
                                  foreground='white', borderwidth=2)
        self.start_date.pack(side=tk.LEFT, padx=5)
        
        # Tanggal akhir
        ttk.Label(filter_frame, text="Sampai:").pack(side=tk.LEFT)
        self.end_date = DateEntry(filter_frame, width=12, background='darkblue',
                                foreground='white', borderwidth=2)
        self.end_date.pack(side=tk.LEFT, padx=5)
        
        # Tombol filter
        ttk.Button(filter_frame, text="Tampilkan", 
                  command=self.show_sales_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Export Excel", 
                  command=self.export_to_excel).pack(side=tk.LEFT)
        
        # Frame untuk tabel
        table_frame = ttk.Frame(main_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Treeview untuk laporan
        self.report_tree = ttk.Treeview(
            table_frame,
            columns=('No', 'Tanggal', 'Invoice', 'Total', 'Metode', 'Customer'),
            show='headings',
            yscrollcommand=scrollbar.set
        )
        
        # Konfigurasi scrollbar
        scrollbar.config(command=self.report_tree.yview)
        
        # Konfigurasi kolom
        self.report_tree.heading('No', text='No')
        self.report_tree.heading('Tanggal', text='Tanggal')
        self.report_tree.heading('Invoice', text='No Invoice')
        self.report_tree.heading('Total', text='Total')
        self.report_tree.heading('Metode', text='Metode Bayar')
        self.report_tree.heading('Customer', text='Customer')
        
        # Atur lebar kolom
        self.report_tree.column('No', width=50)
        self.report_tree.column('Tanggal', width=150)
        self.report_tree.column('Invoice', width=150)
        self.report_tree.column('Total', width=150)
        self.report_tree.column('Metode', width=100)
        self.report_tree.column('Customer', width=150)
        
        self.report_tree.pack(fill=tk.BOTH, expand=True)
        
        # Frame untuk summary
        summary_frame = ttk.LabelFrame(main_frame, text="Ringkasan", padding=10)
        summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Label untuk total
        self.total_sales_label = ttk.Label(summary_frame, text="Total Penjualan: Rp 0")
        self.total_sales_label.pack(side=tk.LEFT, padx=10)
        
        self.total_transactions_label = ttk.Label(summary_frame, text="Jumlah Transaksi: 0")
        self.total_transactions_label.pack(side=tk.LEFT, padx=10)

    def show_sales_report(self):
        """Menampilkan laporan penjualan sesuai filter tanggal"""
        # Bersihkan treeview
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
            
        try:
            start_date = self.start_date.get_date().strftime('%Y-%m-%d')
            end_date = self.end_date.get_date().strftime('%Y-%m-%d')
            
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT date, transaction_id, total_amount, payment_method, 
                       customer_name
                FROM sales 
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            ''', (f"{start_date} 00:00:00", f"{end_date} 23:59:59"))
            
            total_amount = 0
            for idx, row in enumerate(cursor.fetchall(), 1):
                self.report_tree.insert('', 'end', values=(
                    idx,
                    row[0],
                    row[1],
                    f"Rp {row[2]:,.2f}",
                    row[3],
                    row[4] or '-'
                ))
                total_amount += row[2]
            
            # Update summary
            self.total_sales_label.config(
                text=f"Total Penjualan: Rp {total_amount:,.2f}")
            self.total_transactions_label.config(
                text=f"Jumlah Transaksi: {idx}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memuat laporan: {str(e)}")

    def export_to_excel(self):
        """Export laporan ke file Excel"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                title="Simpan Laporan"
            )
            
            if not filename:
                return
                
            # Buat workbook baru
            wb = Workbook()
            ws = wb.active
            ws.title = "Laporan Penjualan"
            
            # Tulis header
            headers = ['No', 'Tanggal', 'No Invoice', 'Total', 'Metode Bayar', 'Customer']
            for col, header in enumerate(headers, 1):
                ws.cell(row=1, column=col, value=header)
            
            # Tulis data
            for idx, item in enumerate(self.report_tree.get_children(), 2):
                values = self.report_tree.item(item)['values']
                for col, value in enumerate(values, 1):
                    if col == 4:  # Kolom total
                        # Hapus "Rp " dan koma dari string
                        value = float(value.replace("Rp ", "").replace(",", ""))
                    ws.cell(row=idx, column=col, value=value)
            
            # Simpan file
            wb.save(filename)
            messagebox.showinfo("Sukses", f"Laporan berhasil disimpan ke:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal export laporan: {str(e)}")

    def search_products(self):
        search_term = self.search_var.get().strip()
        
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            
            # Jika search term kosong, tampilkan semua produk
            if not search_term:
                self.load_products()
                return
                
            # Cari produk berdasarkan nama atau barcode
            cursor.execute('''
                SELECT id, name, barcode, price, quantity, last_updated 
                FROM products 
                WHERE name LIKE ? OR barcode LIKE ?
                ORDER BY name
            ''', (f'%{search_term}%', f'%{search_term}%'))
            
            # Tampilkan hasil pencarian di treeview
            for row in cursor.fetchall():
                self.product_tree.insert('', 'end', values=(
                    row[0],  # ID
                    row[1],  # Nama
                    row[2],  # Barcode
                    f"{row[3]:,.2f}",  # Harga
                    row[4],  # Jumlah
                    row[5]   # Terakhir diupdate
                ))
                
            if not self.product_tree.get_children():
                messagebox.showinfo("Info", "Tidak ada produk yang ditemukan")
                self.load_products()  # Tampilkan kembali semua produk
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencari produk: {str(e)}")

    def on_closing(self):
        if messagebox.askokcancel("Keluar", "Yakin ingin keluar?"):
            # Tutup koneksi database
            if hasattr(self, 'conn'):
                self.conn.close()
            
            # Hancurkan window utama
            self.root.destroy()

# Jalankan aplikasi
if __name__ == "__main__":
    root = ThemedTk(theme="arc")  # Anda bisa mengganti theme sesuai preferensi
    app = ProductInventorySystem(root)
    root.mainloop()