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
        self.WIA_IMG_FORMAT_PNG = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"
        self.WIA_IPS_XRES = 6147
        self.WIA_IPS_YRES = 6148
        self.WIA_IPA_DATATYPE = 4103
        self._scanner_registry = {}

    def _register_scanner(self, display_name, protocol, identifier):
        self._scanner_registry[display_name] = {
            "name": display_name,
            "protocol": protocol,
            "identifier": identifier,
        }

    def _twain_dsm_path(self):
        candidates = []

        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(os.path.join(meipass, "TWAINDSM.dll"))

        module_dir = os.path.dirname(os.path.abspath(__file__))
        candidates.append(
            os.path.abspath(os.path.join(module_dir, os.pardir, "TWAINDSM.dll"))
        )

        exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        candidates.append(os.path.join(exe_dir, "TWAINDSM.dll"))

        windir = os.environ.get("WINDIR", r"C:\Windows")
        candidates.append(os.path.join(windir, "TWAINDSM.dll"))
        candidates.append(os.path.join(windir, "twain_32.dll"))

        for path in candidates:
            if os.path.isfile(path):
                return path

        return candidates[0] if candidates else os.path.join(windir, "twain_32.dll")

    def _create_twain_source_manager(self):
        if not TWAIN_AVAILABLE:
            return None

        dsm_path = self._twain_dsm_path()
        if not os.path.isfile(dsm_path):
            raise RuntimeError(
                "No se encontró el DSM TWAIN. Rutas revisadas: {}".format(dsm_path)
            )

        return twain.SourceManager(0, ProtocolMajor=1, dsm_name=dsm_path)

    def _wia_property(self, info, property_names):
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
        pythoncom.CoInitialize()
        dev_names = []

        try:
            dev_manager = win32com.client.Dispatch("Wia.DeviceManager")
            device_infos = dev_manager.DeviceInfos
            count = int(device_infos.Count)

            for index in range(1, count + 1):
                try:
                    info = device_infos.Item(index)
                    if int(info.Type) != 1:
                        continue

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
                    print("Aviso WIA: no se pudo leer el dispositivo {}: {}".format(
                        index,
                        e
                    ))
                    continue

        except Exception as e:
            print("Error WIA al enumerar scanners: {}".format(e))
        finally:
            pythoncom.CoUninitialize()

        return dev_names

    def _list_twain_scanners(self):
        if not TWAIN_AVAILABLE:
            return []

        sources = []

        try:
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
        self._scanner_registry = {}
        result = []

        wia_scanners = self._list_wia_scanners()

        for name, device_id in wia_scanners:
            display_name = name
            self._register_scanner(display_name, "WIA", device_id)
            result.append(display_name)

        twain_scanners = self._list_twain_scanners()

        for name in twain_scanners:
            display_name = name
            if display_name in self._scanner_registry:
                display_name = name + " [TWAIN]"

            self._register_scanner(display_name, "TWAIN", name)
            result.append(display_name)

        if not result:
            return ["No se detectaron Scanners"]

        return result

    def _scan_wia(self, scanner_identifier, output_path, dpi=300):
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

            try:
                item.Properties(self.WIA_IPA_DATATYPE).Value = 1
                item.Properties(self.WIA_IPS_XRES).Value = dpi
                item.Properties(self.WIA_IPS_YRES).Value = dpi
            except Exception:
                print("Aviso: Configuración parcial de hardware WIA.")

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
        """Adquiere una sola imagen TWAIN y convierte el DIB nativo a BMP."""
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

                    source.request_acquire(
                        show_ui=False,
                        modal_ui=False,
                    )

                    handle, remaining_count = source.xfer_image_natively()

                    if not handle:
                        return False, "TWAIN no devolvió una imagen"

                    twain.dib_to_bm_file(
                        handle,
                        temp_bmp
                    )

                    if not os.path.exists(temp_bmp):
                        return False, "TWAIN no generó el archivo de imagen"

                    with Image.open(temp_bmp) as scanned_image:
                        scanned_image.load()
                        scanned_image.save(output_path)

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
