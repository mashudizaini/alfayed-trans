// Kalender Reservasi: judul "plat · pemesan", warna menurut status.
frappe.views.calendar["Reservasi Rental"] = {
	field_map: {
		start: "tanggal_mulai",
		end: "tanggal_selesai",
		id: "name",
		title: "judul",
		allDay: "all_day",
	},
	filters: [
		{ fieldtype: "Link", fieldname: "kendaraan", options: "Kendaraan", label: __("Kendaraan") },
		{
			fieldtype: "Select",
			fieldname: "status",
			options: "\nPermintaan\nMenunggu Pembayaran\nDikonfirmasi\nBerjalan\nSelesai\nBatal",
			label: __("Status"),
		},
	],
	get_css_class(data) {
		return (
			{
				Permintaan: "gray",
				"Menunggu Pembayaran": "orange",
				Dikonfirmasi: "blue",
				Berjalan: "green",
				Selesai: "cyan",
				Batal: "red",
			}[data.status] || "blue"
		);
	},
	get_events_method: "alfayed_rental.alfayed_rental.kalender.get_events",
};
