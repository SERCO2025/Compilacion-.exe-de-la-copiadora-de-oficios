# -*- coding: utf-8 -*-
import sys
import os
import socket
import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading


# ============================================================
# IMPORTACIÓN DE HARDWARE (WINDOWS)
# ============================================================

try:
    import win32print
except ImportError:
    win32print = None


# ============================================================
# MÓDULOS DEL NÚCLEO
# ============================================================

try:
    from core.config_manager import ConfigManager
    from core.scanner import ScannerManager
    from core.image_processor import procesar_union_y_preview
    from core.printer import PrinterManager
    from ui.config_window import ConfigWindow
    from core.network import NetworkServer
except ImportError as e:
    print("Error importando módulos del core: {}".format(e))


# ============================================================
# RUTA DE RECURSOS
# ============================================================

def resource_path(relative_path):
    """Obtiene la ruta absoluta para recursos empaquetados en el .exe."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# ============================================================
# IP LOCAL
# ============================================================

def obtener_ip_local():
    """Detecta la IP real de la PC en la red local para la APK."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


# ============================================================
# INDICADOR DE ESTADO
# ============================================================

class IndicadorEstado:
    def __init__(self, parent):
        self.parent = parent
        self.var = tk.StringVar(value="Listo")

        self.entry = tk.Entry(
            parent,
            textvariable=self.var,
            state="readonly",
            readonlybackground="#001A33",
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

        self.entry.xview_moveto(0.0)

        self.parent.update_idletasks()

    def desplazar_horizontal(self, event):
        if event.delta:
            self.entry.xview_scroll(
                int(-event.delta / 120),
                "units"
            )

        return "break"


# ============================================================
# BOTÓN 3D TIPO CÁPSULA
# ============================================================

class BotonChingon(tk.Canvas):

    def __init__(
        self,
        parent,
        text,
        color,
        command,
        width=280,
        height=55,
        **kwargs
    ):
        self.width = width
        self.height = height
        self.color = color
        self.text = text
        self.command = command

        self.pressed = False
        self.hover = False

        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#0050C8",
            highlightthickness=0,
            bd=0,
            relief="flat",
            **kwargs
        )

        self.bind(
            "<Enter>",
            self.on_enter
        )

        self.bind(
            "<Leave>",
            self.on_leave
        )

        self.bind(
            "<ButtonPress-1>",
            self.on_press
        )

        self.bind(
            "<ButtonRelease-1>",
            self.on_release
        )

        self.dibujar_boton()

    # --------------------------------------------------------
    # CONVERSIÓN DE COLOR
    # --------------------------------------------------------

    def hex_to_rgb(self, color):
        color = color.lstrip("#")

        if len(color) != 6:
            return 0, 0, 0

        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16)
        )

    def rgb_to_hex(self, rgb):
        return "#{:02X}{:02X}{:02X}".format(
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2])))
        )

    def aclarar_color(self, color, cantidad):
        r, g, b = self.hex_to_rgb(color)

        return self.rgb_to_hex(
            (
                r + (255 - r) * cantidad,
                g + (255 - g) * cantidad,
                b + (255 - b) * cantidad
            )
        )

    def oscurecer_color(self, color, cantidad):
        r, g, b = self.hex_to_rgb(color)

        return self.rgb_to_hex(
            (
                r * (1.0 - cantidad),
                g * (1.0 - cantidad),
                b * (1.0 - cantidad)
            )
        )

    # --------------------------------------------------------
    # RECTÁNGULO REDONDEADO
    # --------------------------------------------------------

    def rounded_rectangle(
        self,
        x1,
        y1,
        x2,
        y2,
        radius,
        fill,
        outline=None,
        width=1,
        tags=None
    ):
        if radius > (x2 - x1) / 2:
            radius = (x2 - x1) / 2

        if radius > (y2 - y1) / 2:
            radius = (y2 - y1) / 2

        if outline is None:
            outline = fill

        tag = tags

        self.create_rectangle(
            x1 + radius,
            y1,
            x2 - radius,
            y2,
            fill=fill,
            outline=outline,
            width=width,
            tags=tag
        )

        self.create_rectangle(
            x1,
            y1 + radius,
            x2,
            y2 - radius,
            fill=fill,
            outline=outline,
            width=width,
            tags=tag
        )

        self.create_arc(
            x1,
            y1,
            x1 + radius * 2,
            y1 + radius * 2,
            start=90,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
            style="pieslice",
            tags=tag
        )

        self.create_arc(
            x2 - radius * 2,
            y1,
            x2,
            y1 + radius * 2,
            start=0,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
            style="pieslice",
            tags=tag
        )

        self.create_arc(
            x1,
            y2 - radius * 2,
            x1 + radius * 2,
            y2,
            start=180,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
            style="pieslice",
            tags=tag
        )

        self.create_arc(
            x2 - radius * 2,
            y2 - radius * 2,
            x2,
            y2,
            start=270,
            extent=90,
            fill=fill,
            outline=outline,
            width=width,
            style="pieslice",
            tags=tag
        )

    # --------------------------------------------------------
    # DIBUJAR BOTÓN
    # --------------------------------------------------------

    def dibujar_boton(self, offset=0):

        self.delete("all")

        w = self.width
        h = self.height

        # ----------------------------------------------------
        # CONFIGURACIÓN
        # ----------------------------------------------------

        margin_x = 4
        margin_y = 3

        x1 = margin_x + offset
        y1 = margin_y + offset
        x2 = w - margin_x + offset
        y2 = h - margin_y + offset

        radius = min(26, h // 2)

        # ----------------------------------------------------
        # COLOR BASE
        # ----------------------------------------------------

        base = self.color

        if self.hover and not self.pressed:
            base = self.aclarar_color(
                base,
                0.08
            )

        if self.pressed:
            base = self.oscurecer_color(
                base,
                0.10
            )

        # ----------------------------------------------------
        # SOMBRA PROFUNDA
        # ----------------------------------------------------

        sombra_y = 5

        self.rounded_rectangle(
            x1,
            y1 + sombra_y,
            x2,
            y2 + sombra_y,
            radius,
            fill="#00336F",
            outline="#00336F"
        )

        # ----------------------------------------------------
        # BORDE OSCURO
        # ----------------------------------------------------

        self.rounded_rectangle(
            x1,
            y1,
            x2,
            y2,
            radius,
            fill="#003C8F",
            outline="#002E70"
        )

        # ----------------------------------------------------
        # CUERPO PRINCIPAL
        # ----------------------------------------------------

        inner = 2

        self.rounded_rectangle(
            x1 + inner,
            y1 + inner,
            x2 - inner,
            y2 - inner,
            radius - 2,
            fill=base,
            outline=base
        )

        # ----------------------------------------------------
        # BRILLO SUPERIOR
        # ----------------------------------------------------

        brillo = self.aclarar_color(
            base,
            0.28
        )

        brillo_y1 = y1 + 5
        brillo_y2 = y1 + int(h * 0.30)

        self.rounded_rectangle(
            x1 + 5,
            brillo_y1,
            x2 - 5,
            brillo_y2,
            max(8, radius - 7),
            fill=brillo,
            outline=brillo
        )

        # ----------------------------------------------------
        # LÍNEA DE BRILLO SUTIL
        # ----------------------------------------------------

        self.create_line(
            x1 + radius,
            y1 + 4,
            x2 - radius,
            y1 + 4,
            fill=self.aclarar_color(base, 0.42),
            width=1,
            capstyle="round"
        )

        # ----------------------------------------------------
        # TEXTO
        # ----------------------------------------------------

        if self.color.upper() in (
            "#FFFF00",
            "#FFD700",
            "#FFC107"
        ):
            text_color = "#FFFFFF"
        else:
            text_color = "#FFFFFF"

        # Sombra del texto
        self.create_text(
            (x1 + x2) // 2 + 1,
            (y1 + y2) // 2 + 2 + offset,
            text=self.text,
            fill="#00316B",
            font=("Arial", 15, "bold"),
            anchor="center"
        )

        # Texto principal
        self.create_text(
            (x1 + x2) // 2,
            (y1 + y2) // 2 + offset,
            text=self.text,
            fill=text_color,
            font=("Arial", 15, "bold"),
            anchor="center"
        )

    # --------------------------------------------------------
    # MOUSE
    # --------------------------------------------------------

    def on_enter(self, event):
        self.hover = True
        self.dibujar_boton(
            2 if self.pressed else 0
        )

    def on_leave(self, event):
        self.hover = False
        self.dibujar_boton(
            2 if self.pressed else 0
        )

    def on_press(self, event):
        self.pressed = True
        self.dibujar_boton(offset=2)

    def on_release(self, event):

        estaba_presionado = self.pressed

        self.pressed = False

        self.dibujar_boton(offset=0)

        if estaba_presionado:

            # Verifica que el cursor siga dentro del botón.
            if (
                0 <= event.x <= self.width and
                0 <= event.y <= self.height
            ):
                self.command()


# ============================================================
# BOTÓN PEQUEÑO PARA CONFIGURACIÓN Y SALIR
# ============================================================

class BotonPequeno3D(tk.Canvas):

    def __init__(
        self,
        parent,
        text,
        command,
        color,
        width=52,
        height=42
    ):
        self.width = width
        self.height = height
        self.text = text
        self.command = command
        self.color = color
        self.pressed = False
        self.hover = False

        super().__init__(
            parent,
            width=width,
            height=height,
            bg="#0047AB",
            highlightthickness=0,
            bd=0
        )

        self.bind(
            "<Enter>",
            self.on_enter
        )

        self.bind(
            "<Leave>",
            self.on_leave
        )

        self.bind(
            "<ButtonPress-1>",
            self.on_press
        )

        self.bind(
            "<ButtonRelease-1>",
            self.on_release
        )

        self.dibujar()

    def hex_to_rgb(self, color):
        color = color.lstrip("#")

        return (
            int(color[0:2], 16),
            int(color[2:4], 16),
            int(color[4:6], 16)
        )

    def rgb_to_hex(self, rgb):
        return "#{:02X}{:02X}{:02X}".format(
            max(0, min(255, int(rgb[0]))),
            max(0, min(255, int(rgb[1]))),
            max(0, min(255, int(rgb[2])))
        )

    def aclarar(self, color, cantidad):
        r, g, b = self.hex_to_rgb(color)

        return self.rgb_to_hex(
            (
                r + (255 - r) * cantidad,
                g + (255 - g) * cantidad,
                b + (255 - b) * cantidad
            )
        )

    def rounded(self, x1, y1, x2, y2, radius, fill):

        self.create_rectangle(
            x1 + radius,
            y1,
            x2 - radius,
            y2,
            fill=fill,
            outline=fill
        )

        self.create_rectangle(
            x1,
            y1 + radius,
            x2,
            y2 - radius,
            fill=fill,
            outline=fill
        )

        self.create_oval(
            x1,
            y1,
            x1 + radius * 2,
            y1 + radius * 2,
            fill=fill,
            outline=fill
        )

        self.create_oval(
            x2 - radius * 2,
            y1,
            x2,
            y1 + radius * 2,
            fill=fill,
            outline=fill
        )

        self.create_oval(
            x1,
            y2 - radius * 2,
            x1 + radius * 2,
            y2,
            fill=fill,
            outline=fill
        )

        self.create_oval(
            x2 - radius * 2,
            y2 - radius * 2,
            x2,
            y2,
            fill=fill,
            outline=fill
        )

    def dibujar(self):

        self.delete("all")

        offset = 2 if self.pressed else 0

        x1 = 2 + offset
        y1 = 2 + offset
        x2 = self.width - 2 + offset
        y2 = self.height - 4 + offset

        # Sombra
        self.rounded(
            x1,
            y1 + 4,
            x2,
            y2 + 4,
            13,
            "#002E70"
        )

        # Cuerpo
        color = self.color

        if self.hover:
            color = self.aclarar(
                color,
                0.12
            )

        self.rounded(
            x1,
            y1,
            x2,
            y2,
            13,
            color
        )

        # Brillo
        self.rounded(
            x1 + 4,
            y1 + 3,
            x2 - 4,
            y1 + 12,
            5,
            self.aclarar(color, 0.25)
        )

        # Texto
        self.create_text(
            (x1 + x2) / 2 + 1,
            (y1 + y2) / 2 + 1,
            text=self.text,
            fill="#00316B",
            font=("Arial", 17, "bold")
        )

        self.create_text(
            (x1 + x2) / 2,
            (y1 + y2) / 2,
            text=self.text,
            fill="white",
            font=("Arial", 17, "bold")
        )

    def on_enter(self, event):
        self.hover = True
        self.dibujar()

    def on_leave(self, event):
        self.hover = False
        self.dibujar()

    def on_press(self, event):
        self.pressed = True
        self.dibujar()

    def on_release(self, event):

        estaba = self.pressed

        self.pressed = False
        self.dibujar()

        if estaba:
            if (
                0 <= event.x <= self.width and
                0 <= event.y <= self.height
            ):
                self.command()


# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

class CopiadoraDeOficios:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "COPIADORA DE OFICIOS"
        )

        self.root.geometry(
            "400x650"
        )

        self.root.overrideredirect(
            True
        )

        # Azul principal del programa
        self.root.configure(
            bg="#0047AB"
        )

        # ----------------------------------------------------
        # CONFIGURACIÓN
        # ----------------------------------------------------

        self.config = ConfigManager()

        self.scanner = ScannerManager()

        self.printer = PrinterManager(
            self.config.config_data.get(
                "impresora",
                ""
            )
        )

        self.modo_imagen = tk.StringVar(
            value=self.config.config_data.get(
                "modo",
                "BN"
            )
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

        # ----------------------------------------------------
        # MOVIMIENTO DE VENTANA
        # ----------------------------------------------------

        self.root.bind(
            "<ButtonPress-1>",
            self.start_move
        )

        self.root.bind(
            "<B1-Motion>",
            self.do_move
        )

        # ----------------------------------------------------
        # INTERFAZ
        # ----------------------------------------------------

        self.setup_ui()

        # ----------------------------------------------------
        # SERVIDOR DE RED
        # ----------------------------------------------------

        self.server = NetworkServer(
            port=self.puerto,
            callback=self.process_remote
        )

        self.server.start()

    # ========================================================
    # INTERFAZ
    # ========================================================

    def setup_ui(self):

        # ----------------------------------------------------
        # ENCABEZADO
        # ----------------------------------------------------

        header = tk.Frame(
            self.root,
            bg="#0047AB"
        )

        header.pack(
            fill="x",
            padx=10,
            pady=4
        )

        # Botón configuración
        self.btn_config = BotonPequeno3D(
            header,
            "⚙",
            self.abrir_config,
            "#40546A",
            width=48,
            height=40
        )

        self.btn_config.pack(
            side="left"
        )

        # Botón salir
        self.btn_exit = BotonPequeno3D(
            header,
            "×",
            self.salir_limpio,
            "#D92D2D",
            width=48,
            height=40
        )

        self.btn_exit.pack(
            side="right"
        )

        # ----------------------------------------------------
        # TÍTULO
        # ----------------------------------------------------

        tk.Label(
            self.root,
            text="COPIADORA DE OFICIOS",
            bg="#0047AB",
            fg="#20E5E5",
            font=("Arial", 25, "bold")
        ).pack(
            pady=(5, 7)
        )

        # ----------------------------------------------------
        # INDICADOR DE ESTADO
        # ----------------------------------------------------

        self.estado = IndicadorEstado(
            self.root
        )

        # ----------------------------------------------------
        # COPIA DIRECTA
        # ----------------------------------------------------

        self.btn_directa = BotonChingon(
            self.root,
            "COPIA DIRECTA",
            "#18D83E",
            self.cmd_copia_directa,
            width=310,
            height=58
        )

        self.btn_directa.pack(
            pady=4
        )

        # ----------------------------------------------------
        # ESCANEAR ARRIBA
        # ----------------------------------------------------

        self.btn_up = BotonChingon(
            self.root,
            "ESCANEAR ARRIBA",
            "#1674E8",
            self.cmd_scan_arriba,
            width=300,
            height=46
        )

        self.btn_up.pack(
            pady=3
        )

        # ----------------------------------------------------
        # ESCANEAR ABAJO
        # ----------------------------------------------------

        self.btn_down = BotonChingon(
            self.root,
            "ESCANEAR ABAJO",
            "#1674E8",
            self.cmd_scan_abajo,
            width=300,
            height=46
        )

        self.btn_down.pack(
            pady=3
        )

        # ----------------------------------------------------
        # UNIR PARTES
        # ----------------------------------------------------

        self.btn_unir = BotonChingon(
            self.root,
            "UNIR PARTES",
            "#F08A00",
            self.cmd_unir,
            width=300,
            height=46
        )

        self.btn_unir.pack(
            pady=3
        )

        # ----------------------------------------------------
        # PREVISUALIZAR
        # ----------------------------------------------------

        self.btn_preview = BotonChingon(
            self.root,
            "PREVISUALIZAR",
            "#F5C400",
            self.cmd_preview,
            width=300,
            height=46
        )

        self.btn_preview.pack(
            pady=3
        )

        # ----------------------------------------------------
        # IMPRIMIR
        # ----------------------------------------------------

        self.btn_print = BotonChingon(
            self.root,
            "IMPRIMIR OFICIO",
            "#18D83E",
            self.cmd_imprimir_oficio,
            width=310,
            height=58
        )

        self.btn_print.pack(
            pady=4
        )

        # ----------------------------------------------------
        # MODO DE IMAGEN
        # ----------------------------------------------------

        mode_frame = tk.Frame(
            self.root,
            bg="#0047AB"
        )

        mode_frame.pack(
            pady=5
        )

        tk.Radiobutton(
            mode_frame,
            text="B/N",
            variable=self.modo_imagen,
            value="BN",
            bg="#0047AB",
            fg="white",
            activebackground="#0047AB",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            selectcolor="#00316B",
            command=self.cambiar_modo
        ).pack(
            side="left",
            padx=8
        )

        tk.Radiobutton(
            mode_frame,
            text="COLOR",
            variable=self.modo_imagen,
            value="COLOR",
            bg="#0047AB",
            fg="white",
            activebackground="#0047AB",
            activeforeground="white",
            font=("Arial", 11, "bold"),
            selectcolor="#00316B",
            command=self.cambiar_modo
        ).pack(
            side="left",
            padx=8
        )

        # ----------------------------------------------------
        # MEJORAMIENTO
        # ----------------------------------------------------

        tk.Checkbutton(
            self.root,
            text="MEJORAMIENTO DE IMAGEN",
            variable=self.mejoramiento_imagen,
            bg="#0047AB",
            fg="#FFF200",
            activebackground="#0047AB",
            activeforeground="#FFF200",
            selectcolor="#00316B",
            font=("Arial", 10, "bold"),
            command=self.cambiar_mejoramiento
        ).pack(
            pady=2
        )

    # ========================================================
    # ESTADO
    # ========================================================

    def mostrar_estado(
        self,
        mensaje,
        color="#00FF00"
    ):
        """Actualiza el indicador desde cualquier hilo."""

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

    # ========================================================
    # ERROR DE SCANNER
    # ========================================================

    def mensaje_error_scanner(
        self,
        detalle
    ):
        """Devuelve el texto apropiado para un error de escáner."""

        detalle = str(
            detalle or ""
        )

        if "desconectado" in detalle.lower():
            return "Scanner desconectado"

        return "Fallo de escaneo"

    # ========================================================
    # MOVIMIENTO DE VENTANA
    # ========================================================

    def start_move(self, event):
        self.x, self.y = event.x, event.y

    def do_move(self, event):

        x = (
            self.root.winfo_x() +
            (event.x - self.x)
        )

        y = (
            self.root.winfo_y() +
            (event.y - self.y)
        )

        self.root.geometry(
            "+{}+{}".format(
                x,
                y
            )
        )

    # ========================================================
    # COPIA DIRECTA
    # ========================================================

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

        mejoramiento = (
            self.mejoramiento_imagen.get()
        )

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

            from core.image_processor import (
                aplicar_mejoras_impresion
            )

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

    # ========================================================
    # ESCANEAR ARRIBA
    # ========================================================

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

    # ========================================================
    # ESCANEAR ABAJO
    # ========================================================

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

    # ========================================================
    # UNIR
    # ========================================================

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
                    "Error al procesar la unión: {}".format(e),
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    # ========================================================
    # PREVISUALIZAR
    # ========================================================

    def cmd_preview(self):

        if os.path.exists(
            "oficio.png"
        ):

            os.startfile(
                "oficio.png"
            )

        else:

            self.mostrar_estado(
                "Error: oficio.png no existe",
                "#FF3333"
            )

    # ========================================================
    # IMPRIMIR OFICIO
    # ========================================================

    def cmd_imprimir_oficio(self):

        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()

        mejoramiento = (
            self.mejoramiento_imagen.get()
        )

        if not os.path.exists(
            "oficio.png"
        ):

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

                from core.image_processor import (
                    aplicar_mejoras_impresion
                )

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
                    "Error de impresión: {}".format(e),
                    "#FF3333"
                )

        threading.Thread(
            target=run,
            daemon=True
        ).start()

    # ========================================================
    # CONFIGURACIÓN
    # ========================================================

    def abrir_config(self):

        ConfigWindow(
            self.root,
            self.config,
            self.scanner,
            self.printer,
            on_saved=self._actualizar_configuracion
        )

    # ========================================================
    # ACTUALIZAR CONFIGURACIÓN
    # ========================================================

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

    # ========================================================
    # CAMBIAR MODO
    # ========================================================

    def cambiar_modo(self):

        self.config.update_setting(
            "modo",
            self.modo_imagen.get()
        )

    # ========================================================
    # MEJORAMIENTO
    # ========================================================

    def cambiar_mejoramiento(self):

        self.config.update_setting(
            "mejoramiento",
            bool(
                self.mejoramiento_imagen.get()
            )
        )

    # ========================================================
    # COMANDOS REMOTOS
    # ========================================================

    def process_remote(self, cmd):

        operaciones = {
            "COPIA_DIRECTA":
                self._remote_copia_directa,

            "ESCANEAR_ARRIBA":
                self._remote_scan_arriba,

            "ESCANEAR_ABAJO":
                self._remote_scan_abajo,

            "UNIR":
                self._remote_unir,

            "IMPRIMIR":
                self._remote_imprimir,
        }

        operacion = operaciones.get(
            cmd
        )

        if operacion is None:
            return False

        try:

            return bool(
                operacion()
            )

        except Exception as e:

            print(
                "ERROR en comando remoto {}: {}".format(
                    cmd,
                    e
                )
            )

            self.mostrar_estado(
                "Error en comando remoto: {}".format(e),
                "#FF3333"
            )

            return False

    # ========================================================
    # REMOTO - COPIA DIRECTA
    # ========================================================

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

        mejoramiento = (
            self.mejoramiento_imagen.get()
        )

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

        from core.image_processor import (
            aplicar_mejoras_impresion
        )

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

    # ========================================================
    # REMOTO - ESCANEAR ARRIBA
    # ========================================================

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

    # ========================================================
    # REMOTO - ESCANEAR ABAJO
    # ========================================================

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

    # ========================================================
    # REMOTO - UNIR
    # ========================================================

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
                "Error al procesar la unión: {}".format(e),
                "#FF3333"
            )

            return False

    # ========================================================
    # REMOTO - IMPRIMIR
    # ========================================================

    def _remote_imprimir(self):

        printer_name = self.config.config_data.get(
            "impresora",
            ""
        )

        modo = self.modo_imagen.get()

        mejoramiento = (
            self.mejoramiento_imagen.get()
        )

        if not os.path.exists(
            "oficio.png"
        ):

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

        from core.image_processor import (
            aplicar_mejoras_impresion
        )

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

    # ========================================================
    # SALIR
    # ========================================================

    def salir_limpio(self):

        try:

            self.server.stop()

        except Exception:
            pass

        self.root.destroy()


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = CopiadoraDeOficios(
        root
    )

    root.mainloop()