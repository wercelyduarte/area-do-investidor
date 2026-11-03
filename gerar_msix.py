# -*- coding: utf-8 -*-
r"""
Empacota o build do cx_Freeze num .msix para a Microsoft Store.

  python setup.py build      (gera build\GerenciadorInvestidor\)
  python gerar_msix.py       -> dist\GerenciadorInvestidor-X.Y.Z.msix

A Store assina o pacote na publicacao: nao precisa de certificado pago. A identidade
(nome, publisher) vem do Partner Center > Gerenciamento de produto > Identidade do produto,
pelas variaveis MSIX_NOME, MSIX_PUBLISHER e MSIX_PUBLISHER_NOME (no GitHub: Settings >
Variables). Sem elas o pacote sai com uma identidade de teste, que a Store recusa.
"""
import glob
import os
import shutil
import subprocess
import sys
from xml.sax.saxutils import escape

from PIL import Image

APP_NAME = "GerenciadorInvestidor"
VERSION = os.environ.get("VERSAO", "2.0.0")
BUILD_DIR = os.path.join("build", APP_NAME)
NOME = os.environ.get("MSIX_NOME") or "wercelyduarte.AreadoInvestidor"
PUBLISHER = os.environ.get("MSIX_PUBLISHER") or "CN=wercelyduarte"
PUBLISHER_NOME = os.environ.get("MSIX_PUBLISHER_NOME") or "wercelyduarte"

# Tamanhos que o manifesto pede (a Store exige StoreLogo, 44 e 150)
LOGOS = {"StoreLogo.png": 50, "Square44x44Logo.png": 44, "Square150x150Logo.png": 150,
         "Square44x44Logo.targetsize-256_altform-unplated.png": 256}

MANIFESTO = """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
         xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
         xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
         IgnorableNamespaces="uap rescap">
  <Identity Name="{nome}" Publisher="{publisher}" Version="{versao}" ProcessorArchitecture="x64"/>
  <Properties>
    <DisplayName>Área do Investidor</DisplayName>
    <PublisherDisplayName>{publisher_nome}</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>
  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22621.0"/>
  </Dependencies>
  <Resources>
    <Resource Language="pt-BR"/>
  </Resources>
  <Applications>
    <Application Id="Gerenciador" Executable="{app}.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements DisplayName="Gerenciador do Investidor"
                          Description="Cadastre investidores e aplicações numa planilha do Google Sheets."
                          BackgroundColor="transparent"
                          Square150x150Logo="Assets\\Square150x150Logo.png"
                          Square44x44Logo="Assets\\Square44x44Logo.png"/>
    </Application>
  </Applications>
  <Capabilities>
    <rescap:Capability Name="runFullTrust"/>
  </Capabilities>
</Package>
"""


def achar_makeappx():
    """makeappx.exe do Windows SDK mais novo instalado."""
    achados = glob.glob(r"C:\Program Files (x86)\Windows Kits\10\bin\10.*\x64\makeappx.exe")
    if not achados:
        sys.exit("makeappx.exe nao encontrado: instale o Windows SDK.")
    return sorted(achados, key=lambda p: [int(n) for n in p.split("\\")[-3].split(".")])[-1]


def main():
    if not os.path.isfile(os.path.join(BUILD_DIR, f"{APP_NAME}.exe")):
        sys.exit(f"Build nao encontrado em {BUILD_DIR}: rode antes  python setup.py build")
    if glob.glob(os.path.join(BUILD_DIR, "client_secret*.json")):
        sys.exit("client_secret no build: a versao da Store nao pode levar credencial.")

    pacote = os.path.join("build", "msix")
    shutil.rmtree(pacote, ignore_errors=True)
    shutil.copytree(BUILD_DIR, pacote)

    # Logos a partir do maior tamanho do icone.ico
    assets = os.path.join(pacote, "Assets")
    os.makedirs(assets)
    with Image.open("icone.ico") as ico:
        ico.size = max(ico.ico.sizes())
        base = ico.convert("RGBA")
    for arquivo, lado in LOGOS.items():
        base.resize((lado, lado), Image.LANCZOS).save(os.path.join(assets, arquivo))

    # A Store exige o 4o numero da versao = 0
    with open(os.path.join(pacote, "AppxManifest.xml"), "w", encoding="utf-8") as f:
        f.write(MANIFESTO.format(nome=escape(NOME), publisher=escape(PUBLISHER, {'"': "&quot;"}),
                                 publisher_nome=escape(PUBLISHER_NOME), versao=f"{VERSION}.0",
                                 app=APP_NAME))

    os.makedirs("dist", exist_ok=True)
    saida = os.path.join("dist", f"{APP_NAME}-{VERSION}.msix")
    subprocess.run([achar_makeappx(), "pack", "/o", "/d", pacote, "/p", saida], check=True)
    print("MSIX gerado:", saida)


if __name__ == "__main__":
    main()
