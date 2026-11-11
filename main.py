"""Roda tudo na ordem e gera docs/index.html.  Uso: python main.py"""

import os
import runpy
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
os.chdir(AQUI)  # o script antigo grava em ./docs

ETAPAS = [
    ("script_antigo.py", ["--export"]),  # --export = não abre o navegador
    ("gera_detalhado.py", []),
    ("gera_tabela.py", []),
    ("build_index.py", []),
]

for nome, args in ETAPAS:
    print(f"\n=== {nome} ===")
    sys.argv = [nome] + args
    runpy.run_path(os.path.join(AQUI, nome), run_name="__main__")

print("\nPronto: docs/index.html")
