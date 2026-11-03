#!/usr/bin/env python3
"""
Seed data dummy Alfayed untuk ERPNext, per usaha (versi 3, dua situs terpisah).
Hanya langkah master, stok, rental, dan POS yang pernah dijalankan (di satu situs lokal);
pemecahan per profil di bawah ini BELUM diuji. Lihat baris [GAGAL] lalu kirim ke Claude.

Profil:
  toko    untuk situs pos.aimz.my.id (Company Priok Busana):
          cost center Toko A/B/C, gudang, item baju varian, harga, stok awal, POS Profile Toko A
  rental  untuk situs rental.aimz.my.id (Company Alfayed Transportation):
          cost center Rental Mobil, akun deposit dan pendapatan sewa, item jasa, pelanggan, invoice contoh

Cara pakai (per situs; API key dibuat di situs yang bersangkutan):
  1. Di ERPNext: User > Administrator > tab "API Access" > Generate Keys.
  2. export ERP_URL=https://pos.aimz.my.id        # atau rental.aimz.my.id; lokal: http://localhost:8080
     export ERP_KEY=<api key>
     export ERP_SECRET=<api secret>
  3. python3 seed_alfayed.py toko                 # master, stock, pos
     python3 seed_alfayed.py rental               # rental
     python3 seed_alfayed.py toko stock           # hanya satu langkah dari profilnya
     python3 seed_alfayed.py toko -y              # lewati pertanyaan konfirmasi

Skrip menampilkan nama Company situs tujuan dan meminta konfirmasi sebelum menulis data,
supaya profil toko tidak terlanjur dijalankan di situs rental atau sebaliknya.
Aman dijalankan berulang: data yang sudah ada dilewati.
Nama bawaan ERPNext yang ikut diterjemahkan setup wizard (gudang induk, grup item induk,
price list penjualan, mode pembayaran tunai) dideteksi otomatis, tidak ditulis mati.
Butuh: pip install requests
"""
import json
import os
import sys

import requests

URL = os.environ.get("ERP_URL", "http://localhost:8080").rstrip("/")
KEY = os.environ.get("ERP_KEY", "")
SECRET = os.environ.get("ERP_SECRET", "")
HEAD = {"Authorization": f"token {KEY}:{SECRET}", "Content-Type": "application/json"}

failed = []


def call(method, path, payload=None, params=None):
    r = requests.request(method, URL + path, headers=HEAD, params=params,
                         data=json.dumps(payload) if payload is not None else None, timeout=60)
    return r


def exists(doctype, name):
    return call("GET", f"/api/resource/{doctype}/{requests.utils.quote(name, safe='')}").status_code == 200


def ensure(doctype, name, data):
    """Buat dokumen bila belum ada."""
    if exists(doctype, name):
        print(f"[ADA]    {doctype}: {name}")
        return True
    r = call("POST", "/api/resource/" + doctype, data)
    if r.status_code in (200, 201):
        print(f"[BUAT]   {doctype}: {name}")
        return True
    print(f"[GAGAL]  {doctype}: {name} -> {r.status_code} {r.text[:300]}")
    failed.append(f"{doctype}: {name}")
    return False


def submit(doc):
    """Simpan dan submit dokumen baru lewat frappe.client.submit."""
    r = call("POST", "/api/method/frappe.client.submit", {"doc": doc})
    if r.status_code == 200:
        name = r.json().get("message", {}).get("name")
        print(f"[SUBMIT] {doc['doctype']}: {name}")
        return name
    print(f"[GAGAL]  submit {doc['doctype']} -> {r.status_code} {r.text[:300]}")
    failed.append(f"submit {doc['doctype']}")
    return None


def rows(doctype, filters, fields):
    """Ambil daftar dokumen sebagai list of dict."""
    r = call("GET", f"/api/resource/{doctype}", params={
        "filters": json.dumps(filters), "fields": json.dumps(fields), "limit_page_length": 1000})
    return r.json().get("data", []) if r.status_code == 200 else []


def choose(candidates, prefer):
    """Pilih nama pertama yang memuat salah satu kata di 'prefer'; jika tidak ada, ambil yang pertama."""
    for w in prefer:
        for n in candidates:
            if w.lower() in n.lower():
                return n
    return candidates[0] if candidates else None


