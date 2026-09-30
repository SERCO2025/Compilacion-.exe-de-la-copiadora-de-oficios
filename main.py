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
        self._scroll_job = None
        self._scroll_position = 0

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
        if self._scroll_job is not None:
            try:
                self.entry.after_cancel(self._scroll_job)
            except Exception:
                pass
            self._scroll_job = None

        self.var.set(str(mensaje))
        self.entry.configure(fg=color)
        self.entry.xview_moveto(0.0)
        self._scroll_position = 0
        self._scroll_direction = 1

        self.parent.update_idletasks()

        # Si el mensaje es largo, comienza desde la izquierda, hace una pausa
        # y después se desplaza lentamente de lado a lado.
        if len(str(mensaje)) > 42:
            self._scroll_job = self.entry.after(
                900,
                self._auto_scroll
            )

    def _auto_scroll(self):
        texto = self.var.get()

        if len(texto) <= 42:
            self._scroll_job = None
            return

        first, last = self.entry.xview()

        if self._scroll_direction > 0 and last >= 0.999:
            self._scroll_direction = -1
        elif self._scroll_direction < 0 and first <= 0.001:
            self._scroll_direction = 1

        self.entry.xview_scroll(
            self._scroll_direction,
            "units"
        )

        self._scroll_job = self.entry.after(
            180,
            self._auto_scroll
        )

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