import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import datetime
import random
import string
from PIL import Image, ImageTk
from ttkthemes import ThemedTk
import cv2
from pyzbar.pyzbar import decode
import threading
import time
import os
import logging
import configparser

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

class ProductInventorySystem:
    def __init__(self, root):
        self.root = root
        self.root.title("Sistem Inventaris & POS Produk")
        self.root.geometry("1200x700")
        self.root.resizable(True, True)
        
        # Load configuration
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        
        # Set default values if not present
        if 'Database' not in self.config:
            self.config['Database'] = {'path': 'inventory.db'}
        if 'Tax' not in self.config:
            self.config['Tax'] = {'rate': '0.11'}
            
        self.db_path = self.config['Database']['path']
        self.tax_rate = float(self.config['Tax']['rate'])
        
        # Save configuration
        with open('config.ini', 'w') as configfile:
            self.config.write(configfile)
        
        # Koneksi ke database SQLite
        self.conn = sqlite3.connect(self.db_path)
        self.create_tables()
        
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

    def create_tables(self):
        try:
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
            logging.info("Tables created successfully.")
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            messagebox.showerror("Error", f"Database error: {str(e)}")
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
        
        ttk.Button(left_frame, text="Generate Otomatis", command=self.generate_barcode).grid(row=0, column=3, padx=10, pady=5)
        
       
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
    def setup_product_list_frame(self, right_frame):
        # Frame Pencarian
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(search_frame, text="Cari:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(search_frame, textvariable=self.search_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Cari", command=self.search_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Tampilkan Semua", command=self.display_products).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Stok Rendah", command=self.display_low_stock).pack(side=tk.LEFT, padx=5)

        # Treeview untuk Produk
        self.tree_frame = ttk.Frame(right_frame)
        self.tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame)
        self.tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_scroll_x = ttk.Scrollbar(self.tree_frame, orient="horizontal")
        self.tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.product_tree = ttk.Treeview(self.tree_frame,
                                        columns=("id", "barcode", "name", "capital_price", "selling_price",
                                                "quantity", "low_stock", "status", "date_added", "last_updated"),
                                        show="headings",
                                        yscrollcommand=self.tree_scroll_y.set,
                                        xscrollcommand=self.tree_scroll_x.set)
        
        self.tree_scroll_y.config(command=self.product_tree.yview)
        self.tree_scroll_x.config(command=self.product_tree.xview)
        
        # Definisi kolom
        self.product_tree.heading("id", text="ID")
        self.product_tree.heading("barcode", text="Barcode")
        self.product_tree.heading("name", text="Nama Produk")
        self.product_tree.heading("capital_price", text="Harga Modal")
        self.product_tree.heading("selling_price", text="Harga Jual")
        self.product_tree.heading("quantity", text="Stok")
        self.product_tree.heading("low_stock", text="Batas Stok")
        self.product_tree.heading("status", text="Status")
        self.product_tree.heading("date_added", text="Tanggal Ditambahkan")
        self.product_tree.heading("last_updated", text="Terakhir Diupdate")
        
        # Konfigurasi lebar kolom
        self.product_tree.column("id", width=50)
        self.product_tree.column("barcode", width=120)
        self.product_tree.column("name", width=200)
        self.product_tree.column("capital_price", width=100)
        self.product_tree.column("selling_price", width=100)
        self.product_tree.column("quantity", width=80)
        self.product_tree.column("low_stock", width=80)
        self.product_tree.column("status", width=80)
        self.product_tree.column("date_added", width=150)
        self.product_tree.column("last_updated", width=150)
        
        self.product_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind treeview selection
        self.product_tree.bind("<ButtonRelease-1>", self.get_selected_product)
        
        # Create tags for status highlighting
        self.product_tree.tag_configure('low_stock', background='#FFCCCC')

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
        
        # Add search functionality
        self.setup_pos_search_frame(pos_left_frame)
        
        # Setup frame keranjang
        self.setup_cart_frame(pos_left_frame)
        
        # Setup frame pembayaran
        self.setup_payment_frame(pos_right_frame)

    def setup_pos_search_frame(self, parent_frame):
        search_frame = ttk.LabelFrame(parent_frame, text="Cari Produk")
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(search_frame, text="Cari (Barcode/Nama):").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.pos_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.pos_search_var, width=30)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        search_entry.bind("<Return>", lambda event: self.search_pos_products())  # Bind Enter key to search

        ttk.Button(search_frame, text="Cari", command=self.search_pos_products).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(search_frame, text="Reset", command=self.reset_pos_search).grid(row=0, column=3, padx=5, pady=5)

        # Treeview for search results
        self.pos_search_tree = ttk.Treeview(search_frame,
                                            columns=("id", "barcode", "name", "price", "stock"),
                                            show="headings",
                                            height=5)
        self.pos_search_tree.grid(row=1, column=0, columnspan=4, padx=5, pady=5, sticky=tk.W+tk.E)

        self.pos_search_tree.heading("id", text="ID")
        self.pos_search_tree.heading("barcode", text="Barcode")
        self.pos_search_tree.heading("name", text="Nama Produk")
        self.pos_search_tree.heading("price", text="Harga Jual")
        self.pos_search_tree.heading("stock", text="Stok")

        self.pos_search_tree.column("id", width=50)
        self.pos_search_tree.column("barcode", width=120)
        self.pos_search_tree.column("name", width=200)
        self.pos_search_tree.column("price", width=100)
        self.pos_search_tree.column("stock", width=80)

        self.pos_search_tree.bind("<Double-1>", self.select_pos_product)

    def search_pos_products(self):
        search_term = self.pos_search_var.get()
        if not search_term:
            messagebox.showwarning("Peringatan", "Masukkan barcode atau nama produk untuk mencari.")
            return

        # Clear previous search results
        for item in self.pos_search_tree.get_children():
            self.pos_search_tree.delete(item)

        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, barcode, name, selling_price, quantity
                FROM products
                WHERE barcode LIKE ? OR name LIKE ?
                ORDER BY name
            ''', (f'%{search_term}%', f'%{search_term}%'))

            results = cursor.fetchall()

            if len(results) == 1 and results[0][1] == search_term:  # Exact barcode match
                product_id, barcode, name, price, stock = results[0]
                if stock <= 0:
                    messagebox.showwarning("Peringatan", "Stok tidak mencukupi.")
                    return

                # Check if the product is already in the cart
                for item in self.cart_tree.get_children():
                    values = self.cart_tree.item(item)['values']
                    if values[1] == barcode:  # Match by barcode
                        new_qty = values[4] + 1
                        if new_qty > stock:
                            messagebox.showwarning("Peringatan", f"Stok tidak mencukupi. Stok tersedia: {stock}")
                            return
                        new_total = new_qty * price
                        self.cart_tree.item(item, values=(values[0], values[1], values[2], values[3], new_qty, new_total))
                        self.update_totals()
                        self.pos_search_var.set('')  # Clear search field
                        messagebox.showinfo("Sukses", f"Jumlah produk '{name}' di keranjang diperbarui.")
                        return

                # Add new product to the cart
                self.cart_tree.insert('', 'end', values=(product_id, barcode, name, price, 1, price))
                self.update_totals()
                self.pos_search_var.set('')  # Clear search field
                messagebox.showinfo("Sukses", f"Produk '{name}' berhasil ditambahkan ke keranjang.")
            else:
                # Populate search results for manual selection
                for row in results:
                    self.pos_search_tree.insert('', 'end', values=row)

        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencari produk: {str(e)}")

    def reset_pos_search(self):
        self.pos_search_var.set('')
        for item in self.pos_search_tree.get_children():
            self.pos_search_tree.delete(item)

    def select_pos_product(self, event):
        selected_item = self.pos_search_tree.selection()
        if selected_item:
            item = self.pos_search_tree.item(selected_item[0])
            values = item['values']
            product_id, barcode, name, price, stock = values

            if stock <= 0:
                messagebox.showwarning("Peringatan", "Stok tidak mencukupi.")
                return

            # Check if the product is already in the cart
            for cart_item in self.cart_tree.get_children():
                cart_values = self.cart_tree.item(cart_item)['values']
                if cart_values[1] == barcode:  # Match by barcode
                    new_qty = cart_values[4] + 1
                    if new_qty > stock:
                        messagebox.showwarning("Peringatan", f"Stok tidak mencukupi. Stok tersedia: {stock}")
                        return
                    new_total = new_qty * price
                    self.cart_tree.item(cart_item, values=(cart_values[0], cart_values[1], cart_values[2], cart_values[3], new_qty, new_total))
                    self.update_totals()
                    self.pos_search_var.set('')  # Clear search field
                    messagebox.showinfo("Sukses", f"Jumlah produk '{name}' di keranjang diperbarui.")
                    return

            # Add new product to the cart
            self.cart_tree.insert('', 'end', values=(product_id, barcode, name, price, 1, price))
            self.update_totals()
            self.pos_search_var.set('')  # Clear search field
            messagebox.showinfo("Sukses", f"Produk '{name}' berhasil ditambahkan ke keranjang.")

    def setup_product_entry_frame(self, parent_frame):
        entry_frame = ttk.LabelFrame(parent_frame, text="Input Produk")
        entry_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(entry_frame, text="Barcode:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        barcode_entry = ttk.Entry(entry_frame, textvariable=self.pos_barcode_var, width=20)
        barcode_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        barcode_entry.bind("<Return>", lambda event: self.add_to_cart())
        
        ttk.Label(entry_frame, text="Jumlah:").grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(entry_frame, textvariable=self.pos_qty_var, width=5).grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        
        ttk.Button(entry_frame, text="Tambah ke Keranjang", command=self.add_to_cart).grid(row=0, column=5, padx=5, pady=5)

    def setup_cart_frame(self, parent_frame):
        cart_frame = ttk.LabelFrame(parent_frame, text="Keranjang Belanja")
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
        self.cart_tree.column("name", width=250)
        self.cart_tree.column("price", width=100)
        self.cart_tree.column("qty", width=60)
        self.cart_tree.column("total", width=100)
        
        self.cart_tree.pack(fill=tk.BOTH, expand=True)
        
        # Tombol keranjang
        cart_btn_frame = ttk.Frame(cart_frame)
        cart_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(cart_btn_frame, text="Hapus Item", command=self.remove_from_cart).pack(side=tk.LEFT, padx=5)
        ttk.Button(cart_btn_frame, text="Kosongkan Keranjang", command=self.clear_cart).pack(side=tk.LEFT, padx=5)

    def setup_payment_frame(self, parent_frame):
        payment_frame = ttk.LabelFrame(parent_frame, text="Pembayaran")
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

    def validate_numeric_input(self, P):
        if P == "" or P == ".":
            return True
        try:
            float(P)
            return True
        except ValueError:
            return False

    def generate_barcode(self):
        # Generate random 13-digit barcode
        random_barcode = ''.join(random.choices(string.digits, k=13))
        self.barcode_var.set(random_barcode)

    def on_closing(self):
        # Tutup koneksi database
        if hasattr(self, 'conn'):
            self.conn.close()
        
        # Hancurkan window utama
        self.root.destroy()

    def add_product(self):
        try:
            if not all([self.barcode_var.get(), self.product_name_var.get(), 
                       self.capital_price_var.get(), self.selling_price_var.get(), 
                       self.quantity_var.get(), self.low_stock_threshold_var.get()]):
                messagebox.showerror("Error", "Semua field harus diisi")
                return
                
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO products (
                    barcode, name, capital_price, selling_price, 
                    quantity, low_stock_threshold, date_added
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.barcode_var.get(),
                self.product_name_var.get(),
                float(self.capital_price_var.get()),
                float(self.selling_price_var.get()),
                int(self.quantity_var.get()),
                int(self.low_stock_threshold_var.get()),
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            self.conn.commit()
            
            messagebox.showinfo("Sukses", "Produk berhasil ditambahkan")
            self.clear_fields()
            self.display_products()
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Barcode sudah ada dalam database")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menambahkan produk: {str(e)}")

    def update_product(self):
        if not self.edit_id:
            messagebox.showwarning("Peringatan", "Pilih produk yang akan diupdate")
            return
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE products 
                SET barcode=?, name=?, capital_price=?, selling_price=?,
                    quantity=?, low_stock_threshold=?, last_updated=?
                WHERE id=?
            ''', (
                self.barcode_var.get(),
                self.product_name_var.get(),
                float(self.capital_price_var.get()),
                float(self.selling_price_var.get()),
                int(self.quantity_var.get()),
                int(self.low_stock_threshold_var.get()),
                datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.edit_id
            ))
            self.conn.commit()
            
            messagebox.showinfo("Sukses", "Produk berhasil diupdate")
            self.clear_fields()
            self.display_products()
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengupdate produk: {str(e)}")

    def delete_product(self):
        if not self.edit_id:
            messagebox.showwarning("Peringatan", "Pilih produk yang akan dihapus")
            return
            
        if messagebox.askyesno("Konfirmasi", "Yakin ingin menghapus produk ini?"):
            try:
                cursor = self.conn.cursor()
                cursor.execute('DELETE FROM products WHERE id=?', (self.edit_id,))
                self.conn.commit()
                
                messagebox.showinfo("Sukses", "Produk berhasil dihapus")
                self.clear_fields()
                self.display_products()
                
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menghapus produk: {str(e)}")

    def get_selected_product(self, event):
        selected_item = self.product_tree.selection()
        if selected_item:
            item = self.product_tree.item(selected_item[0])
            values = item['values']
            
            self.edit_id = values[0]
            self.barcode_var.set(values[1])
            self.product_name_var.set(values[2])
            self.capital_price_var.set(values[3])
            self.selling_price_var.set(values[4])
            self.quantity_var.set(values[5])
            self.low_stock_threshold_var.set(values[6])
            self.edit_mode = True

    def setup_reports_tab(self):
        # Variabel untuk laporan
        self.report_type_var = tk.StringVar()
        self.report_type_var.set("Penjualan Harian")
        self.date_from_var = tk.StringVar()
        self.date_to_var = tk.StringVar()
        
        # Set tanggal default ke hari ini
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.date_from_var.set(today)
        self.date_to_var.set(today)
        
        # Frame kontrol laporan
        controls_frame = ttk.LabelFrame(self.reports_frame, text="Kontrol Laporan")
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Jenis laporan
        ttk.Label(controls_frame, text="Jenis Laporan:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        report_types = ["Penjualan Harian", "Penjualan Produk", "Pergerakan Inventaris", "Stok Rendah"]
        report_combo = ttk.Combobox(controls_frame, textvariable=self.report_type_var, values=report_types, state="readonly", width=20)
        report_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Rentang tanggal
        ttk.Label(controls_frame, text="Dari Tanggal:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(controls_frame, textvariable=self.date_from_var, width=12).grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        ttk.Label(controls_frame, text="(YYYY-MM-DD)").grid(row=1, column=3, padx=5, pady=0, sticky=tk.W)
        
        ttk.Label(controls_frame, text="Sampai Tanggal:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(controls_frame, textvariable=self.date_to_var, width=12).grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)
        ttk.Label(controls_frame, text="(YYYY-MM-DD)").grid(row=1, column=5, padx=5, pady=0, sticky=tk.W)
        
        ttk.Button(controls_frame, text="Generate Laporan", command=self.generate_report).grid(row=0, column=6, padx=20, pady=5, rowspan=2)
        
        # Frame hasil laporan
        report_frame = ttk.LabelFrame(self.reports_frame, text="Hasil Laporan")
        report_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Treeview untuk laporan
        self.report_tree_frame = ttk.Frame(report_frame)
        self.report_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        report_scroll_y = ttk.Scrollbar(self.report_tree_frame)
        report_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        report_scroll_x = ttk.Scrollbar(self.report_tree_frame, orient="horizontal")
        report_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.report_tree = ttk.Treeview(self.report_tree_frame,
                                       show="headings",
                                       yscrollcommand=report_scroll_y.set,
                                       xscrollcommand=report_scroll_x.set)
        
        report_scroll_y.config(command=self.report_tree.yview)
        report_scroll_x.config(command=self.report_tree.xview)
        
        self.report_tree.pack(fill=tk.BOTH, expand=True)
        
        # Frame ringkasan laporan
        self.report_summary_frame = ttk.Frame(report_frame)
        self.report_summary_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Tombol export
        ttk.Button(report_frame, text="Export Laporan", command=self.export_report).pack(pady=10)

    def generate_report(self):
        report_type = self.report_type_var.get()
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()
        
        # Hapus kolom lama
        for col in self.report_tree["columns"]:
            self.report_tree.heading(col, text="")
        self.report_tree["columns"] = ()
        
        # Hapus data lama
        for item in self.report_tree.get_children():
            self.report_tree.delete(item)
            
        try:
            if report_type == "Penjualan Harian":
                self.generate_daily_sales_report(date_from, date_to)
            elif report_type == "Penjualan Produk":
                self.generate_product_sales_report(date_from, date_to)
            elif report_type == "Pergerakan Inventaris":
                self.generate_inventory_movement_report(date_from, date_to)
            elif report_type == "Stok Rendah":
                self.generate_low_stock_report()
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal generate laporan: {str(e)}")

    def export_report(self):
        if not self.report_tree["columns"]:
            messagebox.showwarning("Peringatan", "Tidak ada data untuk diexport")
            return
            
        try:
            # Buat folder laporan jika belum ada
            if not os.path.exists('laporan'):
                os.makedirs('laporan')
                
            filename = os.path.join('laporan', f"laporan_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
            
            with open(filename, 'w', encoding='utf-8') as f:
                # Tulis header
                headers = [self.report_tree.heading(col)["text"] for col in self.report_tree["columns"]]
                f.write("\t".join(headers) + "\n")
                
                # Tulis data
                for item in self.report_tree.get_children():
                    values = [str(value) for value in self.report_tree.item(item)["values"]]
                    f.write("\t".join(values) + "\n")
                    
            messagebox.showinfo("Sukses", f"Laporan tersimpan sebagai {filename}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal export laporan: {str(e)}")

    def clear_fields(self):
        self.barcode_var.set('')
        self.product_name_var.set('')
        self.capital_price_var.set('')
        self.selling_price_var.set('')
        self.quantity_var.set('')
        self.low_stock_threshold_var.set('3')
        self.edit_id = None
        self.edit_mode = False

    def display_products(self):
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, barcode, name, capital_price, selling_price,
                       quantity, low_stock_threshold, date_added, last_updated
                FROM products
                ORDER BY name
            ''')
            
            for row in cursor.fetchall():
                status = "Stok Rendah" if row[5] <= row[6] else "Normal"
                values = list(row) + [status]
                
                # Tambahkan tag untuk stok rendah
                tags = ('low_stock',) if status == "Stok Rendah" else ()
                
                self.product_tree.insert('', 'end', values=values, tags=tags)
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menampilkan produk: {str(e)}")
    def add_to_cart(self):
        barcode = self.pos_barcode_var.get()
        if not barcode:
            messagebox.showwarning("Peringatan", "Silakan masukkan atau scan barcode produk")
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
            
        # Tambahkan ke keranjang
        total = price * qty
        self.cart_tree.insert('', 'end', values=(product_id, barcode, name, price, qty, total))
        
        # Update total
        self.update_totals()
        
        # Reset input
        self.pos_barcode_var.set('')
        self.pos_qty_var.set('1')

    def update_totals(self):
        subtotal = sum(float(self.cart_tree.item(item)['values'][5]) for item in self.cart_tree.get_children())
        tax = subtotal * self.tax_rate  # PPN 11%
        total = subtotal + tax
        
        self.subtotal_label.config(text=f"Rp {subtotal:,.2f}")
        self.tax_label.config(text=f"Rp {tax:,.2f}")
        self.total_label.config(text=f"Rp {total:,.2f}")

    def process_payment(self):
        if not self.cart_tree.get_children():
            messagebox.showwarning("Peringatan", "Keranjang belanja kosong")
            return
            
        try:
            # Hitung total
            subtotal = sum(float(self.cart_tree.item(item)['values'][5]) for item in self.cart_tree.get_children())
            tax = subtotal * self.tax_rate
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

    def search_products(self):
        search_term = self.search_var.get()
        if not search_term:
            self.display_products()
            return
            
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, barcode, name, capital_price, selling_price,
                       quantity, low_stock_threshold, date_added, last_updated
                FROM products
                WHERE barcode LIKE ? OR name LIKE ?
                ORDER BY name
            ''', (f'%{search_term}%', f'%{search_term}%'))
            
            for row in cursor.fetchall():
                status = "Stok Rendah" if row[5] <= row[6] else "Normal"
                values = list(row) + [status]
                
                # Tambahkan tag untuk stok rendah
                tags = ('low_stock',) if status == "Stok Rendah" else ()
                
                self.product_tree.insert('', 'end', values=values, tags=tags)
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencari produk: {str(e)}")
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
    def display_low_stock(self):
        # Bersihkan treeview
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)
            
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, barcode, name, capital_price, selling_price,
                       quantity, low_stock_threshold, date_added, last_updated
                FROM products
                WHERE quantity <= low_stock_threshold
                ORDER BY name
            ''')
            
            for row in cursor.fetchall():
                status = "Stok Rendah"
                values = list(row) + [status]
                
                self.product_tree.insert('', 'end', values=values, tags=('low_stock',))
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menampilkan produk stok rendah: {str(e)}")

    def check_low_inventory(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT name, quantity, low_stock_threshold 
                FROM products 
                WHERE quantity <= low_stock_threshold
            ''')
            low_stock_items = cursor.fetchall()
            
            if low_stock_items:
                message = "Produk dengan stok rendah:\n\n"
                for item in low_stock_items:
                    message += f"- {item[0]}: {item[1]} (Batas: {item[2]})\n"
                messagebox.showwarning("Peringatan Stok Rendah", message)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memeriksa stok: {str(e)}")

# Jalankan aplikasi
if __name__ == "__main__":
    root = ThemedTk(theme="arc")  # Anda bisa mengganti theme sesuai preferensi
    app = ProductInventorySystem(root)
    root.mainloop()
