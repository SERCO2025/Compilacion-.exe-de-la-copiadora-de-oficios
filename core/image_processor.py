# -*- coding: utf-8 -*-
import cv2
import numpy as np
import os
import time
from PIL import Image


def _estimar_desplazamiento_vertical(img_a, img_b):
    """
    Registra la captura inferior respecto de la captura superior.

    A es la referencia fija. La función calcula cuánto debe desplazarse B
    para que sus características coincidentes queden registradas sobre A.

    Devuelve:
        (offset_x, offset_y, confianza, cantidad_inliers)
        donde B debe colocarse en:
            x_B = x_A + offset_x
            y_B = y_A + offset_y

        o:
        (None, None, 0.0, 0)
        si no existe evidencia suficiente.
    """
    gris_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    gris_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    gris_a = cv2.medianBlur(gris_a, 3)
    gris_b = cv2.medianBlur(gris_b, 3)

    try:
        # SIFT localiza la misma información en ambas capturas. El registro
        # se calcula sobre copias en escala de grises; las imágenes a color
        # permanecen intactas.
        if hasattr(cv2, "SIFT_create"):
            detector = cv2.SIFT_create(nfeatures=6000)
            kp_a, des_a = detector.detectAndCompute(gris_a, None)
            kp_b, des_b = detector.detectAndCompute(gris_b, None)

            if des_a is None or des_b is None or len(kp_a) < 8 or len(kp_b) < 8:
                return None, None, 0.0, 0

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
                return None, None, 0.0, 0

            puntos_a = np.float32([kp_a[m.queryIdx].pt for m in buenos])
            puntos_b = np.float32([kp_b[m.trainIdx].pt for m in buenos])

            desplazamientos = puntos_b - puntos_a

            med_dx = float(np.median(desplazamientos[:, 0]))
            med_dy = float(np.median(desplazamientos[:, 1]))

            desviacion = np.sqrt(
                (desplazamientos[:, 0] - med_dx) ** 2
                + (desplazamientos[:, 1] - med_dy) ** 2
            )
            mascara_inicial = desviacion <= 12.0

            if int(np.count_nonzero(mascara_inicial)) < 8:
                return None, None, 0.0, 0

            pa = puntos_a[mascara_inicial]
            pb = puntos_b[mascara_inicial]

            # RANSAC obtiene la relación dominante y descarta coincidencias
            # aisladas. Se utiliza para calcular el registro; la composición
            # final aplica únicamente la traslación resultante.
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
                return None, None, 0.0, 0

            mascara = mascara.ravel().astype(bool)
            inliers = int(np.count_nonzero(mascara))
            if inliers < 8:
                return None, None, 0.0, inliers

            dx = float(matriz[0, 2])
            dy = float(matriz[1, 2])

            # Una diferencia horizontal grande no corresponde a las dos
            # partes del mismo documento.
            if abs(dx) > 25.0:
                return None, None, 0.0, inliers

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

            # La matriz lleva A -> B. Para colocar B sobre la referencia A
            # se aplica el desplazamiento inverso.
            offset_x = int(round(-dx))
            offset_y = int(round(-dy))

            return offset_x, offset_y, confianza, inliers

    except Exception as e:
        print(
            f"SISTEMA: No fue posible estimar el registro por características: {e}"
        )

    return None, None, 0.0, 0


