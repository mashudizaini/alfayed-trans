import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate


class TarifRental(Document):
    def validate(self):
        if bool(self.model_kendaraan) == bool(self.kelompok_tarif):
            frappe.throw(_("Isi salah satu: Model Kendaraan atau Kelompok Tarif."))
        if flt(self.harga) <= 0:
            frappe.throw(_("Harga harus lebih dari 0."))
        if self.jenis_sewa == "Per Tujuan" and not self.tujuan:
            frappe.throw(_("Tujuan wajib diisi untuk jenis sewa Per Tujuan."))
        if self.berlaku_dari and self.berlaku_sampai and getdate(self.berlaku_sampai) < getdate(self.berlaku_dari):
            frappe.throw(_("Berlaku sampai tidak boleh sebelum berlaku dari."))
        self.cek_tumpang_tindih()

    def cek_tumpang_tindih(self):
        """Tarif aktif untuk kombinasi yang sama tidak boleh punya masa berlaku yang tumpang tindih."""
        if not self.aktif:
            return
        filters = {
            "aktif": 1, "jenis_sewa": self.jenis_sewa, "dengan_driver": self.dengan_driver,
            "name": ["!=", self.name or ""],
            "model_kendaraan": self.model_kendaraan or ["is", "not set"],
            "kelompok_tarif": self.kelompok_tarif or ["is", "not set"],
        }
        if self.jenis_sewa == "Per Tujuan":
            filters["tujuan"] = self.tujuan
        awal = getdate(self.berlaku_dari) if self.berlaku_dari else getdate("1900-01-01")
        akhir = getdate(self.berlaku_sampai) if self.berlaku_sampai else getdate("2999-12-31")
        for lain in frappe.get_all("Tarif Rental", filters=filters, fields=["name", "berlaku_dari", "berlaku_sampai"]):
            a = getdate(lain.berlaku_dari) if lain.berlaku_dari else getdate("1900-01-01")
            b = getdate(lain.berlaku_sampai) if lain.berlaku_sampai else getdate("2999-12-31")
            if awal <= b and a <= akhir:
                frappe.throw(_("Masa berlaku bertabrakan dengan tarif {0}.").format(lain.name))
