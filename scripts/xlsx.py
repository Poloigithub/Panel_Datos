"""Lector mínimo de XLSX, con la biblioteca estándar y nada más.

El CGPJ publica sus estadísticas en hojas de cálculo, y el panel no usa
dependencias externas. Un XLSX es un zip de XML, así que leerlo es abrir el
zip, buscar las hojas y traducir los índices de la tabla de cadenas
compartidas. No pretende cubrir el formato entero: sólo valores de celda, que
es lo que hace falta para leer una tabla de datos.
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.etree import ElementTree

ESPACIO = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RELACIONES = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DOCUMENTO = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
COLUMNA = re.compile(r"^([A-Z]+)")


class Libro:
    """Un XLSX abierto: sus hojas, por nombre y en orden."""

    def __init__(self, datos: bytes) -> None:
        self.zip = zipfile.ZipFile(io.BytesIO(datos))
        self.cadenas = self._cadenas()
        self.hojas = self._hojas()

    def _cadenas(self) -> list[str]:
        if "xl/sharedStrings.xml" not in self.zip.namelist():
            return []
        raiz = ElementTree.fromstring(self.zip.read("xl/sharedStrings.xml"))
        cadenas = []
        for item in raiz.findall(f"{ESPACIO}si"):
            # Una cadena puede venir partida en varios trozos con formato.
            cadenas.append("".join(t.text or "" for t in item.iter(f"{ESPACIO}t")))
        return cadenas

    def _hojas(self) -> dict[str, str]:
        relaciones = {}
        raiz = ElementTree.fromstring(self.zip.read("xl/_rels/workbook.xml.rels"))
        for relacion in raiz.findall(f"{RELACIONES}Relationship"):
            destino = relacion.get("Target", "")
            if destino.startswith("/"):
                destino = destino[1:]
            elif not destino.startswith("xl/"):
                destino = "xl/" + destino
            relaciones[relacion.get("Id")] = destino

        hojas = {}
        raiz = ElementTree.fromstring(self.zip.read("xl/workbook.xml"))
        for hoja in raiz.iter(f"{ESPACIO}sheet"):
            ruta = relaciones.get(hoja.get(f"{DOCUMENTO}id"))
            if ruta:
                hojas[hoja.get("name") or ruta] = ruta
        return hojas

    def filas(self, nombre: str) -> list[list]:
        """Las filas de una hoja, con los huecos rellenos para que cuadren."""
        ruta = self.hojas.get(nombre)
        if not ruta:
            raise KeyError(f"no existe la hoja {nombre!r}")
        raiz = ElementTree.fromstring(self.zip.read(ruta))
        filas = []
        for fila in raiz.iter(f"{ESPACIO}row"):
            celdas: list = []
            for celda in fila.findall(f"{ESPACIO}c"):
                # La referencia («C7») dice en qué columna va: sin esto, una
                # celda vacía correría toda la fila un puesto a la izquierda.
                letras = COLUMNA.match(celda.get("r") or "")
                if letras:
                    posicion = 0
                    for letra in letras.group(1):
                        posicion = posicion * 26 + (ord(letra) - 64)
                    while len(celdas) < posicion - 1:
                        celdas.append(None)
                celdas.append(self._valor(celda))
            filas.append(celdas)
        return filas

    def _valor(self, celda):
        tipo = celda.get("t")
        if tipo == "inlineStr":
            return "".join(t.text or "" for t in celda.iter(f"{ESPACIO}t")) or None
        valor = celda.find(f"{ESPACIO}v")
        if valor is None or valor.text is None:
            return None
        if tipo == "s":
            indice = int(valor.text)
            return self.cadenas[indice] if indice < len(self.cadenas) else None
        if tipo in ("str", "e"):
            return valor.text
        try:
            numero = float(valor.text)
        except ValueError:
            return valor.text
        return int(numero) if numero.is_integer() else numero
