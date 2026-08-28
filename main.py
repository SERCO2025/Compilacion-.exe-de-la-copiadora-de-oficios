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

        self.entry.pack(
            fill="x",
            padx=15,
            pady=(0, 8),
            ipady=4
        )

        # Desplazamiento horizontal para mensajes largos.
        self.entry.bind(
            "<Shift-MouseWheel>",
            self.desplazar_horizontal
        )

        self.entry.bind(
            "<MouseWheel>",
            self.desplazar_horizontal
        )

        self.entry.bind(
            "<Left>",
            lambda event: self.entry.xview_scroll(-1, "units")
        )

        self.entry.bind(
            "<Right>",
            lambda event: self.entry.xview_scroll(1, "units")
        )

    def mostrar(self, mensaje, color="#00FF00"):
        self.var.set(str(mensaje))
        self.entry.configure(fg=color)

        # Reinicia la posición para que los mensajes nuevos comiencen desde
        # el inicio y puedan desplazarse hacia la derecha si son largos.
        self.entry.xview_moveto(0.0)

        self.parent.update_idletasks()

    def desplazar_horizontal(self, event):
        if event.delta:
            self.entry.xview_scroll(
                int(-event.delta / 120),
                "units"
            )

        return "break"


# --- CLASE PARA BOTONES CON EFECTO 3D ---
class BotonChingon(tk.Canvas):
    def __init__(self, parent, text, color, command, width=280, height=45, **kwargs):
        super().__init__(
            parent,
            width=width,
            height=height,
            bg='#0047AB',
            highlightthickness=0,
            **kwargs
        )

        self.command = command
        self.text = text
        self.color = color
        self.pressed = False
        self.fg = "black" if color == "#FFFF00" else "white"

        self.dibujar_boton()

        self.bind(
            "<ButtonPress-1>",
            self.on_press
        )

        self.bind(
            "<ButtonRelease-1>",
            self.on_release
        )

    def dibujar_boton(self, offset=0):
        self.delete("all")

        w = int(self.cget("width"))
        h = int(self.cget("height"))

        self.create_rectangle(
            5,
            5,
            w,
            h,
            fill="#001a33",
            outline=""
        )

        self.rect = self.create_rectangle(
            offset,
            offset,
            w - 5 + offset,
            h - 5 + offset,
            fill=self.color,
            outline=""
        )

        self.create_line(
            offset,
            offset,
            w - 5 + offset,
            offset,
            fill="#ffffff",
            width=2
        )

        self.create_line(
            offset,
            offset,
            offset,
            h - 5 + offset,
            fill="#ffffff",
            width=2
        )

        self.create_line(
            w - 5 + offset,
            offset,
            w - 5 + offset,
            h - 5 + offset,
            fill="#333333",
            width=3
        )

        self.create_line(
            offset,
            h - 5 + offset,
            w - 5 + offset,
            h - 5 + offset,
            fill="#333333",
            width=3
        )

        self.create_text(
            (w - 5) // 2 + offset,
            (h - 5) // 2 + offset,
            text=self.text,
            fill=self.fg,
            font=("Impact", 16)
        )

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

        self.puerto = self.config.config_data.get(
            "port",
            5000
        )

        self.root.bind(
            "<ButtonPress-1>",
            self.start_move
        )

        self.root.bind(
            "<B1-Motion>",
            self.do_move
        )

        self.setup_ui()

        self.server = NetworkServer(
            port=self.puerto,
            callback=self.process_remote
        )

        self.server.start()

    def setup_ui(self):
        header = tk.Frame(
            self.root,
            bg='#0047AB'
        )

        header.pack(
            fill='x',
            padx=10,
            pady=5
        )

        tk.Button(
            header,
            text=" ⚙ ",
            bg='#002366',
            fg='cyan',
            font=("Arial", 12, "bold"),
            command=self.abrir_config,
            relief='flat'
        ).pack(
            side='left'
        )

        tk.Button(
            header,
            text=" X ",
            bg='#8B0000',
            fg='white',
            font=("Arial", 12, "bold"),
            command=self.salir_limpio,
            relief='flat'
        ).pack(
            side='right'
        )

        tk.Label(
            self.root,
            text="COPIADORA DE OFICIOS",
            bg='#0047AB',
            fg='cyan',
            font=("Impact", 32)
        ).pack(
            pady=10
        )

        # Pantalla de estado integrada.
        # Queda arriba de los botones, como el display de una calculadora.
        self.estado = IndicadorEstado(
            self.root
        )

        self.btn_directa = BotonChingon(
            self.root,
            "COPIA DIRECTA",
            "#008000",
            self.cmd_copia_directa
        )

        self.btn_directa.pack(
            pady=8
        )

        self.btn_up = BotonChingon(
            self.root,
            "ESCANEAR ARRIBA",
            "#4169E1",
            self.cmd_scan_arriba
        )

        self.btn_up.pack(
            pady=8
        )

        self.btn_down = BotonChingon(
            self.root,
            "ESCANEAR ABAJO",
            "#4169E1",
            self.cmd_scan_abajo
        )

        self.btn_down.pack(
            pady=8
        )

        self.btn_unir = BotonChingon(
            self.root,
            "UNIR PARTES",
            "#FF8C00",
            self.cmd_unir
        )

        self.btn_unir.pack(
            pady=8
        )

        self.btn_preview = BotonChingon(
            self.root,
            "PREVISUALIZAR",
            "#FFFF00",
            self.cmd_preview
        )

        self.btn_preview.pack(
            pady=8
        )

        self.btn_print = BotonChingon(
            self.root,
            "IMPRIMIR OFICIO",
            "#008000",
            self.cmd_imprimir_oficio
        )

        self.btn_print.pack(
            pady=8
        )

        mode_frame = tk.Frame(
            self.root,
            bg='#0047AB'
        )

        mode_frame.pack(
            pady=12
        )

        tk.Radiobutton(
            mode_frame,
            text="B/N",
            variable=self.modo_imagen,
            value="BN",
            bg='#0047AB',
            fg='white',
            font=("Impact", 12),
            selectcolor='#001a33',
            command=self.cambiar_modo
        ).pack(
            side='left',
            padx=10
        )

        tk.Radiobutton(
            mode_frame,
            text="COLOR",
            variable=self.modo_imagen,
            value="COLOR",
            bg='#0047AB',
            fg='white',
            font=("Impact", 12),
            selectcolor='#001a33',
            command=self.cambiar_modo
        ).pack(
            side='left',
            padx=10
        )

        tk.Checkbutton(
            self.root,
            text="MEJORAMIENTO DE IMAGEN",
            variable=self.mejoramiento_imagen,
            bg='#0047AB',
            fg='yellow',
            activebackground='#0047AB',
            activeforeground='yellow',
            selectcolor='#001a33',
            font=("Impact", 11),
            command=self.cambiar_mejoramiento
        ).pack(
            pady=4
        )

    def mostrar_estado(self, mensaje, color="#00FF00"):
        """Actualiza el indicador desde cualquier hilo de trabajo."""
        try:
            self.root.after(
                0,
                lambda: self.estado.mostrar(
                    mensaje,
                    color
                )
            )
        except Exception:
            pass

    def mensaje_error_scanner(self, detalle):
        """Devuelve el texto de estado apropiado para un error de escáner."""
        detalle = str(detalle or "")

        if "desconectado" in detalle.lower():
            return "Scanner desconectado"

        return "Fallo de escaneo"

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (
            event.x - self.x
        )

        y = self.root.winfo_y() + (
            event.y - self.y
        )

        self.root.geometry(
            f"+{x}+{y}"
        )

    def cmd_copia_directa(self):
        scanner = self.config.config_data.get(
            "scanner1",
            ""
        )

        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()
        mejoramiento = self.mejoramiento_imagen.get()

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return

        if not printer_name:
            self.mostrar_estado(
                "Error de impresión: impresora no configurada",
                "#FF3333"
            )
            return

        self.mostrar_estado(
            "Copia Directa",
            "#FFFF00"
        )

        def run():
            self.mostrar_estado(
                "Escaneando",
                "#FFFF00"
            )

            exito, msg = self.scanner.scan_image(
                scanner,
                "copia.png",
                dpi=300
            )

            if not exito:
                self.mostrar_estado(
                    self.mensaje_error_scanner(msg),
                    "#FF3333"
                )
                return

            self.mostrar_estado(
                "Imprimiendo",
                "#FFFF00"
            )

            from core.image_processor import aplicar_mejoras_impresion

            final = aplicar_mejoras_impresion(
                "copia.png",
                modo,
                mejoramiento
            )

            if not self.printer.seleccionar_impresora(
                printer_name
            ):
                self.mostrar_estado(
                    "Error de impresión: impresora no disponible",
                    "#FF3333"
                )
                return

            ok = self.printer.imprimir_archivo(
                final
            )

            if ok:
                self.mostrar_estado(
                    "Copia completada",
                    "#00FF00"
                )
            else:
                self.mostrar_estado(
                    "Error de impresión",
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def cmd_scan_arriba(self):
        scanner = self.config.config_data.get(
            "scanner2",
            ""
        )

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return

        def run():
            self.mostrar_estado(
                "Escaneando arriba",
                "#FFFF00"
            )

            exito, msg = self.scanner.scan_image(
                scanner,
                "arriba.png"
            )

            if exito:
                self.mostrar_estado(
                    "Escaneo arriba completado",
                    "#00FF00"
                )
            else:
                self.mostrar_estado(
                    self.mensaje_error_scanner(msg),
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def cmd_scan_abajo(self):
        scanner = self.config.config_data.get(
            "scanner2",
            ""
        )

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return

        def run():
            self.mostrar_estado(
                "Escaneando abajo",
                "#FFFF00"
            )

            exito, msg = self.scanner.scan_image(
                scanner,
                "abajo.png"
            )

            if exito:
                self.mostrar_estado(
                    "Escaneo abajo completado",
                    "#00FF00"
                )
            else:
                self.mostrar_estado(
                    self.mensaje_error_scanner(msg),
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def cmd_unir(self):
        self.mostrar_estado(
            "Procesando unión",
            "#FFFF00"
        )

        def run():
            try:
                ok = procesar_union_y_preview(
                    "arriba.png",
                    "abajo.png"
                )

                if ok:
                    self.mostrar_estado(
                        "Unión completada",
                        "#00FF00"
                    )
                else:
                    self.mostrar_estado(
                        "Error al procesar la unión: revisa los escaneos",
                        "#FF3333"
                    )

            except Exception as e:
                self.mostrar_estado(
                    f"Error al procesar la unión: {e}",
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def cmd_preview(self):
        if os.path.exists("oficio.png"):
            os.startfile(
                "oficio.png"
            )
        else:
            self.mostrar_estado(
                "Error: oficio.png no existe",
                "#FF3333"
            )

    def cmd_imprimir_oficio(self):
        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()
        mejoramiento = self.mejoramiento_imagen.get()

        if not os.path.exists("oficio.png"):
            self.mostrar_estado(
                "Error de impresión: oficio.png no existe",
                "#FF3333"
            )
            return

        if not printer_name:
            self.mostrar_estado(
                "Error de impresión: impresora no configurada",
                "#FF3333"
            )
            return

        self.mostrar_estado(
            "Imprimiendo",
            "#FFFF00"
        )

        def run():
            try:
                from core.image_processor import aplicar_mejoras_impresion

                final = aplicar_mejoras_impresion(
                    "oficio.png",
                    modo,
                    mejoramiento
                )

                if not self.printer.seleccionar_impresora(
                    printer_name
                ):
                    self.mostrar_estado(
                        "Error de impresión: impresora no disponible",
                        "#FF3333"
                    )
                    return

                ok = self.printer.imprimir_archivo(
                    final
                )

                if ok:
                    self.mostrar_estado(
                        "Impresión completada",
                        "#00FF00"
                    )
                else:
                    self.mostrar_estado(
                        "Error de impresión",
                        "#FF3333"
                    )

            except Exception as e:
                self.mostrar_estado(
                    f"Error de impresión: {e}",
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    def abrir_config(self):
        ConfigWindow(
            self.root,
            self.config,
            self.scanner,
            self.printer,
            on_saved=self._actualizar_configuracion
        )

    def _actualizar_configuracion(self):
        nuevo_puerto = self.config.config_data.get(
            "port",
            5000
        )

        impresora = self.config.config_data.get(
            "impresora",
            ""
        )

        self.mejoramiento_imagen.set(
            bool(
                self.config.config_data.get(
                    "mejoramiento",
                    False
                )
            )
        )

        if impresora:
            self.printer.seleccionar_impresora(
                impresora
            )
        else:
            self.printer.printer_name = ""

        # Si el puerto cambió desde la ventana de configuración,
        # el servidor existente debe detenerse y levantarse
        # nuevamente en el nuevo puerto.
        if nuevo_puerto != self.puerto:
            self.server.stop()

            self.puerto = nuevo_puerto

            self.server = NetworkServer(
                port=self.puerto,
                callback=self.process_remote
            )

            self.server.start()
        else:
            self.puerto = nuevo_puerto

        self.mostrar_estado(
            "Configuración guardada correctamente",
            "#00FF00"
        )

    def cambiar_modo(self):
        self.config.update_setting(
            "modo",
            self.modo_imagen.get()
        )

    def cambiar_mejoramiento(self):
        self.config.update_setting(
            "mejoramiento",
            bool(self.mejoramiento_imagen.get())
        )

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
            self.mostrar_estado(
                f"Error en comando remoto: {e}",
                "#FF3333"
            )
            return False

    def _remote_copia_directa(self):
        scanner = self.config.config_data.get(
            "scanner1",
            ""
        )

        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()
        mejoramiento = self.mejoramiento_imagen.get()

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return False

        if not printer_name:
            self.mostrar_estado(
                "Error de impresión: impresora no configurada",
                "#FF3333"
            )
            return False

        self.mostrar_estado(
            "Copia Directa",
            "#FFFF00"
        )

        self.mostrar_estado(
            "Escaneando",
            "#FFFF00"
        )

        exito, msg = self.scanner.scan_image(
            scanner,
            "copia.png",
            dpi=300
        )

        if not exito:
            self.mostrar_estado(
                self.mensaje_error_scanner(msg),
                "#FF3333"
            )
            return False

        self.mostrar_estado(
            "Imprimiendo",
            "#FFFF00"
        )

        from core.image_processor import aplicar_mejoras_impresion

        final = aplicar_mejoras_impresion(
            "copia.png",
            modo,
            mejoramiento
        )

        if not self.printer.seleccionar_impresora(
            printer_name
        ):
            self.mostrar_estado(
                "Error de impresión: impresora no disponible",
                "#FF3333"
            )
            return False

        ok = self.printer.imprimir_archivo(
            final
        )

        if ok:
            self.mostrar_estado(
                "Copia completada",
                "#00FF00"
            )
        else:
            self.mostrar_estado(
                "Error de impresión",
                "#FF3333"
            )

        return bool(ok)

    def _remote_scan_arriba(self):
        scanner = self.config.config_data.get(
            "scanner2",
            ""
        )

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return False

        self.mostrar_estado(
            "Escaneando arriba",
            "#FFFF00"
        )

        exito, msg = self.scanner.scan_image(
            scanner,
            "arriba.png"
        )

        if exito:
            self.mostrar_estado(
                "Escaneo arriba completado",
                "#00FF00"
            )
        else:
            self.mostrar_estado(
                self.mensaje_error_scanner(msg),
                "#FF3333"
            )

        return bool(exito)

    def _remote_scan_abajo(self):
        scanner = self.config.config_data.get(
            "scanner2",
            ""
        )

        if not scanner:
            self.mostrar_estado(
                "Fallo de escaneo: scanner no configurado",
                "#FF3333"
            )
            return False

        self.mostrar_estado(
            "Escaneando abajo",
            "#FFFF00"
        )

        exito, msg = self.scanner.scan_image(
            scanner,
            "abajo.png"
        )

        if exito:
            self.mostrar_estado(
                "Escaneo abajo completado",
                "#00FF00"
            )
        else:
            self.mostrar_estado(
                self.mensaje_error_scanner(msg),
                "#FF3333"
            )

        return bool(exito)

    def _remote_unir(self):
        self.mostrar_estado(
            "Procesando unión",
            "#FFFF00"
        )

        try:
            ok = procesar_union_y_preview(
                "arriba.png",
                "abajo.png"
            )

            if ok:
                self.mostrar_estado(
                    "Unión completada",
                    "#00FF00"
                )
            else:
                self.mostrar_estado(
                    "Error al procesar la unión: revisa los escaneos",
                    "#FF3333"
                )

            return bool(ok)

        except Exception as e:
            self.mostrar_estado(
                f"Error al procesar la unión: {e}",
                "#FF3333"
            )
            return False

    def _remote_imprimir(self):
        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()
        mejoramiento = self.mejoramiento_imagen.get()

        if not os.path.exists("oficio.png"):
            self.mostrar_estado(
                "Error de impresión: oficio.png no existe",
                "#FF3333"
            )
            return False

        if not printer_name:
            self.mostrar_estado(
                "Error de impresión: impresora no configurada",
                "#FF3333"
            )
            return False

        self.mostrar_estado(
            "Imprimiendo",
            "#FFFF00"
        )

        from core.image_processor import aplicar_mejoras_impresion

        final = aplicar_mejoras_impresion(
            "oficio.png",
            modo,
            mejoramiento
        )

        if not self.printer.seleccionar_impresora(
            printer_name
        ):
            self.mostrar_estado(
                "Error de impresión: impresora no disponible",
                "#FF3333"
            )
            return False

        ok = self.printer.imprimir_archivo(
            final
        )

        if ok:
            self.mostrar_estado(
                "Impresión completada",
                "#00FF00"
            )
        else:
            self.mostrar_estado(
                "Error de impresión",
                "#FF3333"
            )

        return bool(ok)

    def salir_limpio(self):
        try:
            self.server.stop()
        except Exception:
            pass

        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = CopiadoraDeOficios(root)
    root.mainloop()
