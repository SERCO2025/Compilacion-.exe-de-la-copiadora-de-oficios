# -*- coding: utf-8 -*-
import socket
import threading
import os
import struct  # Protocolo binario para comunicación con Android

class NetworkServer:
    def __init__(self, host='0.0.0.0', port=5000, callback=None):
        self.host = host
        self.port = port
        self.callback = callback  # Recibe el comando y lo manda al main.py
        self.server_socket = None
        self.running = False

    def start(self):
        """Inicia el servidor en un hilo independiente (No bloquea la UI)."""
        self.running = True
        self.server_thread = threading.Thread(target=self._listen, daemon=True)
        self.server_thread.start()
        print("SISTEMA: Servidor de red iniciado en puerto " + str(self.port))

    def _listen(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Permite reiniciar el servidor sin esperar a que el OS libere el puerto
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)

            while self.running:
                try:
                    client_sock, addr = self.server_socket.accept()
                    # Atender cada petición de la APK en un hilo nuevo
                    t = threading.Thread(
                        target=self._handle_client,
                        args=(client_sock,),
                        daemon=True
                    )
                    t.start()
                except socket.error:
                    break
        except Exception as e:
            print("ERROR Critico en socket: " + str(e))

    def _handle_client(self, conn):
        try:
            with conn:
                # Recibir comando del celular (max 1024 bytes)
                raw_data = conn.recv(1024)
                if not raw_data:
                    return

                comando = raw_data.decode('utf-8').strip()
                print("RED: Comando recibido -> " + comando)

                # CASO A: SOLICITUD DE IMAGEN PARA EL CELULAR
                if comando == "PREVIEW":
                    self._enviar_preview_binario(conn)

                # CASO B: COMANDOS DE ACCIÓN (COPIA_DIRECTA, ESCANEAR_ARRIBA,
                # ESCANEAR_ABAJO, UNIR, IMPRIMIR, etc.)
                else:
                    if self.callback:
                        # El callback ejecuta la operación de forma síncrona dentro
                        # de este hilo de cliente. La interfaz principal no se bloquea
                        # porque cada conexión ya se atiende en su propio hilo.
                        resultado = self.callback(comando)
                    else:
                        resultado = False

                    # La respuesta se envía únicamente después de conocer el resultado
                    # real de la operación. Así se evita confirmar un comando antes de
                    # que termine el escaneo, la unión o la impresión.
                    conn.sendall(b"OK" if resultado else b"ERROR")
        except Exception as e:
            print("ERROR al procesar cliente red: " + str(e))

    def _enviar_preview_binario(self, conn):
        """Envía preview.jpg siguiendo el protocolo: SIZE(4B) + DATA."""
        preview_file = "preview.jpg"

        if os.path.exists(preview_file):
            try:
                filesize = os.path.getsize(preview_file)

                # 1. Enviar el tamaño exacto en 4 bytes (Entero Big-endian)
                # Esto le dice a la APK exactamente cuántos bytes leer
                conn.sendall(struct.pack('>I', filesize))

                # 2. Enviar el archivo en bloques de 4KB para estabilidad
                with open(preview_file, 'rb') as f:
                    while True:
                        chunk = f.read(4096)
                        if not chunk:
                            break
                        conn.sendall(chunk)
                print("RED: Preview enviado con exito (" + str(filesize) + " bytes).")
            except Exception as e:
                print("ERROR al leer archivo de preview: " + str(e))
        else:
            # Si el archivo no existe, enviamos tamaño 0
            print("RED: Advertencia - preview.jpg no encontrado en disco.")
            conn.sendall(struct.pack('>I', 0))

    def stop(self):
        """Detiene el servidor y libera el puerto."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("SISTEMA: Servidor de red detenido.")
