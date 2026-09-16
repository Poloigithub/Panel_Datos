"""Pruebas del lector de lanzamientos del CGPJ.

El fichero del CGPJ tiene dos trampas que estas pruebas fijan: los periodos
vienen como «13-T1» y, debajo de la tabla de datos, hay un segundo cuadro con
variaciones y las mismas provincias repetidas.
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import cgpj_lanzamientos as cgpj  # noqa: E402
from xlsx import Libro  # noqa: E402

CADENAS = ["", "13-T1", "13-T2", "13-T3", "13-T4", "ALICANTE", "CASTELLON",
           "VALENCIA", "MADRID", "TOTAL", "Lanzamientos"]


def celda(referencia, valor):
    if isinstance(valor, str):
        return f'<c r="{referencia}" t="s"><v>{CADENAS.index(valor)}</v></c>'
    return f'<c r="{referencia}"><v>{valor}</v></c>'


def hoja(filas: list[list]) -> bytes:
    letras = "ABCDEFGH"
    cuerpo = []
    for i, fila in enumerate(filas, 1):
        celdas = "".join(celda(f"{letras[j]}{i}", v)
                         for j, v in enumerate(fila) if v is not None)
        cuerpo.append(f'<row r="{i}">{celdas}</row>')
    return ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org'
            '/spreadsheetml/2006/main"><sheetData>' + "".join(cuerpo) +
            "</sheetData></worksheet>").encode()


def libro_de_prueba(filas) -> Libro:
    cadenas = "".join(f"<si><t>{c}</t></si>" for c in CADENAS)
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w") as z:
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org'
                   '/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org'
                   '/officeDocument/2006/relationships"><sheets>'
                   '<sheet name="Lanzamientos pract. Total prov" sheetId="1" r:id="rId1"/>'
                   "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats'
                   '.org/package/2006/relationships"><Relationship Id="rId1" Type="x" '
                   'Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/sharedStrings.xml",
                   '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org'
                   '/spreadsheetml/2006/main">' + cadenas + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", hoja(filas))
    return Libro(memoria.getvalue())


FILAS = [
    ["Lanzamientos"],
    [None, "13-T1", "13-T2", "13-T3", "13-T4"],
    ["ALICANTE", 100, 110, 120, 130],
    ["CASTELLON", 20, 25, 30, 35],
    ["VALENCIA", 200, 210, 220, 230],
    ["MADRID", 300, 310, 320, 330],
    ["TOTAL", 1000, 1100, 1200, 1300],
    # Debajo, el cuadro de variaciones: mismas provincias, otros números.
    ["ALICANTE", 0.1, 0.2, 0.3, 0.4],
    ["CASTELLON", -0.5, 0.75, 0.1, 0.2],
    ["TOTAL", 0.05, 0.1, 0.15, 0.2],
]


class Periodos(unittest.TestCase):
    def test_el_ano_de_dos_cifras_se_completa(self):
        self.assertEqual(cgpj.etiqueta_periodo("13-T1"), "2013T1")

    def test_tambien_vale_el_ano_entero(self):
        self.assertEqual(cgpj.etiqueta_periodo("2026-T1"), "2026T1")

    def test_lo_que_no_es_un_periodo_no_se_fuerza(self):
        self.assertIsNone(cgpj.etiqueta_periodo("Provincias"))
        self.assertIsNone(cgpj.etiqueta_periodo(None))


class LecturaDeLaHoja(unittest.TestCase):
    def test_se_para_en_el_total(self):
        """El cuadro de variaciones de debajo no debe colarse en los datos."""
        leido = cgpj.lee_hoja(libro_de_prueba(FILAS), "Lanzamientos pract. Total prov")
        self.assertEqual(leido["castellon"],
                         {"2013T1": 20.0, "2013T2": 25.0, "2013T3": 30.0, "2013T4": 35.0})
        self.assertEqual(leido["total"]["2013T4"], 1300.0)

    def test_la_comunitat_se_suma_de_sus_tres_provincias(self):
        series = cgpj.series_del_libro(libro_de_prueba(FILAS))
        self.assertEqual(series["comunitat-valenciana"]["lanzamientos"]["2013T1"], 320.0)
        self.assertEqual(series["comunitat-valenciana"]["lanzamientos"]["2013T4"], 395.0)
        self.assertEqual(series["espana"]["lanzamientos"]["2013T1"], 1000.0)
        self.assertEqual(series["castellon"]["lanzamientos"]["2013T2"], 25.0)

    def test_sin_las_tres_provincias_no_hay_comunitat(self):
        """Sumar dos de tres daría una cifra menor que la real, y callada."""
        filas = [f for f in FILAS if f[0] != "VALENCIA"]
        series = cgpj.series_del_libro(libro_de_prueba(filas))
        self.assertNotIn("lanzamientos", series["comunitat-valenciana"])

    def test_una_hoja_sin_cabecera_de_trimestres_se_denuncia(self):
        filas = [["Lanzamientos"], ["ALICANTE", 1, 2, 3, 4], ["TOTAL", 3, 4, 5, 6]]
        with self.assertRaises(ValueError):
            cgpj.lee_hoja(libro_de_prueba(filas), "Lanzamientos pract. Total prov")


class EleccionDelFichero(unittest.TestCase):
    def test_gana_el_trimestre_mas_reciente(self):
        """Los enlaces no vienen ordenados: manda lo que dice el nombre."""
        nombres = ["Series - ... por provincias 4T-2025.xlsx",
                   "Series - ... por provincias 1T-2026_revisado.xlsx",
                   "Series - ... por provincias 2T 2025.xlsx"]
        orden = []
        for nombre in nombres:
            c = cgpj.TRIMESTRE_EN_NOMBRE.search(nombre)
            orden.append(((int(c.group(2)), int(c.group(1))), nombre))
        self.assertEqual(max(orden)[1], "Series - ... por provincias 1T-2026_revisado.xlsx")


if __name__ == "__main__":
    unittest.main()
