app_name = "alfayed_rental"
app_title = "Alfayed Rental"
app_publisher = "PT Priok Jaya Trans"
app_description = "Aplikasi rental Alfayed"
app_email = "admin@alfayedtrans.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["erpnext"]

# Tampil sebagai app "Rental" di layar Apps; membuka workspace Rental.
add_to_apps_screen = [
	{
		"name": "alfayed_rental",
		"title": "Rental",
		"route": "/desk/rental",
		"has_permission": "alfayed_rental.alfayed_rental.pengguna.akses_app",
		"sequence_id": 2,
	}
]

# Peran Staf Rental dan profil modul dibuat/diperbarui otomatis.
after_install = "alfayed_rental.alfayed_rental.pengguna.setelah_migrate"
after_migrate = ["alfayed_rental.alfayed_rental.pengguna.setelah_migrate"]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `alfayed_rental/dock/alfayed_rental/alfayed_rental.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/alfayed_rental/css/alfayed_rental.css"
# app_include_js = "/assets/alfayed_rental/js/alfayed_rental.js"

# include js, css files in header of web template
# web_include_css = "/assets/alfayed_rental/css/alfayed_rental.css"
# web_include_js = "/assets/alfayed_rental/js/alfayed_rental.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "alfayed_rental/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "alfayed_rental/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "alfayed_rental.utils.jinja_methods",
# 	"filters": "alfayed_rental.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "alfayed_rental.install.before_install"
# after_install = "alfayed_rental.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "alfayed_rental.uninstall.before_uninstall"
# after_uninstall = "alfayed_rental.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "alfayed_rental.utils.before_app_install"
# after_app_install = "alfayed_rental.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "alfayed_rental.utils.before_app_uninstall"
# after_app_uninstall = "alfayed_rental.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "alfayed_rental.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "alfayed_rental.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "alfayed_rental.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["alfayed_rental.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"alfayed_rental.tasks.all"
# 	],
# 	"daily": [
# 		"alfayed_rental.tasks.daily"
# 	],
# 	"hourly": [
# 		"alfayed_rental.tasks.hourly"
# 	],
# 	"weekly": [
# 		"alfayed_rental.tasks.weekly"
# 	],
# 	"monthly": [
# 		"alfayed_rental.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "alfayed_rental.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "alfayed_rental.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "alfayed_rental.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "alfayed_rental.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["alfayed_rental.utils.before_request"]
# after_request = ["alfayed_rental.utils.after_request"]

# Job Events
# ----------
# before_job = ["alfayed_rental.utils.before_job"]
# after_job = ["alfayed_rental.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"alfayed_rental.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


scheduler_events = {
    "hourly": [
        "alfayed_rental.alfayed_rental.jadwal.batalkan_kedaluwarsa",
    ],
}
