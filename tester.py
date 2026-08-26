# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import messagebox
import threading
import socket
import struct
import os
from core.config_manager import ConfigManager

class TesterCopiadoraDeOficios:
    def __init__(self, root):
        self.root = root
        self.root.title("TESTER DE COMUNICACIÓN - COPIADORA DE OFICIOS")
        self.root.geometry("400x650")
        self.root.overrideredirect(True)
        self.root.configure(bg='#0047AB') # Azul Cobalto

        # Cargar config
        try:
            self.config = ConfigManager()
            self.puerto = self.config.config_data.get("port", 5000)
        except:
            self.puerto = 5000

        self.botones_refs = {}
        self.root.bind("<ButtonPress-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)

        self.setup_ui()
        self.start_server()

    def setup_ui(self):
        header = tk.Frame(self.root, bg='#0047AB', height=40)
        header.pack(fill='x', padx=5, pady=5)
        
        tk.Label(header, text="MODO TESTER ACTIVO", bg='#0047AB', fg='yellow', 
                 font=("Impact", 10)).pack(side='left')
        
        tk.Button(header, text=" X ", bg='red', fg='white', font=("Impact", 12, "bold"), 
                  command=self.root.destroy, relief='flat').pack(side='right')

        tk.Label(self.root, text="TESTER DE RED", bg='#0047AB', fg='cyan', 
                 font=("Impact", 28)).pack(pady=10)

        # Mantenemos tus IDs de comando exactos
        botones_spec = [
            ("COPIA DIRECTA", "#008000", "COPIA_DIRECTA"),
            ("ESCANEAR ARRIBA", "#4169E1", "ESCANEAR_ARRIBA"),
            ("ESCANEAR ABAJO", "#4169E1", "ESCANEAR_ABAJO"),
            ("UNIR PARTES", "#FF8C00", "UNIR"),
            ("PREVISUALIZAR", "#FFFF00", "PREVIEW"),
            ("IMPRIMIR OFICIO", "#008000", "IMPRIMIR")
        ]

        for txt, color, cmd_id in botones_spec:
            fg_btn = "black" if color == "#FFFF00" else "white"
            btn = tk.Button(self.root, text=txt, bg=color, fg=fg_btn, 
                            font=("Impact", 16), width=22, height=1,
                            relief='raised', bd=4, state='disabled') 
            btn.pack(pady=6)
            self.botones_refs[cmd_id] = {"obj": btn, "color": color, "fg": fg_btn}

        mode_frame = tk.Frame(self.root, bg='#0047AB')
        mode_frame.pack(pady=12)

        # El tester no ejecuta estas opciones. Solo reproduce la forma visual
        # de la ventana principal para comprobar las señales del Android.
        tk.Radiobutton(
            mode_frame, text="B/N", bg='#0047AB', fg='white',
            selectcolor='#001a33', font=("Impact", 12), state='disabled'
        ).pack(side='left', padx=10)
        tk.Radiobutton(
            mode_frame, text="COLOR", bg='#0047AB', fg='white',
            selectcolor='#001a33', font=("Impact", 12), state='disabled'
        ).pack(side='left', padx=10)

        tk.Checkbutton(
            self.root, text="MEJORAMIENTO DE IMAGEN",
            bg='#0047AB', fg='yellow', selectcolor='#001a33',
            font=("Impact", 11), state='disabled'
        ).pack(pady=4)

        self.status_lbl = tk.Label(self.root, text="Esperando señal del cel...", 
                                   bg='#0047AB', fg='white', font=("Arial", 10))
        self.status_lbl.pack(pady=10)

    def start_move(self, event):
        self.x, self.y = event.x, event.y
    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def iluminar_boton(self, cmd_id):
        cmd_id = cmd_id.strip() 
        if cmd_id in self.botones_refs:
            btn_info = self.botones_refs[cmd_id]
            btn_info["obj"].config(bg="white", fg="black")
            self.status_lbl.config(text=f"RECIBIDO: {cmd_id}", fg="yellow")
            
            self.root.after(800, lambda: self.restaurar_boton(cmd_id))
        else:
            self.status_lbl.config(text=f"COMANDO DESCONOCIDO: {cmd_id}", fg="red")

    def restaurar_boton(self, cmd_id):
        if cmd_id in self.botones_refs:
            btn_info = self.botones_refs[cmd_id]
            btn_info["obj"].config(bg=btn_info["color"], fg=btn_info["fg"])
            self.status_lbl.config(text="Esperando señal...", fg="white")

    def start_server(self):
        threading.Thread(target=self.network_listener, daemon=True).start()

    def network_listener(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', self.puerto))
                s.listen(5)
                while True:
                    conn, addr = s.accept()
                    with conn:
                        data = conn.recv(1024).decode('utf-8').strip()
                        if data:
                            self.root.after(0, lambda d=data: self.iluminar_boton(d))
                            
                            if data == "PREVIEW":
                                img_path = "preview.jpg"
                                if os.path.exists(img_path):
                                    with open(img_path, "rb") as f:
                                        img_bytes = f.read()
                                else:
                                    # Generar buffer vacío si no hay imagen
                                    img_bytes = b"SIN_IMAGEN"
                                
                                size_header = struct.pack('>I', len(img_bytes))
                                conn.sendall(size_header)
                                conn.sendall(img_bytes)
                            else:
                                conn.sendall(b"OK")
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Fallo en servidor: {e}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = TesterCopiadoraDeOficios(root)
    root.mainloop()