import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from alfayed_rental.alfayed_rental import akuntansi


class DepositRental(Document):
    def validate(self):
        if flt(self.jumlah) <= 0:
            frappe.throw(_("Jumlah deposit harus lebih dari 0."))
        if flt(self.potongan) > flt(self.jumlah):
            frappe.throw(_("Potongan tidak boleh melebihi jumlah deposit."))
        if self.status == "Dipotong" and not flt(self.potongan):
            frappe.throw(_("Isi potongan untuk status Dipotong."))

    def after_insert(self):
        # Jurnal penerimaan dibuat sekali, saat deposit dicatat.
        self.db_set("jurnal_terima", akuntansi.jurnal_terima(self))
        frappe.db.set_value("Reservasi Rental", self.reservasi, "deposit", self.name)

    def on_update(self):
        if self.status in ("Dikembalikan", "Dipotong") and not self.jurnal_selesai:
            self.db_set("jurnal_selesai", akuntansi.jurnal_selesai(self))
