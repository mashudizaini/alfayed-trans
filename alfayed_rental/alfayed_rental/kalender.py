"""Sumber data Kalender Reservasi."""
import frappe
from frappe.desk.calendar import get_events as frappe_get_events


@frappe.whitelist()
def get_events(doctype, start, end, field_map, filters=None, fields=None, order_by=None):
    """Event kalender bawaan Frappe ditambah judul 'plat · pemesan' dan status untuk pewarnaan.

    Reservasi Batal tidak ditampilkan kecuali difilter khusus.
    """
    if doctype != "Reservasi Rental":
        frappe.throw("Kalender ini hanya untuk Reservasi Rental.")
    filters = frappe.parse_json(filters) or []
    if isinstance(filters, dict):
        filters = [[doctype, k, "=", v] for k, v in filters.items()]
    if not any(isinstance(f, (list, tuple)) and "status" in f for f in filters):
        filters.append(["Reservasi Rental", "status", "!=", "Batal"])
    kolom = ["name", "tanggal_mulai", "tanggal_selesai", "nama_pemesan", "kendaraan", "model_kendaraan", "status"]
    hasil = frappe_get_events(doctype, start, end, field_map, filters=frappe.as_json(filters), fields=kolom)
    for e in hasil:
        unit = e.get("kendaraan") or e.get("model_kendaraan") or "?"
        e["judul"] = f"{unit} · {e.get('nama_pemesan') or ''} ({e.get('status')})"
        e["all_day"] = 0
    return hasil
