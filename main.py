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

# --- NOTIFICACIÓN QUE SE CIERRA SOLA (5 SEGUNDOS) ---
class NotificacionFlash(tk.Toplevel):
    def __init__(self, parent, mensaje, color="#008000"):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg=color)
        
        # Posicionamiento en el centro de la app
        x = parent.winfo_x() + 50
        y = parent.winfo_y() + 250
        self.geometry(f"300x100+{x}+{y}")
        
        tk.Label(self, text=mensaje, fg="white", bg=color, 
                 font=("Impact", 14), wraplength=280).pack(expand=True, pady=10)
        
        # Se destruye sola tras 5000ms (5 segundos)
        self.after(5000, self.destroy)

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
        w, h = int(self.cget("width")), int(self.cget("height"))
        self.create_rectangle(5, 5, w, h, fill="#001a33", outline="")
        self.rect = self.create_rectangle(offset, offset, w-5+offset, h-5+offset, fill=self.color, outline="")
        self.create_line(offset, offset, w-5+offset, offset, fill="#ffffff", width=2)
        self.create_line(offset, offset, offset, h-5+offset, fill="#ffffff", width=2)
        self.create_line(w-5+offset, offset, w-5+offset, h-5+offset, fill="#333333", width=3)
        self.create_line(offset, h-5+offset, w-5+offset, h-5+offset, fill="#333333", width=3)
        self.create_text((w-5)//2+offset, (h-5)//2+offset, text=self.text, fill=self.fg, font=("Impact", 16))

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

        # Persistencia corregida para Program Files
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

    def setup_ui(self):
        header = tk.Frame(self.root, bg='#0047AB')
        header.pack(fill='x', padx=10, pady=5)
        tk.Button(header, text=" ⚙ ", bg='#002366', fg='cyan', font=("Arial", 12, "bold"), 
                  command=self.abrir_config, relief='flat').pack(side='left')
        tk.Button(header, text=" X ", bg='#8B0000', fg='white', font=("Arial", 12, "bold"), 
                  command=self.salir_limpio, relief='flat').pack(side='right')
        
        tk.Label(self.root, text="COPIADORA DE OFICIOS", bg='#0047AB', fg='cyan', font=("Impact", 32)).pack(pady=10)

        self.btn_directa = BotonChingon(self.root, "COPIA DIRECTA", "#008000", self.cmd_copia_directa)
        self.btn_directa.pack(pady=8)
        self.btn_up = BotonChingon(self.root, "ESCANEAR ARRIBA", "#4169E1", self.cmd_scan_arriba)
        self.btn_up.pack(pady=8)
        self.btn_down = BotonChingon(self.root, "ESCANEAR ABAJO", "#4169E1", self.cmd_scan_abajo)
        self.btn_down.pack(pady=8)
        self.btn_unir = BotonChingon(self.root, "UNIR PARTES", "#FF8C00", self.cmd_unir)
        self.btn_unir.pack(pady=8)
        self.btn_preview = BotonChingon(self.root, "PREVISUALIZAR", "#FFFF00", self.cmd_preview)
        self.btn_preview.pack(pady=8)
        self.btn_print = BotonChingon(self.root, "IMPRIMIR OFICIO", "#008000", self.cmd_imprimir_oficio)
        self.btn_print.pack(pady=8)

        mode_frame = tk.Frame(self.root, bg='#0047AB')
        mode_frame.pack(pady=12)

        tk.Radiobutton(
            mode_frame, text="B/N", variable=self.modo_imagen, value="BN",
            bg='#0047AB', fg='white', font=("Impact", 12),
            selectcolor='#001a33', command=self.cambiar_modo
        ).pack(side='left', padx=10)

        tk.Radiobutton(
            mode_frame, text="COLOR", variable=self.modo_imagen, value="COLOR",
            bg='#0047AB', fg='white', font=("Impact", 12),
            selectcolor='#001a33', command=self.cambiar_modo
        ).pack(side='left', padx=10)

        tk.Checkbutton(
            self.root, text="MEJORAMIENTO DE IMAGEN",
            variable=self.mejoramiento_imagen, bg='#0047AB', fg='yellow',
            activebackground='#0047AB', activeforeground='yellow',
            selectcolor='#001a33', font=("Impact", 11),
            command=self.cambiar_mejoramiento
        ).pack(pady=4)

    def start_move(self, event): self.x, self.y = event.x, event.y
    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def cmd_copia_directa(self):
        scanner = self.config.config_data.get("scanner1", "")
        printer_name = self.config.config_data.get("impresora", "")
        modo = self.modo_imagen.get()
        if not scanner: return
        
        def run():
            exito, msg = self.scanner.scan_image(scanner, "copia.png", dpi=300)
            if exito and printer_name:
                from core.image_processor import aplicar_mejoras_impresion
                final = aplicar_mejoras_impresion("copia.png", modo, self.mejoramiento_imagen.get())
                if self.printer.seleccionar_impresora(printer_name):
                    self.printer.imprimir_archivo(final)
                self.root.after(0, lambda: NotificacionFlash(self.root, "Copia enviada."))
        threading.Thread(target=run, daemon=True).start()

    def cmd_scan_arriba(self):
        scanner = self.config.config_data.get("scanner2", "")
        if not scanner: return
        threading.Thread(target=lambda: self.scanner.scan_image(scanner, "arriba.png"), daemon=True).start()

    def cmd_scan_abajo(self):
        scanner = self.config.config_data.get("scanner2", "")
        if not scanner: return
        threading.Thread(target=lambda: self.scanner.scan_image(scanner, "abajo.png"), daemon=True).start()

    def cmd_unir(self):
        if procesar_union_y_preview("arriba.png", "abajo.png"):
            NotificacionFlash(self.root, "Partes unidas con éxito.")
        else:
            NotificacionFlash(self.root, "Error al unir. Revisa escaneos.", "#8B0000")

    def cmd_preview(self):
        if os.path.exists("oficio.png"): os.startfile("oficio.png")

    def cmd_imprimir_oficio(self):
        printer_name = self.config.config_data.get("impresora", "")
        modo = self.modo_imagen.get()
        if os.path.exists("oficio.png") and printer_name:
            from core.image_processor import aplicar_mejoras_impresion
            final = aplicar_mejoras_impresion("oficio.png", modo, self.mejoramiento_imagen.get())
            if self.printer.seleccionar_impresora(printer_name):
                    self.printer.imprimir_archivo(final)
            NotificacionFlash(self.root, "Imprimiendo oficio...")

    def abrir_config(self):
        ConfigWindow(
            self.root,
            self.config,
            self.scanner,
            self.printer,
            on_saved=self._actualizar_configuracion
        )

    def _actualizar_configuracion(self):
        nuevo_puerto = self.config.config_data.get("port", 5000)
        impresora = self.config.config_data.get("impresora", "")
        self.mejoramiento_imagen.set(bool(self.config.config_data.get("mejoramiento", False)))

        if impresora:
            self.printer.seleccionar_impresora(impresora)
        else:
            self.printer.printer_name = ""

        # Si el puerto cambió desde la ventana de configuración, el servidor
        # existente debe detenerse y levantarse nuevamente en el nuevo puerto.
        if nuevo_puerto != self.puerto:
            self.server.stop()
            self.puerto = nuevo_puerto
            self.server = NetworkServer(port=self.puerto, callback=self.process_remote)
            self.server.start()
        else:
            self.puerto = nuevo_puerto

    def cambiar_modo(self):
        self.config.update_setting("modo", self.modo_imagen.get())

    def cambiar_mejoramiento(self):
        self.config.update_setting("mejoramiento", bool(self.mejoramiento_imagen.get()))
    def process_remote(self, cmd):
        """Ejecuta un comando remoto y devuelve su resultado real.

        Esta función se ejecuta dentro del hilo de atención de la conexión de red,
        por lo que puede esperar a que termine una operación larga sin bloquear
        la interfaz gráfica principal.
        """
        operaciones = {
            "COPIA_DIRECTA": self._remote_copia_directa,
            "ESCANEAR_ARRIBA": self._remote_scan_arriba,
            "ESCANEAR_ABAJO": self._remote_scan_abajo,
            "UNIR": self._remote_unir,
            "IMPRIMIR": self._remote_imprimir,
        }
        operacion = operaciones.get(cmd)
        if operacion is None:
            return False

        try:
            return bool(operacion())
        except Exception as e:
            print(f"ERROR en comando remoto {cmd}: {e}")
            return False

    def _remote_copia_directa(self):
        scanner = self.config.config_data.get("scanner1", "")
        printer_name = self.config.config_data.get("impresora", "")
        modo = self.modo_imagen.get()
        if not scanner or not printer_name:
            return False
        exito, msg = self.scanner.scan_image(scanner, "copia.png", dpi=300)
        if not exito:
            return False
        from core.image_processor import aplicar_mejoras_impresion
        final = aplicar_mejoras_impresion("copia.png", modo, self.mejoramiento_imagen.get())
        if not self.printer.seleccionar_impresora(printer_name):
            return False
        ok = self.printer.imprimir_archivo(final)
        if ok:
            self.root.after(0, lambda: NotificacionFlash(self.root, "Copia enviada."))
        return bool(ok)

    def _remote_scan_arriba(self):
        scanner = self.config.config_data.get("scanner2", "")
        if not scanner:
            return False
        exito, _ = self.scanner.scan_image(scanner, "arriba.png")
        return bool(exito)

    def _remote_scan_abajo(self):
        scanner = self.config.config_data.get("scanner2", "")
        if not scanner:
            return False
        exito, _ = self.scanner.scan_image(scanner, "abajo.png")
        return bool(exito)

    def _remote_unir(self):
        ok = procesar_union_y_preview("arriba.png", "abajo.png")
        if ok:
            self.root.after(0, lambda: NotificacionFlash(self.root, "Partes unidas con éxito."))
        else:
            self.root.after(0, lambda: NotificacionFlash(self.root, "Error al unir. Revisa escaneos.", "#8B0000"))
        return bool(ok)

    def _remote_imprimir(self):
        printer_name = self.config.config_data.get("impresora", "")
        modo = self.modo_imagen.get()
        if not os.path.exists("oficio.png") or not printer_name:
            return False
        from core.image_processor import aplicar_mejoras_impresion
        final = aplicar_mejoras_impresion("oficio.png", modo, self.mejoramiento_imagen.get())
        if not self.printer.seleccionar_impresora(printer_name):
            return False
        ok = self.printer.imprimir_archivo(final)
        if ok:
            self.root.after(0, lambda: NotificacionFlash(self.root, "Imprimiendo oficio..."))
        return bool(ok)
    def salir_limpio(self):
        self.server.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = CopiadoraDeOficios(root)
    root.mainloop()

