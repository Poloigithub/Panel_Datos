"""Pruebas del motor de resolución de series del INE.

Se centran en las decisiones que determinan qué se publica: cómo se lee el
periodo, cuándo dos series se consideran la misma y cuál gana cuando hay
varias. Todo sin red: las descargas se inyectan en la caché del módulo.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import ine_series as motor  # noqa: E402


class LecturaDePeriodos(unittest.TestCase):
    """El INE devuelve el periodo de tres formas según el detalle pedido."""

    def test_nombre_ya_formateado(self):
        self.assertEqual(motor.etiqueta_periodo({"NombrePeriodo": "2024T3"}), "2024T3")

    def test_tip_amigable_trae_el_subperiodo_aparte(self):
        self.assertEqual(motor.etiqueta_periodo({"Anyo": 2024, "T3_Periodo": "T2"}), "2024T2")

    def test_sin_detalle_el_trimestre_es_un_numero_interno(self):
        self.assertEqual(motor.etiqueta_periodo({"Anyo": 2024, "FK_Periodo": 21}), "2024T3")

    def test_semestres(self):
        self.assertEqual(motor.etiqueta_periodo({"Anyo": 2024, "FK_Periodo": 23}), "2024S1")

    def test_periodo_en_numeracion_romana(self):
        self.assertEqual(motor.etiqueta_periodo({"Anyo": 2024, "Periodo": {"Nombre": "III"}}), "2024T3")

    def test_operacion_anual_se_queda_en_el_ano(self):
        self.assertEqual(motor.etiqueta_periodo({"Anyo": 2023}), "2023")

    def test_admite_periodos_mensuales(self):
        # El motor es común a todas las operaciones y el IPC es mensual; quien
        # exige trimestres es el descargador de la EPA, no esto.
        self.assertEqual(motor.etiqueta_periodo({"NombrePeriodo": "2024M03"}), "2024M03")

    def test_un_periodo_que_no_reconocemos_no_se_inventa(self):
        self.assertIsNone(motor.etiqueta_periodo({}))
        self.assertIsNone(motor.etiqueta_periodo({"NombrePeriodo": "no es un periodo"}))

    def test_orden_cronologico(self):
        periodos = ["2024T1", "2023", "2024S2", "2024T4", "2002T1"]
        self.assertEqual(
            sorted(periodos, key=motor.orden_periodo),
            ["2002T1", "2023", "2024T1", "2024S2", "2024T4"],
        )

    def test_los_meses_tambien_ordenan(self):
        self.assertEqual(
            sorted(["2024M12", "2024M02", "2023M11"], key=motor.orden_periodo),
            ["2023M11", "2024M02", "2024M12"],
        )

    def test_un_periodo_ilegible_no_rompe_la_ordenacion(self):
        self.assertEqual(motor.orden_periodo("vete a saber"), (0, 0, 0))

    def test_meses_y_trimestres_del_mismo_bloque_no_empatan(self):
        """Un bloque puede mezclar frecuencias y el orden ha de ser estable."""
        mezcla = ["2024M01", "2024T1", "2024", "2024S1"]
        self.assertEqual(
            sorted(mezcla, key=motor.orden_periodo),
            ["2024", "2024S1", "2024T1", "2024M01"],
        )


class SegmentosDelNombre(unittest.TestCase):
    """El nombre de una serie encadena los valores de sus variables."""

    def test_separa_por_puntos_y_normaliza(self):
        self.assertEqual(
            motor.segmentos("Mujeres. Castellón/Castelló. Total. Parados. Valor absoluto."),
            {"mujeres", "castellon/castello", "total", "parados", "valor absoluto"},
        )

    def test_algunas_series_usan_comas(self):
        self.assertEqual(
            motor.segmentos("Castellón/Castelló, Mortalidad, Total"),
            {"castellon/castello", "mortalidad", "total"},
        )

    def test_los_espacios_de_sobra_no_crean_segmentos_distintos(self):
        self.assertEqual(
            motor.segmentos("Fecundidad. Edad media a la maternidad     . Total."),
            {"fecundidad", "edad media a la maternidad", "total"},
        )


class ConcordanciaEntreSeries(unittest.TestCase):
    """Dos series sólo se pueden unir si miden lo mismo donde se solapan."""

    def test_valores_iguales_en_el_solape(self):
        self.assertTrue(
            motor.concuerdan({"2023": 10.0, "2024": 11.0}, {"2024": 11.0, "2025": 12.0})
        )

    def test_valores_distintos_en_el_solape(self):
        self.assertFalse(
            motor.concuerdan({"2024": 10.0}, {"2024": 25.0, "2025": 12.0})
        )

    def test_sin_solape_no_se_puede_afirmar_que_midan_lo_mismo(self):
        # Unirlas encadenaría metodologías distintas sin saberlo.
        self.assertFalse(motor.concuerdan({"2020": 10.0}, {"2024": 11.0}))

    def test_tolera_el_redondeo_del_ine(self):
        self.assertTrue(motor.concuerdan({"2024": 100.0}, {"2024": 100.5}))
        self.assertFalse(motor.concuerdan({"2024": 100.0}, {"2024": 102.0}))


class SeleccionEntreCandidatas(unittest.TestCase):
    """El INE reparte la misma cifra entre varias series y conserva versiones
    antiguas: gana la que mejor cubre la historia."""

    def setUp(self):
        motor._descargadas.clear()

    def tearDown(self):
        motor._descargadas.clear()

    def _candidata(self, cod, nombre, valores):
        motor._descargadas[cod] = valores
        return {"COD": cod, "Nombre": nombre}

    def test_una_serie_testimonial_no_gana_a_la_historica(self):
        # El caso real: los parados de hombres en España tenían una serie
        # nueva de dos trimestres y otra con el histórico entero.
        nueva = self._candidata("NUEVA", "a. b.", {"2026T1": 5.0, "2026T2": 6.0})
        historica = self._candidata(
            "HIST", "a. b. c.", {f"20{a:02d}": float(a) for a in range(2, 26)}
        )
        valores, usados = motor.fusiona([nueva, historica], "prueba")
        self.assertEqual(usados[0], "HIST")
        self.assertGreater(len(valores), 20)

    def test_rellena_huecos_con_las_que_concuerdan(self):
        base = self._candidata("BASE", "a.", {"2023": 8.0, "2024": 9.0})
        vieja = self._candidata("VIEJA", "a. b.", {"2021": 6.0, "2022": 7.0, "2023": 8.0})
        valores, usados = motor.fusiona([base, vieja], "prueba")
        self.assertEqual(sorted(valores), ["2021", "2022", "2023", "2024"])
        self.assertEqual(set(usados), {"BASE", "VIEJA"})

    def test_no_mezcla_una_serie_que_mide_otra_cosa(self):
        base = self._candidata("BASE", "a.", {"2023": 8.0, "2024": 9.0})
        otra = self._candidata("OTRA", "a. b.", {"2023": 80.0, "2022": 70.0})
        valores, usados = motor.fusiona([base, otra], "prueba")
        self.assertEqual(usados, ["BASE"])
        self.assertNotIn("2022", valores)

    def test_descarta_las_candidatas_cuyos_valores_no_cuadran(self):
        # El INE conserva el IPC con bases antiguas: miden lo mismo pero en
        # otra escala, y la más larga no es la buena.
        vieja = self._candidata("VIEJA", "x.", {f"1993M{m:02d}": 8.0 for m in range(1, 13)})
        actual = self._candidata("ACTUAL", "x. y.", {"2026M01": 118.0, "2026M02": 119.0})
        acepta = lambda valores: all(50 <= v <= 200 for v in valores.values())
        valores, usados = motor.fusiona([vieja, actual], "ipc", acepta=acepta)
        self.assertEqual(usados, ["ACTUAL"])
        self.assertNotIn("1993M01", valores)

    def test_sin_datos_no_devuelve_nada(self):
        vacia = self._candidata("VACIA", "a.", {})
        valores, usados = motor.fusiona([vacia], "prueba")
        self.assertEqual(valores, {})
        self.assertEqual(usados, [])


class BusquedaPorSegmentos(unittest.TestCase):
    """Una serie del total es la que añade, como mucho, muletillas."""

    def setUp(self):
        motor._descargadas.clear()
        self.indice = {
            frozenset({"castellon/castello", "parados", "total", "valor absoluto"}):
                [{"COD": "BUENA", "Nombre": "Castellón/Castelló. Parados. Total. Valor absoluto."}],
            frozenset({"castellon/castello", "parados", "de 25 a 54 anos", "valor absoluto"}):
                [{"COD": "EDAD", "Nombre": "Castellón/Castelló. Parados. De 25 a 54 años. Valor absoluto."}],
            frozenset({"castellon/castello", "parados", "servicios", "valor absoluto"}):
                [{"COD": "SECTOR", "Nombre": "Castellón/Castelló. Parados. Servicios. Valor absoluto."}],
        }

    def tearDown(self):
        motor._descargadas.clear()

    def test_descarta_los_desgloses(self):
        candidatas = motor.candidatas_para(self.indice, {"castellon/castello", "parados"})
        self.assertEqual([c["COD"] for c in candidatas], ["BUENA"])

    def test_no_encuentra_lo_que_no_esta(self):
        self.assertEqual(motor.candidatas_para(self.indice, {"castellon/castello", "ocupados"}), [])

    def test_resuelve_devuelve_los_valores_de_la_serie(self):
        motor._descargadas["BUENA"] = {"2024T1": 30.0}
        valores, usados = motor.resuelve(self.indice, {"castellon/castello", "parados"}, "prueba")
        self.assertEqual(valores, {"2024T1": 30.0})
        self.assertEqual(usados, ["BUENA"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
