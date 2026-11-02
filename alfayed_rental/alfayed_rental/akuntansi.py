"""Penghubung ke modul akuntansi ERPNext: Sales Invoice, Journal Entry deposit, Customer."""
import frappe
from frappe import _
from frappe.utils import flt, nowdate

from alfayed_rental.alfayed_rental.tarif import nilai_pengaturan


def _company():
    return frappe.db.get_single_value("Global Defaults", "default_company") or frappe.defaults.get_user_default("Company")


def _cost_center(company):
    return frappe.db.get_value("Cost Center", {"cost_center_name": "Rental Mobil", "company": company})


def _akun(field, nama_akun, company):
    """Akun dari Pengaturan Rental; bila kosong cari berdasarkan nama akun."""
    akun = nilai_pengaturan(field, None) or frappe.db.get_value("Account", {"account_name": nama_akun, "company": company})
    if not akun:
        frappe.throw(_("Akun {0} tidak ditemukan. Isi di Pengaturan Rental.").format(nama_akun))
    return akun


def pastikan_item(kode, nama):
    if frappe.db.exists("Item", kode):
        return kode
    grup = "Jasa Rental" if frappe.db.exists("Item Group", "Jasa Rental") else "All Item Groups"
    frappe.get_doc({
        "doctype": "Item", "item_code": kode, "item_name": nama, "item_group": grup,
        "stock_uom": "Nos", "is_stock_item": 0,
    }).insert(ignore_permissions=True)
    return kode


def pastikan_customer(nama):
    """Buat Customer perorangan dari nama pemesan; grup dan wilayah dipilih dari yang bukan grup induk."""
    grup = frappe.get_all("Customer Group", filters={"is_group": 0}, pluck="name")
    wilayah = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name")
    if not grup or not wilayah:
        frappe.throw(_("Customer Group atau Territory (bukan grup induk) belum ada."))
    pilih = lambda daftar, kata: next((n for n in daftar if kata in n.lower()), daftar[0])
    cust = frappe.get_doc({
        "doctype": "Customer", "customer_name": nama, "customer_type": "Individual",
        "customer_group": pilih(grup, "individual"), "territory": pilih(wilayah, "indonesia"),
    })
    cust.insert(ignore_permissions=True)
    return cust.name


def _buat_invoice(customer, company, cost_center, baris, catatan):
    si = frappe.get_doc({
        "doctype": "Sales Invoice", "customer": customer, "company": company, "posting_date": nowdate(),
        "cost_center": cost_center, "remarks": catatan, "items": baris,
    })
    si.insert(ignore_permissions=True)
    if int(nilai_pengaturan("submit_invoice_otomatis", 0)):
        si.submit()
    return si.name


def buat_sales_invoice(rsv):
    """Invoice sewa dari reservasi: satu baris sewa ditambah satu baris per biaya tambahan."""
    company = _company()
    cc = _cost_center(company)
    per_jam = rsv.jenis_sewa in ("12 Jam", "14 Jam")
    kode = nilai_pengaturan("item_sewa_jam", "SEWA-12JAM") if per_jam else nilai_pengaturan("item_sewa_harian", "SEWA-HARIAN")
    pastikan_item(kode, kode)
    unit = rsv.kendaraan or rsv.model_kendaraan or rsv.kelompok_tarif or ""
    baris = [{
        "item_code": kode, "qty": rsv.jumlah_satuan, "rate": rsv.harga_dasar, "cost_center": cc,
        "description": f"Sewa {unit} ({rsv.jenis_sewa}) {rsv.tanggal_mulai} s/d {rsv.tanggal_selesai}",
    }]
    if rsv.biaya_tambahan:
        titipan = nilai_pengaturan("item_biaya_titipan", "BIAYA-TITIPAN")
        pastikan_item(titipan, "Biaya Titipan Rental")
        for b in rsv.biaya_tambahan:
            baris.append({
                "item_code": titipan, "qty": 1, "rate": b.jumlah, "cost_center": cc,
                "description": f"{b.jenis}: {b.keterangan or ''}".strip(": "),
            })
    return _buat_invoice(rsv.customer, company, cc, baris, f"Reservasi {rsv.name}")


def buat_invoice_denda(rsv):
    """Satu invoice untuk semua denda berstatus Ditagih yang belum punya invoice."""
    denda = frappe.get_all(
        "Denda Rental", filters={"reservasi": rsv.name, "status": "Ditagih", "sales_invoice": ["is", "not set"]},
        fields=["name", "jenis", "jumlah", "keterangan"],
    )
    if not denda:
        return None
    company = _company()
    cc = _cost_center(company)
    kode = nilai_pengaturan("item_denda", "DENDA-RENTAL")
    pastikan_item(kode, "Denda Rental")
    baris = [{
        "item_code": kode, "qty": 1, "rate": d.jumlah, "cost_center": cc,
        "description": f"{d.jenis}: {d.keterangan or ''}".strip(": "),
    } for d in denda]
    nama = _buat_invoice(rsv.customer, company, cc, baris, f"Denda reservasi {rsv.name}")
    for d in denda:
        frappe.db.set_value("Denda Rental", d.name, "sales_invoice", nama)
    return nama


def _jurnal(company, tanggal, baris, catatan):
    je = frappe.get_doc({
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": company,
        "posting_date": tanggal, "user_remark": catatan, "accounts": baris,
    })
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


def jurnal_terima(dep):
    """Deposit diterima: debit kas atau bank, kredit akun deposit (kewajiban)."""
    company = _company()
    cc = _cost_center(company)
    akun_deposit = _akun("akun_deposit", "Deposit Pelanggan", company)
    return _jurnal(company, dep.tanggal_terima or nowdate(), [
        {"account": dep.akun_pembayaran, "debit_in_account_currency": flt(dep.jumlah), "cost_center": cc},
        {"account": akun_deposit, "credit_in_account_currency": flt(dep.jumlah), "cost_center": cc},
    ], f"Deposit {dep.name} diterima, reservasi {dep.reservasi}")


def jurnal_selesai(dep):
    """Deposit diselesaikan: kewajiban dihapus; sisanya dikembalikan, potongan jadi pendapatan."""
    company = _company()
    cc = _cost_center(company)
    akun_deposit = _akun("akun_deposit", "Deposit Pelanggan", company)
    potongan = flt(dep.potongan)
    kembali = flt(dep.jumlah) - potongan
    baris = [{"account": akun_deposit, "debit_in_account_currency": flt(dep.jumlah), "cost_center": cc}]
    if kembali > 0:
        baris.append({"account": dep.akun_pembayaran, "credit_in_account_currency": kembali, "cost_center": cc})
    if potongan > 0:
        akun_denda = _akun("akun_pendapatan_denda", "Pendapatan Sewa Kendaraan", company)
        baris.append({"account": akun_denda, "credit_in_account_currency": potongan, "cost_center": cc})
    return _jurnal(company, nowdate(), baris, f"Deposit {dep.name} diselesaikan ({dep.status}), reservasi {dep.reservasi}")
