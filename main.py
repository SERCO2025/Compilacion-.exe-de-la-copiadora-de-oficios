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
    # (tu clase completa aquí, sin cambios)
    ...

# --- CLASE PARA BOTONES CON EFECTO 3D ---
class BotonChingon(tk.Canvas):
    # (tu clase completa aquí, sin cambios)
    ...

# --- APLICACIÓN PRINCIPAL ---
class CopiadoraDeOficios:
    def __init__(self, root):
        self.root = root
        self.root.title("COPIADORA DE OFICIOS")
        self.root.geometry("400x650")
        self.root.overrideredirect(True)
        self.root.configure(bg='#0047AB')

        # Persistencia corregida para Program Files
        self.config = ConfigManager()
        self.scanner = ScannerManager()
        self.printer = PrinterManager(
            self.config.config_data.get("impresora", "")
        )

        self.modo_imagen = tk.StringVar(
            value=self.config.config_data.get("modo", "BN")
        )

        self.mejoramiento_imagen = tk.BooleanVar(
            value=bool(
                self.config.config_data.get(
                    "mejoramiento",
                    False
                )
            )
        )

        self.puerto = self.config.config_data.get("port", 5000)

        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.setup_ui()

        self.server = NetworkServer(
            port=self.puerto,
            callback=self.process_remote
        )
        self.server.start()

    # (todos tus métodos cmd_* y setup_ui aquí, sin cambios)

    def abrir_config(self):
        ConfigWindow(
            self.root,
            self.config,
            self.scanner,
            self.printer,
            on_saved=self._actualizar_configuracion,
            on_status=self.mostrar_estado
        )

    def _actualizar_configuracion(self):
        nuevo_puerto = self.config.config_data.get("port", 5000)
        impresora = self.config.config_data.get("impresora", "")

        self.mejoramiento_imagen.set(
            bool(self.config.config_data.get("mejoramiento", False))
        )

        if impresora:
            self.printer.seleccionar_impresora(impresora)
        else:
            self.printer.printer_name = ""

        if nuevo_puerto != self.puerto:
            self.server.stop()
            self.puerto = nuevo_puerto
            self.server = NetworkServer(
                port=self.puerto,
                callback=self.process_remote
            )
            self.server.start()

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