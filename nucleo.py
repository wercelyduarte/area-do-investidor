# -*- coding: utf-8 -*-
"""
Nucleo do Gerenciador - Area do Investidor (sem interface).

  - Caminhos: arquivos do programa x dados da conta (estado.json, token.json).
  - Login OAuth no Google.
  - Leitura/gravacao das abas "Aplicacoes" e "Usuarios".
  - Criacao da planilha e publicacao do Web App (Code.gs + Index.html).
  - Funcoes de formatacao/conversao (R$, numeros no padrao brasileiro).
"""
import os
import re
import sys
import glob
import json
import shutil
import hashlib
import secrets

APP_NAME = "GerenciadorInvestidor"
REPO_URL = "https://github.com/wercelyduarte/area-do-investidor"
GUIA_URL = REPO_URL + "/blob/main/docs/GUIA_GOOGLE.md"

# Atalhos do Google Cloud Console usados pelo assistente de primeiro uso.
LINKS_GOOGLE = {
    "projeto": "https://console.cloud.google.com/projectcreate",
    "apis": ("https://console.cloud.google.com/flows/enableapi?"
             "apiid=script.googleapis.com,sheets.googleapis.com,drive.googleapis.com"),
    "consentimento": "https://console.cloud.google.com/auth/overview",
    "publico": "https://console.cloud.google.com/auth/audience",
    "credencial": "https://console.cloud.google.com/auth/clients/create",
    "apps_script": "https://script.google.com/home/usersettings",
}

# Arquivos do programa (Code.gs, Index.html, client_secret) ficam ao lado do .exe/.py.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    # Instalado em "Arquivos de Programas" (sem permissao de escrita):
    # os dados da conta ficam em %LOCALAPPDATA%\GerenciadorInvestidor.
    DATA_DIR = os.environ.get("GERENCIADOR_DADOS") or os.path.join(
        os.environ.get("LOCALAPPDATA", APP_DIR), APP_NAME)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.environ.get("GERENCIADOR_DADOS") or APP_DIR
os.makedirs(DATA_DIR, exist_ok=True)

ESTADO_FILE = os.path.join(DATA_DIR, "estado.json")
TOKEN_FILE = os.path.join(DATA_DIR, "token.json")
CODE_GS = os.path.join(APP_DIR, "Code.gs")
INDEX_HTML = os.path.join(APP_DIR, "Index.html")

