"""El validador: que un rango de bloque gane al rango general.

Dos bloques pueden llamar igual a cosas distintas. El azúcar de la cesta de
la compra es un índice del IPC con base 100; el de materias primas son
dólares por kilo. Con un único diccionario de rangos por nombre, el rango de
uno declaraba inválido al otro, que es exactamente lo que pasó al publicar
las materias primas.
"""

from __future__ import annotations

import datetime as dt
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import validar_datos as validador  # noqa: E402


class RangosPorBloque(unittest.TestCase):
    def setUp(self) -> None:
        self.originales = dict(validador.RANGOS)
        validador.RANGOS.clear()
        validador.RANGOS.update({
            "azucar": (30, 400),            # el índice del IPC
            "materias/azucar": (0.01, 5),   # dólares por kilo
            "tasa_paro": (0, 70),           # sin bloque: vale para todos
        })

    def tearDown(self) -> None:
        validador.RANGOS.clear()
        validador.RANGOS.update(self.originales)

    def _revisa(self, bloque: str, clave: str, valores: list[float]):
        informe = validador.Informe()
        contenido = {"series": {"ambos": {clave: valores}}}
        validador.revisa_rangos(bloque, "espana", contenido, informe)
        return informe

    def test_el_rango_del_bloque_manda_sobre_el_general(self) -> None:
        """0,12 $/kg es azúcar correcto aunque el rango general pida 30-400."""
        informe = self._revisa("materias", "azucar", [0.12, 0.78, 0.41])
        self.assertEqual(informe.errores, [])

    def test_el_rango_general_sigue_valiendo_donde_no_hay_uno_de_bloque(self) -> None:
        informe = self._revisa("cesta", "azucar", [95.4, 101.2])
        self.assertEqual(informe.errores, [])

        informe = self._revisa("cesta", "azucar", [0.12])
        self.assertEqual(len(informe.errores), 1)
        self.assertIn("cesta/espana/ambos/azucar", informe.errores[0])

    def test_el_rango_del_bloque_tambien_puede_fallar(self) -> None:
        """No es un permiso para todo: fuera de su propio rango sigue siendo error."""
        informe = self._revisa("materias", "azucar", [0.4, 912.0])
        self.assertEqual(len(informe.errores), 1)
        self.assertIn("912.0", informe.errores[0])

    def test_un_indicador_sin_rango_declarado_no_se_revisa(self) -> None:
        informe = self._revisa("materias", "platino", [-5.0, 99999.0])
        self.assertEqual(informe.errores, [])

    def test_los_huecos_no_cuentan_como_valores_fuera_de_rango(self) -> None:
        """El panel no interpola: un None es un hueco, no un dato inválido."""
        informe = self._revisa("epa", "tasa_paro", [12.3, None, 14.1])
        self.assertEqual(informe.errores, [])


