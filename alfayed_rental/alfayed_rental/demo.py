"""Data transaksi DEMO untuk situs rental, agar laporan dan dashboard terisi.

Hanya untuk situs uji. Semua data diberi tanda "DEMO" (catatan reservasi, remarks invoice/payment,
user_remark jurnal) dan pelanggan bertanda "(demo)".

    bench --site rental.aimz.my.id execute alfayed_rental.alfayed_rental.demo.buat_data_demo
    bench --site rental.aimz.my.id execute alfayed_rental.alfayed_rental.demo.hapus_data_demo

Yang dibuat (deterministik, seed acak tetap):
- Setoran modal awal dan biaya operasional bulanan (BBM, servis, gaji driver) lewat Journal Entry.
- Reservasi 1 Agustus 2026 sampai sekitar 6 minggu ke depan, melewati alur status sungguhan:
  selesai (invoice submit, DP dan pelunasan, sebagian deposit dan denda), sedang berjalan,
  dikonfirmasi ke depan, menunggu pembayaran, permintaan, dan beberapa batal.
Tanggal dokumen akuntansi mengikuti tanggal kejadian (bukan tanggal skrip dijalankan).
"""
import random
from datetime import datetime, time, timedelta

import frappe
from frappe.utils import add_days, flt, getdate, now_datetime

from alfayed_rental.alfayed_rental import akuntansi

TANDA = "DEMO"
MULAI_DEMO = datetime(2026, 8, 1)
NAMA = [
    "Agus Setiawan", "Siti Rahma", "Budi Hartono", "Dewi Lestari", "Rizky Pratama", "Nur Aini", "Hendra Wijaya",
    "Fitri Handayani", "Joko Susilo", "Maya Sari", "Andi Saputra", "Rina Kurniawati", "Teguh Santoso",
    "Lina Marlina", "Fajar Nugroho", "Yuni Astuti", "Dodi Firmansyah", "Ratna Dewi", "Eko Prasetyo", "Wulan Sari",
    "PT Sinar Wisata", "SMK Negeri 1 Wonosobo", "Kelompok Arisan Kalianget", "CV Dieng Tour",
    "Paguyuban Ojek Wisata", "Keluarga Pak Darto",
]
SUMBER = ["WhatsApp"] * 6 + ["Website"] * 2 + ["Telepon", "Langsung"]
JAM_SATUAN = {"12 Jam": 12, "14 Jam": 14}


def _company():
    return akuntansi._company()


def _akun_kas(company):
    akun = frappe.get_cached_value("Company", company, "default_cash_account")
    return akun or frappe.db.get_value("Account", {"company": company, "account_type": "Cash", "is_group": 0}, "name")


def _pada_tanggal(tanggal):
    """Paksa akuntansi.nowdate() mengembalikan tanggal kejadian selama dokumen dibuat."""
    akuntansi.nowdate = lambda: getdate(tanggal).isoformat()


def _kembalikan_tanggal():
    from frappe.utils import nowdate
    akuntansi.nowdate = nowdate


def _jurnal(company, tanggal, debit, kredit, jumlah, keterangan, cc=None):
    je = frappe.get_doc({
        "doctype": "Journal Entry", "voucher_type": "Journal Entry", "company": company,
        "posting_date": tanggal, "user_remark": f"{TANDA}: {keterangan}",
        "accounts": [
            {"account": debit, "debit_in_account_currency": jumlah, "cost_center": cc},
            {"account": kredit, "credit_in_account_currency": jumlah, "cost_center": cc},
        ],
    })
    je.insert(ignore_permissions=True)
    je.submit()
    return je.name


def _akun_biaya(company, nama):
    """Akun beban bertanda nama (dibuat bila belum ada) di bawah grup beban langsung."""
    ada = frappe.db.get_value("Account", {"company": company, "account_name": nama, "is_group": 0}, "name")
    if ada:
        return ada
    grup = frappe.get_all("Account", filters={"company": company, "is_group": 1, "root_type": "Expense"},
                          fields=["name", "parent_account"], order_by="lft asc")
    induk = next((g.name for g in grup if g.parent_account and any(
        k in g.name.lower() for k in ("langsung", "direct", "pokok", "operasional"))), None)
    induk = induk or next((g.name for g in grup if g.parent_account), grup[0].name)
    return frappe.get_doc({"doctype": "Account", "account_name": nama, "company": company,
                           "parent_account": induk, "is_group": 0, "root_type": "Expense"}).insert(
        ignore_permissions=True).name


