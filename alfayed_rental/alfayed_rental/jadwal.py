"""Jadwal unit: deteksi bentrok, ketersediaan, dan pembatalan reservasi kedaluwarsa."""
import frappe
from frappe.utils import add_to_date, now_datetime

# Status yang menahan unit pada jadwalnya.
AKTIF = ("Menunggu Pembayaran", "Dikonfirmasi", "Berjalan")


def cari_bentrok(kendaraan, mulai, selesai, abaikan=None):
    """Nama reservasi aktif pada kendaraan yang sama dengan rentang waktu tumpang tindih."""
    filters = [
        ["kendaraan", "=", kendaraan],
        ["status", "in", list(AKTIF)],
        ["tanggal_mulai", "<", selesai],
        ["tanggal_selesai", ">", mulai],
    ]
    if abaikan:
        filters.append(["name", "!=", abaikan])
    return frappe.get_all("Reservasi Rental", filters=filters, pluck="name")


def unit_tersedia(mulai, selesai, model=None, kelompok=None):
    """Kendaraan yang tidak bentrok pada rentang waktu. Servis dan Nonaktif dikecualikan."""
    filters = {"status": ["not in", ["Nonaktif", "Servis"]]}
    if model:
        filters["model_kendaraan"] = model
    unit = frappe.get_all("Kendaraan", filters=filters, fields=["name", "model_kendaraan"])
    if kelompok:
        model_kelompok = set(frappe.get_all("Model Kendaraan", filters={"kelompok_tarif": kelompok}, pluck="name"))
        unit = [u for u in unit if u.model_kendaraan in model_kelompok]
    return [u for u in unit if not cari_bentrok(u.name, mulai, selesai)]


def batalkan_kedaluwarsa():
    """Job per jam: batalkan reservasi Menunggu Pembayaran yang melewati batas tahan.

    Batas diatur di Pengaturan Rental (tahan_jam). Nilai 0 berarti tidak ada pembatalan otomatis.
    """
    jam = int(frappe.db.get_single_value("Pengaturan Rental", "tahan_jam") or 0)
    if jam <= 0:
        return
    batas = add_to_date(now_datetime(), hours=-jam)
    for nama in frappe.get_all(
        "Reservasi Rental",
        filters={"status": "Menunggu Pembayaran", "menunggu_sejak": ["<", batas]},
        pluck="name",
    ):
        doc = frappe.get_doc("Reservasi Rental", nama)
        doc.status = "Batal"
        doc.save(ignore_permissions=True)