def find_accounts():
    """Cari akun induk dan akun lain yang cocok dengan chart of accounts yang dipakai."""
    acc = rows("Account", [["company", "=", COMPANY]],
               ["name", "account_name", "is_group", "root_type", "parent_account", "account_type"])
    liab_groups = [a["name"] for a in acc if a["is_group"] and a["root_type"] == "Liability" and a["parent_account"]]
    liab_root = [a["name"] for a in acc if a["is_group"] and a["root_type"] == "Liability" and not a["parent_account"]]
    inc_groups = [a["name"] for a in acc if a["is_group"] and a["root_type"] == "Income" and a["parent_account"]]
    inc_root = [a["name"] for a in acc if a["is_group"] and a["root_type"] == "Income" and not a["parent_account"]]
    exp_leaf = [a["name"] for a in acc if not a["is_group"] and a["root_type"] == "Expense"]
    found = {
        "liab_parent": choose(liab_groups, ("current liabilities", "lancar", "jangka pendek")) or choose(liab_root, ()),
        "income_parent": choose(inc_groups, ("direct income", "pendapatan usaha", "pendapatan", "penjualan")) or choose(inc_root, ()),
        "write_off": choose(exp_leaf, ("write off", "penghapusan", "selisih", "lain")),
    }
    print("Akun terdeteksi:", found)
    return found


_cache = {}


def root_group(doctype, parent_field, filters=None):
    """Nama node akar (grup tanpa induk) sebuah tree, misalnya 'All Warehouses - AB' atau terjemahannya."""
    key = (doctype, json.dumps(filters))
    if key not in _cache:
        data = rows(doctype, [["is_group", "=", 1]] + (filters or []), ["name", parent_field])
        akar = [d["name"] for d in data if not d.get(parent_field)]
        _cache[key] = akar[0] if akar else None
        print(f"Akar {doctype}: {_cache[key]}")
    return _cache[key]


def gudang_induk():
    return root_group("Warehouse", "parent_warehouse", [["company", "=", COMPANY]])


def grup_item_induk():
    return root_group("Item Group", "parent_item_group")


def price_list_jual():
    if "pl" not in _cache:
        daftar = [x["name"] for x in rows("Price List", [["selling", "=", 1], ["enabled", "=", 1]], ["name"])]
        _cache["pl"] = choose(daftar, ("standard selling", "standar", "penjualan"))
        print("Price list penjualan:", _cache["pl"])
    return _cache["pl"]


def mode_tunai():
    if "mop" not in _cache:
        daftar = [x["name"] for x in rows("Mode of Payment", [["type", "=", "Cash"]], ["name"])]
        _cache["mop"] = choose(daftar, ("cash", "tunai"))
        print("Mode pembayaran tunai:", _cache["mop"])
    return _cache["mop"]


def get_company():
    r = call("GET", "/api/resource/Company", params={"fields": json.dumps(["name", "abbr"]), "limit_page_length": 5})
    r.raise_for_status()
    rows = r.json()["data"]
    if not rows:
        sys.exit("Belum ada Company. Selesaikan setup wizard dulu.")
    print("Company:", rows[0])
    return rows[0]["name"], rows[0]["abbr"]


COMPANY, ABBR = get_company()
ROOT_CC = f"{COMPANY} - {ABBR}"
SIZES = {"S": "S", "M": "M", "L": "L", "XL": "XL"}
COLORS = {"Hitam": "HTM", "Putih": "PTH", "Navy": "NVY"}
MODELS = [  # kode, nama, harga jual, harga pokok
    ("KMJ", "Kemeja Pria Lengan Panjang", 159000, 95000),
    ("KAOS", "Kaos Polos Cotton", 79000, 40000),
    ("GMS", "Gamis Wanita", 249000, 150000),
    ("CHN", "Celana Chino Pria", 189000, 115000),
]
STORES = ["Toko A", "Toko B", "Toko C"]


