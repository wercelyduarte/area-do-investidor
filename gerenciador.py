#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gerenciador - Area do Investidor
================================
  - Primeiro uso: assistente conecta a conta Google e cria (ou conecta) a planilha
    e publica a pagina do investidor.
  - Aplicacoes: cadastro por formulario, filtros e totais.
  - Investidores: criar login/senha, trocar senha, copiar mensagem de acesso.
  - Tudo e editado localmente e enviado com um unico "Salvar na planilha".

Rodar do codigo-fonte:  rodar.bat   (ou: py -3 gerenciador.py)
"""
import os
import json
import datetime
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, filedialog

import ttkbootstrap as ttk
from ttkbootstrap.widgets import DateEntry

import nucleo as nc

FONTE = "Segoe UI"
STATUS_PADRAO = ["Ativo", "Pago"]


# ─────────────────────────── utilitarios de UI ──────────────────────────────
def copiar(widget, texto):
    widget.clipboard_clear()
    widget.clipboard_append(texto)


def centralizar(janela, pai):
    janela.update_idletasks()
    x = pai.winfo_rootx() + (pai.winfo_width() - janela.winfo_width()) // 2
    y = pai.winfo_rooty() + (pai.winfo_height() - janela.winfo_height()) // 3
    janela.geometry(f"+{max(x, 0)}+{max(y, 0)}")


def mensagem_acesso(login, senha, url):
    return (f"Olá! Seu acesso à Área do Investidor:\n\n"
            f"Link: {url or '(pagina ainda nao publicada)'}\n"
            f"Usuário: {login}\n"
            f"Senha: {senha}\n\n"
            f"Guarde estes dados. Qualquer dúvida, é só chamar.")


class Dialogo(ttk.Toplevel):
    """Janela modal base: subclasses montam o corpo e preenchem self.resultado."""

    def __init__(self, pai, titulo):
        super().__init__(pai)
        self.withdraw()
        self.title(titulo)
        icone = os.path.join(nc.APP_DIR, "icone.ico")
        if os.path.exists(icone):
            try:
                self.iconbitmap(icone)
            except tk.TclError:
                pass
        self.resizable(False, False)
        self.transient(pai)
        self.resultado = None
        self.corpo = ttk.Frame(self, padding=20)
        self.corpo.pack(fill=tk.BOTH, expand=True)
        self.bind("<Escape>", lambda e: self.destroy())

    def botoes(self, texto_ok="Salvar"):
        rod = ttk.Frame(self, padding=(20, 0, 20, 16))
        rod.pack(fill=tk.X)
        ttk.Button(rod, text=texto_ok, bootstyle="primary", command=self.ok).pack(side=tk.RIGHT)
        ttk.Button(rod, text="Cancelar", bootstyle="secondary-outline",
                   command=self.destroy).pack(side=tk.RIGHT, padx=8)
        self.bind("<Return>", lambda e: self.ok())

    def mostrar(self):
        centralizar(self, self.master)
        self.deiconify()
        self.grab_set()
        self.wait_window()
        return self.resultado

    def ok(self):
        raise NotImplementedError

    def erro(self, msg):
        messagebox.showwarning("Confira os dados", msg, parent=self)


# ─────────────────────────── dialogo: aplicacao ─────────────────────────────
class DialogoAplicacao(Dialogo):
    def __init__(self, pai, headers, investidores, status, valores=None):
        super().__init__(pai, "Editar aplicação" if valores else "Nova aplicação")
        self.headers = headers
        self.col = {k: nc.achar_coluna(headers, k) for k in
                    ("investidor", "valor", "data", "prazo", "porcent", "lucro gerado", "status")}
        valores = valores or {}
        v = lambda chave: valores.get(headers[self.col[chave]], "") if self.col[chave] >= 0 else ""
        c = self.corpo
        c.columnconfigure(1, weight=1)
        lin = 0

        def rotulo(texto):
            ttk.Label(c, text=texto, font=(FONTE, 10)).grid(row=lin, column=0, sticky="w", pady=6, padx=(0, 14))

        rotulo("Investidor")
        self.inv = ttk.Combobox(c, values=investidores, state="readonly", width=30)
        self.inv.set(v("investidor") or (investidores[0] if len(investidores) == 1 else ""))
        self.inv.grid(row=lin, column=1, sticky="ew"); lin += 1

        rotulo("Valor aplicado (R$)")
        self.valor = ttk.Entry(c)
        self.valor.insert(0, nc.num_br(v("valor")))
        self.valor.grid(row=lin, column=1, sticky="ew"); lin += 1

        rotulo("Data da aplicação")
        data_ini = None
        try:
            data_ini = datetime.datetime.strptime(str(v("data")), "%d/%m/%Y")
        except ValueError:
            pass
        self.data = DateEntry(c, dateformat="%d/%m/%Y", firstweekday=6,
                              startdate=data_ini or datetime.datetime.today(),
                              popup_title="Escolha a data")
        self.data.grid(row=lin, column=1, sticky="ew"); lin += 1

        rotulo("Prazo (meses)")
        self.prazo = ttk.Spinbox(c, from_=1, to=600, increment=1)
        self.prazo.set(nc.num_br(v("prazo")) or "6")
        self.prazo.grid(row=lin, column=1, sticky="ew"); lin += 1

        rotulo("Lucro (%)")
        self.pct = ttk.Entry(c)
        self.pct.insert(0, nc.num_br(v("porcent")))
        self.pct.grid(row=lin, column=1, sticky="ew"); lin += 1

        rotulo("Lucro gerado (R$)")
        lf = ttk.Frame(c)
        lf.grid(row=lin, column=1, sticky="ew"); lin += 1
        self.lucro = ttk.Entry(lf, width=16)
        self.lucro.insert(0, nc.num_br(v("lucro gerado")))
        self.lucro.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.auto = tk.BooleanVar(value=not valores or self._lucro_bate(valores))
        ttk.Checkbutton(lf, text="calcular (valor × %)", variable=self.auto,
                        bootstyle="round-toggle", command=self._recalcular).pack(side=tk.LEFT, padx=(10, 0))

        rotulo("Status")
        self.status = ttk.Combobox(c, values=status, width=30)
        self.status.set(v("status") or "Ativo")
        self.status.grid(row=lin, column=1, sticky="ew"); lin += 1

        # Colunas extras que alguem tenha criado na planilha: campo de texto simples.
        conhecidas = {i for i in self.col.values() if i >= 0}
        self.extras = {}
        for i, h in enumerate(headers):
            if i in conhecidas or not str(h).strip():
                continue
            rotulo(h)
            e = ttk.Entry(c)
            e.insert(0, str(valores.get(h, "")))
            e.grid(row=lin, column=1, sticky="ew"); lin += 1
            self.extras[h] = e

        for e in (self.valor, self.pct):
            e.bind("<KeyRelease>", lambda ev: self._recalcular())
        self._recalcular()
        self.botoes()
        (self.valor if self.inv.get() else self.inv).focus_set()

    def _lucro_bate(self, valores):
        h = self.headers
        if min(self.col["valor"], self.col["porcent"], self.col["lucro gerado"]) < 0:
            return False
        val = nc.para_numero(valores.get(h[self.col["valor"]]))
        pct = nc.para_numero(valores.get(h[self.col["porcent"]]))
        luc = nc.para_numero(valores.get(h[self.col["lucro gerado"]]))
        return None not in (val, pct, luc) and abs(val * pct / 100 - luc) < 0.01

    def _recalcular(self):
        self.lucro.configure(state="normal")
        if self.auto.get():
            val, pct = nc.para_numero(self.valor.get()), nc.para_numero(self.pct.get())
            self.lucro.delete(0, tk.END)
            if val is not None and pct is not None:
                self.lucro.insert(0, nc.num_br(round(val * pct / 100, 2)))
            self.lucro.configure(state="readonly")

    def ok(self):
        inv = self.inv.get().strip()
        val = nc.para_numero(self.valor.get())
        pct = nc.para_numero(self.pct.get())
        prazo = nc.para_numero(self.prazo.get())
        luc = nc.para_numero(self.lucro.get())
        data = self.data.entry.get().strip()
        if not inv:
            return self.erro("Escolha o investidor.")
        if val is None or val <= 0:
            return self.erro("Informe o valor aplicado (ex.: 5000 ou 5.000,00).")
        try:
            datetime.datetime.strptime(data, "%d/%m/%Y")
        except ValueError:
            return self.erro("Data inválida. Use dd/mm/aaaa.")
        if prazo is None or prazo <= 0:
            return self.erro("Informe o prazo em meses.")
        if pct is None:
            return self.erro("Informe a porcentagem de lucro (ex.: 10).")
        if self.lucro.get().strip() and luc is None:
            return self.erro("Lucro gerado inválido.")

        campos = {"investidor": inv, "valor": val, "data": data, "prazo": int(prazo),
                  "porcent": pct, "lucro gerado": luc if luc is not None else "",
                  "status": self.status.get().strip() or "Ativo"}
        res = {h: e.get().strip() for h, e in self.extras.items()}
        for chave, valor in campos.items():
            if self.col[chave] >= 0:
                res[self.headers[self.col[chave]]] = valor
        self.resultado = res
        self.destroy()


# ─────────────────────────── dialogo: investidor / senha ────────────────────
class DialogoInvestidor(Dialogo):
    def __init__(self, pai, existentes, login=None):
        super().__init__(pai, f"Nova senha para {login}" if login else "Novo investidor")
        self.existentes = {e.lower() for e in existentes}
        self.login_fixo = login
        c = self.corpo
        c.columnconfigure(1, weight=1)

        ttk.Label(c, text="Login", font=(FONTE, 10)).grid(row=0, column=0, sticky="w", pady=6, padx=(0, 14))
        self.login = ttk.Entry(c, width=28)
        self.login.grid(row=0, column=1, sticky="ew")
        if login:
            self.login.insert(0, login)
            self.login.configure(state="readonly")
        ttk.Label(c, text="Sem espaços. O investidor usa este nome para entrar.",
                  font=(FONTE, 8), bootstyle="secondary").grid(row=1, column=1, sticky="w")

        ttk.Label(c, text="Senha", font=(FONTE, 10)).grid(row=2, column=0, sticky="w", pady=(12, 6), padx=(0, 14))
        sf = ttk.Frame(c)
        sf.grid(row=2, column=1, sticky="ew", pady=(12, 6))
        self.senha = ttk.Entry(sf, width=18)
        self.senha.insert(0, nc.gerar_senha())
        self.senha.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(sf, text="↻ Gerar outra", bootstyle="link",
                   command=self._nova_senha).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(c, text="A senha não fica guardada: copie a mensagem de acesso ao salvar.",
                  font=(FONTE, 8), bootstyle="secondary").grid(row=3, column=1, sticky="w")

        self.botoes("Criar" if not login else "Trocar senha")
        (self.senha if login else self.login).focus_set()

    def _nova_senha(self):
        self.senha.delete(0, tk.END)
        self.senha.insert(0, nc.gerar_senha())

    def ok(self):
        login = self.login.get().strip().lower()
        senha = self.senha.get().strip()
        if not self.login_fixo:
            if not login or " " in login:
                return self.erro("Informe um login sem espaços.")
            if login in self.existentes:
                return self.erro(f"Já existe um investidor com o login \"{login}\".")
        if len(senha) < 6:
            return self.erro("A senha precisa ter pelo menos 6 caracteres.")
        self.resultado = (login, senha)
        self.destroy()


class DialogoMensagem(Dialogo):
    """Mostra a mensagem de acesso pronta para copiar (WhatsApp/e-mail)."""

    def __init__(self, pai, titulo, texto):
        super().__init__(pai, titulo)
        ttk.Label(self.corpo, text="Envie esta mensagem ao investidor:",
                  font=(FONTE, 10, "bold")).pack(anchor="w", pady=(0, 8))
        txt = tk.Text(self.corpo, width=52, height=9, font=(FONTE, 10), wrap="word", relief="flat")
        txt.insert("1.0", texto)
        txt.configure(state="disabled")
        txt.pack(fill=tk.BOTH)
        rod = ttk.Frame(self, padding=(20, 0, 20, 16))
        rod.pack(fill=tk.X)
        self.btn = ttk.Button(rod, text="📋  Copiar mensagem", bootstyle="primary",
                              command=lambda: self._copiar(texto))
        self.btn.pack(side=tk.RIGHT)
        ttk.Button(rod, text="Fechar", bootstyle="secondary-outline",
                   command=self.destroy).pack(side=tk.RIGHT, padx=8)

    def _copiar(self, texto):
        copiar(self, texto)
        self.btn.configure(text="✓  Copiado!", bootstyle="success")

    def ok(self):
        self.destroy()


# ─────────────────────────── janela principal ──────────────────────────────
class App(ttk.Window):
    def __init__(self):
        super().__init__(title="Gerenciador - Área do Investidor", themename="flatly",
                         size=(1100, 720), minsize=(900, 560))
        if self.winfo_screenwidth() < 1200 or self.winfo_screenheight() < 800:
            self.state("zoomed")   # tela pequena: abre maximizado
        icone = os.path.join(nc.APP_DIR, "icone.ico")
        if os.path.exists(icone):
            try:
                self.iconbitmap(icone)
            except tk.TclError:
                pass
        self.style.configure("primary.Treeview", rowheight=32, font=(FONTE, 10))
        self.style.configure("primary.Treeview.Heading", font=(FONTE, 10, "bold"), padding=(6, 6))

        self.estado = nc.carregar_estado()
        self.creds = None
        self.email = ""
        self.ocupado = False
        self.publicar_apos_carregar = False
        self._limpar_dados()

        self.conteudo = ttk.Frame(self)
        self.conteudo.pack(fill=tk.BOTH, expand=True)
        self.protocol("WM_DELETE_WINDOW", self._fechar)

        if self.estado.get("sheet_id") and nc.tem_token():
            self._mostrar_principal()
        else:
            self._mostrar_assistente()

    # ─── infraestrutura ─────────────────────────────────────────────────────
    def _limpar_dados(self):
        self.h_aplic, self.aplicacoes = list(nc.HDR_APLIC), []   # aplicacoes: lista de dicts
        self.h_users, self.usuarios = list(nc.HDR_USERS), []     # usuarios: lista de listas
        self.original = {}        # o que foi lido da planilha (para detectar mudanca externa)
        self.sujo = set()         # abas com alteracoes nao salvas
        self.senhas_novas = {}    # login -> senha criada nesta sessao (para a mensagem)
        self.carregado = False

    def _em_segundo_plano(self, msg, tarefa, ao_terminar=None):
        """Roda `tarefa` numa thread (chamadas ao Google) sem travar a janela."""
        if self.ocupado:
            return
        self.ocupado = True
        self._status(msg, ocupado=True)
        self.configure(cursor="watch")

        def run():
            try:
                res, erro = tarefa(), None
            except Exception as e:  # noqa: BLE001 - mostramos qualquer erro ao usuario
                res, erro = None, e
            self.after(0, lambda: fim(res, erro))

        def fim(res, erro):
            self.ocupado = False
            self.configure(cursor="")
            self._status("")
            if erro is not None:
                messagebox.showerror("Algo deu errado", nc.explicar_erro(erro), parent=self)
            elif ao_terminar:
                ao_terminar(res)

        threading.Thread(target=run, daemon=True).start()

    def _status(self, msg, ocupado=False):
        if hasattr(self, "lbl_status") and self.lbl_status.winfo_exists():
            self.lbl_status.configure(text=msg)
            if ocupado:
                self.barra.pack(side=tk.LEFT, padx=(0, 8))
                self.barra.start(12)
            else:
                self.barra.stop()
                self.barra.pack_forget()

    def _garantir_creds(self):
        if not self.creds:
            self.creds = nc.autenticar(interativo=True)
        return self.creds

    def _limpar_conteudo(self):
        for w in self.conteudo.winfo_children():
            w.destroy()

    def _fechar(self):
        if self.sujo and not messagebox.askyesno(
                "Alterações não salvas",
                "Há alterações que ainda não foram enviadas para a planilha.\n\nSair mesmo assim?",
                icon="warning", parent=self):
            return
        self.destroy()

    # ════════════════════════ ASSISTENTE (primeiro uso) ═════════════════════
    def _mostrar_credencial(self):
        """Passo 0: cada pessoa cria a propria credencial gratuita no Google Cloud."""
        self._limpar_conteudo()
        c = ttk.Frame(self.conteudo, padding=30)
        c.place(relx=0.5, rely=0.47, anchor="center")

        ttk.Label(c, text="Bem-vindo ao Gerenciador", font=(FONTE, 22, "bold"),
                  bootstyle="primary").pack(anchor="w")
        ttk.Label(c, text="Primeiro, crie sua credencial gratuita do Google (uns 10 minutos, só uma vez).\n"
                          "Clique em cada botão na ordem: ele abre a página certa no navegador.",
                  font=(FONTE, 11), bootstyle="secondary", justify="left").pack(anchor="w", pady=(4, 16))

        passos = ttk.Frame(c)
        passos.pack(fill=tk.X)
        passos.columnconfigure(1, weight=1)
        etapas = [
            ("projeto", "1. Criar um projeto", "Dê qualquer nome (ex.: Area do Investidor) e clique em Criar."),
            ("apis", "2. Ativar as APIs", "Confirme o projeto criado e clique em Ativar."),
            ("consentimento", "3. Configurar o acesso", "Clique em Começar: nome do app, seu e-mail, "
                                                        "público Externo, e conclua."),
            ("publico", "4. Publicar o app", "Em Público-alvo clique em \"Publicar app\" (evita ter que "
                                             "entrar de novo a cada 7 dias)."),
            ("credencial", "5. Criar a credencial", "Tipo \"App para computador\" → Criar → "
                                                    "\"Fazer download do JSON\"."),
        ]
        for i, (chave, titulo, dica) in enumerate(etapas):
            ttk.Button(passos, text=titulo, bootstyle="primary-outline", width=24,
                       command=lambda k=chave: webbrowser.open(nc.LINKS_GOOGLE[k])).grid(
                row=i, column=0, sticky="w", pady=4)
            ttk.Label(passos, text=dica, font=(FONTE, 10), wraplength=480, justify="left").grid(
                row=i, column=1, sticky="w", padx=(14, 0))

        fim = ttk.Labelframe(c, text="  6. Pronto? Carregue o arquivo baixado  ", padding=14)
        fim.pack(fill=tk.X, pady=(18, 0))
        lf = ttk.Frame(fim)
        lf.pack(fill=tk.X)
        ttk.Button(lf, text="Procurar em Downloads", bootstyle="success",
                   command=self._credencial_downloads).pack(side=tk.LEFT)
        ttk.Button(lf, text="Escolher arquivo…", bootstyle="secondary-outline",
                   command=self._credencial_escolher).pack(side=tk.LEFT, padx=8)
        ttk.Button(lf, text="📖 Guia com imagens", bootstyle="link",
                   command=lambda: webbrowser.open(nc.GUIA_URL)).pack(side=tk.RIGHT)

    def _credencial_usar(self, caminho):
        try:
            nc.importar_client_secret(caminho)
        except ValueError as e:
            return messagebox.showerror("Credencial", str(e), parent=self)
        self._mostrar_assistente()

    def _credencial_downloads(self):
        achado = nc.procurar_client_secret_downloads()
        if not achado:
            messagebox.showinfo("Não encontrei", "Nenhum arquivo client_secret*.json na pasta Downloads.\n"
                                                 "Use \"Escolher arquivo…\".", parent=self)
            return self._credencial_escolher()
        self._credencial_usar(achado)

    def _credencial_escolher(self):
        arq = filedialog.askopenfilename(parent=self, title="Escolha o arquivo baixado do Google",
                                         filetypes=[("Credencial do Google", "*.json")])
        if arq:
            self._credencial_usar(arq)

    def _mostrar_assistente(self):
        if not nc.arquivo_client_secret():
            return self._mostrar_credencial()
        self._limpar_conteudo()
        c = ttk.Frame(self.conteudo, padding=40)
        c.place(relx=0.5, rely=0.45, anchor="center")

        ttk.Label(c, text="Bem-vindo ao Gerenciador", font=(FONTE, 22, "bold"),
                  bootstyle="primary").pack(anchor="w")
        ttk.Label(c, text="Vamos deixar tudo pronto em dois passos.",
                  font=(FONTE, 11), bootstyle="secondary").pack(anchor="w", pady=(2, 24))

        # Passo 1
        p1 = ttk.Labelframe(c, text="  1. Conectar sua conta Google  ", padding=16)
        p1.pack(fill=tk.X)
        ttk.Label(p1, text="O navegador vai abrir para você autorizar. Os dados ficam na sua conta.",
                  font=(FONTE, 10), wraplength=560).pack(anchor="w")
        l1 = ttk.Frame(p1)
        l1.pack(fill=tk.X, pady=(10, 0))
        self.btn_conectar = ttk.Button(l1, text="Conectar conta Google", bootstyle="primary",
                                       command=self._assist_conectar)
        self.btn_conectar.pack(side=tk.LEFT)
        self.lbl_conta = ttk.Label(l1, text="", font=(FONTE, 10, "bold"), bootstyle="success")
        self.lbl_conta.pack(side=tk.LEFT, padx=12)

        # Passo 2
        self.p2 = ttk.Labelframe(c, text="  2. Planilha  ", padding=16)
        self.p2.pack(fill=tk.X, pady=(16, 0))
        nb = ttk.Notebook(self.p2)
        nb.pack(fill=tk.X)

        nova = ttk.Frame(nb, padding=14)
        nb.add(nova, text=" Criar planilha nova ")
        ttk.Label(nova, text="Crie a senha do usuário \"admin\" (ele vê as aplicações de todos "
                             "na página do investidor).", font=(FONTE, 10), wraplength=540).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(nova, text="Senha do admin").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.senha_admin = ttk.Entry(nova, show="•", width=24)
        self.senha_admin.grid(row=1, column=1, sticky="w")
        ttk.Label(nova, text="Repita a senha").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=6)
        self.senha_admin2 = ttk.Entry(nova, show="•", width=24)
        self.senha_admin2.grid(row=2, column=1, sticky="w", pady=6)
        ttk.Label(nova, text="Antes, ative a \"API do Google Apps Script\" na sua conta:").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(nova, text="Abrir configuração do Apps Script", bootstyle="link",
                   command=lambda: webbrowser.open(nc.LINKS_GOOGLE["apps_script"])).grid(
            row=3, column=2, sticky="w", pady=(8, 0))
        self.btn_criar = ttk.Button(nova, text="Criar planilha e página", bootstyle="success",
                                    command=self._assist_criar)
        self.btn_criar.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))

        exist = ttk.Frame(nb, padding=14)
        nb.add(exist, text=" Usar planilha que já tenho ")
        ttk.Label(exist, text="Cole o link da planilha (ela precisa ter as abas Aplicacoes e Usuarios).",
                  font=(FONTE, 10), wraplength=540).pack(anchor="w", pady=(0, 10))
        self.link_planilha = ttk.Entry(exist, width=64)
        self.link_planilha.pack(anchor="w", fill=tk.X)
        le = ttk.Frame(exist)
        le.pack(fill=tk.X, pady=(10, 0))
        self.btn_usar = ttk.Button(le, text="Conectar planilha", bootstyle="success",
                                   command=self._assist_usar)
        self.btn_usar.pack(side=tk.LEFT)
        ttk.Button(le, text="Importar configuração (estado.json)…", bootstyle="link",
                   command=self._assist_importar).pack(side=tk.LEFT, padx=10)

        rod = ttk.Frame(c)
        rod.pack(fill=tk.X, pady=(18, 0))
        self.barra = ttk.Progressbar(rod, mode="indeterminate", length=120)
        self.lbl_status = ttk.Label(rod, text="", bootstyle="secondary")
        self.lbl_status.pack(side=tk.LEFT)

        self._assist_habilitar(False)

    def _assist_habilitar(self, conectado):
        estado = "normal" if conectado else "disabled"
        for w in (self.btn_criar, self.btn_usar, self.senha_admin, self.senha_admin2, self.link_planilha):
            w.configure(state=estado)

    def _assist_conectar(self):
        def tarefa():
            self.creds = nc.autenticar(interativo=True)
            return nc.email_da_conta(self.creds)

        def ok(email):
            self.email = email
            self.lbl_conta.configure(text=f"✓ Conectado {('como ' + email) if email else ''}")
            self.btn_conectar.configure(text="Trocar conta", bootstyle="secondary-outline",
                                        command=self._assist_trocar_conta)
            self._assist_habilitar(True)

        self._em_segundo_plano("Aguardando autorização no navegador…", tarefa, ok)

    def _assist_trocar_conta(self):
        self.creds = None
        nc.desconectar()
        self._assist_conectar()

    def _assist_criar(self):
        s1, s2 = self.senha_admin.get(), self.senha_admin2.get()
        if len(s1) < 6:
            return messagebox.showwarning("Senha", "A senha do admin precisa ter pelo menos 6 caracteres.", parent=self)
        if s1 != s2:
            return messagebox.showwarning("Senha", "As senhas não conferem.", parent=self)

        def tarefa():
            sheet_id, url = nc.criar_planilha(self.creds, s1)
            self.estado = {"sheet_id": sheet_id, "sheet_url": url}
            nc.salvar_estado(self.estado)
            nc.publicar_web_app(self.creds, self.estado, "Primeira publicacao")

        def ok(_):
            messagebox.showinfo(
                "Tudo pronto!",
                "Planilha e página do investidor criadas.\n\n"
                f"Link para os investidores:\n{self.estado.get('webapp_url')}\n\n"
                "Agora cadastre seus investidores e as aplicações.", parent=self)
            self._mostrar_principal()

        self._em_segundo_plano("Criando planilha e publicando a página (leva ~30 s)…", tarefa, ok)

    def _assist_usar(self):
        sheet_id = nc.extrair_sheet_id(self.link_planilha.get())
        if not sheet_id:
            return messagebox.showwarning("Link", "Cole o link completo da planilha do Google.", parent=self)

        def tarefa():
            _, url = nc.verificar_planilha(self.creds, sheet_id)
            self.estado = {"sheet_id": sheet_id, "sheet_url": url}
            nc.salvar_estado(self.estado)

        def ok(_):
            # Publica depois que o carregamento da tela principal terminar.
            self.publicar_apos_carregar = messagebox.askyesno(
                "Página do investidor",
                "Planilha conectada.\n\nPublicar agora a página do investidor para esta planilha?\n"
                "(Isso cria um link novo de acesso.)", parent=self)
            self._mostrar_principal()

        self._em_segundo_plano("Verificando a planilha…", tarefa, ok)

    def _assist_importar(self):
        arq = filedialog.askopenfilename(parent=self, title="Escolha o estado.json",
                                         filetypes=[("Configuração", "*.json")])
        if not arq:
            return
        try:
            with open(arq, encoding="utf-8") as f:
                estado = json.load(f)
            if not estado.get("sheet_id"):
                raise ValueError("arquivo sem sheet_id")
        except Exception as e:
            return messagebox.showerror("Arquivo inválido", f"Não consegui ler a configuração:\n{e}", parent=self)

        def tarefa():
            nc.verificar_planilha(self.creds, estado["sheet_id"])
            self.estado = estado
            nc.salvar_estado(estado)

        self._em_segundo_plano("Verificando a planilha…", tarefa, lambda _: self._mostrar_principal())

    # ════════════════════════ TELA PRINCIPAL ════════════════════════════════
    def _mostrar_principal(self):
        self._limpar_conteudo()
        self._limpar_dados()

        # Cabecalho
        topo = ttk.Frame(self.conteudo, bootstyle="primary", padding=(18, 12))
        topo.pack(fill=tk.X)
        ttk.Label(topo, text="Área do Investidor", font=(FONTE, 16, "bold"),
                  bootstyle="inverse-primary").pack(side=tk.LEFT)
        self.lbl_conta_topo = ttk.Label(topo, text="", font=(FONTE, 9), bootstyle="inverse-primary")
        self.lbl_conta_topo.pack(side=tk.LEFT, padx=14)
        ttk.Button(topo, text="🔗 Copiar link dos investidores", bootstyle="light",
                   command=self._copiar_link).pack(side=tk.RIGHT)
        ttk.Button(topo, text="📄 Abrir planilha", bootstyle="light",
                   command=lambda: webbrowser.open(self.estado.get("sheet_url", ""))).pack(side=tk.RIGHT, padx=8)

        # Rodape: status + salvar (sempre visivel)
        rod = ttk.Frame(self.conteudo, padding=(18, 10))
        rod.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Separator(self.conteudo).pack(fill=tk.X, side=tk.BOTTOM)
        self.barra = ttk.Progressbar(rod, mode="indeterminate", length=120)
        self.lbl_status = ttk.Label(rod, text="", bootstyle="secondary")
        self.lbl_status.pack(side=tk.LEFT)
        self.btn_salvar = ttk.Button(rod, text="💾  Salvar na planilha", bootstyle="success",
                                     command=self._salvar, state="disabled")
        self.btn_salvar.pack(side=tk.RIGHT)
        self.btn_descartar = ttk.Button(rod, text="Descartar alterações", bootstyle="secondary-outline",
                                        command=self._descartar, state="disabled")
        self.btn_descartar.pack(side=tk.RIGHT, padx=8)
        self.lbl_sujo = ttk.Label(rod, text="", bootstyle="warning", font=(FONTE, 10, "bold"))
        self.lbl_sujo.pack(side=tk.RIGHT, padx=8)

        self.nb = ttk.Notebook(self.conteudo, bootstyle="primary")
        self.nb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(12, 6))
        self._aba_aplicacoes()
        self._aba_investidores()
        self._aba_config()

        self.bind_all("<Control-s>", lambda e: self._salvar())
        self._carregar()

    # ─── aba Aplicacoes ─────────────────────────────────────────────────────
    def _aba_aplicacoes(self):
        frm = ttk.Frame(self.nb, padding=12)
        self.nb.add(frm, text="  Aplicações  ")

        cards = ttk.Frame(frm)
        cards.pack(fill=tk.X, pady=(0, 12))
        self.cards = {}
        for i, (chave, titulo, estilo) in enumerate([
                ("total", "Total aplicado", "primary"), ("lucro", "Lucro previsto", "success"),
                ("ativas", "Aplicações ativas", "info"), ("invest", "Investidores", "secondary")]):
            moldura = ttk.Frame(cards, bootstyle=estilo, padding=(4, 0, 0, 0))   # faixa colorida a esquerda
            moldura.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=1)
            card = ttk.Frame(moldura, padding=(14, 8))
            card.pack(fill=tk.BOTH, expand=True)
            ttk.Label(card, text=titulo, font=(FONTE, 9), bootstyle="secondary").pack(anchor="w")
            lbl = ttk.Label(card, text="—", font=(FONTE, 17, "bold"), bootstyle=estilo)
            lbl.pack(anchor="w")
            self.cards[chave] = lbl

        barra = ttk.Frame(frm)
        barra.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(barra, text="+  Nova aplicação", bootstyle="primary",
                   command=self._nova_aplicacao).pack(side=tk.LEFT)
        self.btn_editar = ttk.Button(barra, text="✎  Editar", bootstyle="secondary-outline",
                                     command=self._editar_aplicacao, state="disabled")
        self.btn_editar.pack(side=tk.LEFT, padx=6)
        self.btn_excluir = ttk.Button(barra, text="🗑  Excluir", bootstyle="danger-outline",
                                      command=self._excluir_aplicacao, state="disabled")
        self.btn_excluir.pack(side=tk.LEFT)

        ttk.Label(barra, text="🔍").pack(side=tk.LEFT, padx=(24, 4))
        self.f_busca = ttk.Entry(barra, width=22)
        self.f_busca.pack(side=tk.LEFT)
        self.f_inv = ttk.Combobox(barra, state="readonly", width=16)
        self.f_status = ttk.Combobox(barra, state="readonly", width=12)
        ttk.Label(barra, text="Investidor").pack(side=tk.LEFT, padx=(14, 4))
        self.f_inv.pack(side=tk.LEFT)
        ttk.Label(barra, text="Status").pack(side=tk.LEFT, padx=(14, 4))
        self.f_status.pack(side=tk.LEFT)

        self.f_busca.bind("<KeyRelease>", lambda e: self._atualizar_aplicacoes())
        self.f_inv.bind("<<ComboboxSelected>>", lambda e: self._atualizar_aplicacoes())
        self.f_status.bind("<<ComboboxSelected>>", lambda e: self._atualizar_aplicacoes())

        ttk.Label(frm, text="Dica: dê dois cliques numa linha para editar. Clique no título da coluna para ordenar.",
                  font=(FONTE, 8), bootstyle="secondary").pack(side=tk.BOTTOM, anchor="w", pady=(6, 0))
        self.tv_aplic = self._tabela(frm)
        self.tv_aplic.bind("<Double-1>", lambda e: self._editar_aplicacao())
        self.tv_aplic.bind("<Delete>", lambda e: self._excluir_aplicacao())
        self.tv_aplic.bind("<<TreeviewSelect>>", lambda e: self._sel_aplic())

    def _tabela(self, pai):
        box = ttk.Frame(pai)
        box.pack(fill=tk.BOTH, expand=True)
        tv = ttk.Treeview(box, show="headings", selectmode="browse", bootstyle="primary")
        sb = ttk.Scrollbar(box, orient=tk.VERTICAL, command=tv.yview, bootstyle="round")
        tv.configure(yscrollcommand=sb.set)
        tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        tv.tag_configure("par", background="#f5f8fb")
        tv.tag_configure("pago", foreground="#6c757d")
        tv.tag_configure("admin", foreground="#2c3e50", font=(FONTE, 10, "italic"))
        return tv

    def _configurar_colunas(self, tv, colunas, largura_num=("Valor", "Lucro", "Prazo", "Porcent", "Total", "Aplica")):
        tv.configure(columns=colunas)
        for c in colunas:
            num = any(k.lower() in c.lower() for k in largura_num) and "Data" not in c
            tv.heading(c, text=c, anchor="e" if num else "w",
                       command=lambda c=c: self._ordenar(tv, c))
            tv.column(c, anchor="e" if num else "w", width=max(90, len(c) * 9 + 20), minwidth=70, stretch=True)

    def _ordenar(self, tv, coluna):
        atual = getattr(tv, "_ordem", (None, False))
        desc = atual[0] == coluna and not atual[1]
        tv._ordem = (coluna, desc)
        if tv is self.tv_aplic:
            self._atualizar_aplicacoes()
        else:
            self._atualizar_investidores()

    @staticmethod
    def _chave_ordem(v):
        n = nc.para_numero(v)
        if n is not None:
            return (0, n, "")
        try:
            return (0, datetime.datetime.strptime(str(v), "%d/%m/%Y").timestamp(), "")
        except ValueError:
            return (1, 0, str(v).lower())

    def _col(self, chave):
        i = nc.achar_coluna(self.h_aplic, chave)
        return self.h_aplic[i] if i >= 0 else None

    def _atualizar_aplicacoes(self):
        tv = self.tv_aplic
        sel = tv.selection()
        tv.delete(*tv.get_children())
        h_inv, h_status = self._col("investidor"), self._col("status")
        h_valor, h_lucro = self._col("valor"), self._col("lucro gerado")
        moeda = {h for h in (h_valor, h_lucro) if h}

        investidores = sorted({str(a.get(h_inv, "")) for a in self.aplicacoes if h_inv} - {""})
        status = sorted({str(a.get(h_status, "")) for a in self.aplicacoes if h_status} - {""})
        self.f_inv.configure(values=["Todos"] + investidores)
        self.f_status.configure(values=["Todos"] + status)
        if self.f_inv.get() not in self.f_inv.cget("values"):
            self.f_inv.set("Todos")
        if self.f_status.get() not in self.f_status.cget("values"):
            self.f_status.set("Todos")

        busca = self.f_busca.get().strip().lower()
        linhas = []
        for idx, a in enumerate(self.aplicacoes):
            if self.f_inv.get() != "Todos" and str(a.get(h_inv, "")) != self.f_inv.get():
                continue
            if self.f_status.get() != "Todos" and str(a.get(h_status, "")) != self.f_status.get():
                continue
            if busca and busca not in " ".join(str(v) for v in a.values()).lower():
                continue
            linhas.append((idx, a))

        col, desc = getattr(tv, "_ordem", (None, False))
        if col:
            linhas.sort(key=lambda p: self._chave_ordem(p[1].get(col, "")), reverse=desc)

        total = lucro = 0.0
        ativas = 0
        invs = set()
        for n, (idx, a) in enumerate(linhas):
            vals = [nc.brl(a.get(h, "")) if h in moeda else nc.num_br(a.get(h, "")) for h in self.h_aplic]
            tags = ["par"] if n % 2 else []
            st = str(a.get(h_status, "")).lower() if h_status else ""
            if st and st != "ativo":
                tags.append("pago")
            tv.insert("", tk.END, iid=str(idx), values=vals, tags=tags)
            total += (nc.para_numero(a.get(h_valor)) or 0) if h_valor else 0
            lucro += (nc.para_numero(a.get(h_lucro)) or 0) if h_lucro else 0
            ativas += st == "ativo"
            invs.add(str(a.get(h_inv, "")))

        filtrado = len(linhas) != len(self.aplicacoes)
        self.cards["total"].configure(text=nc.brl(total))
        self.cards["lucro"].configure(text=nc.brl(lucro))
        self.cards["ativas"].configure(text=f"{ativas} de {len(linhas)}")
        self.cards["invest"].configure(text=str(len(invs - {""})) + (" (filtro)" if filtrado else ""))
        for s in sel:
            if tv.exists(s):
                tv.selection_set(s)
        self._sel_aplic()

    def _sel_aplic(self):
        estado = "normal" if self.tv_aplic.selection() else "disabled"
        self.btn_editar.configure(state=estado)
        self.btn_excluir.configure(state=estado)

    def _logins_investidores(self):
        return sorted(u[0] for u in self.usuarios if u and u[0] and u[0].lower() != nc.USUARIO_ADMIN)

    def _status_existentes(self):
        h = self._col("status")
        return sorted(set(STATUS_PADRAO) | {str(a.get(h, "")) for a in self.aplicacoes if h} - {""})

    def _nova_aplicacao(self):
        if not self._pronto():
            return
        invs = self._logins_investidores()
        if not invs:
            messagebox.showinfo("Cadastre um investidor",
                                "Antes de lançar uma aplicação, cadastre o investidor na aba \"Investidores\".",
                                parent=self)
            self.nb.select(1)
            return
        dlg = DialogoAplicacao(self, self.h_aplic, invs, self._status_existentes())
        if self.f_inv.get() not in ("", "Todos"):
            dlg.inv.set(self.f_inv.get())
        res = dlg.mostrar()
        if res:
            self.aplicacoes.append(res)
            self._marcar_sujo(nc.ABA_APLIC)
            self._atualizar_aplicacoes()
            self.tv_aplic.selection_set(str(len(self.aplicacoes) - 1))
            self.tv_aplic.see(str(len(self.aplicacoes) - 1))

    def _editar_aplicacao(self):
        sel = self.tv_aplic.selection()
        if not sel:
            return
        idx = int(sel[0])
        invs = self._logins_investidores()
        atual = str(self.aplicacoes[idx].get(self._col("investidor"), ""))
        if atual and atual not in invs:
            invs.append(atual)   # investidor sem login: mantem para nao perder o dado
        res = DialogoAplicacao(self, self.h_aplic, invs, self._status_existentes(),
                               self.aplicacoes[idx]).mostrar()
        if res and res != self.aplicacoes[idx]:
            self.aplicacoes[idx] = res
            self._marcar_sujo(nc.ABA_APLIC)
            self._atualizar_aplicacoes()

    def _excluir_aplicacao(self):
        sel = self.tv_aplic.selection()
        if not sel:
            return
        idx = int(sel[0])
        a = self.aplicacoes[idx]
        desc = f"{a.get(self._col('investidor'), '')} — {nc.brl(a.get(self._col('valor'), ''))} em {a.get(self._col('data'), '')}"
        if messagebox.askyesno("Excluir aplicação", f"Excluir esta aplicação?\n\n{desc}", parent=self):
            del self.aplicacoes[idx]
            self._marcar_sujo(nc.ABA_APLIC)
            self._atualizar_aplicacoes()

    # ─── aba Investidores ───────────────────────────────────────────────────
    def _aba_investidores(self):
        frm = ttk.Frame(self.nb, padding=12)
        self.nb.add(frm, text="  Investidores  ")

        barra = ttk.Frame(frm)
        barra.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(barra, text="+  Novo investidor", bootstyle="primary",
                   command=self._novo_investidor).pack(side=tk.LEFT)
        self.btn_msg = ttk.Button(barra, text="✉  Mensagem de acesso", bootstyle="secondary-outline",
                                  command=self._mensagem_investidor, state="disabled")
        self.btn_msg.pack(side=tk.LEFT, padx=6)
        self.btn_senha = ttk.Button(barra, text="🔑  Trocar senha", bootstyle="secondary-outline",
                                    command=self._trocar_senha, state="disabled")
        self.btn_senha.pack(side=tk.LEFT)
        self.btn_del_inv = ttk.Button(barra, text="🗑  Excluir", bootstyle="danger-outline",
                                      command=self._excluir_investidor, state="disabled")
        self.btn_del_inv.pack(side=tk.LEFT, padx=6)

        ttk.Label(frm, text="As senhas ficam guardadas de forma protegida (hash): para reenviar o acesso "
                            "a alguém, use \"Trocar senha\".",
                  font=(FONTE, 8), bootstyle="secondary").pack(side=tk.BOTTOM, anchor="w", pady=(6, 0))
        self.tv_users = self._tabela(frm)
        self._configurar_colunas(self.tv_users, ["Login", "Aplicações", "Total aplicado", "Lucro previsto"])
        self.tv_users.bind("<<TreeviewSelect>>", lambda e: self._sel_users())
        self.tv_users.bind("<Double-1>", lambda e: self._mensagem_investidor())

    def _resumo_por_investidor(self):
        h_inv, h_valor, h_lucro = self._col("investidor"), self._col("valor"), self._col("lucro gerado")
        res = {}
        for a in self.aplicacoes:
            k = str(a.get(h_inv, "")).strip().lower()
            r = res.setdefault(k, [0, 0.0, 0.0])
            r[0] += 1
            r[1] += (nc.para_numero(a.get(h_valor)) or 0) if h_valor else 0
            r[2] += (nc.para_numero(a.get(h_lucro)) or 0) if h_lucro else 0
        return res

    def _atualizar_investidores(self):
        tv = self.tv_users
        tv.delete(*tv.get_children())
        resumo = self._resumo_por_investidor()
        linhas = []
        for idx, u in enumerate(self.usuarios):
            login = u[0] if u else ""
            if not login:
                continue
            n, total, lucro = resumo.get(login.lower(), [0, 0.0, 0.0])
            if login.lower() == nc.USUARIO_ADMIN:
                linhas.append((idx, [f"{login} (vê todas)", "—", "—", "—"], True))
            else:
                linhas.append((idx, [login, n, nc.brl(total), nc.brl(lucro)], False))
        col, desc = getattr(tv, "_ordem", (None, False))
        if col:
            i = ["Login", "Aplicações", "Total aplicado", "Lucro previsto"].index(col)
            linhas.sort(key=lambda p: self._chave_ordem(p[1][i]), reverse=desc)
        for n, (idx, vals, admin) in enumerate(linhas):
            tags = (["par"] if n % 2 else []) + (["admin"] if admin else [])
            tv.insert("", tk.END, iid=str(idx), values=vals, tags=tags)
        self._sel_users()

    def _login_sel(self):
        sel = self.tv_users.selection()
        return self.usuarios[int(sel[0])][0] if sel else None

    def _sel_users(self):
        login = self._login_sel()
        estado = "normal" if login else "disabled"
        self.btn_msg.configure(state=estado)
        self.btn_senha.configure(state=estado)
        admin = login and login.lower() == nc.USUARIO_ADMIN
        self.btn_del_inv.configure(state="disabled" if (not login or admin) else "normal")

    def _novo_investidor(self):
        if not self._pronto():
            return
        res = DialogoInvestidor(self, [u[0] for u in self.usuarios if u]).mostrar()
        if not res:
            return
        login, senha = res
        self.usuarios.append([login, nc.hash_senha(senha)] + [""] * (len(self.h_users) - 2))
        self.senhas_novas[login] = senha
        self._marcar_sujo(nc.ABA_USERS)
        self._atualizar_investidores()
        DialogoMensagem(self, f"Investidor {login} criado",
                        mensagem_acesso(login, senha, self.estado.get("webapp_url"))
                        + "\n\n(Lembre-se de clicar em \"Salvar na planilha\".)").mostrar()

    def _trocar_senha(self):
        login = self._login_sel()
        if not login:
            return
        res = DialogoInvestidor(self, [], login=login).mostrar()
        if not res:
            return
        senha = res[1]
        for u in self.usuarios:
            if u and u[0] == login:
                u[1] = nc.hash_senha(senha)
        self.senhas_novas[login] = senha
        self._marcar_sujo(nc.ABA_USERS)
        DialogoMensagem(self, f"Nova senha de {login}",
                        mensagem_acesso(login, senha, self.estado.get("webapp_url"))).mostrar()

    def _mensagem_investidor(self):
        login = self._login_sel()
        if not login:
            return
        senha = self.senhas_novas.get(login)
        if not senha:
            if messagebox.askyesno(
                    "Senha não disponível",
                    f"Por segurança a senha de \"{login}\" não fica guardada.\n\n"
                    "Quer gerar uma senha nova para enviar a ele?", parent=self):
                self._trocar_senha()
            return
        DialogoMensagem(self, f"Acesso de {login}",
                        mensagem_acesso(login, senha, self.estado.get("webapp_url"))).mostrar()

    def _excluir_investidor(self):
        login = self._login_sel()
        if not login or login.lower() == nc.USUARIO_ADMIN:
            return
        n = self._resumo_por_investidor().get(login.lower(), [0])[0]
        aviso = (f"\n\nEle tem {n} aplicação(ões). Elas continuam na planilha, "
                 "mas ele não conseguirá mais entrar.") if n else ""
        if messagebox.askyesno("Excluir investidor",
                               f"Remover o acesso de \"{login}\"?{aviso}", icon="warning", parent=self):
            self.usuarios = [u for u in self.usuarios if not (u and u[0] == login)]
            self.senhas_novas.pop(login, None)
            self._marcar_sujo(nc.ABA_USERS)
            self._atualizar_investidores()

    # ─── aba Configuracoes ──────────────────────────────────────────────────
    def _aba_config(self):
        self.frm_config = ttk.Frame(self.nb, padding=20)
        self.nb.add(self.frm_config, text="  Configurações  ")
        self._montar_config()

    def _montar_config(self):
        frm = self.frm_config
        for w in frm.winfo_children():
            w.destroy()
        frm.columnconfigure(1, weight=1)

        def linha(r, rotulo, valor, *botoes):
            ttk.Label(frm, text=rotulo, font=(FONTE, 10, "bold")).grid(row=r, column=0, sticky="w", pady=8, padx=(0, 16))
            e = ttk.Entry(frm, font=(FONTE, 9))
            e.insert(0, valor or "—")
            e.configure(state="readonly")
            e.grid(row=r, column=1, sticky="ew")
            for i, (txt, cmd) in enumerate(botoes):
                ttk.Button(frm, text=txt, bootstyle="secondary-outline", command=cmd).grid(
                    row=r, column=2 + i, padx=(8, 0))

        url = self.estado.get("webapp_url")
        if self.email:
            linha(0, "Conta Google", self.email)
        linha(1, "Planilha", self.estado.get("sheet_url"),
              ("Abrir", lambda: webbrowser.open(self.estado.get("sheet_url", ""))))
        linha(2, "Página do investidor", url or "ainda não publicada",
              ("Abrir", lambda: url and webbrowser.open(url)), ("Copiar", self._copiar_link))
        linha(3, "Pasta de dados", nc.DATA_DIR, ("Abrir", lambda: os.startfile(nc.DATA_DIR)))

        box = ttk.Labelframe(frm, text="  Página do investidor  ", padding=14)
        box.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(20, 0))
        ttk.Label(box, text=("Use quando atualizar o programa ou alterar a página. "
                             "O link continua o mesmo." if url else
                             "Cria o link que os investidores usam para ver as aplicações."),
                  font=(FONTE, 10), wraplength=700).pack(anchor="w", pady=(0, 10))
        ttk.Button(box, text="⚙  Atualizar página do investidor" if url else "🚀  Publicar página do investidor",
                   bootstyle="primary", command=self._publicar).pack(anchor="w")

        box2 = ttk.Labelframe(frm, text="  Conta  ", padding=14)
        box2.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(16, 0))
        ttk.Button(box2, text="Trocar conta / planilha…", bootstyle="danger-outline",
                   command=self._trocar_conta).pack(anchor="w")

    def _copiar_link(self):
        url = self.estado.get("webapp_url")
        if not url:
            messagebox.showinfo("Link", "A página do investidor ainda não foi publicada (aba Configurações).", parent=self)
            return
        copiar(self, url)
        self._status("Link copiado para a área de transferência.")

    def _publicar(self, confirmar=True):
        if confirmar and not messagebox.askyesno("Página do investidor",
                                                 "Publicar a página do investidor com a versão deste programa?",
                                                 parent=self):
            return

        def tarefa():
            self._garantir_creds()
            return nc.publicar_web_app(self.creds, self.estado)

        def ok(versao):
            self._montar_config()
            messagebox.showinfo("Pronto", f"Página publicada (versão {versao}).\n\n"
                                          f"Link:\n{self.estado.get('webapp_url')}", parent=self)

        self._em_segundo_plano("Publicando a página do investidor…", tarefa, ok)

    def _trocar_conta(self):
        if not messagebox.askyesno(
                "Trocar conta / planilha",
                "Desconectar deste Google e desta planilha?\n\nNada é apagado da planilha. "
                "A configuração atual fica guardada em estado.bak.json.", icon="warning", parent=self):
            return
        if self.sujo and not messagebox.askyesno("Alterações não salvas",
                                                 "Há alterações não salvas que serão perdidas. Continuar?",
                                                 parent=self):
            return
        nc.desconectar()
        self.creds, self.email, self.estado = None, "", {}
        self.unbind_all("<Control-s>")
        self._mostrar_assistente()

    # ─── carregar / salvar ──────────────────────────────────────────────────
    def _pronto(self):
        if not self.carregado:
            messagebox.showinfo("Aguarde", "Os dados ainda estão sendo carregados da planilha.", parent=self)
        return self.carregado

    def _carregar(self):
        def tarefa():
            self._garantir_creds()
            dados = nc.ler_abas(self.creds, self.estado["sheet_id"])
            email = self.email or nc.email_da_conta(self.creds)
            return dados, email

        def ok(res):
            dados, self.email = res
            self._aplicar_dados(dados)
            self.lbl_conta_topo.configure(text=self.email)
            self._montar_config()
            self._status(f"Dados carregados às {datetime.datetime.now():%H:%M}.")
            if self.publicar_apos_carregar:
                self.publicar_apos_carregar = False
                self._publicar(confirmar=False)

        self._em_segundo_plano("Carregando dados da planilha…", tarefa, ok)

    def _aplicar_dados(self, dados):
        apl, usr = dados[nc.ABA_APLIC], dados[nc.ABA_USERS]
        self.original = {nc.ABA_APLIC: apl, nc.ABA_USERS: usr}
        self.h_aplic = [str(h) for h in apl[0]] if apl and any(apl[0]) else list(nc.HDR_APLIC)
        self.aplicacoes = []
        for row in apl[1:]:
            if not any(str(c).strip() for c in row):
                continue
            row = list(row) + [""] * (len(self.h_aplic) - len(row))
            self.aplicacoes.append(dict(zip(self.h_aplic, row)))
        self.h_users = [str(h) for h in usr[0]] if usr and any(usr[0]) else list(nc.HDR_USERS)
        self.usuarios = []
        for row in usr[1:]:
            row = [str(c) for c in row] + [""] * (len(self.h_users) - len(row))
            if row[0].strip():
                self.usuarios.append(row)
        self.sujo.clear()
        self.carregado = True
        self._configurar_colunas(self.tv_aplic, self.h_aplic)
        self._atualizar_aplicacoes()
        self._atualizar_investidores()
        self._atualizar_sujo()

    def _valores_aba(self, aba):
        if aba == nc.ABA_APLIC:
            # Numeros salvos como numero (planilhas antigas tinham "5000.00" como texto).
            numericas = {self._col(k) for k in ("valor", "prazo", "porcent", "lucro gerado")} - {None}

            def celula(a, h):
                v = a.get(h, "")
                n = nc.para_numero(v) if h in numericas else None
                return v if n is None else n
            return [self.h_aplic] + [[celula(a, h) for h in self.h_aplic] for a in self.aplicacoes]
        return [self.h_users] + [list(u) for u in self.usuarios]

    def _marcar_sujo(self, aba):
        self.sujo.add(aba)
        self._atualizar_sujo()

    def _atualizar_sujo(self):
        if self.sujo:
            self.lbl_sujo.configure(text="● Alterações não salvas")
            self.btn_salvar.configure(state="normal")
            self.btn_descartar.configure(state="normal")
        else:
            self.lbl_sujo.configure(text="")
            self.btn_salvar.configure(state="disabled")
            self.btn_descartar.configure(state="disabled")

    def _descartar(self):
        if messagebox.askyesno("Descartar", "Descartar as alterações e recarregar da planilha?", parent=self):
            self.senhas_novas.clear()
            self._carregar()

    def _salvar(self):
        if not self.sujo or not self.carregado or self.ocupado:
            return
        abas = sorted(self.sujo)
        valores = {aba: self._valores_aba(aba) for aba in abas}

        def tarefa():
            self._garantir_creds()
            atual = nc.ler_abas(self.creds, self.estado["sheet_id"])
            mudou = [a for a in abas if atual[a] != self.original[a]]
            return atual, mudou

        def conferido(res):
            atual, mudou = res
            if mudou and not messagebox.askyesno(
                    "A planilha mudou",
                    "Alguém alterou a planilha diretamente no Google depois que você abriu o programa "
                    f"(aba: {', '.join(mudou)}).\n\nSalvar vai SUBSTITUIR essas alterações. Continuar?",
                    icon="warning", parent=self):
                return

            def gravar():
                for aba in abas:
                    nc.gravar_aba(self.creds, self.estado["sheet_id"], aba, valores[aba])
                return nc.ler_abas(self.creds, self.estado["sheet_id"])

            def ok(dados):
                senhas = dict(self.senhas_novas)
                self._aplicar_dados(dados)
                self.senhas_novas = senhas
                self._status(f"✓ Salvo na planilha às {datetime.datetime.now():%H:%M}.")

            self._em_segundo_plano("Salvando na planilha…", gravar, ok)

        self._em_segundo_plano("Conferindo a planilha…", tarefa, conferido)


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
