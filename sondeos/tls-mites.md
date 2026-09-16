# ¿Se puede hablar con el ministerio?

El error era `unable to get local issuer certificate`, que casi
siempre significa que el servidor no manda el certificado
intermedio. Esto lo comprueba y busca el eslabón que falta.

No se ha podido ni mirar: AttributeError: 'SSLSocket' object has no attribute 'get_unverified_chain'
