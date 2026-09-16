# ¿Se puede hablar con el ministerio?

El error era `unable to get local issuer certificate`, que casi
siempre significa que el servidor no manda el certificado
intermedio. Esto lo comprueba y busca el eslabón que falta.

- el servidor entrega 1 certificado(s) al pedirlo suelto
    0. FNMT-RCM1%0# · AC Componentes Inform · ticos0 · 251214065317Z · 261214065317Z0 · MADRID100. · 'MINISTERIO DE TRABAJO Y ECONOMIA SOCIAL1 · S2819001E1

## Direcciones escritas dentro del certificado

- `http://ocspcomp.cer`
- `http://www.cert.fnmt.es/certs/ACCOMP.crt`
- `http://www.cer`

## Con el eslabón que faltaba

- `http://ocspcomp.cer` → no se ha podido bajar: URLError: <urlopen error [Errno -2] Name or service not known>
- `http://www.cert.fnmt.es/certs/ACCOMP.crt` → **sirve**: 200, 4000 bytes con verificación completa
- `http://www.cer` → no se ha podido bajar: URLError: <urlopen error [Errno -2] Name or service not known>