def _akun_modal(company):
    return frappe.db.get_value("Account", {"company": company, "root_type": "Equity", "is_group": 0}, "name")


def _bayar(si_name, jumlah, tanggal, keterangan):
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

    si = frappe.get_doc("Sales Invoice", si_name)
    jumlah = min(flt(jumlah), flt(si.outstanding_amount))
    if jumlah <= 0:
        return None
    pe = get_payment_entry("Sales Invoice", si_name, party_amount=jumlah, bank_account=_akun_kas(si.company))
    pe.posting_date = tanggal
    pe.reference_date = tanggal
    pe.reference_no = keterangan
    pe.mode_of_payment = "Cash" if frappe.db.exists("Mode of Payment", "Cash") else pe.mode_of_payment
    pe.remarks = f"{TANDA}: {keterangan}"
    pe.paid_amount = pe.received_amount = jumlah
    for ref in pe.references:
        ref.allocated_amount = jumlah
    pe.insert(ignore_permissions=True)
    pe.submit()
    return pe.name


def _submit_invoice(nama, tanggal):
    """Submit invoice draft dengan tanggal kejadian (ERPNext mengisi tanggal hari ini pada draft)."""
    if not nama:
        return
    si = frappe.get_doc("Sales Invoice", nama)
    if si.docstatus == 0:
        si.remarks = f"{TANDA}: {si.remarks or ''}"
        si.set_posting_time = 1
        si.posting_date = si.due_date = getdate(tanggal)
        for jadwal in si.get("payment_schedule") or []:
            jadwal.due_date = si.posting_date
        si.flags.ignore_permissions = True
        si.submit()


def _pilihan_tarif(unit):
    """Daftar (tarif, unit) yang bisa dipakai unit ini."""
    model = unit.model_kendaraan
    kelompok = frappe.db.get_value("Model Kendaraan", model, "kelompok_tarif")
    return frappe.get_all(
        "Tarif Rental",
        filters={"aktif": 1},
        or_filters=[["model_kendaraan", "=", model], ["kelompok_tarif", "=", kelompok]],
        fields=["name", "jenis_sewa", "dengan_driver", "tujuan", "harga", "model_kendaraan"],
    )


def _durasi(t, rnd):
    if t.jenis_sewa in JAM_SATUAN:
        return timedelta(hours=JAM_SATUAN[t.jenis_sewa])
    if t.jenis_sewa == "Per Tujuan":
        return timedelta(hours=rnd.choice([12, 14, 16]))
    return timedelta(days=rnd.choice([1, 1, 1, 2, 2, 3]))


def _rencana(rnd, akhir):
    """Susun jadwal tanpa bentrok: [(unit, tarif, mulai, selesai)]."""
    unit = frappe.get_all("Kendaraan", filters={"status": ["!=", "Nonaktif"]}, fields=["name", "model_kendaraan"])
    rencana = []
    for u in unit:
        pilihan = _pilihan_tarif(u)
        if not pilihan:
            continue
        laku = rnd.uniform(0.10, 0.30)  # tingkat okupansi per unit
        hari = MULAI_DEMO
        while hari < akhir:
            if rnd.random() < laku:
                t = rnd.choice(pilihan)
                jam_mulai = rnd.choice([6, 7, 8, 9, 10, 13])
                mulai = datetime.combine(hari.date(), time(jam_mulai))
                selesai = mulai + _durasi(t, rnd)
                rencana.append((u, t, mulai, selesai))
                hari = datetime.combine(selesai.date(), time()) + timedelta(days=rnd.choice([1, 2, 3, 4]))
            else:
                hari += timedelta(days=1)
    rencana.sort(key=lambda r: r[2])
    return rencana


