# -*- coding: utf-8 -*-
import cv2
import numpy as np
import os
import time
from PIL import Image


def _estimar_desplazamiento_vertical(img_a, img_b):
    """
    Estima la relación vertical entre las dos capturas.

    El valor devuelto representa en qué fila de A se encuentra la fila 0 de B.
    Ejemplo: si devuelve 624, B[0] corresponde aproximadamente a A[624].

    Se trabaja exclusivamente con copias auxiliares en escala de grises.
    Las imágenes originales a color nunca se modifican.

    Devuelve:
        (offset_y, confianza, cantidad_inliers)
        o (None, 0.0, 0) si no existe evidencia suficiente.
    """
    gris_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gris_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    gris_a = cv2.medianBlur(gris_a, 3)
    gris_b = cv2.medianBlur(gris_b, 3)

    try:
        # SIFT permite localizar la misma información aun cuando las dos
        # capturas corresponden a posiciones distintas del mismo documento.
        if hasattr(cv2, "SIFT_create"):
            detector = cv2.SIFT_create(nfeatures=6000)
            kp_a, des_a = detector.detectAndCompute(gris_a, None)
            kp_b, des_b = detector.detectAndCompute(gris_b, None)

            if des_a is None or des_b is None or len(kp_a) < 8 or len(kp_b) < 8:
                return None, 0.0, 0

            matcher = cv2.BFMatcher(cv2.NORM_L2)
            pares = matcher.knnMatch(des_a, des_b, k=2)

            buenos = []
            for par in pares:
                if len(par) != 2:
                    continue
                m, n = par
                if m.distance < 0.72 * n.distance:
                    buenos.append(m)

            if len(buenos) < 8:
                return None, 0.0, 0

            puntos_a = np.float32([kp_a[m.queryIdx].pt for m in buenos])
            puntos_b = np.float32([kp_b[m.trainIdx].pt for m in buenos])

            # B = A + desplazamiento. Para una captura inferior, el
            # desplazamiento vertical suele ser negativo; por eso el offset
            # solicitado por esta función es -dy.
            desplazamientos = puntos_b - puntos_a

            # Filtrado inicial por mediana para eliminar coincidencias absurdas.
            med_dx = float(np.median(desplazamientos[:, 0]))
            med_dy = float(np.median(desplazamientos[:, 1]))

            desviacion = np.sqrt(
                (desplazamientos[:, 0] - med_dx) ** 2
                + (desplazamientos[:, 1] - med_dy) ** 2
            )
            mascara_inicial = desviacion <= 12.0

            if int(np.count_nonzero(mascara_inicial)) < 8:
                return None, 0.0, 0

            pa = puntos_a[mascara_inicial]
            pb = puntos_b[mascara_inicial]

            # RANSAC para obtener la traslación dominante y descartar
            # coincidencias aisladas.
            matriz, mascara = cv2.estimateAffinePartial2D(
                pa,
                pb,
                method=cv2.RANSAC,
                ransacReprojThreshold=3.0,
                maxIters=5000,
                confidence=0.995,
                refineIters=20,
            )

            if matriz is None or mascara is None:
                return None, 0.0, 0

            mascara = mascara.ravel().astype(bool)
            inliers = int(np.count_nonzero(mascara))
            if inliers < 8:
                return None, 0.0, inliers

            dx = float(matriz[0, 2])
            dy = float(matriz[1, 2])

            # La captura debe coincidir horizontalmente. Una desviación
            # importante indica que no estamos ante las dos partes del mismo
            # escaneo.
            if abs(dx) > 25.0:
                return None, 0.0, inliers

            # Medimos la consistencia del desplazamiento entre inliers.
            pa_i = pa[mascara]
            pb_i = pb[mascara]
            residuos = pb_i - pa_i
            error = np.sqrt(
                (residuos[:, 0] - dx) ** 2
                + (residuos[:, 1] - dy) ** 2
            )
            error_mediano = float(np.median(error))

            confianza = max(0.0, min(1.0, 1.0 - error_mediano / 5.0))
            confianza *= min(1.0, inliers / 40.0)

            offset_y = int(round(-dy))
            return offset_y, confianza, inliers

    except Exception as e:
        print(f"SISTEMA: No fue posible estimar el desplazamiento por características: {e}")

    return None, 0.0, 0


