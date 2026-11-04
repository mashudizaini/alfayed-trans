// Filter Utilisasi Kendaraan. Periode bawaan: bulan berjalan.
frappe.query_reports["Utilisasi Kendaraan"] = {
	filters: [
		{
			fieldname: "dari_tanggal",
			label: __("Dari Tanggal"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "sampai_tanggal",
			label: __("Sampai Tanggal"),
			fieldtype: "Date",
			default: frappe.datetime.month_end(),
			reqd: 1,
		},
		{
			fieldname: "kelompok_tarif",
			label: __("Kelompok Tarif"),
			fieldtype: "Select",
			options: "\nBig Bus\nMedium Bus\nHiace\nElf\nMobil 3 Baris\nMobil 2 Baris\nGran Max\nPick Up",
		},
		{ fieldname: "model_kendaraan", label: __("Model"), fieldtype: "Link", options: "Model Kendaraan" },
	],
};
