import os
import win32ui
import win32con
from PIL import Image, ImageWin


class PrinterManager:
    """Impresion a escala fisica 1:1 basada en 300 DPI."""

    DPI_DOCUMENTO = 300
    OFICIO_ANCHO_PULGADAS = 8.5
    OFICIO_ALTO_PULGADAS = 13.0
    PAPER_OFICIO = 14  # DMPAPER_FOLIO: 8.5 x 13 in

    def __init__(self, printer_name=None):
        self.printer_name = printer_name

    @staticmethod
    def listar_impresoras():
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [printer[2] for printer in win32print.EnumPrinters(flags)]

    def seleccionar_impresora(self, printer_name):
        if not printer_name:
            self.printer_name = ""
            return False
        if printer_name not in self.listar_impresoras():
            return False
        self.printer_name = printer_name
        return True


    def _configurar_papel_oficio(self):
        import win32print
        handle = win32print.OpenPrinter(self.printer_name)
        try:
            info = win32print.GetPrinter(handle, 2)
            devmode = info.get("pDevMode")
            if devmode is None:
                raise RuntimeError("El controlador no proporciono DEVMODE.")
            devmode.PaperSize = self.PAPER_OFICIO
            try:
                devmode.Fields |= 0x00000002  # DM_PAPERSIZE
                devmode.Orientation = 1         # DMORIENT_PORTRAIT
                devmode.Fields |= 0x00000001   # DM_ORIENTATION
            except Exception:
                pass
            return devmode, info.get("pDriverName")
        finally:
            win32print.ClosePrinter(handle)

    def _crear_dc_oficio(self):
        devmode, driver = self._configurar_papel_oficio()
        if not driver:
            raise RuntimeError(
                "El controlador de la impresora no fue proporcionado por Windows; "
                "no se puede garantizar la configuracion Oficio."
            )

        dc = win32ui.CreateDC()
        try:
            dc.CreateDC(driver, self.printer_name, None, devmode)
            return dc, True
        except Exception as e:
            try:
                dc.DeleteDC()
            except Exception:
                pass
            raise RuntimeError(
                "No fue posible crear el contexto de impresion con papel Oficio."
            ) from e

    def imprimir_archivo(self, ruta_imagen):
        """
        Imprime a escala fisica 1:1 respecto de una imagen interpretada
        a 300 DPI. No aplica 'fit to page'. Si parte de la imagen queda
        fuera del area imprimible, esa parte se pierde.
        """
        if not self.printer_name:
            print("ERROR: No hay impresora configurada.")
            return False
        if not os.path.isfile(ruta_imagen):
            print(f"ERROR: No existe el archivo: {ruta_imagen}")
            return False
        try:
            image = Image.open(ruta_imagen)
            image.load()
            hDC, devmode_aplicado = self._crear_dc_oficio()
            try:
                dpi_x = hDC.GetDeviceCaps(win32con.LOGPIXELSX)
                dpi_y = hDC.GetDeviceCaps(win32con.LOGPIXELSY)
                if dpi_x <= 0 or dpi_y <= 0:
                    raise RuntimeError("El controlador no devolvio DPI validos.")

                physical_width = hDC.GetDeviceCaps(win32con.PHYSICALWIDTH)
                physical_height = hDC.GetDeviceCaps(win32con.PHYSICALHEIGHT)
                printable_width = hDC.GetDeviceCaps(win32con.HORZRES)
                printable_height = hDC.GetDeviceCaps(win32con.VERTRES)

                # La imagen representa image.width/image.DPI_DOCUMENTO pulgadas.
                # No se escala para hacerla caber en HORZRES/VERTRES.
                physical_width_in = image.width / float(self.DPI_DOCUMENTO)
                physical_height_in = image.height / float(self.DPI_DOCUMENTO)
                draw_width = int(round(physical_width_in * dpi_x))
                draw_height = int(round(physical_height_in * dpi_y))

                physical_offset_x = hDC.GetDeviceCaps(win32con.PHYSICALOFFSETX)
                physical_offset_y = hDC.GetDeviceCaps(win32con.PHYSICALOFFSETY)

                if physical_width <= 0 or physical_height <= 0:
                    raise RuntimeError(
                        "El controlador no devolvio dimensiones fisicas validas."
                    )
                if printable_width <= 0 or printable_height <= 0:
                    raise RuntimeError(
                        "El controlador no devolvio un area imprimible valida."
                    )
                if physical_offset_x < 0 or physical_offset_y < 0:
                    raise RuntimeError(
                        "El controlador devolvio offsets fisicos invalidos."
                    )

                # El origen (0, 0) del DC corresponde al inicio del area imprimible.
                # Para colocar la imagen respecto del borde fisico de la hoja,
                # desplazamos el dibujo hacia atras exactamente el offset no imprimible.
                # No se reduce la imagen para hacerla caber: el dispositivo recorta
                # cualquier zona que quede fuera de su area fisicamente imprimible.
                left = -int(physical_offset_x)
                top = -int(physical_offset_y)

                dib = ImageWin.Dib(image)
                hDC.StartDoc(os.path.basename(ruta_imagen))
                try:
                    hDC.StartPage()
                    try:
                        dib.draw(hDC.GetHandleOutput(),
                                 (left, top, left + draw_width, top + draw_height))
                    finally:
                        hDC.EndPage()
                finally:
                    hDC.EndDoc()

                print(
                    f"Impresion enviada | escala=1:1 a {self.DPI_DOCUMENTO} DPI | "
                    f"imagen={image.width}x{image.height}px | "
                    f"fisico={physical_width_in:.4f}x{physical_height_in:.4f}in | "
                    f"salida={draw_width}x{draw_height}px | "
                    f"printer_dpi={dpi_x}x{dpi_y} | "
                    f"area_imprimible={printable_width}x{printable_height}px | "
                    f"offset={physical_offset_x},{physical_offset_y}px | "
                    f"DEVMODE_oficio={'SI' if devmode_aplicado else 'NO'}"
                )
                return True
            finally:
                try: hDC.DeleteDC()
                except Exception: pass
        except Exception as e:
            print(f"ERROR DE IMPRESION: {e}")
            return False
