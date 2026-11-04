"""Peran, profil modul, dan pengguna operasional rental.

Dijalankan otomatis setiap install dan migrate (lihat hooks.py), sehingga aman diulang.
Pembuatan pengguna dijalankan manual sekali per situs:

    bench --site rental.aimz.my.id execute alfayed_rental.alfayed_rental.pengguna.buat_user_operasional \
        --kwargs "{'email_rental': 'rental@contoh.com', 'email_keuangan': 'keuangan@contoh.com'}"

Kata sandi tidak diatur di sini; atur dengan `bench --site ... set-password <email>`.
"""
import frappe

PERAN_RENTAL = "Staf Rental"
MODUL_RENTAL = "Alfayed Rental"

# Profil modul hanya mengatur menu yang tampil; hak akses tetap ditentukan peran.
PROFIL_MODUL = {
    "Staf Rental": {MODUL_RENTAL},
    "Keuangan": {MODUL_RENTAL, "Accounts"},
}

# Peran yang boleh membuka app Rental dari layar Apps.
PERAN_APP = {PERAN_RENTAL, "Accounts User", "Accounts Manager", "System Manager"}


def setelah_migrate():
    pastikan_peran()
    pastikan_profil_modul()


def pastikan_peran():
    if not frappe.db.exists("Role", PERAN_RENTAL):
        frappe.get_doc({"doctype": "Role", "role_name": PERAN_RENTAL, "desk_access": 1}).insert(
            ignore_permissions=True
        )


def pastikan_profil_modul():
    semua = frappe.get_all("Module Def", pluck="name")
    for nama, boleh in PROFIL_MODUL.items():
        blokir = sorted(m for m in semua if m not in boleh)
        if frappe.db.exists("Module Profile", nama):
            doc = frappe.get_doc("Module Profile", nama)
            doc.set("block_modules", [])
        else:
            doc = frappe.new_doc("Module Profile")
            doc.module_profile_name = nama
        for m in blokir:
            doc.append("block_modules", {"module": m})
        doc.save(ignore_permissions=True)


def akses_app():
    """Dipakai hook add_to_apps_screen: siapa yang melihat app Rental di layar Apps."""
    if frappe.session.user == "Administrator":
        return True
    return bool(PERAN_APP & set(frappe.get_roles()))


def _pastikan_user(email, nama_depan, peran, profil_modul, workspace, app_bawaan):
    if frappe.db.exists("User", email):
        user = frappe.get_doc("User", email)
        status = "diperbarui"
    else:
        user = frappe.new_doc("User")
        user.email = email
        user.send_welcome_email = 0
        status = "dibuat"
    user.first_name = nama_depan
    user.user_type = "System User"
    user.enabled = 1
    user.module_profile = profil_modul
    user.default_workspace = workspace
    user.default_app = app_bawaan
    user.save(ignore_permissions=True)
    user.add_roles(*peran)
    print(f"User {email} {status}: peran {', '.join(peran)}, halaman awal {workspace}")


def buat_user_operasional(email_rental, email_keuangan):
    setelah_migrate()
    _pastikan_user(email_rental, "Staf Rental", [PERAN_RENTAL], "Staf Rental", "Rental", "alfayed_rental")
    _pastikan_user(email_keuangan, "Keuangan", ["Accounts User", "Accounts Manager"], "Keuangan",
                   "Accounting", "erpnext")
    frappe.db.commit()
    print("Selesai. Atur kata sandi: bench --site <situs> set-password <email>")