def _recortar_y_componer(img_a, img_b, dpi_original=300):
    """
    Construye el documento Oficio conservando las imágenes originales.

    Reglas geométricas:
    - A: se elimina 1 pulgada de su extremo inferior.
    - B: se elimina 1 pulgada de su extremo superior.
    - La relación vertical entre A y B se obtiene con una copia auxiliar en
      escala de grises.
    - B limpia comienza físicamente en la coordenada:
          offset_y + recorte
      respecto de A.
    - Si el documento estimado es menor que Oficio, se conserva completo y el
      espacio restante del lienzo queda blanco.
    - Si el documento estimado coincide con Oficio, se ocupa exactamente el
      lienzo.
    - Si excede ligeramente el lienzo por una diferencia de registro pequeña,
      la corrección se reparte entre los extremos exteriores. Esto reproduce
      el caso real de referencia: 24 px de diferencia => 12 px por extremo.
    - Si la discrepancia supera el margen de registro permitido, se rechaza en
      lugar de recortar contenido real.
    - Si no existe información suficiente en el traslape, no se interpreta el
      blanco como fin del documento. B se ancla por su borde inferior al
      lienzo Oficio.
    """
    recorte = int(dpi_original)
    if recorte <= 0:
        raise ValueError("dpi_original debe ser mayor que cero.")

    h_a, w_a = img_a.shape[:2]
    h_b, w_b = img_b.shape[:2]

    if w_a != w_b:
        raise ValueError(
            f"Las capturas tienen anchos diferentes: A={w_a}px, B={w_b}px."
        )

    if h_a <= recorte or h_b <= recorte:
        raise ValueError("Las capturas no tienen altura suficiente para eliminar 1 pulgada.")

    # Capturas originales conservadas. Estas dos vistas son las únicas que se
    # utilizan para construir el resultado final.
    img_a_limpia = img_a[0 : h_a - recorte, :]
    img_b_limpia = img_b[recorte : h_b, :]

    alto_a = img_a_limpia.shape[0]
    alto_b = img_b_limpia.shape[0]

    ancho_objetivo = int(round(8.5 * dpi_original))
    alto_objetivo = int(round(13.0 * dpi_original))

    if w_a != ancho_objetivo:
        raise ValueError(
            f"El ancho de las capturas no corresponde a Oficio a {dpi_original} DPI: "
            f"se esperaba {ancho_objetivo}px y se obtuvo {w_a}px."
        )

    # B se ancla por su borde inferior cuando no existe información suficiente
    # para calcular la relación entre las dos capturas.
    inicio_b_en_lienzo = alto_objetivo - alto_b

    offset_y, confianza, inliers = _estimar_desplazamiento_vertical(img_a, img_b)

    # Caso sin evidencia suficiente: no se intenta inferir la longitud física
    # observando zonas blancas. Se usa directamente la geometría de anclaje.
    if offset_y is None:
        inicio_a = 0
        fin_a = inicio_b_en_lienzo
        inicio_b = 0
        fin_b = alto_b

        print(
            "SISTEMA: No hay evidencia suficiente para localizar el traslape. "
            "Se utiliza el anclaje inferior del lienzo sin interpretar el blanco."
        )

    else:
        # B limpia comienza en A[offset_y + recorte]. Esta es la frontera
        # natural de unión porque desde ahí B contiene la continuación del
        # documento que ya apareció en A.
        frontera_a = offset_y + recorte

        # Longitud estimada del documento a partir de la relación de las dos
        # capturas originales.
        longitud_estimada = offset_y + h_b

        if frontera_a < 0 or frontera_a > alto_a:
            raise ValueError(
                "La relación vertical encontrada no es compatible con las "
                "dimensiones de las capturas."
            )

        if longitud_estimada <= alto_objetivo:
            # Documento más corto o exactamente Oficio. Conservamos todo el
            # documento y, si es más corto, el resto del lienzo queda blanco.
            inicio_a = 0
            fin_a = frontera_a
            inicio_b = 0
            fin_b = min(alto_b, alto_objetivo - fin_a)

            print(
                "SISTEMA: Documento estimado dentro de Oficio: "
                f"{longitud_estimada}px. Se conservará el espacio sobrante."
            )

        else:
            # El documento excede el lienzo. Una diferencia pequeña puede ser
            # causada por el registro entre las dos capturas. Se permite
            # corregir únicamente una discrepancia limitada y se reparte entre
            # los dos extremos exteriores, nunca dentro de la zona útil.
            exceso = longitud_estimada - alto_objetivo

            # El caso real entregado por el usuario tiene 24 px de exceso
            # geométrico y se reproduce como 12 px por cada extremo. Se fija
            # un límite pequeño de 50 px para no convertir una diferencia real
            # de tamaño en un supuesto ajuste de registro.
            max_exceso_registro = 50

            if exceso > max_exceso_registro:
                raise ValueError(
                    "El documento estimado excede el formato Oficio más allá "
                    f"de la tolerancia de registro permitida ({max_exceso_registro}px): "
                    f"exceso={exceso}px."
                )

            ajuste = int(round(exceso / 2.0))

            inicio_a = ajuste
            fin_a = frontera_a
            inicio_b = 0
            fin_b = alto_b - ajuste

            print(
                "SISTEMA: Documento ligeramente mayor por discrepancia de registro: "
                f"exceso={exceso}px. Se corrigen {ajuste}px en cada extremo."
            )

        print(
            "SISTEMA: Relación encontrada entre capturas: "
            f"offset_y={offset_y}, confianza={confianza:.3f}, inliers={inliers}."
        )
        print(
            "SISTEMA: Composición calculada: "
            f"A[{inicio_a}:{fin_a}] + B[{inicio_b}:{fin_b}]."
        )

    bloque_a = img_a_limpia[inicio_a:fin_a, :]
    bloque_b = img_b_limpia[inicio_b:fin_b, :]

    if bloque_a.size == 0 or bloque_b.size == 0:
        raise ValueError("La geometría calculada produjo un bloque vacío.")

    alto_compuesto = bloque_a.shape[0] + bloque_b.shape[0]
    if alto_compuesto > alto_objetivo:
        raise ValueError(
            f"La composición excede el lienzo Oficio: {alto_compuesto}px."
        )

    # Lienzo físico fijo. Si el documento es más corto, la región no utilizada
    # permanece blanca. Esto es deliberado y evita escalar el documento.
    oficio_mat = np.full(
        (alto_objetivo, ancho_objetivo, img_a.shape[2]),
        255,
        dtype=img_a.dtype,
    )

    oficio_mat[0 : bloque_a.shape[0], 0:w_a] = bloque_a
    oficio_mat[
        bloque_a.shape[0] : bloque_a.shape[0] + bloque_b.shape[0],
        0:w_b,
    ] = bloque_b

    return oficio_mat