def step_master():
    print("\n== Master: cost center, gudang, item, harga ==")
    for s in STORES:
        ensure("Cost Center", f"{s} - {ABBR}", {
            "cost_center_name": s, "parent_cost_center": ROOT_CC, "company": COMPANY, "is_group": 0})

    for s in STORES:
        ensure("Warehouse", f"{s} - {ABBR}", {
            "warehouse_name": s, "company": COMPANY, "parent_warehouse": gudang_induk()})

    ensure("Item Group", "Pakaian", {"item_group_name": "Pakaian", "parent_item_group": grup_item_induk(), "is_group": 0})
    ensure("Item Attribute", "Ukuran", {
        "attribute_name": "Ukuran",
        "item_attribute_values": [{"attribute_value": v, "abbr": a} for v, a in SIZES.items()]})
    ensure("Item Attribute", "Warna", {
        "attribute_name": "Warna",
        "item_attribute_values": [{"attribute_value": v, "abbr": a} for v, a in COLORS.items()]})

    barcode = 899000000000
    for code, nama, harga, pokok in MODELS:
        ensure("Item", code, {
            "item_code": code, "item_name": nama, "item_group": "Pakaian", "stock_uom": "Nos",
            "is_stock_item": 1, "has_variants": 1, "variant_based_on": "Item Attribute",
            "attributes": [{"attribute": "Ukuran"}, {"attribute": "Warna"}]})
        for sv, sa in SIZES.items():
            for cv, ca in COLORS.items():
                barcode += 1
                vcode = f"{code}-{sa}-{ca}"
                ensure("Item", vcode, {
                    "item_code": vcode, "item_name": f"{nama} {sv} {cv}", "item_group": "Pakaian",
                    "stock_uom": "Nos", "is_stock_item": 1, "variant_of": code,
                    "valuation_rate": pokok,
                    "attributes": [{"attribute": "Ukuran", "attribute_value": sv},
                                   {"attribute": "Warna", "attribute_value": cv}],
                    "barcodes": [{"barcode": str(barcode)}]})
                r = call("GET", "/api/resource/Item Price", params={
                    "filters": json.dumps([["item_code", "=", vcode], ["price_list", "=", price_list_jual()]])})
                if not r.json().get("data"):
                    rp = call("POST", "/api/resource/Item Price", {
                        "item_code": vcode, "price_list": price_list_jual(), "price_list_rate": harga})
                    if rp.status_code not in (200, 201):
                        print(f"[GAGAL]  Item Price: {vcode} -> {rp.status_code} {rp.text[:300]}")
                        failed.append(f"Item Price: {vcode}")


def step_stock():
    print("\n== Stok awal 10 pcs per varian per toko ==")
    for s in STORES:
        wh = f"{s} - {ABBR}"
        if rows("Bin", [["item_code", "=", "KMJ-S-HTM"], ["warehouse", "=", wh], ["actual_qty", ">", 0]], ["name"]):
            print(f"[ADA]    stok awal {wh}")
            continue
        items = []
        for code, _nama, _harga, pokok in MODELS:
            for sa in SIZES.values():
                for ca in COLORS.values():
                    items.append({"item_code": f"{code}-{sa}-{ca}", "qty": 10, "basic_rate": pokok, "t_warehouse": wh})
        submit({"doctype": "Stock Entry", "stock_entry_type": "Material Receipt",
                "company": COMPANY, "to_warehouse": wh, "items": items})