def buat_data_demo():
    if frappe.db.exists("Reservasi Rental", {"catatan": ["like", f"{TANDA}%"]}):
        print("Data DEMO sudah ada. Jalankan hapus_data_demo dulu bila ingin membuat ulang.")
        return
    rnd = random.Random(2026)
    company = _company()
    cc = akuntansi._cost_center(company)
    kas = _akun_kas(company)
    sekarang = now_datetime()
    akhir = sekarang + timedelta(days=42)

    # Modal awal dan biaya operasional bulanan.
    modal = _akun_modal(company)
    if modal:
        _jurnal(company, MULAI_DEMO.date(), kas, modal, 50_000_000, "Setoran modal awal rental", cc)
    biaya = {
        "Biaya BBM Operasional": (2_500_000, 4_000_000),
        "Biaya Servis Kendaraan": (1_500_000, 3_500_000),
        "Gaji Driver": (9_000_000, 9_000_000),
    }
    bulan = MULAI_DEMO.date()
    while bulan <= sekarang.date():
        for nama, (bawah, atas) in biaya.items():
            tgl = min(bulan.replace(day=25), sekarang.date())
            if tgl < bulan:
                continue
            _jurnal(company, tgl, _akun_biaya(company, nama), kas, round(rnd.uniform(bawah, atas), -4),
                    f"{nama} {tgl.strftime('%B %Y')}", cc)
        bulan = (bulan.replace(day=28) + timedelta(days=4)).replace(day=1)
    frappe.db.commit()

    jumlah = {"Selesai": 0, "Berjalan": 0, "Dikonfirmasi": 0, "Menunggu Pembayaran": 0, "Permintaan": 0, "Batal": 0}
    for n, (u, t, mulai, selesai) in enumerate(_rencana(rnd, akhir), 1):
        try:
            status = _buat_satu(rnd, company, kas, u, t, mulai, selesai, sekarang)
            jumlah[status] += 1
            frappe.db.commit()
        except Exception as e:
            frappe.db.rollback()
            print(f"[LEWAT] {u.name} {mulai:%Y-%m-%d}: {str(e)[:160]}")
        finally:
            _kembalikan_tanggal()
        if n % 20 == 0:
            print(f"... {n} reservasi diproses")
    frappe.db.commit()
    print("Selesai. Reservasi DEMO per status:", jumlah)


def _buat_satu(rnd, company, kas, u, t, mulai, selesai, sekarang):
    pemesan = f"{rnd.choice(NAMA)} (demo)"
    konfirmasi = mulai - timedelta(days=rnd.choice([1, 2, 3, 5, 7]))
    doc = frappe.get_doc({
        "doctype": "Reservasi Rental", "status": "Permintaan", "sumber": rnd.choice(SUMBER),
        "nama_pemesan": pemesan, "no_whatsapp": f"0812{rnd.randint(10000000, 99999999)}",
        "jenis_sewa": t.jenis_sewa, "dengan_driver": t.dengan_driver, "tujuan": t.tujuan,
        "tanggal_mulai": mulai, "tanggal_selesai": selesai, "kendaraan": u.name,
        "jumlah_penumpang": rnd.randint(2, 7), "lokasi_jemput": "Wonosobo",
        "jaminan": "" if t.dengan_driver else "KTP + STNK motor", "catatan": f"{TANDA}: data contoh",
    })
    if t.dengan_driver and rnd.random() < 0.5:
        doc.append("biaya_tambahan", {"jenis": "Tol", "keterangan": "Tol perjalanan", "jumlah": rnd.choice([50000, 85000, 120000])})
        doc.append("biaya_tambahan", {"jenis": "Parkir", "keterangan": "Parkir wisata", "jumlah": rnd.choice([20000, 30000])})
    doc.insert(ignore_permissions=True)

    masa_depan = mulai > sekarang
    if masa_depan and rnd.random() < 0.15:
        return "Permintaan"

    doc.status = "Menunggu Pembayaran"
    doc.save(ignore_permissions=True)
    if rnd.random() < 0.06:
        doc.status = "Batal"
        doc.save(ignore_permissions=True)
        return "Batal"
    if masa_depan and rnd.random() < 0.2:
        return "Menunggu Pembayaran"

    # Dikonfirmasi: customer dan invoice dibuat oleh app pada tanggal konfirmasi.
    tgl_konf = min(konfirmasi, sekarang).date()
    _pada_tanggal(tgl_konf)
    doc.status = "Dikonfirmasi"
    doc.save(ignore_permissions=True)
    doc.reload()
    _submit_invoice(doc.sales_invoice, tgl_konf)
    _bayar(doc.sales_invoice, doc.uang_muka, tgl_konf, f"DP {doc.name}")

    deposit = None
    if not t.dengan_driver and rnd.random() < 0.35 and mulai <= sekarang:
        _pada_tanggal(mulai.date())
        deposit = frappe.get_doc({
            "doctype": "Deposit Rental", "reservasi": doc.name, "jumlah": 500000, "akun_pembayaran": kas,
            "tanggal_terima": mulai.date(), "keterangan": f"{TANDA}: deposit tunai",
        }).insert(ignore_permissions=True)

    if mulai > sekarang:
        return "Dikonfirmasi"

    doc.reload()
    doc.status = "Berjalan"
    doc.save(ignore_permissions=True)
    if selesai > sekarang:
        return "Berjalan"

    # Selesai: denda dibuat sebelum status Selesai agar ikut ditagih.
    _pada_tanggal(selesai.date())
    denda = None
    if rnd.random() < 0.15:
        dipotong = bool(deposit) and rnd.random() < 0.6
        denda = frappe.get_doc({
            "doctype": "Denda Rental", "reservasi": doc.name,
            "jenis": rnd.choice(["Keterlambatan", "Keterlambatan", "BBM Kurang", "Kerusakan"]),
            "jumlah": rnd.choice([50000, 75000, 100000, 150000]),
            "status": "Dipotong dari Deposit" if dipotong else "Ditagih",
            "keterangan": f"{TANDA}: contoh denda",
        }).insert(ignore_permissions=True)
    doc.reload()
    doc.status = "Selesai"
    doc.save(ignore_permissions=True)
    _bayar(doc.sales_invoice, doc.sisa_pembayaran, selesai.date(), f"Pelunasan {doc.name}")

    if denda and denda.status == "Ditagih":
        denda.reload()
        _submit_invoice(denda.sales_invoice, selesai.date())
        _bayar(denda.sales_invoice, denda.jumlah, selesai.date(), f"Denda {doc.name}")
    if deposit:
        deposit.reload()
        if denda and denda.status == "Dipotong dari Deposit":
            deposit.status, deposit.potongan = "Dipotong", denda.jumlah
        else:
            deposit.status = "Dikembalikan"
        deposit.save(ignore_permissions=True)
    return "Selesai"