class SeriesRetiradas(unittest.TestCase):
    """Una serie sólo puede desaparecer si alguien lo ha escrito y explicado.

    La comprobación de cobertura es la alarma que caza el fallo silencioso: el
    INE renombra una serie, el descargador deja de encontrarla y el indicador
    se esfuma sin que nada falle. Si se pudiera callar borrando el registro de
    cobertura, dejaría de proteger. Por eso la retirada se declara.
    """

    def setUp(self) -> None:
        self.retiradas = dict(validador.RETIRADAS)

    def tearDown(self) -> None:
        validador.RETIRADAS.clear()
        validador.RETIRADAS.update(self.retiradas)

    def _cobertura(self, antes: dict, ahora: dict, tmp) -> list[str]:
        import json
        fichero = tmp / "cobertura.json"
        fichero.write_text(json.dumps({"series": antes}), encoding="utf-8")
        original = validador.COBERTURA
        validador.COBERTURA = fichero
        try:
            informe = validador.Informe()
            validador.revisa_cobertura(ahora, informe)
            return informe.errores
        finally:
            validador.COBERTURA = original

    def test_una_serie_que_se_va_sin_declarar_es_un_error(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            validador.RETIRADAS.clear()
            errores = self._cobertura({"epa/espana/ambos/ocupados": 90}, {},
                                      Path(carpeta))
        self.assertEqual(len(errores), 1)
        self.assertIn("desaparecida", errores[0])

    def test_una_serie_declarada_no_es_un_error(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            validador.RETIRADAS.clear()
            validador.RETIRADAS["materias/espana/ambos/cebada"] = "porque sí"
            errores = self._cobertura({"materias/espana/ambos/cebada": 728}, {},
                                      Path(carpeta))
        self.assertEqual(errores, [])

    def test_declararla_no_perdona_que_encoja(self) -> None:
        """Declarar una retirada permite que se vaya entera, no a medias.

        Una serie que pierde periodos pero sigue estando es el otro fallo: el
        descargador encuentra la serie pero lee de menos.
        """
        import tempfile
        with tempfile.TemporaryDirectory() as carpeta:
            validador.RETIRADAS.clear()
            validador.RETIRADAS["materias/espana/ambos/cebada"] = "porque sí"
            errores = self._cobertura({"materias/espana/ambos/cebada": 728},
                                      {"materias/espana/ambos/cebada": 400},
                                      Path(carpeta))
        self.assertEqual(len(errores), 1)
        self.assertIn("encogida", errores[0])

    def test_lo_declarado_apunta_a_algo_que_existio(self) -> None:
        """Cada retirada nombra un bloque real y trae fecha y motivo.

        Es lo que evita que el registro se llene de entradas sueltas que nadie
        puede comprobar.
        """
        bloques = {c.name for c in (RAIZ / "data").iterdir() if c.is_dir()}
        for clave, motivo in validador.RETIRADAS.items():
            trozos = clave.split("/")
            self.assertEqual(len(trozos), 4, f"clave mal formada: {clave}")
            self.assertIn(trozos[0], bloques, f"bloque inexistente en {clave}")
            self.assertRegex(motivo, r"^\d{4}-\d{2}-\d{2} · .",
                             f"la retirada de {clave} no dice cuándo ni por qué")


class FrescuraDeLosDiarios(unittest.TestCase):
    """Que un fichero diario que deja de crecer haga ruido.

    Es un punto ciego que existió de verdad: la frescura del bloque de
    carburantes la marca la serie semanal del boletín europeo, que llega
    siempre, así que el ministerio podía llevar semanas caído sin que nada lo
    dijera. Y como el descargador sigue adelante a propósito cuando una de sus
    dos fuentes falla, el run tampoco salía en rojo.
    """

    def setUp(self) -> None:
        import json, tempfile
        self.carpeta = tempfile.TemporaryDirectory()
        self.raiz = Path(self.carpeta.name)
        self.datos_original = validador.DATOS
        self.ficha_original = dict(validador.FRESCURA_DIARIA)
        validador.DATOS = self.raiz
        validador.FRESCURA_DIARIA.clear()
        validador.FRESCURA_DIARIA["carburantes/diario.json"] = {
            "cadencia": "diaria", "margen": 3,
            "donde": ("espana", "castellon"),
        }
        self._json = json

    def tearDown(self) -> None:
        validador.DATOS = self.datos_original
        validador.FRESCURA_DIARIA.clear()
        validador.FRESCURA_DIARIA.update(self.ficha_original)
        self.carpeta.cleanup()

    def _escribe(self, contenido) -> None:
        destino = self.raiz / "carburantes"
        destino.mkdir(parents=True, exist_ok=True)
        (destino / "diario.json").write_text(self._json.dumps(contenido),
                                             encoding="utf-8")

    def _revisa(self, hoy) -> list[str]:
        informe = validador.Informe()
        validador.revisa_frescura_diaria(informe, hoy=hoy)
        return informe.errores

    def test_al_dia_no_da_error(self) -> None:
        self._escribe({"espana": {"2026-09-17": {"gasolina_95": 1.9}},
                       "castellon": {"2026-09-16": {"gasolina_95": 1.9}}})
        self.assertEqual(self._revisa(dt.date(2026, 9, 17)), [])

    def test_dentro_del_margen_tampoco(self) -> None:
        """Un día suelto sin recoger es normal: la API se cae a ratos."""
        self._escribe({"espana": {"2026-09-14": {}}, "castellon": {"2026-09-14": {}}})
        self.assertEqual(self._revisa(dt.date(2026, 9, 17)), [])

    def test_pasado_el_margen_salta(self) -> None:
        self._escribe({"espana": {"2026-09-10": {}}, "castellon": {"2026-09-10": {}}})
        errores = self._revisa(dt.date(2026, 9, 17))
        self.assertEqual(len(errores), 2)
        self.assertIn("hace 7 días", errores[0])

    def test_un_ambito_puede_quedarse_atras_solo(self) -> None:
        """El caso que de verdad preocupa: España llega y Castellón no.

        Si el ministerio renumerase las provincias, la media nacional seguiría
        saliendo y la provincial se quedaría vacía sin que nada fallara.
        """
        self._escribe({"espana": {"2026-09-17": {}}, "castellon": {"2026-08-01": {}}})
        errores = self._revisa(dt.date(2026, 9, 17))
        self.assertEqual(len(errores), 1)
        self.assertIn("castellon", errores[0])

    def test_un_ambito_vacio_es_error(self) -> None:
        self._escribe({"espana": {"2026-09-17": {}}, "castellon": {}})
        errores = self._revisa(dt.date(2026, 9, 17))
        self.assertEqual(len(errores), 1)
        self.assertIn("no hay días recogidos", errores[0])

    def test_el_fichero_que_falta_es_error(self) -> None:
        errores = self._revisa(dt.date(2026, 9, 17))
        self.assertEqual(len(errores), 1)
        self.assertIn("no está publicado", errores[0])

    def test_las_claves_que_no_son_fechas_no_cuentan(self) -> None:
        """`actualizado` y `unidad` viven junto a los días en algunos ficheros."""
        self._escribe({"espana": {"actualizado": "2026-09-17T10:00:00+00:00",
                                  "2026-09-10": {}},
                       "castellon": {"2026-09-17": {}}})
        errores = self._revisa(dt.date(2026, 9, 17))
        self.assertEqual(len(errores), 1)
        self.assertIn("2026-09-10", errores[0])


if __name__ == "__main__":
    unittest.main()
