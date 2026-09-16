"""Pruebas del lector de XLSX, con libros fabricados a mano.

El formato es zip de XML y el panel lo lee sin dependencias, así que conviene
fijar por prueba las dos cosas que se hacen mal al escribir un lector así: las
celdas vacías, que corren la fila si no se mira la referencia, y la tabla de
cadenas compartidas.
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from xlsx import Libro  # noqa: E402

LIBRO = b'''<?xml version="1.0"?><workbook
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
 <sheets><sheet name="Lanzamientos" sheetId="1" r:id="rId1"/>
 <sheet name="Notas" sheetId="2" r:id="rId2"/></sheets></workbook>'''

RELACIONES = b'''<?xml version="1.0"?><Relationships
 xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="x" Target="worksheets/sheet1.xml"/>
 <Relationship Id="rId2" Type="x" Target="/xl/worksheets/sheet2.xml"/></Relationships>'''

CADENAS = b'''<?xml version="1.0"?><sst
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
 <si><t>Castellon</t></si><si><r><t>Ley </t></r><r><t>Hipotecaria</t></r></si></sst>'''

HOJA1 = b'''<?xml version="1.0"?><worksheet
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
 <row r="1"><c r="A1" t="s"><v>0</v></c><c r="C1" t="s"><v>1</v></c></row>
 <row r="2"><c r="A2"><v>336</v></c><c r="B2"><v>1.5</v></c>
 <c r="C2" t="inlineStr"><is><t>..</t></is></c></row>
 </sheetData></worksheet>'''

HOJA2 = b'''<?xml version="1.0"?><worksheet
 xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
 <row r="1"><c r="A1" t="s"><v>0</v></c></row></sheetData></worksheet>'''


def libro_de_prueba() -> Libro:
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("xl/workbook.xml", LIBRO)
        z.writestr("xl/_rels/workbook.xml.rels", RELACIONES)
        z.writestr("xl/sharedStrings.xml", CADENAS)
        z.writestr("xl/worksheets/sheet1.xml", HOJA1)
        z.writestr("xl/worksheets/sheet2.xml", HOJA2)
    return Libro(memoria.getvalue())


class LecturaDeXlsx(unittest.TestCase):
    def test_las_hojas_se_listan_en_orden(self):
        self.assertEqual(list(libro_de_prueba().hojas), ["Lanzamientos", "Notas"])

    def test_una_celda_vacia_no_corre_la_fila(self):
        """Sin mirar la referencia de la celda, «Ley Hipotecaria» caería en B."""
        filas = libro_de_prueba().filas("Lanzamientos")
        self.assertEqual(filas[0], ["Castellon", None, "Ley Hipotecaria"])

    def test_los_numeros_llegan_como_numeros(self):
        filas = libro_de_prueba().filas("Lanzamientos")
        self.assertEqual(filas[1][0], 336)
        self.assertIsInstance(filas[1][0], int)
        self.assertEqual(filas[1][1], 1.5)

    def test_el_texto_en_linea_tambien_se_lee(self):
        self.assertEqual(libro_de_prueba().filas("Lanzamientos")[1][2], "..")

    def test_una_hoja_que_no_existe_se_dice(self):
        with self.assertRaises(KeyError):
            libro_de_prueba().filas("Inventada")


if __name__ == "__main__":
    unittest.main()
