"""
PALMA macOS — tkinter GUI.

Tk 8.5 uyumlu. Sekme geçişi grid+tkraise ile yapılır.
"""
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
from typing import Optional, List


class PalmaApp:
    TITLE = "PALMA — Akıllı Kart Yönetimi (macOS)"
    VERSION = "2.9.0-mac"

    def __init__(self, card_manager, pin_manager, server=None,
                 activation_service=None):
        self.card_manager = card_manager
        self.pin_manager = pin_manager
        self.server = server
        self.activation_service = activation_service

        self.root = tk.Tk()
        self.root.title(self.TITLE)
        self.root.geometry("860x640")
        self.root.minsize(700, 500)

        self._selected_slot: Optional[int] = None
        self._slot_map = {}
        self._certs: List = []

        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # === Üst — okuyucu seçimi ===
        top = tk.Frame(self.root, padx=10, pady=8)
        top.pack(fill=tk.X)

        tk.Label(top, text="Kart Okuyucu:", font=("Helvetica", 13, "bold")).pack(side=tk.LEFT)

        self.reader_var = tk.StringVar(value="(taranıyor…)")
        self.reader_menu = tk.OptionMenu(top, self.reader_var, "(taranıyor…)")
        self.reader_menu.config(width=35, font=("Helvetica", 12))
        self.reader_menu.pack(side=tk.LEFT, padx=(8, 4))

        tk.Button(top, text="Yenile", command=self._refresh_readers,
                  font=("Helvetica", 12)).pack(side=tk.LEFT, padx=4)

        self.status_top = tk.Label(top, text="", fg="gray", font=("Helvetica", 11))
        self.status_top.pack(side=tk.RIGHT)

        # === Sekme çubuğu ===
        tab_bar = tk.Frame(self.root, padx=10, pady=4)
        tab_bar.pack(fill=tk.X)

        self._tab_btns = {}
        tabs = [
            ("Sertifikalar", "cert"),
            ("PIN Yönetimi", "pin"),
            ("Aktivasyon", "act"),
            ("Sunucu", "srv"),
            ("Hakkında", "about"),
        ]
        for text, key in tabs:
            b = tk.Button(tab_bar, text=text, font=("Helvetica", 12),
                          padx=12, pady=2,
                          command=lambda k=key: self._switch_tab(k))
            b.pack(side=tk.LEFT, padx=2)
            self._tab_btns[key] = b

        # === İçerik konteyneri — grid ile ===
        container = tk.Frame(self.root, padx=10, pady=5)
        container.pack(fill=tk.BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._tabs = {}
        for _, key in tabs:
            f = tk.Frame(container)
            f.grid(row=0, column=0, sticky="nsew")
            self._tabs[key] = f

        self._build_cert_tab(self._tabs["cert"])
        self._build_pin_tab(self._tabs["pin"])
        self._build_act_tab(self._tabs["act"])
        self._build_srv_tab(self._tabs["srv"])
        self._build_about_tab(self._tabs["about"])

        # === Alt — durum çubuğu ===
        self.statusbar = tk.Label(self.root, text="Hazır", relief=tk.SUNKEN,
                                  anchor=tk.W, font=("Helvetica", 11), padx=6)
        self.statusbar.pack(fill=tk.X, padx=10, pady=(0, 6))

        self._switch_tab("cert")

    def _switch_tab(self, key):
        for k, b in self._tab_btns.items():
            if k == key:
                b.config(relief=tk.SUNKEN, bg="#d0d0d0")
            else:
                b.config(relief=tk.RAISED, bg="SystemButtonFace")
        self._tabs[key].tkraise()

    # ---- Sertifikalar ----
    def _build_cert_tab(self, tab):
        tk.Button(tab, text="Sertifikaları Oku", font=("Helvetica", 12),
                  command=self._read_certificates).pack(anchor=tk.W, pady=(0, 6))

        lf = tk.Frame(tab)
        lf.pack(fill=tk.BOTH, expand=True)

        sb = tk.Scrollbar(lf)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.cert_listbox = tk.Listbox(lf, font=("Menlo", 12), height=8,
                                        yscrollcommand=sb.set)
        self.cert_listbox.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.cert_listbox.yview)
        self.cert_listbox.bind("<<ListboxSelect>>", self._on_cert_selected)

        df = tk.LabelFrame(tab, text="Sertifika Detayları", font=("Helvetica", 12, "bold"),
                           padx=8, pady=6)
        df.pack(fill=tk.X, pady=(8, 0))
        self.cert_detail = tk.Text(df, height=6, state=tk.DISABLED,
                                   wrap=tk.WORD, font=("Menlo", 11))
        self.cert_detail.pack(fill=tk.X)

    # ---- PIN Yönetimi ----
    def _build_pin_tab(self, tab):
        # PIN durumu
        f1 = tk.LabelFrame(tab, text="PIN Durumu", font=("Helvetica", 12, "bold"),
                           padx=10, pady=8)
        f1.pack(fill=tk.X, pady=(0, 8))
        self.pin_status_label = tk.Label(f1, text="PIN durumu bilinmiyor",
                                         font=("Helvetica", 12))
        self.pin_status_label.pack(anchor=tk.W)
        tk.Button(f1, text="PIN Durumunu Sorgula", font=("Helvetica", 11),
                  command=self._check_pin_status).pack(anchor=tk.W, pady=(6, 0))

        # PIN doğrulama
        f2 = tk.LabelFrame(tab, text="PIN Doğrulama", font=("Helvetica", 12, "bold"),
                           padx=10, pady=8)
        f2.pack(fill=tk.X, pady=(0, 8))
        row = tk.Frame(f2)
        row.pack(fill=tk.X)
        tk.Label(row, text="PIN:", font=("Helvetica", 12), width=14,
                 anchor=tk.E).pack(side=tk.LEFT)
        self.verify_pin_entry = tk.Entry(row, show="●", width=20, font=("Helvetica", 12))
        self.verify_pin_entry.pack(side=tk.LEFT, padx=8)
        tk.Button(row, text="Doğrula", font=("Helvetica", 11),
                  command=self._verify_pin).pack(side=tk.LEFT)

        # PIN değiştirme
        f3 = tk.LabelFrame(tab, text="PIN Değiştir", font=("Helvetica", 12, "bold"),
                           padx=10, pady=8)
        f3.pack(fill=tk.X)

        for label_text, attr_name in [("Mevcut PIN:", "old_pin_entry"),
                                       ("Yeni PIN:", "new_pin_entry"),
                                       ("Yeni PIN (tekrar):", "new_pin2_entry")]:
            r = tk.Frame(f3)
            r.pack(fill=tk.X, pady=2)
            tk.Label(r, text=label_text, width=18, anchor=tk.E,
                     font=("Helvetica", 12)).pack(side=tk.LEFT)
            e = tk.Entry(r, show="●", width=20, font=("Helvetica", 12))
            e.pack(side=tk.LEFT, padx=8)
            setattr(self, attr_name, e)

        tk.Button(f3, text="PIN Değiştir", font=("Helvetica", 11),
                  command=self._change_pin).pack(anchor=tk.W, pady=(8, 0))

    # ---- Aktivasyon ----
    def _build_act_tab(self, tab):
        tk.Label(tab, text="Sertifika Aktivasyonu",
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(tab, text="TÜRKTRUST sertifikanızı aktive etmek için adımları izleyin.",
                 fg="gray", font=("Helvetica", 11)).pack(anchor=tk.W, pady=(0, 10))

        # Adım 1
        s1 = tk.LabelFrame(tab, text="Adım 1: Sertifika Seri Numarası",
                            font=("Helvetica", 11, "bold"), padx=8, pady=6)
        s1.pack(fill=tk.X, pady=4)
        r1 = tk.Frame(s1)
        r1.pack(fill=tk.X)
        tk.Label(r1, text="Seri No:", font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.serial_entry = tk.Entry(r1, width=36, font=("Helvetica", 12))
        self.serial_entry.pack(side=tk.LEFT, padx=8)
        tk.Button(r1, text="Karttan Oku", font=("Helvetica", 11),
                  command=self._read_serial_from_card).pack(side=tk.LEFT)

        # Adım 2
        s2 = tk.LabelFrame(tab, text="Adım 2: Telefon Doğrulama (Arama)",
                            font=("Helvetica", 11, "bold"), padx=8, pady=6)
        s2.pack(fill=tk.X, pady=4)
        r2 = tk.Frame(s2)
        r2.pack(fill=tk.X)
        tk.Label(r2, text="Telefon:", font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.phone_entry = tk.Entry(r2, width=20, font=("Helvetica", 12))
        self.phone_entry.pack(side=tk.LEFT, padx=8)
        tk.Button(r2, text="Doğrulama Araması Yap", font=("Helvetica", 11),
                  command=self._send_sms).pack(side=tk.LEFT)

        # Adım 3
        s3 = tk.LabelFrame(tab, text="Adım 3: Aktivasyon Kodu",
                            font=("Helvetica", 11, "bold"), padx=8, pady=6)
        s3.pack(fill=tk.X, pady=4)
        r3 = tk.Frame(s3)
        r3.pack(fill=tk.X)
        tk.Label(r3, text="Kod:", font=("Helvetica", 12)).pack(side=tk.LEFT)
        self.activation_code_entry = tk.Entry(r3, width=20, font=("Helvetica", 12))
        self.activation_code_entry.pack(side=tk.LEFT, padx=8)
        tk.Button(r3, text="Aktive Et", font=("Helvetica", 11),
                  command=self._activate).pack(side=tk.LEFT)

        self.activation_result = tk.Label(tab, text="", font=("Helvetica", 12))
        self.activation_result.pack(anchor=tk.W, pady=8)

    # ---- Sunucu ----
    def _build_srv_tab(self, tab):
        tk.Label(tab, text="Yerel HTTPS Sunucu (Tarayıcı Entegrasyonu)",
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(tab, text="localhost:8443 üzerinden tarayıcıyla iletişim kurar.",
                 fg="gray", font=("Helvetica", 11)).pack(anchor=tk.W, pady=(0, 10))

        self.server_status_label = tk.Label(tab, text="● Sunucu: Durdu",
                                            font=("Helvetica", 13), fg="red")
        self.server_status_label.pack(anchor=tk.W, pady=4)

        self.btn_server = tk.Button(tab, text="Sunucuyu Başlat",
                                    font=("Helvetica", 12),
                                    command=self._toggle_server)
        self.btn_server.pack(anchor=tk.W, pady=8)

        tk.Label(tab, text="Endpoint'ler:", font=("Helvetica", 12, "bold")).pack(anchor=tk.W, pady=(10, 4))
        for ep in [
            "GET  /status",
            "GET  /readers",
            "GET  /certificates?slot=1&pin=...",
            "POST /sign",
            "POST /verify-pin",
            "GET  /token-info?slot=1",
        ]:
            tk.Label(tab, text=f"  https://localhost:8443{ep.split(' ', 1)[1].strip()}",
                     font=("Menlo", 11), fg="gray", anchor=tk.W).pack(anchor=tk.W)

    # ---- Hakkında ----
    def _build_about_tab(self, tab):
        tk.Label(tab, text="", font=("Helvetica", 4)).pack()  # spacer
        tk.Label(tab, text="PALMA macOS",
                 font=("Helvetica", 22, "bold")).pack(pady=(40, 4))
        tk.Label(tab, text=f"Sürüm {self.VERSION}",
                 font=("Helvetica", 13), fg="gray").pack()
        tk.Label(tab, text="TÜRKTRUST Akıllı Kart Yönetim Yazılımı\nTopluluk Portu (macOS ARM64)",
                 font=("Helvetica", 12), justify=tk.CENTER).pack(pady=12)
        tk.Label(tab, text="Bu uygulama resmi değildir.\n"
                 "Tersine mühendislik ile oluşturulmuştur.",
                 fg="gray", justify=tk.CENTER, font=("Helvetica", 11)).pack(pady=4)
        tk.Label(tab, text="PKCS#11: /usr/local/lib/libakisp11.dylib",
                 font=("Menlo", 11), fg="gray").pack(pady=(30, 0))

    # ------------------------------------------------------------ Aksiyonlar
    def _set_status(self, msg):
        self.statusbar.config(text=msg)
        self.root.update_idletasks()

    def _run_async(self, func, on_done=None):
        def wrapper():
            try:
                result = func()
                if on_done:
                    self.root.after(0, on_done, result)
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Hata", str(e)))
                self.root.after(0, lambda: self._set_status(f"Hata: {e}"))
        threading.Thread(target=wrapper, daemon=True).start()

    def _refresh_readers(self):
        self._set_status("Okuyucular taranıyor…")

        def do():
            return self.card_manager.get_slots(token_present=False)

        def done(slots):
            menu = self.reader_menu["menu"]
            menu.delete(0, "end")
            self._slot_map = {}
            for s in slots:
                tp = " [Kart var]" if s.token_present else ""
                label = f"{s.description}{tp}"
                self._slot_map[label] = s.slot_id
                menu.add_command(label=label,
                                 command=lambda l=label: self._select_reader(l))
            if slots:
                first_label = list(self._slot_map.keys())[0]
                self._select_reader(first_label)
            self._set_status(f"{len(slots)} okuyucu bulundu")

        self._run_async(do, on_done=done)

    def _select_reader(self, label):
        self.reader_var.set(label)
        self._selected_slot = self._slot_map.get(label)

    def _ensure_slot(self):
        if self._selected_slot is None:
            messagebox.showwarning("Uyarı", "Önce bir okuyucu seçin.")
            return False
        return True

    def _read_certificates(self):
        if not self._ensure_slot():
            return
        pin = simpledialog.askstring("PIN", "Kart PIN'inizi girin:",
                                     show="●", parent=self.root)
        if not pin:
            return
        self._set_status("Sertifikalar okunuyor…")
        slot = self._selected_slot

        def do():
            return self.card_manager.get_certificates(slot, pin=pin)

        def done(certs):
            self._certs = certs
            self.cert_listbox.delete(0, tk.END)
            for c in certs:
                exp = "✓ Geçerli" if not c.is_expired else "✗ Süresi dolmuş"
                na = c.not_after.strftime("%Y-%m-%d") if c.not_after else "?"
                self.cert_listbox.insert(tk.END, f"{c.label}  |  {c.subject}  |  {na}  |  {exp}")
            self._set_status(f"{len(certs)} sertifika okundu")

        self._run_async(do, on_done=done)

    def _on_cert_selected(self, event=None):
        sel = self.cert_listbox.curselection()
        if not sel or sel[0] >= len(self._certs):
            return
        c = self._certs[sel[0]]
        self.cert_detail.config(state=tk.NORMAL)
        self.cert_detail.delete("1.0", tk.END)
        self.cert_detail.insert("1.0", "\n".join([
            f"Etiket:     {c.label}",
            f"Sahip:      {c.subject}",
            f"Veren:      {c.issuer}",
            f"Seri No:    {c.serial_number}",
            f"Başlangıç:  {c.not_before}",
            f"Bitiş:      {c.not_after}",
            f"Durum:      {'Geçerli' if not c.is_expired else 'Süresi dolmuş'}",
        ]))
        self.cert_detail.config(state=tk.DISABLED)

    def _check_pin_status(self):
        if not self._ensure_slot():
            return
        slot = self._selected_slot
        self._set_status("PIN durumu sorgulanıyor…")

        def do():
            return self.pin_manager.get_pin_info(slot)

        def done(info):
            if info.is_locked:
                self.pin_status_label.config(text="🔒 PIN KİLİTLİ — Kart bloke!", fg="red")
            else:
                r = f", kalan: {info.remaining_attempts}" if info.remaining_attempts else ""
                self.pin_status_label.config(
                    text=f"✓ PIN aktif — uzunluk: {info.min_length}–{info.max_length}{r}",
                    fg="#006600")
            self._set_status("PIN durumu sorgulandı")

        self._run_async(do, on_done=done)

    def _verify_pin(self):
        if not self._ensure_slot():
            return
        pin = self.verify_pin_entry.get()
        if not pin:
            messagebox.showwarning("Uyarı", "PIN girin.")
            return
        slot = self._selected_slot

        def do():
            return self.pin_manager.verify_pin(slot, pin)

        def done(res):
            if res.success:
                messagebox.showinfo("PIN Doğrulama", "✓ PIN doğru!")
            else:
                msg = res.error_message or "PIN hatalı"
                if res.remaining_attempts is not None:
                    msg += f"\nKalan deneme: {res.remaining_attempts}"
                messagebox.showwarning("PIN Doğrulama", msg)
            self._set_status("PIN doğrulama tamamlandı")

        self._run_async(do, on_done=done)

    def _change_pin(self):
        if not self._ensure_slot():
            return
        old_p = self.old_pin_entry.get()
        new_p = self.new_pin_entry.get()
        new_p2 = self.new_pin2_entry.get()
        if not old_p or not new_p:
            messagebox.showwarning("Uyarı", "Tüm alanları doldurun.")
            return
        if new_p != new_p2:
            messagebox.showwarning("Uyarı", "Yeni PIN'ler eşleşmiyor.")
            return
        slot = self._selected_slot

        def do():
            return self.pin_manager.change_pin(slot, old_p, new_p)

        def done(res):
            if res.success:
                messagebox.showinfo("PIN", "✓ PIN başarıyla değiştirildi!")
                for e in (self.old_pin_entry, self.new_pin_entry, self.new_pin2_entry):
                    e.delete(0, tk.END)
            else:
                messagebox.showerror("PIN", res.error_message or "Hata oluştu")

        self._run_async(do, on_done=done)

    def _read_serial_from_card(self):
        if not self._ensure_slot():
            return
        pin = simpledialog.askstring("PIN", "PIN girin:", show="●", parent=self.root)
        if not pin:
            return
        slot = self._selected_slot

        def do():
            certs = self.card_manager.get_certificates(slot, pin=pin)
            return certs[0].serial_number if certs else None

        def done(serial):
            if serial:
                self.serial_entry.delete(0, tk.END)
                self.serial_entry.insert(0, serial)
            else:
                messagebox.showwarning("Uyarı", "Sertifika bulunamadı.")

        self._run_async(do, on_done=done)

    def _send_sms(self):
        if not self.activation_service:
            messagebox.showwarning("Uyarı", "Aktivasyon servisi yapılandırılmamış.")
            return
        serial = self.serial_entry.get().strip()
        phone = self.phone_entry.get().strip()
        if not serial or not phone:
            messagebox.showwarning("Uyarı", "Seri no ve telefonu doldurun.")
            return

        def do():
            return self.activation_service.sertifika_aktivasyon_sms_gonder(serial, phone)

        def done(r):
            if r.basarili:
                messagebox.showinfo("Doğrulama", f"✓ Doğrulama araması başlatıldı!\n{r.mesaj}")
            else:
                messagebox.showerror("Doğrulama", r.mesaj or "Arama başlatılamadı")

        self._run_async(do, on_done=done)

    def _activate(self):
        if not self.activation_service:
            messagebox.showwarning("Uyarı", "Aktivasyon servisi yapılandırılmamış.")
            return
        serial = self.serial_entry.get().strip()
        code = self.activation_code_entry.get().strip()
        if not serial or not code:
            messagebox.showwarning("Uyarı", "Seri no ve kodu girin.")
            return

        def do():
            return self.activation_service.sertifika_aktivasyon_bildir(serial, code)

        def done(r):
            if r.basarili:
                messagebox.showinfo("Aktivasyon", f"✓ Sertifika aktive edildi!\n{r.mesaj}")
                self.activation_result.config(text="✓ Aktive edildi", fg="#006600")
            else:
                messagebox.showerror("Aktivasyon", r.mesaj or "Başarısız")
                self.activation_result.config(text="✗ Başarısız", fg="red")

        self._run_async(do, on_done=done)

    def _toggle_server(self):
        if self.server is None:
            messagebox.showwarning("Uyarı", "Sunucu yapılandırılmamış.")
            return
        if self.server.is_running():
            self.server.stop()
            self.server_status_label.config(text="● Sunucu: Durdu", fg="red")
            self.btn_server.config(text="Sunucuyu Başlat")
        else:
            try:
                self.server.start()
                self.server_status_label.config(
                    text="● Sunucu: Çalışıyor — https://localhost:8443", fg="#006600")
                self.btn_server.config(text="Sunucuyu Durdur")
            except Exception as e:
                messagebox.showerror("Sunucu Hatası", str(e))

    # ---- Yaşam döngüsü ----
    def run(self):
        self._refresh_readers()
        self.root.mainloop()

    def quit(self):
        if self.server and self.server.is_running():
            self.server.stop()
        self.root.destroy()
