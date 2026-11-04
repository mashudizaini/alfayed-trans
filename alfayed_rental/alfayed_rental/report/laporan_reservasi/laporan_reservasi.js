// Filter Laporan Reservasi. Periode bawaan: bulan berjalan.
frappe.query_reports["Laporan Reservasi"] = {
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
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nPermintaan\nMenunggu Pembayaran\nDikonfirmasi\nBerjalan\nSelesai\nBatal",
		},
		{ fieldname: "kendaraan", label: __("Kendaraan"), fieldtype: "Link", options: "Kendaraan" },
		{
			fieldname: "kelompok_tarif",
			label: __("Kelompok Tarif"),
			fieldtype: "Select",
			options: "\nBig Bus\nMedium Bus\nHiace\nElf\nMobil 3 Baris\nMobil 2 Baris\nGran Max\nPick Up",
		},
		{
			fieldname: "sumber",
			label: __("Sumber"),
			fieldtype: "Select",
			options: "\nWebsite\nWhatsApp\nTelepon\nLangsung",
		},
		{ fieldname: "termasuk_batal", label: __("Termasuk Batal"), fieldtype: "Check" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "belum_dibayar" && data && data.belum_dibayar > 0) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