def hapus_data_demo():
    """Batalkan dan hapus semua dokumen bertanda DEMO di situs ini."""
    def batal_hapus(doctype, filters):
        n = 0
        for nama in frappe.get_all(doctype, filters=filters, pluck="name", order_by="creation desc"):
            doc = frappe.get_doc(doctype, nama)
            if doc.docstatus == 1:
                doc.flags.ignore_links = True
                doc.cancel()
            frappe.delete_doc(doctype, nama, force=True, ignore_permissions=True)
            n += 1
        print(f"{doctype}: {n} dihapus")

    batal_hapus("Payment Entry", {"remarks": ["like", f"{TANDA}%"]})
    reservasi = frappe.get_all("Reservasi Rental", filters={"catatan": ["like", f"{TANDA}%"]}, pluck="name")
    jurnal_deposit = []
    for d in frappe.get_all("Deposit Rental", filters={"reservasi": ["in", reservasi or [""]]},
                            fields=["jurnal_terima", "jurnal_selesai"]):
        jurnal_deposit += [j for j in (d.jurnal_selesai, d.jurnal_terima) if j]
    for dt in ("Deposit Rental", "Denda Rental"):
        for nama in frappe.get_all(dt, filters={"reservasi": ["in", reservasi or [""]]}, pluck="name"):
            frappe.db.set_value(dt, nama, {"jurnal_terima": None, "jurnal_selesai": None} if dt == "Deposit Rental"
                                else {"sales_invoice": None})
            frappe.delete_doc(dt, nama, force=True, ignore_permissions=True)
    for nama in reservasi:
        frappe.db.set_value("Reservasi Rental", nama, {"sales_invoice": None, "deposit": None})
    batal_hapus("Sales Invoice", {"remarks": ["like", f"%Reservasi%"], "customer": ["like", "%(demo)%"]})
    batal_hapus("Sales Invoice", {"remarks": ["like", f"%Denda reservasi%"], "customer": ["like", "%(demo)%"]})
    batal_hapus("Journal Entry", {"user_remark": ["like", f"{TANDA}%"]})
    batal_hapus("Journal Entry", {"name": ["in", jurnal_deposit or [""]]})
    for nama in reservasi:
        frappe.delete_doc("Reservasi Rental", nama, force=True, ignore_permissions=True)
    print(f"Reservasi Rental: {len(reservasi)} dihapus")
    for nama in frappe.get_all("Customer", filters={"customer_name": ["like", "%(demo)%"]}, pluck="name"):
        try:
            frappe.delete_doc("Customer", nama, force=True, ignore_permissions=True)
        except Exception:
            pass
    frappe.db.commit()
    print("Data DEMO dihapus.")