def step_rental():
    print("\n== Keuangan rental: cost center, akun, item jasa, pelanggan, invoice contoh ==")
    ensure("Cost Center", f"Rental Mobil - {ABBR}", {
        "cost_center_name": "Rental Mobil", "parent_cost_center": ROOT_CC, "company": COMPANY, "is_group": 0})
    akun = find_accounts()
    if not akun["liab_parent"] or not akun["income_parent"]:
        print("[GAGAL]  Akun induk tidak ditemukan; periksa Chart of Accounts.")
        failed.append("akun induk")
        return
    ensure("Account", f"Deposit Pelanggan - {ABBR}", {
        "account_name": "Deposit Pelanggan", "company": COMPANY, "parent_account": akun["liab_parent"],
        "is_group": 0, "root_type": "Liability"})
    ensure("Account", f"Pendapatan Sewa Kendaraan - {ABBR}", {
        "account_name": "Pendapatan Sewa Kendaraan", "company": COMPANY, "parent_account": akun["income_parent"],
        "is_group": 0, "root_type": "Income"})
    ensure("Item Group", "Jasa Rental", {"item_group_name": "Jasa Rental", "parent_item_group": grup_item_induk(), "is_group": 0})
    for code, nama in [("SEWA-HARIAN", "Sewa Kendaraan per Hari"), ("SEWA-12JAM", "Sewa Kendaraan 12 Jam"),
                       ("DENDA-RENTAL", "Denda Rental")]:
        ensure("Item", code, {"item_code": code, "item_name": nama, "item_group": "Jasa Rental",
                              "stock_uom": "Nos", "is_stock_item": 0,
                              "item_defaults": [{"company": COMPANY, "income_account": f"Pendapatan Sewa Kendaraan - {ABBR}",
                                                 "selling_cost_center": f"Rental Mobil - {ABBR}"}]})
    customers = [("Pelanggan Umum", "Individual"), ("CV Maju Wisata (dummy)", "Company"), ("Budi Santoso (dummy)", "Individual")]
    cg = choose([x["name"] for x in rows("Customer Group", [["is_group", "=", 0]], ["name"])],
                ("individual", "perorangan", "commercial"))
    terr = choose([x["name"] for x in rows("Territory", [["is_group", "=", 0]], ["name"])], ("indonesia",))
    print("Customer Group:", cg, "| Territory:", terr)
    for nama, tipe in customers:
        ensure("Customer", nama, {"customer_name": nama, "customer_type": tipe,
                                  "customer_group": cg, "territory": terr})
    contoh = [("CV Maju Wisata (dummy)", "SEWA-HARIAN", 3, 2500000), ("Budi Santoso (dummy)", "SEWA-12JAM", 1, 200000),
              ("CV Maju Wisata (dummy)", "SEWA-HARIAN", 2, 1900000)]
    for i, (cust, item, qty, rate) in enumerate(contoh, 1):
        tanda = f"SEED-RENTAL-{i}"
        if rows("Sales Invoice", [["remarks", "=", tanda]], ["name"]):
            print(f"[ADA]    Sales Invoice {tanda}")
            continue
        submit({"doctype": "Sales Invoice", "customer": cust, "company": COMPANY, "remarks": tanda,
                "cost_center": f"Rental Mobil - {ABBR}",
                "items": [{"item_code": item, "qty": qty, "rate": rate, "cost_center": f"Rental Mobil - {ABBR}"}]})


def step_pos():
    print("\n== POS Profile Toko A ==")
    wo = find_accounts()["write_off"]
    if not wo:
        print("[GAGAL]  Akun write off tidak ditemukan; buat satu akun biaya lalu ulangi.")
        failed.append("akun write off")
        return
    ensure("POS Profile", "POS Toko A", {
        "name": "POS Toko A", "company": COMPANY, "warehouse": f"Toko A - {ABBR}", "currency": "IDR",
        "selling_price_list": price_list_jual(), "cost_center": f"Toko A - {ABBR}",
        "write_off_account": wo, "write_off_cost_center": f"Toko A - {ABBR}",
        "payments": [{"mode_of_payment": mode_tunai(), "default": 1}],
        "applicable_for_users": [{"user": "Administrator", "default": 1}]})


STEPS = {"master": step_master, "stock": step_stock, "rental": step_rental, "pos": step_pos}
PROFIL_LANGKAH = {"toko": ["master", "stock", "pos"], "rental": ["rental"]}

if __name__ == "__main__":
    if not KEY or not SECRET:
        sys.exit("Isi ERP_KEY dan ERP_SECRET dulu (lihat petunjuk di bagian atas file).")
    args = [a for a in sys.argv[1:] if a != "-y"]
    if not args or args[0] not in PROFIL_LANGKAH:
        sys.exit("Pakai: python3 seed_alfayed.py toko|rental [langkah ...] [-y]")
    profil = args[0]
    pilih = args[1:] or PROFIL_LANGKAH[profil]
    salah = [p for p in pilih if p not in PROFIL_LANGKAH[profil]]
    if salah:
        sys.exit(f"Langkah {salah} bukan bagian dari profil {profil}: {PROFIL_LANGKAH[profil]}")
    print(f"Situs: {URL} | Company: {COMPANY} (singkatan {ABBR}) | Profil: {profil}")
    if "-y" not in sys.argv and input("Company ini sudah benar untuk profil tersebut? Ketik y untuk lanjut: ").strip().lower() != "y":
        sys.exit("Dibatalkan.")
    for p in pilih:
        STEPS[p]()
    print("\n== Ringkasan ==")
    print("Semua langkah lancar." if not failed else f"{len(failed)} gagal:\n- " + "\n- ".join(failed))