def procesar_union_y_preview(ruta_arriba, ruta_abajo, dpi_original=300):
    if not os.path.exists(ruta_arriba) or not os.path.exists(ruta_abajo):
        return False

    img_a = cv2.imread(ruta_arriba, cv2.IMREAD_COLOR)
    img_b = cv2.imread(ruta_abajo, cv2.IMREAD_COLOR)

    if img_a is None or img_b is None:
        return False

    try:
        # Las imágenes originales se mantienen en color. La conversión a gris
        # ocurre únicamente dentro de _estimar_desplazamiento_vertical(), sobre
        # copias auxiliares utilizadas para el cálculo.
        oficio_mat = _recortar_y_componer(img_a, img_b, dpi_original)

        h_final, w_final = oficio_mat.shape[:2]

        # Garantía programática de la salida física requerida.
        ancho_objetivo = int(round(8.5 * dpi_original))
        alto_objetivo = int(round(13.0 * dpi_original))
        if (w_final, h_final) != (ancho_objetivo, alto_objetivo):
            print(
                "ERROR: La unión no produjo el tamaño Oficio esperado: "
                f"{w_final} x {h_final}px."
            )
            return False

        # 6. Guardar y generar preview.
        cv2.imwrite("oficio.png", oficio_mat, [cv2.IMWRITE_PNG_COMPRESSION, 3])

        # El preview conserva el comportamiento actual del proyecto.
        nuevo_ancho = int(w_final * 0.4)
        nuevo_alto = int(h_final * 0.4)
        preview_mat = cv2.resize(
            oficio_mat,
            (nuevo_ancho, nuevo_alto),
            interpolation=cv2.INTER_AREA,
        )
        # El preview para Android representa el mismo documento a 120 DPI:
        # 2550x3900 a 300 DPI -> 1020x1560 a 120 DPI. Pillow permite además
        # conservar el dato DPI dentro del JPEG, algo que cv2.imwrite no hace.
        preview_rgb = cv2.cvtColor(preview_mat, cv2.COLOR_BGR2RGB)
        Image.fromarray(preview_rgb).save(
            "preview.jpg",
            format="JPEG",
            quality=70,
            dpi=(120, 120),
        )

        print(
            f"SISTEMA: Unión completada correctamente: {w_final} x {h_final}px."
        )
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False


def aplicar_mejoras_impresion(ruta_origen, modo, mejoramiento=False):
    """Prepara una copia para impresión respetando el modo seleccionado.

    ``modo`` solo determina si la impresión será B/N o COLOR.
    ``mejoramiento`` es independiente y, cuando está activo, aplica una
    limpieza suave de ruido y una mejora de nitidez sin convertir a escala
    de grises una impresión seleccionada como COLOR.
    """
    img = cv2.imread(ruta_origen, cv2.IMREAD_COLOR)
    if img is None:
        return ruta_origen

    output_path = "temp_print.png"

    if modo == "BN":
        gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if mejoramiento:
            gris = cv2.GaussianBlur(gris, (3, 3), 0)
        _, final = cv2.threshold(gris, 200, 255, cv2.THRESH_BINARY)
        cv2.imwrite(output_path, final)
        return output_path

    final = img
    if mejoramiento:
        # Limpieza suave de ruido y realce de bordes. Se mantiene BGR/color.
        suavizada = cv2.GaussianBlur(final, (3, 3), 0)
        final = cv2.addWeighted(final, 1.35, suavizada, -0.35, 0)

    if mejoramiento:
        cv2.imwrite(output_path, final)
        return output_path

    return ruta_origen