SCOPES = [
    "https://www.googleapis.com/auth/script.projects",
    "https://www.googleapis.com/auth/script.deployments",
    "https://www.googleapis.com/auth/script.scriptapp",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

ABA_APLIC = "Aplicacoes"
ABA_USERS = "Usuarios"
HDR_APLIC = ["Investidor", "Valor Aplicado (R$)", "Data Aplicacao", "Prazo (meses)",
             "Porcentagem Lucro (%)", "Lucro Gerado (R$)", "Status"]
HDR_USERS = ["usuario", "senha_hash"]
USUARIO_ADMIN = "admin"

MANIFEST = {
    "timeZone": "America/Sao_Paulo",
    "runtimeVersion": "V8",
    "webapp": {"executeAs": "USER_DEPLOYING", "access": "ANYONE_ANONYMOUS"},
    "exceptionLogging": "STACKDRIVER",
}


# ─────────────────────────── estado / credenciais ───────────────────────────
def carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def salvar_estado(estado):
    with open(ESTADO_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2, ensure_ascii=False)


def arquivo_client_secret():
    """client_secret*.json: primeiro na pasta de dados, depois junto do programa."""
    for pasta in (DATA_DIR, APP_DIR):
        achados = glob.glob(os.path.join(pasta, "client_secret*.json"))
        if achados:
            return achados[0]
    return None


def validar_client_secret(caminho):
    """Confere se o JSON e uma credencial OAuth do tipo "App para computador"."""
    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
    except Exception:
        raise ValueError("Este arquivo nao e um JSON valido de credenciais do Google.")
    if "installed" not in dados:
        if "web" in dados:
            raise ValueError("Esta credencial e do tipo \"Aplicativo da Web\".\n"
                             "Crie uma nova do tipo \"App para computador\" (Desktop app).")
        raise ValueError("Este arquivo nao parece ser uma credencial OAuth do Google.")


def importar_client_secret(caminho):
    """Valida e copia a credencial para a pasta de dados."""
    validar_client_secret(caminho)
    for antigo in glob.glob(os.path.join(DATA_DIR, "client_secret*.json")):
        os.remove(antigo)
    destino = os.path.join(DATA_DIR, os.path.basename(caminho) if os.path.basename(caminho)
                           .startswith("client_secret") else "client_secret.json")
    shutil.copyfile(caminho, destino)
    return destino


def procurar_client_secret_downloads():
    """O client_secret*.json mais recente da pasta Downloads (ou None)."""
    pasta = os.path.join(os.path.expanduser("~"), "Downloads")
    achados = glob.glob(os.path.join(pasta, "client_secret*.json"))
    return max(achados, key=os.path.getmtime) if achados else None


def tem_token():
    return os.path.exists(TOKEN_FILE)


def autenticar(interativo=True):
    """Devolve credenciais validas. Se interativo, abre o navegador quando preciso.
    Sem token e nao interativo: devolve None."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None   # token revogado/expirado: pede login de novo
    if not creds or not creds.valid:
        if not interativo:
            return None
        secret = arquivo_client_secret()
        if not secret:
            raise FileNotFoundError(
                "Arquivo de credenciais do Google (client_secret*.json) nao encontrado.\n"
                f"Coloque-o em:\n{DATA_DIR}")
        flow = InstalledAppFlow.from_client_secrets_file(secret, SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True,
                                      success_message="Autorizado! Pode fechar esta aba e voltar ao Gerenciador.")
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    return creds


def desconectar():
    """Apaga o token (o estado e guardado como estado.bak.json)."""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    if os.path.exists(ESTADO_FILE):
        os.replace(ESTADO_FILE, os.path.join(DATA_DIR, "estado.bak.json"))


def _servico(nome, versao, creds):
    from googleapiclient.discovery import build
    return build(nome, versao, credentials=creds, cache_discovery=False)


def email_da_conta(creds):
    try:
        about = _servico("drive", "v3", creds).about().get(fields="user(emailAddress)").execute()
        return about.get("user", {}).get("emailAddress", "")
    except Exception:
        return ""


def explicar_erro(e):
    """Traduz erros comuns do Google para uma mensagem que o usuario entende."""
    txt = str(e)
    if hasattr(e, "content"):
        try:
            txt += " " + e.content.decode("utf-8", "replace")
        except Exception:
            pass
    if "Apps Script API" in txt and ("not enabled" in txt or "has not been used" in txt):
        return ("A API do Apps Script esta desativada na sua conta Google.\n\n"
                "Abra https://script.google.com/home/usersettings, ative a opcao "
                "\"API do Google Apps Script\" e tente de novo.")
    if "access_denied" in txt:
        return ("O Google recusou a autorizacao.\n\nNo Google Cloud Console, em \"Publico-alvo\", "
                "clique em \"Publicar app\" (ou adicione seu e-mail em \"Usuarios de teste\").\n"
                + LINKS_GOOGLE["publico"])
    if "invalid_grant" in txt:
        return "Sua sessao do Google expirou. Use \"Trocar conta / planilha\" e conecte de novo."
    if "Unable to parse range" in txt:
        return "A planilha nao tem as abas \"Aplicacoes\" e \"Usuarios\"."
    if "404" in txt and "Requested entity was not found" in txt:
        return "Planilha nao encontrada. Confira o link e se esta conta tem acesso a ela."
    if "403" in txt and "PERMISSION_DENIED" in txt:
        return "Esta conta Google nao tem permissao para acessar essa planilha."
    if any(s in txt for s in ("getaddrinfo", "timed out", "Connection", "ServerNotFound")):
        return "Sem conexao com a internet (ou o Google nao respondeu). Tente de novo."
    return txt


# ─────────────────────────── planilha ───────────────────────────────────────
def extrair_sheet_id(link):
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", link)
    if m:
        return m.group(1)
    link = link.strip()
    return link if re.fullmatch(r"[a-zA-Z0-9_-]{20,}", link) else None


def ler_abas(creds, sheet_id):
    """Le as duas abas. Numeros vem como numero; datas como texto (dd/mm/aaaa)."""
    sheets = _servico("sheets", "v4", creds)
    res = sheets.spreadsheets().values().batchGet(
        spreadsheetId=sheet_id, ranges=[ABA_APLIC, ABA_USERS],
        valueRenderOption="UNFORMATTED_VALUE",
        dateTimeRenderOption="FORMATTED_STRING",
    ).execute()
    vrs = res.get("valueRanges", [])
    return {ABA_APLIC: vrs[0].get("values", []), ABA_USERS: vrs[1].get("values", [])}


def gravar_aba(creds, sheet_id, aba, valores):
    """Grava primeiro e so depois limpa as linhas que sobraram (se a gravacao
    falhar no meio, nada e apagado)."""
    sheets = _servico("sheets", "v4", creds).spreadsheets().values()
    sheets.update(spreadsheetId=sheet_id, range=f"{aba}!A1",
                  valueInputOption="USER_ENTERED", body={"values": valores}).execute()
    sheets.clear(spreadsheetId=sheet_id, range=f"{aba}!A{len(valores) + 1}:ZZ").execute()


def criar_planilha(creds, senha_admin, titulo="Aplicacoes_Investidores"):
    """Cria a planilha vazia (so cabecalhos + usuario admin) e formata as colunas."""
    sheets = _servico("sheets", "v4", creds).spreadsheets()
    resp = sheets.create(body={
        "properties": {"title": titulo, "locale": "pt_BR", "timeZone": "America/Sao_Paulo"},
        "sheets": [{"properties": {"title": ABA_APLIC, "index": 0}},
                   {"properties": {"title": ABA_USERS, "index": 1}}],
    }).execute()
    sheet_id, url = resp["spreadsheetId"], resp["spreadsheetUrl"]
    abas = {s["properties"]["title"]: s["properties"]["sheetId"] for s in resp["sheets"]}

    sheets.values().batchUpdate(spreadsheetId=sheet_id, body={
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": f"{ABA_APLIC}!A1", "values": [HDR_APLIC]},
                 {"range": f"{ABA_USERS}!A1", "values": [HDR_USERS, [USUARIO_ADMIN, hash_senha(senha_admin)]]}],
    }).execute()

    def fmt_coluna(col, tipo, padrao):
        return {"repeatCell": {
            "range": {"sheetId": abas[ABA_APLIC], "startColumnIndex": col,
                      "endColumnIndex": col + 1, "startRowIndex": 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": tipo, "pattern": padrao}}},
            "fields": "userEnteredFormat.numberFormat"}}

    def negrito(aba):
        return {"repeatCell": {
            "range": {"sheetId": abas[aba], "startRowIndex": 0, "endRowIndex": 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"}}

    sheets.batchUpdate(spreadsheetId=sheet_id, body={"requests": [
        fmt_coluna(1, "CURRENCY", "R$ #,##0.00"),
        fmt_coluna(5, "CURRENCY", "R$ #,##0.00"),
        fmt_coluna(2, "DATE", "dd/MM/yyyy"),
        negrito(ABA_APLIC), negrito(ABA_USERS),
    ]}).execute()
    return sheet_id, url


def verificar_planilha(creds, sheet_id):
    """Confere se a planilha existe e tem as abas certas. Devolve (titulo, url).
    Ajusta a localidade para pt_BR: o programa grava datas como dd/mm/aaaa."""
    sheets = _servico("sheets", "v4", creds).spreadsheets()
    meta = sheets.get(spreadsheetId=sheet_id,
                      fields="properties(title,locale),spreadsheetUrl,sheets.properties.title").execute()
    nomes = {s["properties"]["title"] for s in meta.get("sheets", [])}
    faltando = [a for a in (ABA_APLIC, ABA_USERS) if a not in nomes]
    if faltando:
        raise ValueError("A planilha precisa ter as abas: " + ", ".join(faltando))
    if meta["properties"].get("locale") != "pt_BR":
        sheets.batchUpdate(spreadsheetId=sheet_id, body={"requests": [{"updateSpreadsheetProperties": {
            "properties": {"locale": "pt_BR"}, "fields": "locale"}}]}).execute()
    return meta["properties"]["title"], meta["spreadsheetUrl"]


# ─────────────────────────── Web App (pagina do investidor) ─────────────────
def publicar_web_app(creds, estado, descricao="Atualizacao via Gerenciador"):
    """Cria (se preciso) o Apps Script vinculado a planilha, sobe Code.gs + Index.html
    com o SHEET_ID desta planilha e cria/atualiza o deployment (a URL nao muda).
    Atualiza `estado` e salva estado.json a cada passo."""
    for arq in (CODE_GS, INDEX_HTML):
        if not os.path.exists(arq):
            raise FileNotFoundError(f"Arquivo nao encontrado: {arq}")
    script = _servico("script", "v1", creds)
    sheet_id = estado["sheet_id"]

    script_id = estado.get("script_id")
    if not script_id:
        proj = script.projects().create(
            body={"title": "Area do Investidor", "parentId": sheet_id}).execute()
        script_id = estado["script_id"] = proj["scriptId"]
        salvar_estado(estado)

    with open(CODE_GS, encoding="utf-8") as f:
        code_gs = re.sub(r"const\s+SHEET_ID\s*=\s*'[^']*'", f"const SHEET_ID = '{sheet_id}'", f.read())
    with open(INDEX_HTML, encoding="utf-8") as f:
        index_html = f.read()
    script.projects().updateContent(scriptId=script_id, body={"files": [
        {"name": "Code", "type": "SERVER_JS", "source": code_gs},
        {"name": "Index", "type": "HTML", "source": index_html},
        {"name": "appsscript", "type": "JSON", "source": json.dumps(MANIFEST)},
    ]}).execute()

    versao = script.projects().versions().create(
        scriptId=script_id, body={"description": descricao}).execute()["versionNumber"]
    estado["version_number"] = versao

    deployment_id = estado.get("deployment_id")
    if deployment_id:
        dep = script.projects().deployments().update(
            scriptId=script_id, deploymentId=deployment_id,
            body={"deploymentConfig": {"scriptId": script_id, "versionNumber": versao,
                                       "manifestFileName": "appsscript", "description": descricao}}
        ).execute()
    else:
        dep = script.projects().deployments().create(
            scriptId=script_id,
            body={"versionNumber": versao, "manifestFileName": "appsscript", "description": descricao}
        ).execute()
        deployment_id = estado["deployment_id"] = dep["deploymentId"]

    url = next((ep.get("webApp", {}).get("url") for ep in dep.get("entryPoints", [])
                if ep.get("entryPointType") == "WEB_APP"), None)
    estado["webapp_url"] = url or f"https://script.google.com/macros/s/{deployment_id}/exec"
    salvar_estado(estado)
    return versao


# ─────────────────────────── senhas / formatos ──────────────────────────────
def hash_senha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def gerar_senha(n=8):
    alfabeto = "abcdefghjkmnpqrstuvwxyz23456789"   # sem caracteres ambiguos (l, 1, o, 0)
    return "".join(secrets.choice(alfabeto) for _ in range(n))


def para_numero(v):
    """Aceita 5000, 5000.5, "5.000,50", "R$ 5.000,50", "10%". Vazio/invalido -> None."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = str(v or "").replace("R$", "").replace("%", "").replace(" ", "").strip()
    if not s:
        return None
    if "," in s or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):   # "5.000,50" ou "5.000"
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def brl(v):
    n = para_numero(v)
    if n is None:
        return str(v or "")
    return "R$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def num_br(v):
    """10 -> "10"; 10.5 -> "10,5" (para campos editaveis)."""
    n = para_numero(v)
    if n is None:
        return str(v or "")
    return str(int(n)) if n == int(n) else f"{n}".replace(".", ",")


def achar_coluna(headers, chave):
    """Indice da primeira coluna cujo nome contem `chave` (ignora maiusculas)."""
    chave = chave.lower()
    for i, h in enumerate(headers):
        if chave in str(h).lower():
            return i
    return -1
