# -*- coding: utf-8 -*-
import json
import os

class ConfigManager:
    def __init__(self):
        # Guardamos en AppData para que en Program Files no se borre
        self.config_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'CopiadoraDeOficios')
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.config_data = self.load_config()

    def load_config(self):
        config = {}
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = {}

        defaults = {
            "port": 5000,
            "scanner1": "",
            "scanner2": "",
            "impresora": "",
            "modo": "BN",
            "mejoramiento": False,
        }
        defaults.update(config)

        # La versión anterior utilizaba "IA" para el mejoramiento. El proyecto
        # actual ya no utiliza ese modo como selección de color; el mejoramiento
        # es una opción independiente. Si aparece un valor antiguo, conservamos
        # B/N como modo seguro y activamos el mejoramiento.
        if defaults.get("modo") == "IA":
            defaults["modo"] = "BN"
            defaults["mejoramiento"] = True

        if defaults.get("modo") not in ("BN", "COLOR"):
            defaults["modo"] = "BN"

        return defaults

    def update_setting(self, key, value):
        self.config_data[key] = value
        with open(self.config_file, 'w') as f:
            json.dump(self.config_data, f, indent=4)

