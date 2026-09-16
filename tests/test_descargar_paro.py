"""Pruebas del lector de los ficheros de paro registrado del SEPE.

El CSV real trae una fila de título antes de la cabecera, separadores de punto
y coma, y valores ocultos por secreto estadístico. Aquí se comprueba que todo
eso se maneja y que los tres ámbitos agregan lo que les toca.
"""

from __future__ import annotations

import sys
import unittest
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import descargar_paro as sepe  # noqa: E402

CABECERA = (";;;;PARO REGISTRADO POR MUNICIPIOS DESGLOSADO POR SEXO, TRAMOS DE EDAD"
            " Y SECTOR DE LA ACTIVIDAD ECONÓMICA;;;;;;;;;;;;;;;\n"
            "Código mes ;mes;Código de CA;Comunidad Autónoma;Codigo Provincia;Provincia;"
            "Codigo Municipio; Municipio;total Paro Registrado;Paro hombre edad < 25;"
            "Paro hombre edad 25 -45 ;Paro hombre edad >=45;Paro mujer edad < 25;"
            "Paro mujer edad 25 -45 ;Paro mujer edad >=45;Paro Agricultura;Paro Industria;"
            "Paro Construcción;Paro Servicios;Paro Sin empleo Anterior\n")

# Un municipio de Castellón, uno de Valencia y uno de Almería, en el mismo mes.
FILAS = (
    "202601;Enero de 2026;10;Comunitat Valenciana;12;Castellón;12040;Castellón de la Plana;"
    "1000;50;150;200;60;240;300;100;80;120;600;100\n"
    "202601;Enero de 2026;10;Comunitat Valenciana;46;Valencia;46250;Valencia;"
    "2000;100;300;400;120;480;600;200;160;240;1200;200\n"
    "202601;Enero de 2026;1;Andalucía;4;Almería;04001;Abla;"
    "65;<5;10;24;<5;10;21;10;<5;5;45;<5\n"
)


class LecturaDelFichero(unittest.TestCase):
    def setUp(self):
        self.acumulado = defaultdict(int)
        self.municipios = {}
        self.censura = defaultdict(int)
        self.filas = sepe.lee_anyo(sepe.FUENTES["paro-registrado"], CABECERA + FILAS,
                                   self.acumulado, self.municipios, self.censura)

    def test_lee_todas_las_filas_saltando_el_titulo(self):
        self.assertEqual(self.filas, 3)

    def test_espana_agrega_los_tres_municipios(self):
        self.assertEqual(self.acumulado[("espana", "ambos", "paro_total", "2026M01")],
                         1000 + 2000 + 65)

    def test_la_comunitat_agrega_solo_los_suyos(self):
        self.assertEqual(
            self.acumulado[("comunitat-valenciana", "ambos", "paro_total", "2026M01")],
            3000)

    def test_castellon_agrega_solo_su_provincia(self):
        self.assertEqual(self.acumulado[("castellon", "ambos", "paro_total", "2026M01")],
                         1000)

    def test_el_desglose_por_sexo_suma_en_ambos(self):
        # 150 hombres y 240 mujeres de 25 a 44 en Castellón.
        self.assertEqual(self.acumulado[("castellon", "hombres", "paro_25_44", "2026M01")], 150)
        self.assertEqual(self.acumulado[("castellon", "mujeres", "paro_25_44", "2026M01")], 240)
        self.assertEqual(self.acumulado[("castellon", "ambos", "paro_25_44", "2026M01")], 390)

    def test_los_valores_ocultos_no_se_cuentan_como_cero(self):
        # Abla tiene «<5» en cuatro columnas; ninguna suma, y quedan contadas.
        self.assertEqual(sum(self.censura.values()), 4)
        self.assertEqual(self.acumulado[("espana", "hombres", "paro_menores_25", "2026M01")],
                         50 + 100)

    def test_guarda_el_detalle_municipal_de_castellon(self):
        self.assertEqual(self.municipios[("12040", "Castellón de la Plana", "2026M01")], 1000)
        self.assertNotIn(("46250", "Valencia", "2026M01"), self.municipios)


class TotalesPorSexo(unittest.TestCase):
    def test_el_total_de_un_sexo_es_la_suma_de_sus_tramos(self):
        acumulado = defaultdict(int)
        for tramo, numero in (("paro_menores_25", 50), ("paro_25_44", 150), ("paro_45_mas", 200)):
            acumulado[("castellon", "hombres", tramo, "2026M01")] = numero
        sepe.compone_totales(sepe.FUENTES["paro-registrado"], acumulado)
        self.assertEqual(acumulado[("castellon", "hombres", "paro_total", "2026M01")], 400)


class Contratos(unittest.TestCase):
    """El fichero de contratos tiene la misma forma y otras columnas, con
    espacios irregulares en las cabeceras."""

    CABECERA = (";;;;CONTRATOS POR MUNICIPIOS;;;;;;;;;;;;;;\n"
                "Código mes ;mes;Código de CA;Comunidad Autónoma;Codigo Provincia;Provincia;"
                "Codigo Municipio; Municipio;Total Contratos;"
                "Contratos iniciales indefinidos hombres;Contratos iniciales temporales hombres;"
                "Contratos convertidos en indefinidos hombres;"
                "Contratos iniciales indefinidos mujeres;Contratos iniciales temporales mujeres;"
                "Contratos convertidos en indefinidos mujeres;"
                "Contratos  Agricultura;Contratos  Industria;Contratos Construcción;"
                "Contratos  Servicios\n")
    FILA = ("202601;Enero de 2026;10;Comunitat Valenciana;12;Castellón;12040;Castelló;"
            "500;100;150;20;80;130;20;50;60;90;300\n")

    def test_lee_los_contratos_pese_a_los_espacios_dobles(self):
        acumulado, municipios, censura = defaultdict(int), {}, defaultdict(int)
        filas = sepe.lee_anyo(sepe.FUENTES["contratos"], self.CABECERA + self.FILA,
                              acumulado, municipios, censura)
        self.assertEqual(filas, 1)
        self.assertEqual(acumulado[("castellon", "ambos", "contratos_total", "2026M01")], 500)
        # «Contratos  Agricultura» lleva dos espacios en el fichero real.
        self.assertEqual(acumulado[("castellon", "ambos", "contratos_agricultura", "2026M01")], 50)
        self.assertEqual(acumulado[("castellon", "ambos", "contratos_indefinidos", "2026M01")], 180)
        self.assertEqual(acumulado[("castellon", "hombres", "contratos_temporales", "2026M01")], 150)


class Celdas(unittest.TestCase):
    def test_numeros_con_separador_de_miles(self):
        self.assertEqual(sepe.valor(" 1.387 "), 1387)

    def test_los_valores_ocultos_se_senalan(self):
        with self.assertRaises(sepe.Censurado):
            sepe.valor("<5")
        with self.assertRaises(sepe.Censurado):
            sepe.valor("")

    def test_periodos(self):
        self.assertEqual(sepe.periodo_de("202601"), "2026M01")
        self.assertEqual(sepe.periodo_de("202612"), "2026M12")
        self.assertIsNone(sepe.periodo_de("2026"))
        self.assertIsNone(sepe.periodo_de("202613"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
