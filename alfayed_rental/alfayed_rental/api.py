"""Method publik untuk website booking.

cek_ketersediaan  : terbuka untuk umum, dibatasi laju, tidak membuka data sensitif.
buat_permintaan   : hanya untuk pengguna API (website lewat server perantara membawa API key).
"""
import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, get_datetime

from alfayed_rental.alfayed_rental import jadwal, tarif


def _periksa_rentang(mulai, selesai):
    mulai, selesai = get_datetime(mulai), get_datetime(selesai)
    if selesai <= mulai:
        frappe.throw(_("Waktu selesai harus setelah waktu mulai."))
    return mulai, selesai


def _rapikan_wa(nomor):
    digit = re.sub(r"\D", "", nomor or "")
    if digit.startswith("0"):
        digit = "62" + digit[1:]
    return digit


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=30, seconds=60)
def cek_ketersediaan(tanggal_mulai, tanggal_selesai, kelompok_tarif=None, dengan_driver=0,
                     jenis_sewa=None, tujuan=None):
    """Daftar model yang masih tersedia pada rentang waktu, beserta estimasi harga bila jenis sewa diberikan."""
    mulai, selesai = _periksa_rentang(tanggal_mulai, tanggal_selesai)
    unit = jadwal.unit_tersedia(mulai, selesai, kelompok=kelompok_tarif)
    jumlah = {}
    for u in unit:
        jumlah[u.model_kendaraan] = jumlah.get(u.model_kendaraan, 0) + 1
    hasil = []
    for model, tersedia in sorted(jumlah.items()):
        m = frappe.db.get_value(
            "Model Kendaraan", model, ["nama_model", "kategori", "kelompok_tarif", "kursi", "bisa_lepas_kunci"], as_dict=True)
        if not cint(dengan_driver) and not m.bisa_lepas_kunci:
            continue
        baris = {"model": m.nama_model, "kategori": m.kategori, "kursi": m.kursi, "jumlah_tersedia": tersedia}
        if jenis_sewa:
            t = tarif.cari_tarif(jenis_sewa, cint(dengan_driver), tujuan, model, m.kelompok_tarif, mulai)
            if t:
                satuan = tarif.hitung_satuan(mulai, selesai, jenis_sewa)
                baris["estimasi_total"] = t.harga * satuan
                baris["perlu_tinjauan_admin"] = bool(tarif.perlu_tinjauan(mulai, selesai, jenis_sewa))
        hasil.append(baris)
    return hasil


@frappe.whitelist()
def buat_permintaan(nama_pemesan, no_whatsapp, tanggal_mulai, tanggal_selesai, jenis_sewa,
                    kelompok_tarif=None, model_kendaraan=None, dengan_driver=0, tujuan=None,
                    jumlah_penumpang=None, lokasi_jemput=None, catatan=None):
    """Buat Reservasi berstatus Permintaan dari formulir website dan kembalikan nomornya."""
    _periksa_rentang(tanggal_mulai, tanggal_selesai)
    doc = frappe.get_doc({
        "doctype": "Reservasi Rental", "status": "Permintaan", "sumber": "Website",
        "nama_pemesan": nama_pemesan, "no_whatsapp": _rapikan_wa(no_whatsapp),
        "tanggal_mulai": tanggal_mulai, "tanggal_selesai": tanggal_selesai, "jenis_sewa": jenis_sewa,
        "kelompok_tarif": kelompok_tarif, "model_kendaraan": model_kendaraan,
        "dengan_driver": cint(dengan_driver), "tujuan": tujuan, "jumlah_penumpang": cint(jumlah_penumpang) or None,
        "lokasi_jemput": lokasi_jemput, "catatan": catatan,
    })
    doc.insert()
    return {"nomor": doc.name, "status": doc.status}
