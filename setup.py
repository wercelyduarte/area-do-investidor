# -*- coding: utf-8 -*-
r"""
Build do Gerenciador - Area do Investidor com cx_Freeze.

  python setup.py build        -> pasta pronta em build\GerenciadorInvestidor\
  python setup.py bdist_msi    -> instalador .msi em dist\
"""
import os
import sys
import glob
from cx_Freeze import setup, Executable
from cx_Freeze.command.build_exe import build_exe as _build_exe

APP_NAME = "GerenciadorInvestidor"
VERSION = os.environ.get("VERSAO", "2.0.0")  # no GitHub Actions vem da tag (v2.1.0 -> 2.1.0)
DESCRIPTION = "Gerenciador da Area do Investidor (Google Sheets)"

# base "gui" esconde a janela preta do console no Windows
base = "gui" if sys.platform == "win32" else None

# Sem client_secret*.json na pasta (versao publica): no primeiro uso o assistente guia a
# pessoa a criar a propria credencial. Com o arquivo na pasta, ele vai junto no instalador
# (uso privado). estado.json e token.json NUNCA vao no instalador.
segredos = glob.glob("client_secret*.json")
print("client_secret incluido no instalador:" if segredos else
      "Sem client_secret: o usuario criara a propria credencial no 1o uso.", *segredos)

build_exe_options = {
    "build_exe": f"build/{APP_NAME}",
    "packages": ["googleapiclient", "google_auth_oauthlib", "google.auth", "google.oauth2",
                 "google_auth_httplib2", "httplib2", "ttkbootstrap", "tkinter", "encodings"],
    "excludes": ["matplotlib", "pandas", "scipy", "numpy", "IPython", "pytest", "PyQt5", "PyQt6"],
    "include_files": [("icone.ico", "icone.ico"), ("Code.gs", "Code.gs"),
                      ("Index.html", "Index.html")] + [(s, s) for s in segredos],
    "include_msvcr": True,
    "optimize": 1,
}

APIS_USADAS = ("sheets.v4.json", "script.v1.json", "drive.v3.json")


class build_exe(_build_exe):
    """Apaga as descricoes das ~500 APIs do Google que o programa nao usa (~100 MB)."""

    def run(self):
        super().run()
        docs = os.path.join(self.build_exe, "lib", "googleapiclient", "discovery_cache", "documents")
        for arq in glob.glob(os.path.join(docs, "*.json")):
            if os.path.basename(arq) not in APIS_USADAS:
                os.remove(arq)


bdist_msi_options = {
    "upgrade_code": "{5C2E7A1D-93B4-4F6E-8D0A-7B1C3E9F2A64}",  # mantenha fixo p/ atualizacoes
    "initial_target_dir": rf"[ProgramFiles64Folder]\{APP_NAME}",
    "add_to_path": False,
}

executables = [
    Executable(
        "gerenciador.py",
        base=base,
        target_name=f"{APP_NAME}.exe",
        icon="icone.ico",
        shortcut_name="Gerenciador do Investidor",  # atalho criado pelo .msi
        shortcut_dir="DesktopFolder",
    )
]

setup(
    name=APP_NAME,
    version=VERSION,
    description=DESCRIPTION,
    options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
    cmdclass={"build_exe": build_exe},
    executables=executables,
)
