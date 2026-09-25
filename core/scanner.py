# -*- coding: utf-8 -*-
import os
import sys
import time
import uuid

import win32com.client
import pythoncom

try:
    import twain
    TWAIN_AVAILABLE = True
except ImportError:
    twain = None
    TWAIN_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    PIL_AVAILABLE = False


class ScannerManager:
    def __init__(self):
        # Constantes WIA
        self.WIA_IMG_FORMAT_PNG = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"
        self.WIA_IPS_XRES = 6147
        self.WIA_IPS_YRES = 6148
        self.WIA_IPA_DATATYPE = 4103  # 1 Color, 2 Grises, 4 Blanco/Negro

        # Registro interno de los dispositivos mostrados en la interfaz.
        # La clave es exactamente el nombre que recibe list_scanners().
        self._scanner_registry = {}

    def _register_scanner(self, display_name, protocol, identifier):
        self._scanner_registry[display_name] = {
            "name": display_name,
            "protocol": protocol,
            "identifier": identifier,
        }

    def _twain_dsm_path(self):
        """Busca primero el DSM TWAIN incluido con el EXE y luego los del sistema."""
        candidates = []

        # PyInstaller --onefile extrae los binarios incluidos en _MEIPASS.
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "TWAINDSM.dll"))

        # Permite trabajar también desde el código fuente.
        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(
            os.path.abspath(os.path.join(module_dir, os.pardir, "TWAINDSM.dll"))
        )

        # Si el EXE está acompañado por el DLL, también lo encontramos aquí.
        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidates.append(os.path.join(exe_dir, "TWAINDSM.dll"))

        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates.append(os.path.join(windir, "TWAINDSM.dll"))
        candidates.append(os.path.join(windir, "twain_32.dll"))

        for path in candidates:
            if os.path.isfile(path):
                return path

        # Conserva un mensaje útil si ningún DSM está instalado.
        return candidates[0] if candidates else os.path.join(windir, "twain_32.dll")

    def _create_twain_source_manager(self):
        """Crea pytwain usando el DSM TWAIN disponible para la aplicación."""
        if not TWAIN_AVAILABLE:
            return None

        dsm_path = self._twain_dsm_path()
        if not os.path.isfile(dsm_path):
            raise RuntimeError(
                "No se encontró el DSM TWAIN. Rutas revisadas: {}".format(dsm_path)
            )

        return twain.SourceManager(0, ProtocolMajor=1, dsm_name=dsm_path)

    def _wia_property(self, info, property_names):
        """Obtiene una propiedad WIA probando nombres compatibles."""
        for property_name in property_names:
            try:
                value = info.Properties(property_name).Value
                value = str(value).strip()
                if value:
                    return value
            except Exception:
                pass
        return ""

    def _list_wia_scanners(self):
        """Enumera los escáneres disponibles mediante WIA."""
        pythoncom.CoInitialize()
        dev_names = []

        try:
            dev_manager = win32com.client.Dispatch("Wia.DeviceManager")
            device_infos = dev_manager.DeviceInfos
            count = int(device_infos.Count)

            # Usamos Count + Item() en lugar de iterar directamente la
            # colección COM. Algunas instalaciones WIA se comportan mejor así.
            for index in range(1, count + 1):
                try:
                    info = device_infos.Item(index)
                    if int(info.Type) != 1:
                        continue

                    # Algunos controladores exponen Name y otros FriendlyName.
                    name = self._wia_property(
                        info,
                        ("Name", "FriendlyName")
                    )
                    if not name:
                        continue

                    try:
                        device_id = str(info.DeviceID)
                    except Exception:
                        device_id = ""

                    dev_names.append((name, device_id))
                except Exception as e:
                    # Un dispositivo defectuoso no debe impedir detectar los demás.
                    print("Aviso WIA: no se pudo leer el dispositivo {}: {}".format(
                        index,
                        e
                    ))
                    continue

        except Exception as e:
            # TWAIN seguirá intentándose por separado.
            print("Error WIA al enumerar scanners: {}".format(e))
        finally:
            pythoncom.CoUninitialize()

        return dev_names

    def _list_twain_scanners(self):
        """Enumera las fuentes TWAIN instaladas en Windows."""
        if not TWAIN_AVAILABLE:
            return []

        sources = []

        try:
            # 0 evita depender de Tkinter y permite que esta función sea llamada
            # desde el hilo que actualiza la configuración.
            with self._create_twain_source_manager() as source_manager:
                for source_name in source_manager.source_list:
                    name = str(source_name)
                    if name:
                        sources.append(name)
        except Exception as e:
            print("Error TWAIN al enumerar fuentes: {}".format(e))
            return []

        return sources

    def list_scanners(self):
        """Devuelve una lista unificada de escáneres WIA y TWAIN."""
        self._scanner_registry = {}
        result = []

        # ---------------------------------------------------------------
        # WIA
        # ---------------------------------------------------------------
        wia_scanners = self._list_wia_scanners()

        for name, device_id in wia_scanners:
            display_name = name
            self._register_scanner(display_name, "WIA", device_id)
            result.append(display_name)

        # ---------------------------------------------------------------
        # TWAIN
        # ---------------------------------------------------------------
        twain_scanners = self._list_twain_scanners()

        for name in twain_scanners:
            # Si el mismo nombre ya existe en WIA, diferenciamos el origen.
            display_name = name
            if display_name in self._scanner_registry:
                display_name = name + " [TWAIN]"

            self._register_scanner(display_name, "TWAIN", name)
            result.append(display_name)

        if not result:
            return ["No se detectaron Scanners"]

        return result

    def _scan_wia(self, scanner_identifier, output_path, dpi=300):
        """Realiza un escaneo usando WIA."""
        pythoncom.CoInitialize()

        temp_file = None
        try:
            dev_manager = win32com.client.Dispatch("Wia.DeviceManager")
            device_infos = dev_manager.DeviceInfos
            count = int(device_infos.Count)
            target_device = None

            for index in range(1, count + 1):
                try:
                    info = device_infos.Item(index)
                    if int(info.Type) != 1:
                        continue

                    device_id = str(info.DeviceID)
                    name = self._wia_property(
                        info,
                        ("Name", "FriendlyName")
                    )

                    if device_id == scanner_identifier or name == scanner_identifier:
                        target_device = info.Connect()
                        break
                except Exception:
                    continue

            if target_device is None:
                return False, "Scanner no encontrado"

            item = target_device.Items[1]

            # --- CONFIGURACIÓN ---
            try:
                # Forzar Color (1 = RGB)
                item.Properties(self.WIA_IPA_DATATYPE).Value = 1
                # Establecer DPI
                item.Properties(self.WIA_IPS_XRES).Value = dpi
                item.Properties(self.WIA_IPS_YRES).Value = dpi
            except Exception:
                print("Aviso: Configuración parcial de hardware WIA.")

            # --- TRANSFERENCIA ---
            temp_file = os.path.join(
                os.environ.get("TEMP", "."),
                "wia_scan_{}.png".format(uuid.uuid4().hex),
            )

            image_wia = item.Transfer(self.WIA_IMG_FORMAT_PNG)
            image_wia.SaveFile(temp_file)

            return self._replace_temp_file(temp_file, output_path)

        except Exception as e:
            msg = str(e)
            if "0x80210006" in msg:
                return False, "Scanner ocupado"
            if "0x80210015" in msg:
                return False, "Scanner desconectado"
            return False, msg
        finally:
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception:
                    pass
            pythoncom.CoUninitialize()

    def _scan_twain(self, source_name, output_path, dpi=300):
        """Realiza un escaneo TWAIN usando el ciclo de mensajes de pytwain."""
        if not TWAIN_AVAILABLE:
            return False, "TWAIN no está disponible en este equipo"

        if not PIL_AVAILABLE:
            return False, "Pillow no está disponible"

        temp_bmp = os.path.join(
            os.environ.get("TEMP", "."),
            "twain_scan_{}.bmp".format(uuid.uuid4().hex),
        )

        try:
            with self._create_twain_source_manager() as source_manager:
                source = source_manager.open_source(source_name)

                if source is None:
                    return False, "Fuente TWAIN no encontrada"

                try:
                    try:
                        source.set_capability(
                            twain.ICAP_XRESOLUTION,
                            twain.TWTY_FIX32,
                            dpi,
                        )
                        source.set_capability(
                            twain.ICAP_YRESOLUTION,
                            twain.TWTY_FIX32,
                            dpi,
                        )
                    except Exception:
                        pass

                    transfer_result = []

                    def on_image(image, remaining_count):
                        image.save(temp_bmp)
                        transfer_result.append(True)

                        if remaining_count:
                            raise twain.CancelAll()

                    source.acquire_natively(
                        after=on_image,
                        show_ui=False,
                        modal=False,
                    )

                    if not transfer_result or not os.path.exists(temp_bmp):
                        return False, "TWAIN no devolvió una imagen"

                    with Image.open(temp_bmp) as image:
                        image.load()
                        image.save(output_path)

                    return True, "OK"

                finally:
                    try:
                        source.close()
                    except Exception:
                        pass

        except Exception as e:
            return False, "TWAIN: {}".format(str(e))
        finally:
            if os.path.exists(temp_bmp):
                try:
                    os.remove(temp_bmp)
                except Exception:
                    pass

    def _replace_temp_file(self, temp_file, output_path):
        """Reemplaza de forma segura el archivo final usando un temporal."""
        if os.path.exists(output_path):
            for _ in range(5):
                try:
                    os.remove(output_path)
                    break
                except Exception:
                    time.sleep(0.3)

        for _ in range(5):
            try:
                os.rename(temp_file, output_path)
                return True, "OK"
            except Exception:
                time.sleep(0.3)

        return False, "Error: El archivo final está bloqueado por otro proceso."

    def scan_image(self, scanner_name, output_path, dpi=300):
        """Escanea usando el backend asociado al nombre seleccionado."""
        if not scanner_name:
            return False, "Nombre de scanner vacío"

        scanner_info = self._scanner_registry.get(scanner_name)
        if scanner_info is None:
            self.list_scanners()
            scanner_info = self._scanner_registry.get(scanner_name)

        if scanner_info is None:
            return False, "Scanner no encontrado"

        protocol = scanner_info["protocol"]
        identifier = scanner_info["identifier"]

        if protocol == "WIA":
            wia_ok, wia_msg = self._scan_wia(identifier, output_path, dpi)
            if wia_ok:
                return True, wia_msg

            if TWAIN_AVAILABLE:
                twain_names = self._list_twain_scanners()
                for twain_name in twain_names:
                    if twain_name == scanner_name or twain_name == identifier:
                        twain_ok, twain_msg = self._scan_twain(
                            twain_name,
                            output_path,
                            dpi
                        )
                        if twain_ok:
                            return True, twain_msg
                        return False, "WIA: {}; TWAIN: {}".format(
                            wia_msg,
                            twain_msg
                        )

            return False, "WIA: {}".format(wia_msg)

        if protocol == "TWAIN":
            return self._scan_twain(identifier, output_path, dpi)

        return False, "Protocolo de scanner no reconocido"
