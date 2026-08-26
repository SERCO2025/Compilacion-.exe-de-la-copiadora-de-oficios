# -*- coding: utf-8 -*-
import win32com.client
import pythoncom
import os
import time

class ScannerManager:
    def __init__(self):
        # Constantes WIA
        self.WIA_IMG_FORMAT_PNG = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"
        self.WIA_IPS_XRES = 6147
        self.WIA_IPS_YRES = 6148
        self.WIA_IPA_DATATYPE = 4103 # 1 para Color, 2 Grises, 4 Blanco/Negro
        
    def list_scanners(self):
        pythoncom.CoInitialize()
        dev_names = []
        try:
            dev_manager = win32com.client.Dispatch("Wia.DeviceManager")
            for info in dev_manager.DeviceInfos:
                if info.Type == 1:
                    # Propiedad 10 es el "Name" amigable
                    dev_names.append(info.Properties("Name").Value)
            return dev_names if dev_names else ["No se detectaron Scanners"]
        except Exception as e:
            return [f"Error: {str(e)}"]
        finally:
            pythoncom.CoUninitialize()

    def scan_image(self, scanner_name, output_path, dpi=300):
        if not scanner_name:
            return False, "Nombre de scanner vacío"

        pythoncom.CoInitialize()
        try:
            dev_manager = win32com.client.Dispatch("Wia.DeviceManager")
            target_device = None

            for info in dev_manager.DeviceInfos:
                if info.Properties("Name").Value == scanner_name:
                    target_device = info.Connect()
                    break
            
            if not target_device: 
                return False, "Scanner no encontrado"

            item = target_device.Items[1]

            # --- CONFIGURACIÓN PRO ---
            try:
                # Forzar Color (1 = RGB)
                item.Properties(self.WIA_IPA_DATATYPE).Value = 1
                # Setear DPI
                item.Properties(self.WIA_IPS_XRES).Value = dpi
                item.Properties(self.WIA_IPS_YRES).Value = dpi
            except:
                print("Aviso: Configuración parcial de hardware.")

            # --- TRANSFERENCIA ---
            # WIA es caprichoso: a veces SaveFile falla si el archivo existe.
            # Mejor escaneamos a un temporal y luego lo movemos.
            temp_file = os.path.join(os.environ['TEMP'], f"wia_scan_{int(time.time())}.png")
            
            image_wia = item.Transfer(self.WIA_IMG_FORMAT_PNG)
            image_wia.SaveFile(temp_file)

            # Mover el temporal al destino final (limpiando el camino con reintentos)
            if os.path.exists(output_path):
                for _ in range(5):
                    try:
                        os.remove(output_path)
                        break
                    except:
                        time.sleep(0.3)

            # Reintento de renombrado para evitar el error de "archivo en uso"
            for _ in range(5):
                try:
                    os.rename(temp_file, output_path)
                    return True, "OK"
                except:
                    time.sleep(0.3)
            
            return False, "Error: El archivo final está bloqueado por otro proceso."

        except Exception as e:
            msg = str(e)
            if "0x80210006" in msg: return False, "Scanner ocupado"
            if "0x80210015" in msg: return False, "Scanner desconectado"
            return False, msg
        finally:
            pythoncom.CoUninitialize()