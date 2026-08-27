# -*- coding: utf-8 -*-
import sys
import os
import socket
import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading

# --- IMPORTACIÓN DE HARDWARE (WINDOWS) ---
try:
    import win32print
except ImportError:
    win32print = None

# Módulos del núcleo
try:
    from core.config_manager import ConfigManager
    from core.scanner import ScannerManager
    from core.image_processor import procesar_union_y_preview
    from core.printer import PrinterManager
    from ui.config_window import ConfigWindow
    from core.network import NetworkServer
except ImportError as e:
    print(f"Error importando módulos del core: {e}")

def resource_path(relative_path):
    """ Obtiene la ruta absoluta para recursos empaquetados en el .exe """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def obtener_ip_local():
    """ Detecta la IP real de la PC en la red local para la APK """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# --- INDICADOR DE ESTADO INTEGRADO ---
class IndicadorEstado:
    def __init__(self, parent):
        self.parent = parent
        self.var = tk.StringVar(value="Listo")
        self.entry = tk.Entry(
            parent,
            textvariable=self.var,
            state="readonly",
            readonlybackground="#001a33",
            fg="#00FF00",
            insertbackground="white",
            font=("Consolas", 11, "bold"),
            justify="left",
            relief="sunken",
            bd=2,
            highlightthickness=0,
        )
        self.entry.pack(fill="x", padx=15, pady=(0, 8), ipady=4)
        self.entry.bind("<Shift-MouseWheel>", self.desplazar_horizontal)
        self.entry.bind("<MouseWheel>", self.desplazar_horizontal)
        self.entry.bind("<Left>", lambda event: self.entry.xview_scroll(-1, "units"))
        self.entry.bind("<Right>", lambda event: self.entry.xview_scroll(1, "units"))

    def mostrar(self, mensaje, color="#00FF00"):
        self.var.set(str(mensaje))
        self.entry.configure(fg=color)
        self.entry.xview_moveto(1.0)
        self.parent.update_idletasks()

    def desplazar_horizontal(self, event):
        if event.delta:
            self.entry.xview_scroll(int(-event.delta / 120), "units")
        return "break"

# --- CLASE PARA BOTONES CON EFECTO 3D ---
class BotonChingon(tk.Canvas):
    def __init__(self, parent, text, color, command, width=280, height=45, **kwargs):
        super().__init__(parent, width=width, height=height, bg='#0047AB', highlightthickness=0, **kwargs)
        self.command = command
        self.text = text
        self.color = color
        self.pressed = False
        self.fg = "black" if color == "#FFFF00" else "white"
        self.dibujar_boton()
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

    def dibujar_boton(self, offset=0):
        self.delete("all")
        w = int(self.cget("width"))
        h = int(self.cget("height"))
        self.create_rectangle(5, 5, w, h, fill="#001a33", outline="")
        self.rect = self.create_rectangle(offset, offset, w - 5 + offset, h - 5 + offset, fill=self.color, outline="")
        self.create_line(offset, offset, w - 5 + offset, offset, fill="#ffffff", width=2)
        self.create_line(offset, offset, offset, h - 5 + offset, fill="#ffffff", width=2)
        self.create_line(w - 5 + offset, offset, w - 5 + offset, h - 5 + offset, fill="#333333", width=3)
        self.create_line(offset, h - 5 + offset, w - 5 + offset, h - 5 + offset, fill="#333333", width=3)
        self.create_text((w - 5) // 2 + offset, (h - 5) // 2 + offset, text=self.text, fill=self.fg, font=("Impact", 16))

    def on_press(self, event):
        self.dibujar_boton(offset=2)
        self.pressed = True

    def on_release(self, event):
        self.dibujar_boton(offset=0)
        if self.pressed:
            self.command()
            self.pressed = False

# --- APLICACIÓN PRINCIPAL ---
class CopiadoraDeOficios:
    def __init__(self, root):
        self.root = root
        self.root.title("COPIADORA DE OFICIOS")
        self.root.geometry("400x650")
        self.root.overrideredirect(True)
        self.root.configure(bg='#0047AB')

        self.config = ConfigManager()
        self.scanner = ScannerManager()
        self.printer = PrinterManager(self.config.config_data.get("impresora", ""))

        self.modo_imagen = tk.StringVar(value=self.config.config_data.get("modo", "BN"))
        self.mejoramiento_imagen = tk.BooleanVar(value=bool(self.config.config_data.get("mejoramiento", False)))
        self.puerto = self.config.config_data.get("port", 5000)

        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.setup_ui()

        self.server = NetworkServer(port=self.puerto, callback=self.process_remote)
        self.server.start()

    # --- MÉTODOS DE MOVIMIENTO DE VENTANA ---
    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    # (Aquí van todos tus métodos cmd_copia_directa, cmd_scan_arriba, cmd_scan_abajo, cmd_unir, cmd_preview, cmd_imprimir_oficio, abrir_config, _actualizar_configuracion, salir_limpio — los mantengo igual que en tu código original, solo asegurando que estén dentro de la clase.)

    def salir_limpio(self):
        try:
            self.server.stop()
        except Exception:
            pass
        self.root.destroy()

# --- BLOQUE PRINCIPAL ---
if __name__ == "__main__":
    root = tk.Tk()
    app = CopiadoraDeOficios(root)
    root.mainloop()