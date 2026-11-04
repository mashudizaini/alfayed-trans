// Filter Pendapatan Rental. Periode bawaan: 6 bulan terakhir.
frappe.query_reports["Pendapatan Rental"] = {
	filters: [
		{
			fieldname: "dari_tanggal",
			label: __("Dari Tanggal"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.month_start(), -5),
			reqd: 1,
		},
		{
			fieldname: "sampai_tanggal",
			label: __("Sampai Tanggal"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "kelompokkan_per",
			label: __("Kelompokkan per"),
			fieldtype: "Select",
			options: "Kelompok Tarif\nModel\nKendaraan",
			default: "Kelompok Tarif",
		},
	],
};
