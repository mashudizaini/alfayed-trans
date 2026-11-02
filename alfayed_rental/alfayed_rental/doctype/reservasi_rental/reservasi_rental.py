import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now_datetime

from alfayed_rental.alfayed_rental import akuntansi, jadwal, tarif

# Perpindahan status yang diizinkan.
STATUS_BERIKUT = {
    "Permintaan": {"Menunggu Pembayaran", "Batal"},
    "Menunggu Pembayaran": {"Dikonfirmasi", "Batal"},
    "Dikonfirmasi": {"Berjalan", "Batal"},
    "Berjalan": {"Selesai"},
    "Selesai": set(),
    "Batal": set(),
}
PERLU_KENDARAAN = {"Menunggu Pembayaran", "Dikonfirmasi", "Berjalan", "Selesai"}


class ReservasiRental(Document):
    def validate(self):
        self.validasi_tanggal()
        self.isi_dari_kendaraan()
        self.validasi_transisi()
        self.validasi_kelayakan()
        self.hitung_biaya()
        self.cek_bentrok()
        if self.status == "Dikonfirmasi" and not self.customer:
            self.customer = akuntansi.pastikan_customer(self.nama_pemesan)

    def validasi_tanggal(self):
        if self.tanggal_mulai and self.tanggal_selesai and self.tanggal_selesai <= self.tanggal_mulai:
            frappe.throw(_("Tanggal selesai harus setelah tanggal mulai."))

    def isi_dari_kendaraan(self):
        if self.kendaraan:
            self.model_kendaraan = frappe.db.get_value("Kendaraan", self.kendaraan, "model_kendaraan")
        if self.model_kendaraan:
            self.kelompok_tarif = frappe.db.get_value("Model Kendaraan", self.model_kendaraan, "kelompok_tarif")

    def validasi_transisi(self):
        sebelum = self.get_doc_before_save()
        if sebelum and sebelum.status != self.status:
            if self.status not in STATUS_BERIKUT.get(sebelum.status, set()):
                frappe.throw(_("Status tidak boleh berpindah dari {0} ke {1}.").format(sebelum.status, self.status))
            if self.status == "Menunggu Pembayaran":
                self.menunggu_sejak = now_datetime()
        elif not sebelum and self.status == "Menunggu Pembayaran":
            self.menunggu_sejak = now_datetime()

    def validasi_kelayakan(self):
        if self.status in PERLU_KENDARAAN and not self.kendaraan:
            frappe.throw(_("Pilih kendaraan sebelum status {0}.").format(self.status))
        if not self.dengan_driver and self.model_kendaraan:
            if not frappe.db.get_value("Model Kendaraan", self.model_kendaraan, "bisa_lepas_kunci"):
                frappe.throw(_("{0} hanya disewakan dengan driver.").format(self.model_kendaraan))

    def hitung_biaya(self):
        if not (self.jenis_sewa and self.tanggal_mulai and self.tanggal_selesai):
            return
        self.jumlah_satuan = tarif.hitung_satuan(self.tanggal_mulai, self.tanggal_selesai, self.jenis_sewa)
        self.perlu_tinjauan = 1 if tarif.perlu_tinjauan(self.tanggal_mulai, self.tanggal_selesai, self.jenis_sewa) else 0
        manual = bool(self.alasan_override)
        # Harga hanya dicari saat masih bisa dinegosiasikan; setelah Dikonfirmasi harga dikunci.
        if not manual and (self.is_new() or self.status in ("Permintaan", "Menunggu Pembayaran")):
            t = tarif.cari_tarif(self.jenis_sewa, self.dengan_driver, self.tujuan,
                                 self.model_kendaraan, self.kelompok_tarif, self.tanggal_mulai)
            self.tarif, self.harga_dasar = (t.name, t.harga) if t else (None, 0)
            if self.status not in ("Permintaan", "Batal"):
                if not t:
                    frappe.throw(_("Tarif tidak ditemukan untuk kombinasi ini. Tambahkan Tarif Rental atau isi harga manual beserta alasannya."))
                if self.perlu_tinjauan:
                    frappe.throw(_("Per Tujuan lebih dari satu hari perlu ditinjau admin. Isi harga manual dan alasan override."))
        elif manual and not flt(self.harga_dasar):
            frappe.throw(_("Isi harga dasar manual."))
        self.total_biaya_tambahan = sum(flt(b.jumlah) for b in self.biaya_tambahan)
        self.total = flt(self.harga_dasar) * flt(self.jumlah_satuan) + self.total_biaya_tambahan
        if self.status != "Permintaan" and not flt(self.uang_muka):
            self.uang_muka = round(self.total * flt(tarif.nilai_pengaturan("dp_persen", 30)) / 100)
        self.sisa_pembayaran = self.total - flt(self.uang_muka)

    def cek_bentrok(self):
        if self.kendaraan and self.status in jadwal.AKTIF and self.tanggal_mulai and self.tanggal_selesai:
            bentrok = jadwal.cari_bentrok(self.kendaraan, self.tanggal_mulai, self.tanggal_selesai, abaikan=self.name)
            if bentrok:
                frappe.throw(_("{0} bentrok jadwal dengan reservasi: {1}").format(self.kendaraan, ", ".join(bentrok)))

    def on_update(self):
        sebelum = self.get_doc_before_save()
        lama = sebelum.status if sebelum else None
        if lama == self.status:
            return
        if self.status == "Dikonfirmasi" and not self.sales_invoice:
            self.db_set("sales_invoice", akuntansi.buat_sales_invoice(self))
        elif self.status == "Berjalan":
            frappe.db.set_value("Kendaraan", self.kendaraan, "status", "Disewa")
        elif self.status == "Selesai":
            frappe.db.set_value("Kendaraan", self.kendaraan, "status", "Tersedia")
            akuntansi.buat_invoice_denda(self)
