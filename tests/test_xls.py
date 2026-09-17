"""Pruebas del lector del .xls binario.

No se puede probar contra un fichero real sin meter un binario en el
repositorio, así que se prueba lo que se puede probar de verdad: las piezas
sueltas y difíciles. Y son justo las que se equivocan solas.

Lo que sí se prueba contra ficheros de verdad es el descargador, en el ensayo,
que es donde se ven los tropiezos que ninguna prueba de laboratorio anticipa.
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import xls  # noqa: E402


class DescifraRk(unittest.TestCase):
    """El número comprimido de cuatro bytes, que tiene cuatro casos."""

    def test_entero(self):
        # 1234 guardado como entero: se desplaza dos bits a la izquierda.
        self.assertEqual(xls.descifra_rk(1234 << 2 | 0x02), 1234)

    def test_entero_en_centesimas(self):
        self.assertAlmostEqual(xls.descifra_rk(1234 << 2 | 0x03), 12.34)

    def test_decimal(self):
        # Los treinta bits altos de un decimal, con los dos de abajo a cero.
        crudo = struct.unpack("<Q", struct.pack("<d", 3.5))[0] >> 32
        self.assertAlmostEqual(xls.descifra_rk(crudo & 0xFFFFFFFC), 3.5)

    def test_decimal_en_centesimas(self):
        crudo = struct.unpack("<Q", struct.pack("<d", 250.0))[0] >> 32
        self.assertAlmostEqual(xls.descifra_rk((crudo & 0xFFFFFFFC) | 0x01), 2.5)

    def test_entero_negativo(self):
        # Un menos uno comprimido: los treinta bits a uno.
        self.assertEqual(xls.descifra_rk(((-1 & 0x3FFFFFFF) << 2) | 0x02), -1)


def _cadena_corta(texto: str, ancho16: bool = True) -> bytes:
    crudo = texto.encode("utf-16-le" if ancho16 else "latin-1")
    return struct.pack("<HB", len(texto), 1 if ancho16 else 0) + crudo


class LeeCadena(unittest.TestCase):
    """Las cadenas de BIFF8, que llevan su ancho escrito delante."""

    def test_dos_bytes_por_letra(self):
        trozos = xls._Trozos([_cadena_corta("Castellón")])
        texto, fin = xls._lee_cadena(trozos, 0)
        self.assertEqual(texto, "Castellón")
        self.assertEqual(fin, len(trozos.datos))

    def test_un_byte_por_letra(self):
        trozos = xls._Trozos([_cadena_corta("Total", ancho16=False)])
        self.assertEqual(xls._lee_cadena(trozos, 0)[0], "Total")

    def test_dos_seguidas(self):
        trozos = xls._Trozos([_cadena_corta("uno") + _cadena_corta("dos")])
        primera, fin = xls._lee_cadena(trozos, 0)
        segunda, _ = xls._lee_cadena(trozos, fin)
        self.assertEqual((primera, segunda), ("uno", "dos"))

    def test_partida_por_un_empalme(self):
        """Lo que de verdad rompe un lector: una cadena cortada en dos trozos.

        Al otro lado del corte hay un byte nuevo que dice el ancho, y si no se
        lee, el texto sale convertido en jeroglíficos.
        """
        entera = _cadena_corta("Comunitat Valenciana")
        corte = 3 + 10 * 2          # cabecera más diez letras
        trozos = xls._Trozos([entera[:corte], b"\x01" + entera[corte:]])
        self.assertEqual(xls._lee_cadena(trozos, 0)[0], "Comunitat Valenciana")

    def test_cambia_de_ancho_al_empalmar(self):
        """Y el caso peor: empieza en dos bytes por letra y sigue en uno."""
        cabecera = struct.pack("<HB", 8, 1)
        primera = cabecera + "cuatro".encode("utf-16-le")[:8]   # cuatro letras
        segunda = b"\x00" + "mil".encode("latin-1") + b"x"
        trozos = xls._Trozos([primera, segunda])
        self.assertEqual(xls._lee_cadena(trozos, 0)[0], "cuatmilx")

    def test_texto_con_formatos(self):
        """Con formatos por dentro, los sobrantes van detrás y hay que saltarlos."""
        crudo = struct.pack("<HBH", 3, 0x09, 2) + "abc".encode("utf-16-le")
        relleno = b"\x00" * 8       # dos tramos de formato, cuatro bytes cada uno
        trozos = xls._Trozos([crudo + relleno])
        texto, fin = xls._lee_cadena(trozos, 0)
        self.assertEqual(texto, "abc")
        self.assertEqual(fin, len(trozos.datos))


class Registros(unittest.TestCase):
    """La tira de trozos con dos bytes de tipo y dos de longitud."""

    def test_recorre_y_para(self):
        flujo = (struct.pack("<HH", xls.BOF, 2) + b"ab"
                 + struct.pack("<HH", xls.EOF_, 0))
        vistos = [(tipo, cuerpo) for _, tipo, cuerpo in xls._registros(flujo)]
        self.assertEqual(vistos, [(xls.BOF, b"ab"), (xls.EOF_, b"")])

    def test_no_se_pasa_del_final(self):
        # Un fichero truncado no debe reventar: se deja de leer y ya está.
        flujo = struct.pack("<HH", xls.BOF, 40) + b"corto"
        self.assertEqual(len(list(xls._registros(flujo))), 1)


class Envoltorio(unittest.TestCase):
    def test_rechaza_lo_que_no_es_un_xls(self):
        with self.assertRaises(ValueError):
            xls._Ole(b"PK\x03\x04 esto es un zip")


if __name__ == "__main__":
    unittest.main()
