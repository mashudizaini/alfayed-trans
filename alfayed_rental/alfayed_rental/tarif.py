"""Logika tarif: pemilihan tarif aktif dan perhitungan satuan sewa."""
import math

import frappe
from frappe.utils import flt, get_datetime, getdate

# Panjang satu satuan sewa dalam menit. "Per Tujuan" tidak memakai tabel ini.
UNIT_MENIT = {"12 Jam": 720, "14 Jam": 840, "1 Hari": 1440, "24 Jam": 1440}


def nilai_pengaturan(field, default):
    """Baca Pengaturan Rental; pakai default bila belum pernah disimpan."""
    v = frappe.db.get_single_value("Pengaturan Rental", field)
    return default if v in (None, "") else v


def durasi_menit(mulai, selesai):
    return (get_datetime(selesai) - get_datetime(mulai)).total_seconds() / 60


def hitung_satuan(mulai, selesai, jenis_sewa):
    """Jumlah satuan sewa.

    Kelebihan waktu sampai toleransi (bawaan 30 menit) tidak dihitung satuan baru.
    Contoh jenis 12 Jam: 12 jam 30 menit = 1 satuan, 12 jam 31 menit = 2 satuan.
    Per Tujuan dihitung sekali jalan = 1 satuan.
    """
    if jenis_sewa == "Per Tujuan":
        return 1
    toleransi = flt(nilai_pengaturan("toleransi_menit", 30))
    sisa = max(durasi_menit(mulai, selesai) - toleransi, 0)
    return max(1, math.ceil(sisa / UNIT_MENIT[jenis_sewa]))


def perlu_tinjauan(mulai, selesai, jenis_sewa):
    """Per Tujuan lebih dari satu hari: website meminta pemesan bertanya ke admin."""
    toleransi = flt(nilai_pengaturan("toleransi_menit", 30))
    return jenis_sewa == "Per Tujuan" and durasi_menit(mulai, selesai) > 1440 + toleransi


def cari_tarif(jenis_sewa, dengan_driver, tujuan, model, kelompok, tanggal):
    """Tarif aktif yang berlaku pada tanggal. Tarif khusus model didahulukan dari tarif kelompok."""
    tanggal = getdate(tanggal)
    filters = {"aktif": 1, "jenis_sewa": jenis_sewa, "dengan_driver": 1 if dengan_driver else 0}
    if jenis_sewa == "Per Tujuan":
        filters["tujuan"] = tujuan
    baris = frappe.get_all(
        "Tarif Rental",
        filters=filters,
        fields=["name", "model_kendaraan", "kelompok_tarif", "harga", "berlaku_dari", "berlaku_sampai"],
    )
    berlaku = [
        r for r in baris
        if (not r.berlaku_dari or getdate(r.berlaku_dari) <= tanggal)
        and (not r.berlaku_sampai or getdate(r.berlaku_sampai) >= tanggal)
    ]
    khusus_model = [r for r in berlaku if model and r.model_kendaraan == model]
    khusus_kelompok = [r for r in berlaku if kelompok and not r.model_kendaraan and r.kelompok_tarif == kelompok]
    pilihan = khusus_model or khusus_kelompok
    return pilihan[0] if pilihan else None
