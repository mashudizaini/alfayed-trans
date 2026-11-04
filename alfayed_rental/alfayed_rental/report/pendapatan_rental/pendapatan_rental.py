"""Pendapatan Rental per bulan, dikelompokkan per kelompok tarif, model, atau kendaraan.

Basis: reservasi yang sudah dikonfirmasi (Dikonfirmasi, Berjalan, Selesai), dibukukan ke bulan
tanggal mulai sewa. Angka ini laporan operasional; laporan resmi tetap Laba Rugi ERPNext
dengan cost center Rental Mobil.
"""
from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_first_day, getdate, add_days, add_months, nowdate

STATUS_PENDAPATAN = ["Dikonfirmasi", "Berjalan", "Selesai"]
KELOMPOK = {"Kelompok Tarif": "kelompok_tarif", "Model": "model_kendaraan", "Kendaraan": "kendaraan"}


def execute(filters=None):
    filters = frappe._dict(filters or {})
    dari = getdate(filters.dari_tanggal or add_months(get_first_day(nowdate()), -5))
    sampai = getdate(filters.sampai_tanggal or nowdate())
    field = KELOMPOK.get(filters.kelompokkan_per or "Kelompok Tarif", "kelompok_tarif")

    reservasi = frappe.get_list(
        "Reservasi Rental",
        filters=[
            ["status", "in", STATUS_PENDAPATAN],
            ["tanggal_mulai", ">=", dari],
            ["tanggal_mulai", "<", add_days(sampai, 1)],
        ],
        fields=["name", "tanggal_mulai", "total", "total_biaya_tambahan", "kelompok_tarif",
                "model_kendaraan", "kendaraan"],
    )
    denda = {}
    if reservasi:
        for d in frappe.get_all(
            "Denda Rental",
            filters={"reservasi": ["in", [r.name for r in reservasi]]},
            fields=["reservasi", "jumlah"],
        ):
            denda[d.reservasi] = denda.get(d.reservasi, 0) + flt(d.jumlah)

    data = OrderedDict()
    for r in sorted(reservasi, key=lambda x: x.tanggal_mulai):
        bulan = getdate(r.tanggal_mulai).replace(day=1)
        kunci = (bulan, r.get(field) or _("(kosong)"))
        b = data.setdefault(kunci, frappe._dict(
            bulan=formatdate(bulan, "MMM yyyy"), kelompok=kunci[1], jumlah_reservasi=0,
            sewa=0, biaya_tambahan=0, denda=0, total=0))
        b.jumlah_reservasi += 1
        b.biaya_tambahan += flt(r.total_biaya_tambahan)
        b.sewa += flt(r.total) - flt(r.total_biaya_tambahan)
        b.denda += denda.get(r.name, 0)
        b.total = b.sewa + b.biaya_tambahan + b.denda

    rows = list(data.values())
    return kolom(filters.kelompokkan_per or "Kelompok Tarif"), rows, None, grafik(rows), ringkasan(rows)


def kolom(label_kelompok):
    return [
        {"fieldname": "bulan", "label": _("Bulan"), "fieldtype": "Data", "width": 100},
        {"fieldname": "kelompok", "label": _(label_kelompok), "fieldtype": "Data", "width": 200},
        {"fieldname": "jumlah_reservasi", "label": _("Jumlah Reservasi"), "fieldtype": "Int", "width": 130},
        {"fieldname": "sewa", "label": _("Sewa"), "fieldtype": "Currency", "width": 140},
        {"fieldname": "biaya_tambahan", "label": _("Biaya Tambahan"), "fieldtype": "Currency", "width": 130},
        {"fieldname": "denda", "label": _("Denda"), "fieldtype": "Currency", "width": 120},
        {"fieldname": "total", "label": _("Total"), "fieldtype": "Currency", "width": 140},
    ]


def grafik(rows):
    per_bulan = OrderedDict()
    for r in rows:
        per_bulan[r.bulan] = per_bulan.get(r.bulan, 0) + r.total
    if not per_bulan:
        return None
    return {
        "data": {"labels": list(per_bulan), "datasets": [{"name": _("Total"), "values": list(per_bulan.values())}]},
        "type": "bar",
        "fieldtype": "Currency",
    }


def ringkasan(rows):
    return [
        {"value": sum(r.jumlah_reservasi for r in rows), "label": _("Jumlah Reservasi"), "datatype": "Int", "indicator": "Blue"},
        {"value": sum(r.sewa for r in rows), "label": _("Sewa"), "datatype": "Currency", "indicator": "Green"},
        {"value": sum(r.denda for r in rows), "label": _("Denda"), "datatype": "Currency", "indicator": "Orange"},
        {"value": sum(r.total for r in rows), "label": _("Total Pendapatan"), "datatype": "Currency", "indicator": "Green"},
    ]
