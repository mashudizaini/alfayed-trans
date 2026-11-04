"""Utilisasi Kendaraan: persentase waktu tiap unit tersewa dalam periode.

Waktu tersewa = bagian rentang reservasi (Dikonfirmasi, Berjalan, Selesai) yang jatuh di dalam
periode. Pendapatan = total reservasi yang mulai di dalam periode.
"""
import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, get_first_day, get_last_day, getdate, nowdate

STATUS_TERSEWA = ["Dikonfirmasi", "Berjalan", "Selesai"]


def execute(filters=None):
    filters = frappe._dict(filters or {})
    dari = getdate(filters.dari_tanggal or get_first_day(nowdate()))
    sampai = getdate(filters.sampai_tanggal or get_last_day(nowdate()))
    awal, akhir = get_datetime(dari), get_datetime(add_days(sampai, 1))
    jam_periode = (akhir - awal).total_seconds() / 3600

    f_unit = {"status": ["!=", "Nonaktif"]}
    if filters.model_kendaraan:
        f_unit["model_kendaraan"] = filters.model_kendaraan
    unit = frappe.get_list("Kendaraan", filters=f_unit, fields=["name", "model_kendaraan", "status"],
                           order_by="name asc")
    kelompok = dict(frappe.get_all("Model Kendaraan", fields=["name", "kelompok_tarif"], as_list=True))
    if filters.kelompok_tarif:
        unit = [u for u in unit if kelompok.get(u.model_kendaraan) == filters.kelompok_tarif]

    reservasi = frappe.get_all(
        "Reservasi Rental",
        filters=[
            ["status", "in", STATUS_TERSEWA],
            ["kendaraan", "is", "set"],
            ["tanggal_mulai", "<", akhir],
            ["tanggal_selesai", ">", awal],
        ],
        fields=["kendaraan", "tanggal_mulai", "tanggal_selesai", "total"],
    )
    per_unit = {}
    for r in reservasi:
        mulai, selesai = max(get_datetime(r.tanggal_mulai), awal), min(get_datetime(r.tanggal_selesai), akhir)
        p = per_unit.setdefault(r.kendaraan, frappe._dict(jumlah=0, jam=0.0, pendapatan=0.0))
        p.jumlah += 1
        p.jam += max((selesai - mulai).total_seconds() / 3600, 0)
        if awal <= get_datetime(r.tanggal_mulai) < akhir:
            p.pendapatan += flt(r.total)

    rows = []
    for u in unit:
        p = per_unit.get(u.name, frappe._dict(jumlah=0, jam=0.0, pendapatan=0.0))
        rows.append(frappe._dict(
            kendaraan=u.name, model_kendaraan=u.model_kendaraan, kelompok_tarif=kelompok.get(u.model_kendaraan),
            status=u.status, jumlah_reservasi=p.jumlah, jam=p.jam, hari_tersewa=round(p.jam / 24, 1),
            utilisasi=round(100 * p.jam / jam_periode, 1) if jam_periode else 0, pendapatan=p.pendapatan))
    rows.sort(key=lambda r: r.utilisasi, reverse=True)
    return kolom(), rows, None, grafik(rows), ringkasan(rows, jam_periode)


def kolom():
    return [
        {"fieldname": "kendaraan", "label": _("Kendaraan"), "fieldtype": "Link", "options": "Kendaraan", "width": 120},
        {"fieldname": "model_kendaraan", "label": _("Model"), "fieldtype": "Link", "options": "Model Kendaraan", "width": 200},
        {"fieldname": "kelompok_tarif", "label": _("Kelompok Tarif"), "fieldtype": "Data", "width": 130},
        {"fieldname": "status", "label": _("Status Unit"), "fieldtype": "Data", "width": 100},
        {"fieldname": "jumlah_reservasi", "label": _("Jumlah Reservasi"), "fieldtype": "Int", "width": 130},
        {"fieldname": "hari_tersewa", "label": _("Hari Tersewa"), "fieldtype": "Float", "precision": 1, "width": 110},
        {"fieldname": "utilisasi", "label": _("Utilisasi (%)"), "fieldtype": "Percent", "width": 110},
        {"fieldname": "pendapatan", "label": _("Pendapatan"), "fieldtype": "Currency", "width": 140},
    ]


def grafik(rows):
    teratas = [r for r in rows if r.utilisasi][:15]
    if not teratas:
        return None
    return {
        "data": {"labels": [r.kendaraan for r in teratas],
                 "datasets": [{"name": _("Utilisasi (%)"), "values": [r.utilisasi for r in teratas]}]},
        "type": "bar",
    }


def ringkasan(rows, jam_periode):
    total_jam_unit = jam_periode * len(rows)
    jam_tersewa = sum(r.jam for r in rows)
    return [
        {"value": len(rows), "label": _("Jumlah Unit"), "datatype": "Int", "indicator": "Blue"},
        {"value": round(100 * jam_tersewa / total_jam_unit, 1) if total_jam_unit else 0,
         "label": _("Utilisasi Rata-rata (%)"), "datatype": "Percent", "indicator": "Green"},
        {"value": sum(1 for r in rows if not r.jumlah_reservasi), "label": _("Unit Tanpa Sewa"),
         "datatype": "Int", "indicator": "Orange"},
    ]
