# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import socket


class ConfigWindow:
    def __init__(self, parent, config_manager, scanner_manager, printer_manager, on_saved=None, on_status=None):
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
        self.on_status = on_status

        self.setup_ui()

        # La ventana se construye primero. La enumeración de dispositivos
        # se ejecuta después para que un problema de WIA/TWAIN/impresoras
        # no impida mostrar correctamente el menú de configuración.
        self.top.after(100, self.cargar_dispositivos)

    def setup_ui(self):
        tk.Label(
            self.top,
            text="AJUSTES DE DISPOSITIVOS",
            bg='#001a33',
            fg='cyan',
            font=("Impact", 20)
        ).pack(pady=15)

        tk.Label(
            self.top,
            text="SCANNER 1 (DIRECTO):",
            bg='#001a33',
            fg='white',
            font=("Impact", 10)
        ).pack()

        self.cb_scan1 = ttk.Combobox(
            self.top,
            values=[],
            state="readonly",
            width=40
        )
        self.cb_scan1.pack(pady=5)

        tk.Label(
            self.top,
            text="SCANNER 2 (PARTES):",
            bg='#001a33',
            fg='white',
            font=("Impact", 10)
        ).pack()

        self.cb_scan2 = ttk.Combobox(
            self.top,
            values=[],
            state="readonly",
            width=40
        )
        self.cb_scan2.pack(pady=5)

        tk.Label(
            self.top,
            text="IMPRESORA PREDETERMINADA:",
            bg='#001a33',
            fg='white',
            font=("Impact", 10)
        ).pack()

        self.cb_print = ttk.Combobox(
            self.top,
            values=[],
            state="readonly",
            width=40
        )
        self.cb_print.pack(pady=5)

        tk.Label(
            self.top,
            text="IP DE ESTA PC (CELULAR):",
            bg='#001a33',
            fg='white',
            font=("Impact", 10)
        ).pack(pady=(8, 0))

        self.lbl_ip = tk.Label(
            self.top,
            text=self.obtener_ip_local(),
            bg='#001a33',
            fg='yellow',
            font=("Consolas", 14, "bold")
        )
        self.lbl_ip.pack(pady=(2, 8))

        tk.Label(
            self.top,
            text="PUERTO DE RED (CELULAR):",
            bg='#001a33',
            fg='white',
            font=("Impact", 10)
        ).pack()

        self.ent_port = tk.Entry(
            self.top,
            font=("Consolas", 12),
            justify='center'
        )
        self.ent_port.insert(
            0,
            str(self.config.config_data.get("port", 5000))
        )
        self.ent_port.pack(pady=5)

        self.lbl_devices = tk.Label(
            self.top,
            text="Detectando dispositivos...",
            bg='#001a33',
            fg='yellow',
            font=("Arial", 9)
        )
        self.lbl_devices.pack(pady=(2, 0))

        tk.Button(
            self.top,
            text="GUARDAR CONFIGURACIÓN",
            bg='#008000',
            fg='white',
            font=("Impact", 14),
            command=self.save_and_exit
        ).pack(pady=20)

    def cargar_dispositivos(self):
        """Carga los dispositivos después de construir la ventana."""
        try:
            scanner_list = self.scanner_manager.list_scanners()
        except Exception as e:
            scanner_list = []
            print("Aviso: no fue posible enumerar los scanners: {}".format(e))

        try:
            printer_list = self.printer_manager.listar_impresoras()
        except Exception as e:
            printer_list = []
            print("Aviso: no fue posible enumerar las impresoras: {}".format(e))

        # El backend usa este texto únicamente cuando no encuentra dispositivos.
        # No debe convertirse en una opción seleccionable de configuración.
        scanner_list = [
            name for name in scanner_list
            if name and name != "No se detectaron Scanners"
        ]

        self.cb_scan1["values"] = scanner_list
        self.cb_scan2["values"] = scanner_list
        self.cb_print["values"] = printer_list

        scanner1 = self.config.config_data.get("scanner1", "")
        scanner2 = self.config.config_data.get("scanner2", "")
        impresora = self.config.config_data.get("impresora", "")

        if scanner1 in scanner_list:
            self.cb_scan1.set(scanner1)
        elif scanner_list:
            self.cb_scan1.current(0)
        else:
            self.cb_scan1.set("")

        if scanner2 in scanner_list:
            self.cb_scan2.set(scanner2)
        elif scanner_list:
            self.cb_scan2.current(0)
        else:
            self.cb_scan2.set("")

        if impresora in printer_list:
            self.cb_print.set(impresora)
        elif printer_list:
            self.cb_print.current(0)
        else:
            self.cb_print.set("")

        dispositivos = []
        if scanner_list:
            dispositivos.append("scanners: {}".format(len(scanner_list)))
        if printer_list:
            dispositivos.append("impresoras: {}".format(len(printer_list)))

        if dispositivos:
            self.lbl_devices.config(
                text="Dispositivos detectados | " + " | ".join(dispositivos),
                fg='lightgreen'
            )
        else:
            self.lbl_devices.config(
                text="No se detectaron dispositivos",
                fg='#FFCC00'
            )

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
                raise ValueError(
                    "La impresora seleccionada ya no está disponible."
                )

            self.config.update_setting(
                "port",
                int(self.ent_port.get())
            )

            if self.on_saved:
                self.on_saved()

            self.top.grab_release()
            self.top.destroy()

        except Exception as e:
            if self.on_status:
                self.on_status(
                    f"Error al guardar configuración: {e}",
                    "#FF3333"
                )
            else:
                messagebox.showerror(
                    "ERROR",
                    f"No se pudo guardar: {str(e)}"
                )
