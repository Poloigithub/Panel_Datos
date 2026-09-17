"""Lector del `.xls` de toda la vida, con la biblioteca estándar y nada más.

Media administración española sigue publicando en este formato: los convenios
colectivos, las huelgas, los despidos y su coste, la regulación de empleo. Son
ficheros con dato de provincia y cadencia mensual que el panel no podía tocar
porque su lector sólo abría XLSX, que es un zip de XML y se lee en veinte
líneas. Esto es lo otro: un formato binario de 1997.

Por dentro son dos capas, y las dos hay que escribirlas:

1. **El envoltorio OLE2**, que es un sistema de ficheros en miniatura dentro
   del fichero: una tabla de sectores encadenados, un directorio con nombres, y
   una segunda tabla en pequeño para los flujos que no llegan a 4 KB. De ahí se
   saca un flujo llamado `Workbook`.
2. **Los registros BIFF8**, que es lo que hay dentro de ese flujo: una tira de
   trozos con dos bytes de tipo y dos de longitud. Interesan los que dicen qué
   hojas hay, la tabla de cadenas compartidas y los que llevan valores de
   celda.

No cubre el formato entero ni lo pretende: cubre lo que hace falta para leer
una tabla de datos, que es texto y números. Los formatos, las fórmulas y los
gráficos se ignoran a propósito.

La clase se llama igual que la de XLSX y tiene la misma forma -`hojas` y
`filas()`- para que quien lee un fichero no tenga que saber de qué año es.
"""

from __future__ import annotations

import struct

FIRMA = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
LIBRE, FIN_CADENA = 0xFFFFFFFF, 0xFFFFFFFE

# Los registros BIFF que dicen algo. Los demás se saltan solos.
BOF = 0x0809
EOF_ = 0x000A
BOUNDSHEET = 0x0085
SST = 0x00FC
CONTINUE = 0x003C
LABELSST = 0x00FD
LABEL = 0x0204
NUMBER = 0x0203
RK = 0x027E
MULRK = 0x00BD
BLANK = 0x0201
MULBLANK = 0x00BE
FORMULA = 0x0006
STRING = 0x0207
BOOLERR = 0x0205
DIMENSIONS = 0x0200


# --------------------------------------------------------------- el envoltorio