def _recortar_y_componer(img_a, img_b, dpi_original=300):
    """
    Construye el documento Oficio mediante registro y fusión de las dos capturas.

    Reglas geométricas:
    - A (arriba) es la referencia fija.
    - B (abajo) se desplaza para registrarse respecto de A.
    - A pierde 1 pulgada de su extremo inferior.
    - B pierde 1 pulgada de su extremo superior.
    - La coincidencia se calcula antes de componer y determina la posición de B.
    - B queda como capa base, completamente opaca.
    - A queda encima de B y es la única capa que recibe el alpha blend.
    - La transición de alpha mide exactamente 1 pulgada.
    - La salida es un lienzo fijo de 8.5 x 13 pulgadas a 300 DPI.
    - Si la composición supera los 3900 px, se recorta únicamente en los
      extremos exteriores para que el resultado final siga cabiendo en Oficio.
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
        raise ValueError(
            "Las capturas no tienen altura suficiente para eliminar 1 pulgada."
        )

    # Recortes físicos solicitados:
    # A: se elimina 1" abajo.
    # B: se elimina 1" arriba.
    img_a_limpia = img_a[0 : h_a - recorte, :]
    img_b_limpia = img_b[recorte : h_b, :]

    alto_a = img_a_limpia.shape[0]
    alto_b = img_b_limpia.shape[0]

    ancho_objetivo = int(round(8.5 * dpi_original))
    alto_objetivo = int(round(13.0 * dpi_original))

    # Se conserva la tolerancia del 10% para el ancho adquirido.
    tolerancia_ancho = int(round(ancho_objetivo * 0.10))
    diferencia_ancho = abs(w_a - ancho_objetivo)

    if diferencia_ancho > tolerancia_ancho:
        raise ValueError(
            f"El ancho de las capturas está fuera de la tolerancia permitida: "
            f"se esperaba aproximadamente {ancho_objetivo}px, se obtuvo {w_a}px "
            f"y la tolerancia máxima es de {tolerancia_ancho}px (10%)."
        )

    # La captura superior queda fija y centrada horizontalmente.
    margen_x = (ancho_objetivo - w_a) // 2
    if margen_x < 0:
        raise ValueError(
            f"El ancho adquirido ({w_a}px) no puede ser mayor que el lienzo "
            f"Oficio de salida ({ancho_objetivo}px)."
        )

    offset_x, offset_y, confianza, inliers = _estimar_desplazamiento_vertical(
        img_a,
        img_b,
    )

    if offset_x is None or offset_y is None:
        raise ValueError(
            "No fue posible registrar las dos capturas: "
            "no se encontraron suficientes coincidencias confiables."
        )

    # B se coloca respecto de A. La coordenada de B[0] cambia porque primero
    # se eliminó 1" de la parte superior de B.
    x_b = margen_x + offset_x
    y_b = offset_y + recorte

    if y_b < 0 or y_b >= alto_a:
        raise ValueError(
            "El registro vertical encontrado no deja una zona común válida "
            "entre las capturas."
        )

    # Necesitamos al menos 1" de coincidencia física para realizar exactamente
    # el alpha blend solicitado.
    traslape_disponible = min(alto_a - y_b, alto_b)
    ancho_blend = recorte

    if traslape_disponible < ancho_blend:
        raise ValueError(
            "El registro encontrado no proporciona una zona común suficiente "
            "para aplicar la transición de alpha de 1 pulgada."
        )

    # La imagen superior permanece fija. La inferior se desplaza hasta este
    # punto y queda como base opaca.
    alto_documento = max(alto_a, y_b + alto_b)

    # Se construye primero el documento completo, aunque mida más de Oficio.
    # Después se recortan exclusivamente los extremos exteriores.
    compuesto = np.full(
        (alto_documento, ancho_objetivo, img_a.shape[2]),
        255,
        dtype=img_a.dtype,
    )

    # Colocar B como capa base. Si el registro horizontal la desplaza unos
    # píxeles, se recorta únicamente lo que quede fuera del lienzo.
    bx0 = max(0, x_b)
    bx1 = min(ancho_objetivo, x_b + w_b)

    if bx0 >= bx1:
        raise ValueError(
            "El registro horizontal dejó la captura inferior fuera del lienzo."
        )

    src_b_x0 = bx0 - x_b
    src_b_x1 = src_b_x0 + (bx1 - bx0)

    compuesto[
        y_b : y_b + alto_b,
        bx0:bx1,
    ] = img_b_limpia[:, src_b_x0:src_b_x1]

    # Parte superior de A: completamente opaca y fija.
    ax0 = max(0, margen_x)
    ax1 = min(ancho_objetivo, margen_x + w_a)

    if ax0 >= ax1:
        raise ValueError(
            "La captura superior quedó fuera del lienzo Oficio."
        )

    src_a_x0 = ax0 - margen_x
    src_a_x1 = src_a_x0 + (ax1 - ax0)

    if y_b > 0:
        compuesto[
            0:y_b,
            ax0:ax1,
        ] = img_a_limpia[0:y_b, src_a_x0:src_a_x1]

    # Zona de unión: B permanece debajo al 100%; A está encima y pierde
    # progresivamente opacidad durante exactamente 1".
    #
    # En el comienzo de la zona de unión:
    #     alpha_A = 1.0
    # Al final de la zona de unión:
    #     alpha_A = 0.0
    #
    # Así la información común se ve una sola vez de manera continua y no se
    # concatena una captura después de la otra.
    y_union = y_b
    y_union_fin = y_b + ancho_blend

    if y_union_fin > alto_a or y_union_fin > y_b + alto_b:
        raise ValueError(
            "La zona disponible para el traslape no permite una transición "
            "de alpha completa de 1 pulgada."
        )

    overlap_x0 = max(ax0, bx0)
    overlap_x1 = min(ax1, bx1)

    if overlap_x0 >= overlap_x1:
        raise ValueError(
            "No existe traslape horizontal suficiente entre las capturas registradas."
        )

    top_x0 = overlap_x0 - margen_x
    top_x1 = top_x0 + (overlap_x1 - overlap_x0)

    bottom_x0 = overlap_x0 - x_b
    bottom_x1 = bottom_x0 + (overlap_x1 - overlap_x0)

    for i in range(ancho_blend):
        y = y_union + i

        alpha_superior = 1.0 - (float(i) / float(ancho_blend - 1))
        alpha_inferior = 1.0 - alpha_superior

        fila_superior = img_a_limpia[y, top_x0:top_x1].astype(np.float32)
        fila_inferior = img_b_limpia[i, bottom_x0:bottom_x1].astype(np.float32)

        mezcla = (
            fila_superior * alpha_superior
            + fila_inferior * alpha_inferior
        )

        compuesto[
            y,
            overlap_x0:overlap_x1,
        ] = np.clip(mezcla, 0, 255).astype(np.uint8)

    print(
        "SISTEMA: Registro de capturas: "
        f"offset_x={offset_x}, offset_y={offset_y}, "
        f"confianza={confianza:.3f}, inliers={inliers}."
    )
    print(
        "SISTEMA: Traslape registrado: "
        f"x={overlap_x0}:{overlap_x1}, "
        f"y={y_union}:{y_union_fin}, "
        f"alpha={ancho_blend}px (1 pulgada)."
    )
    print(
        "SISTEMA: Composición antes de ajuste Oficio: "
        f"{ancho_objetivo} x {alto_documento}px."
    )

    # Ajuste vertical final al lienzo Oficio. Nunca se toca la zona de unión
    # para corregir el exceso: únicamente se recortan los extremos exteriores.
    if alto_documento > alto_objetivo:
        exceso = alto_documento - alto_objetivo
        recorte_superior = exceso // 2
        recorte_inferior = exceso - recorte_superior

        compuesto = compuesto[
            recorte_superior : alto_documento - recorte_inferior,
            :,
        ]

        print(
            "SISTEMA: Documento mayor que Oficio: "
            f"exceso={exceso}px. "
            f"Recorte exterior arriba={recorte_superior}px, "
            f"abajo={recorte_inferior}px."
        )

    # Si el documento es menor, se conserva sin escalar y el sobrante queda
    # blanco en el extremo inferior.
    if compuesto.shape[0] < alto_objetivo:
        oficio_mat = np.full(
            (alto_objetivo, ancho_objetivo, img_a.shape[2]),
            255,
            dtype=img_a.dtype,
        )
        oficio_mat[
            0 : compuesto.shape[0],
            :,
        ] = compuesto
    else:
        oficio_mat = compuesto

    if oficio_mat.shape[:2] != (alto_objetivo, ancho_objetivo):
        raise ValueError(
            "No fue posible ajustar la composición al lienzo Oficio de salida: "
            f"{oficio_mat.shape[1]} x {oficio_mat.shape[0]}px."
        )

    return oficio_mat


def procesar_union_y_preview(ruta_arriba, ruta_abajo, dpi_original=300):
    if not os.path.exists(ruta_arriba):
        raise FileNotFoundError("No existe el escaneo de arriba: {}".format(ruta_arriba))
    if not os.path.exists(ruta_abajo):
        raise FileNotFoundError("No existe el escaneo de abajo: {}".format(ruta_abajo))

    img_a = cv2.imread(ruta_arriba, cv2.IMREAD_COLOR)
    img_b = cv2.imread(ruta_abajo, cv2.IMREAD_COLOR)

    if img_a is None:
        raise ValueError("OpenCV no pudo abrir el escaneo de arriba: {}".format(ruta_arriba))
    if img_b is None:
        raise ValueError("OpenCV no pudo abrir el escaneo de abajo: {}".format(ruta_abajo))

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
        raise


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
