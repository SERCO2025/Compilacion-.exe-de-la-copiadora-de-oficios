# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import socket

class ConfigWindow:
    def __init__(self, parent, config_manager, scanner_manager, printer_manager, on_saved=None):
        self.top = tk.Toplevel(parent)
        self.top.title("CONFIGURACIÓN DE HARDWARE - COPIADORA DE OFICIOS")
        self.top.geometry("400x600")
        self.top.resizable(False, False)
        self.top.configure(bg='#001a33')
        self.top.transient(parent)
        self.top.grab_set()

        self.config = config_manager
        self.scanner_manager = scanner_manager
        self.printer_manager = printer_manager
        self.on_saved = on_saved
        
        self.setup_ui()

    def setup_ui(self):
        # Título con estilo Impact
        tk.Label(self.top, text="AJUSTES DE DISPOSITIVOS", bg='#001a33', fg='cyan', 
                 font=("Impact", 20)).pack(pady=15)

        # --- SELECCIÓN SCANNER 1 (COPIA DIRECTA) ---
        tk.Label(self.top, text="SCANNER 1 (DIRECTO):", bg='#001a33', fg='white', font=("Impact", 10)).pack()
        self.cb_scan1 = ttk.Combobox(self.top, values=self.scanner_manager.list_scanners(), state="readonly", width=40)
        self.cb_scan1.set(self.config.config_data.get("scanner1", ""))
        self.cb_scan1.pack(pady=5)

        # --- SELECCIÓN SCANNER 2 (OFICIO/PARTES) ---
        tk.Label(self.top, text="SCANNER 2 (PARTES):", bg='#001a33', fg='white', font=("Impact", 10)).pack()
        self.cb_scan2 = ttk.Combobox(self.top, values=self.scanner_manager.list_scanners(), width=40)
        self.cb_scan2.set(self.config.config_data.get("scanner2", ""))
        self.cb_scan2.pack(pady=5)

        # --- SELECCIÓN IMPRESORA ---
        tk.Label(self.top, text="IMPRESORA PREDETERMINADA:", bg='#001a33', fg='white', font=("Impact", 10)).pack()
        self.cb_print = ttk.Combobox(self.top, values=self.printer_manager.listar_impresoras(), width=40)
        self.cb_print.set(self.config.config_data.get("impresora", ""))
        self.cb_print.pack(pady=5)

        # --- IP LOCAL PARA EL CELULAR ---
        tk.Label(
            self.top, text="IP DE ESTA PC (CELULAR):",
            bg='#001a33', fg='white', font=("Impact", 10)
        ).pack(pady=(8, 0))

        self.lbl_ip = tk.Label(
            self.top, text=self.obtener_ip_local(),
            bg='#001a33', fg='yellow', font=("Consolas", 14, "bold")
        )
        self.lbl_ip.pack(pady=(2, 8))

        # --- PUERTO TCP ---
        tk.Label(self.top, text="PUERTO DE RED (CELULAR):", bg='#001a33', fg='white', font=("Impact", 10)).pack()
        self.ent_port = tk.Entry(self.top, font=("Consolas", 12), justify='center')
        self.ent_port.insert(0, str(self.config.config_data.get("port", 5000)))
        self.ent_port.pack(pady=5)

        # --- BOTÓN GUARDAR ---
        tk.Button(self.top, text="GUARDAR CONFIGURACIÓN", bg='#008000', fg='white', 
                  font=("Impact", 14), command=self.save_and_exit).pack(pady=30)

    def obtener_ip_local(self):
        """Obtiene la IP de la interfaz usada para salir a la red local."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                sock.connect(("8.8.8.8", 80))
                return sock.getsockname()[0]
            finally:
                sock.close()
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return "127.0.0.1"

    def save_and_exit(self):
        try:
            self.config.update_setting("scanner1", self.cb_scan1.get())
            self.config.update_setting("scanner2", self.cb_scan2.get())
            self.config.update_setting("impresora", self.cb_print.get())
            impresora = self.cb_print.get()
            if impresora and not self.printer_manager.seleccionar_impresora(impresora):
                raise ValueError("La impresora seleccionada ya no está disponible.")

            self.config.update_setting("port", int(self.ent_port.get()))
            
            if self.on_saved:
                self.on_saved()

            messagebox.showinfo("COPIADORA DE OFICIOS", "Configuración actualizada con éxito.")
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("ERROR", f"No se pudo guardar: {str(e)}")
