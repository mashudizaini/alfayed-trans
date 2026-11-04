"""Laporan Reservasi: daftar booking per periode beserta status pembayaran invoicenya."""
import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, get_last_day, getdate, nowdate


def execute(filters=None):
    filters = frappe._dict(filters or {})
    dari = getdate(filters.dari_tanggal or get_first_day(nowdate()))
    sampai = getdate(filters.sampai_tanggal or get_last_day(nowdate()))
    data = ambil_data(filters, dari, sampai)
    return kolom(), data, None, None, ringkasan(data)


def kolom():
    def k(fieldname, label, fieldtype="Data", width=120, options=None):
        return {"fieldname": fieldname, "label": _(label), "fieldtype": fieldtype, "width": width, "options": options}

    return [
        k("name", "Reservasi", "Link", 140, "Reservasi Rental"),
        k("status", "Status", width=150),
        k("sumber", "Sumber", width=90),
        k("nama_pemesan", "Pemesan", width=160),
        k("no_whatsapp", "WhatsApp", width=120),
        k("kendaraan", "Kendaraan", "Link", 110, "Kendaraan"),
        k("model_kendaraan", "Model", "Link", 170, "Model Kendaraan"),
        k("jenis_sewa", "Jenis Sewa", width=95),
        k("dengan_driver", "Driver", "Check", 60),
        k("tujuan", "Tujuan", width=120),
        k("tanggal_mulai", "Mulai", "Datetime", 150),
        k("tanggal_selesai", "Selesai", "Datetime", 150),
        k("total", "Total", "Currency", 120),
        k("uang_muka", "Uang Muka", "Currency", 110),
        k("terbayar", "Terbayar", "Currency", 110),
        k("belum_dibayar", "Belum Dibayar", "Currency", 120),
        k("sales_invoice", "Sales Invoice", "Link", 150, "Sales Invoice"),
        k("status_invoice", "Status Invoice", width=110),
        k("deposit", "Deposit", "Link", 110, "Deposit Rental"),
    ]


def ambil_data(filters, dari, sampai):
    # Reservasi yang rentang sewanya bersinggungan dengan periode laporan.
    kondisi = [
        ["tanggal_mulai", "<", add_days(sampai, 1)],
        ["tanggal_selesai", ">=", dari],
    ]
    for f in ("status", "kendaraan", "kelompok_tarif", "sumber"):
        if filters.get(f):
            kondisi.append([f, "=", filters.get(f)])
    if not filters.get("status") and not filters.get("termasuk_batal"):
        kondisi.append(["status", "!=", "Batal"])

    baris = frappe.get_list(
        "Reservasi Rental",
        filters=kondisi,
        fields=[
            "name", "status", "sumber", "nama_pemesan", "no_whatsapp", "kendaraan", "model_kendaraan",
            "jenis_sewa", "dengan_driver", "tujuan", "tanggal_mulai", "tanggal_selesai", "total",
            "uang_muka", "sales_invoice", "deposit",
        ],
        order_by="tanggal_mulai asc",
    )

    invoice = {}
    nama_si = [r.sales_invoice for r in baris if r.sales_invoice]
    if nama_si:
        for si in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", nama_si]},
            fields=["name", "status", "grand_total", "outstanding_amount", "docstatus"],
        ):
            invoice[si.name] = si

    for r in baris:
        si = invoice.get(r.sales_invoice)
        if si and si.docstatus == 1:
            r.status_invoice = si.status
            r.belum_dibayar = flt(si.outstanding_amount)
            r.terbayar = flt(si.grand_total) - r.belum_dibayar
        else:
            r.status_invoice = "Draft" if si else ""
            r.belum_dibayar = flt(r.total)
            r.terbayar = 0
    return baris


def ringkasan(data):
    aktif = [r for r in data if r.status != "Batal"]
    return [
        {"value": len(aktif), "label": _("Jumlah Reservasi"), "datatype": "Int", "indicator": "Blue"},
        {"value": sum(flt(r.total) for r in aktif), "label": _("Nilai Sewa"), "datatype": "Currency", "indicator": "Green"},
        {"value": sum(flt(r.terbayar) for r in aktif), "label": _("Sudah Dibayar"), "datatype": "Currency", "indicator": "Green"},
        {"value": sum(flt(r.belum_dibayar) for r in aktif), "label": _("Belum Dibayar"), "datatype": "Currency", "indicator": "Orange"},
    ]
