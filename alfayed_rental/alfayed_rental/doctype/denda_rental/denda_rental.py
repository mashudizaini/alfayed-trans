import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class DendaRental(Document):
    def validate(self):
        if flt(self.jumlah) <= 0:
            frappe.throw(_("Jumlah denda harus lebih dari 0."))