class _Ole:
    """El sistema de ficheros en miniatura que hay dentro de un .xls."""

    def __init__(self, datos: bytes) -> None:
        if not datos.startswith(FIRMA):
            raise ValueError("no es un fichero OLE2: no lleva su firma")
        self.datos = datos
        self.tam_sector = 1 << struct.unpack_from("<H", datos, 30)[0]
        self.tam_mini = 1 << struct.unpack_from("<H", datos, 32)[0]
        self.corte_mini = struct.unpack_from("<I", datos, 56)[0]
        self.fat = self._lee_fat()
        self.directorio = self._lee_directorio()
        self.minifat, self.miniflujo = self._lee_mini()

    def _sector(self, numero: int) -> bytes:
        inicio = 512 + numero * self.tam_sector
        return self.datos[inicio:inicio + self.tam_sector]

    def _cadena(self, tabla: list[int], primero: int, tamano: int,
                trozo: int, origen: bytes | None = None) -> bytes:
        """Sigue la cadena de sectores de un flujo y los pega."""
        salida = bytearray()
        sector = primero
        visitados = set()
        while sector not in (FIN_CADENA, LIBRE) and sector < len(tabla) + 1:
            if sector in visitados:      # un fichero roto no debe colgar esto
                break
            visitados.add(sector)
            if origen is None:
                salida += self._sector(sector)
            else:
                salida += origen[sector * trozo:(sector + 1) * trozo]
            if sector >= len(tabla):
                break
            sector = tabla[sector]
        return bytes(salida[:tamano]) if tamano else bytes(salida)

    def _lee_fat(self) -> list[int]:
        cuantos = struct.unpack_from("<I", self.datos, 44)[0]
        sectores = [struct.unpack_from("<I", self.datos, 76 + i * 4)[0]
                    for i in range(min(cuantos, 109))]
        # Si hay más de 109, el resto vive en sectores DIFAT encadenados.
        siguiente = struct.unpack_from("<I", self.datos, 68)[0]
        while siguiente not in (FIN_CADENA, LIBRE) and len(sectores) < cuantos:
            trozo = self._sector(siguiente)
            por_sector = self.tam_sector // 4 - 1
            for i in range(por_sector):
                valor = struct.unpack_from("<I", trozo, i * 4)[0]
                if valor not in (FIN_CADENA, LIBRE):
                    sectores.append(valor)
            siguiente = struct.unpack_from("<I", trozo, por_sector * 4)[0]

        fat: list[int] = []
        for numero in sectores:
            trozo = self._sector(numero)
            fat += list(struct.unpack(f"<{len(trozo) // 4}I", trozo))
        return fat

    def _lee_directorio(self) -> dict[str, tuple[int, int]]:
        primero = struct.unpack_from("<I", self.datos, 48)[0]
        crudo = self._cadena(self.fat, primero, 0, self.tam_sector)
        entradas: dict[str, tuple[int, int]] = {}
        self.raiz = (0, 0)
        for i in range(len(crudo) // 128):
            entrada = crudo[i * 128:(i + 1) * 128]
            largo = struct.unpack_from("<H", entrada, 64)[0]
            if largo < 2:
                continue
            nombre = entrada[:largo - 2].decode("utf-16-le", "replace")
            tipo = entrada[66]
            inicio, tamano = struct.unpack_from("<II", entrada, 116)
            if tipo == 5:                       # la entrada raíz
                self.raiz = (inicio, tamano)
            elif tipo == 2:                     # un flujo
                entradas[nombre] = (inicio, tamano)
        return entradas

    def _lee_mini(self) -> tuple[list[int], bytes]:
        primero = struct.unpack_from("<I", self.datos, 60)[0]
        crudo = self._cadena(self.fat, primero, 0, self.tam_sector)
        minifat = list(struct.unpack(f"<{len(crudo) // 4}I", crudo)) if crudo else []
        inicio, tamano = self.raiz
        miniflujo = self._cadena(self.fat, inicio, tamano, self.tam_sector)
        return minifat, miniflujo

    def flujo(self, *nombres: str) -> bytes:
        for nombre in nombres:
            if nombre in self.directorio:
                inicio, tamano = self.directorio[nombre]
                if tamano < self.corte_mini:
                    return self._cadena(self.minifat, inicio, tamano,
                                        self.tam_mini, self.miniflujo)
                return self._cadena(self.fat, inicio, tamano, self.tam_sector)
        raise KeyError(f"no hay ningún flujo llamado {nombres}")


# ------------------------------------------------------------- los registros

def _registros(flujo: bytes, desde: int = 0):
    """Los trozos del flujo, uno a uno: tipo, dónde empieza y qué lleva."""
    pos = desde
    while pos + 4 <= len(flujo):
        tipo, largo = struct.unpack_from("<HH", flujo, pos)
        yield pos, tipo, flujo[pos + 4:pos + 4 + largo]
        pos += 4 + largo


def descifra_rk(crudo: int) -> float:
    """El número comprimido de BIFF, que cabe en cuatro bytes en vez de ocho.

    Dos bits mandan: uno dice si el número es entero o los treinta bits altos
    de un decimal, y el otro si además hay que dividirlo entre cien.
    """
    entero = crudo & 0x02
    centesimas = crudo & 0x01
    if entero:
        valor = float(crudo >> 2 if crudo < 0x80000000 else (crudo >> 2) - (1 << 30))
    else:
        valor = struct.unpack("<d", struct.pack("<Q", (crudo & 0xFFFFFFFC) << 32))[0]
    return valor / 100 if centesimas else valor


class _Trozos:
    """Un buffer que sabe dónde lo empalmaron.

    La tabla de cadenas no cabe en un registro y se parte en varios, y una
    cadena puede quedar cortada por la mitad. Al otro lado del corte hay un
    byte nuevo que dice si lo que sigue va en uno o en dos bytes por letra, así
    que hay que saber exactamente por dónde se cortó.
    """

    def __init__(self, partes: list[bytes]) -> None:
        self.datos = b"".join(partes)
        self.cortes = set()
        suma = 0
        for parte in partes[:-1]:
            suma += len(parte)
            self.cortes.add(suma)


def _lee_cadena(trozos: _Trozos, pos: int) -> tuple[str, int]:
    datos, cortes = trozos.datos, trozos.cortes
    largo = struct.unpack_from("<H", datos, pos)[0]
    pos += 2
    banderas = datos[pos]
    pos += 1
    ancho = 2 if banderas & 0x01 else 1
    if banderas & 0x08:          # texto con formatos: hay runs al final
        runs = struct.unpack_from("<H", datos, pos)[0]
        pos += 2
    else:
        runs = 0
    if banderas & 0x04:          # extensión de Extremo Oriente
        extra = struct.unpack_from("<I", datos, pos)[0]
        pos += 4
    else:
        extra = 0

    letras = []
    leidas = 0
    while leidas < largo:
        if pos in cortes:
            banderas = datos[pos]
            pos += 1
            ancho = 2 if banderas & 0x01 else 1
        siguiente = min((c for c in cortes if c > pos), default=len(datos))
        caben = (siguiente - pos) // ancho
        toma = min(largo - leidas, caben)
        if toma <= 0:
            pos = siguiente
            continue
        crudo = datos[pos:pos + toma * ancho]
        letras.append(crudo.decode("utf-16-le" if ancho == 2 else "latin-1", "replace"))
        pos += toma * ancho
        leidas += toma

    return "".join(letras), pos + runs * 4 + extra


def _lee_sst(trozos: _Trozos) -> list[str]:
    cuantas = struct.unpack_from("<I", trozos.datos, 4)[0]
    cadenas, pos = [], 8
    for _ in range(cuantas):
        if pos >= len(trozos.datos):
            break
        texto, pos = _lee_cadena(trozos, pos)
        cadenas.append(texto)
    return cadenas


class Libro:
    """Un .xls abierto: sus hojas, por nombre y en orden."""

    def __init__(self, datos: bytes) -> None:
        self.flujo = _Ole(datos).flujo("Workbook", "Book")
        self.cadenas: list[str] = []
        self.hojas: dict[str, int] = {}
        self._lee_cabecera()

    def _lee_cabecera(self) -> None:
        """Las hojas y la tabla de cadenas, que viven antes de los datos."""
        registros = list(_registros(self.flujo))
        for i, (_, tipo, cuerpo) in enumerate(registros):
            if tipo == BOUNDSHEET:
                inicio = struct.unpack_from("<I", cuerpo, 0)[0]
                largo = cuerpo[6]
                banderas = cuerpo[7]
                crudo = cuerpo[8:]
                nombre = (crudo[:largo * 2].decode("utf-16-le", "replace")
                          if banderas & 0x01
                          else crudo[:largo].decode("latin-1", "replace"))
                self.hojas[nombre] = inicio
            elif tipo == SST:
                partes = [cuerpo]
                for _, siguiente, mas in registros[i + 1:]:
                    if siguiente != CONTINUE:
                        break
                    partes.append(mas)
                self.cadenas = _lee_sst(_Trozos(partes))
            elif tipo == EOF_ and self.hojas:
                break

    def filas(self, nombre: str) -> list[list]:
        """Las filas de una hoja, con los huecos rellenos para que cuadren."""
        if nombre not in self.hojas:
            raise KeyError(f"no existe la hoja {nombre!r}")

        celdas: dict[int, dict[int, object]] = {}
        pendiente: tuple[int, int] | None = None   # una fórmula esperando su texto
        empezada = False

        for _, tipo, cuerpo in _registros(self.flujo, self.hojas[nombre]):
            if tipo == BOF:
                if empezada:
                    continue
                empezada = True
                continue
            if tipo == EOF_:
                break
            if not empezada or len(cuerpo) < 4:
                continue
            fila, columna = struct.unpack_from("<HH", cuerpo, 0)

            if tipo == LABELSST:
                indice = struct.unpack_from("<I", cuerpo, 6)[0]
                if indice < len(self.cadenas):
                    celdas.setdefault(fila, {})[columna] = self.cadenas[indice]
            elif tipo == LABEL:
                largo = struct.unpack_from("<H", cuerpo, 6)[0]
                texto = cuerpo[9:9 + largo * (2 if cuerpo[8] & 1 else 1)]
                celdas.setdefault(fila, {})[columna] = texto.decode(
                    "utf-16-le" if cuerpo[8] & 1 else "latin-1", "replace")
            elif tipo == NUMBER:
                valor = struct.unpack_from("<d", cuerpo, 6)[0]
                celdas.setdefault(fila, {})[columna] = valor
            elif tipo == RK:
                crudo = struct.unpack_from("<I", cuerpo, 6)[0]
                celdas.setdefault(fila, {})[columna] = descifra_rk(crudo)
            elif tipo == MULRK:
                ultima = struct.unpack_from("<H", cuerpo, len(cuerpo) - 2)[0]
                for i, col in enumerate(range(columna, ultima + 1)):
                    inicio = 4 + i * 6
                    if inicio + 6 > len(cuerpo) - 2:
                        break
                    crudo = struct.unpack_from("<I", cuerpo, inicio + 2)[0]
                    celdas.setdefault(fila, {})[col] = descifra_rk(crudo)
            elif tipo == FORMULA:
                # Si el resultado es texto, viene en el registro siguiente.
                if cuerpo[12:14] == b"\xff\xff" and cuerpo[6] == 0:
                    pendiente = (fila, columna)
                else:
                    valor = struct.unpack_from("<d", cuerpo, 6)[0]
                    celdas.setdefault(fila, {})[columna] = valor
            elif tipo == STRING and pendiente:
                texto, _ = _lee_cadena(_Trozos([cuerpo]), 0)
                celdas.setdefault(pendiente[0], {})[pendiente[1]] = texto
                pendiente = None

        if not celdas:
            return []
        ancho = max(max(fila) for fila in celdas.values()) + 1
        return [[celdas.get(f, {}).get(c) for c in range(ancho)]
                for f in range(max(celdas) + 1)]
