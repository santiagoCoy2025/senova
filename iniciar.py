#!/usr/bin/env python3
"""Prepara e inicia GESICOM local con Python, sin Docker ni servicios externos."""

import argparse
import socket
import sys

from scripts import configurar_entorno


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preparar", action="store_true", help="Prepara el entorno y las cuentas sin iniciar el servidor."
    )
    parser.add_argument("--extensiones", action="store_true", help="Instala las extensiones recomendadas de VS Code.")
    parser.add_argument("--puerto", type=int, default=8000)
    args = parser.parse_args(argv)
    if not 1024 <= args.puerto <= 65535:
        parser.error("El puerto debe estar entre 1024 y 65535.")
    if not args.preparar:
        try:
            with socket.socket() as reserva:
                reserva.settimeout(1)
                ocupado = reserva.connect_ex(("127.0.0.1", args.puerto)) == 0
        except OSError:
            ocupado = True
        if ocupado:
            print(
                f"No se puede usar el puerto {args.puerto}. Cierra la otra instancia o usa: python iniciar.py --puerto 8001",
                file=sys.stderr,
            )
            return 2
    parametros = ["--inicio-rapido", "--solo-ejecucion", "--reparar-entorno", "--puerto", str(args.puerto)]
    if not args.preparar:
        parametros.append("--ejecutar")
    if args.extensiones:
        parametros.append("--extensiones")
    return configurar_entorno.main(parametros)


if __name__ == "__main__":
    raise SystemExit(main())
