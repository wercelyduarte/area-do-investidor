# Para desenvolvedores

## Arquitetura

```
 Gerenciador (Windows, Tkinter)            Google (conta do administrador)
 ┌──────────────────────────┐   Sheets API   ┌──────────────────────────────┐
 │ gerenciador.py  (tela)   │ ─────────────▶ │ Planilha                     │
 │ nucleo.py (Google/dados) │                │  aba Aplicacoes / Usuarios   │
 └──────────────────────────┘   Script API   │                              │
               └──────────────────────────▶  │ Apps Script vinculado        │
                 publica Code.gs+Index.html  │  Code.gs  (login, getDados)  │
                                             │  Index.html (página)         │
                                             └──────────────▲───────────────┘
                                                            │ Web App (link)
                                                     Investidores (navegador)
```

- **Planilha:**
  - aba `Aplicacoes`: a coluna `Investidor` é igual ao login do investidor; as outras colunas são livres;
  - aba `Usuarios`: colunas `usuario` e `senha_hash`, com a senha em SHA-256.
- **Web App** (`Code.gs` + `Index.html`):
  - roda como o dono da planilha (`USER_DEPLOYING`), com acesso `ANYONE_ANONYMOUS`;
  - o login gera um token de sessão no `CacheService` com validade de 6 h;
  - `getDados` devolve só as linhas do usuário logado; o `admin` vê todas.
- **Publicação:** `nucleo.publicar_web_app` cria o projeto Apps Script vinculado à planilha. Ele também injeta o `SHEET_ID` no `Code.gs`, cria uma versão e atualiza sempre o **mesmo deployment**, então o link não muda.

| Arquivo | Função |
|---|---|
| `gerenciador.py` | Interface (ttkbootstrap): assistente de primeiro uso, abas, diálogos |
| `nucleo.py` | Caminhos, OAuth, leitura/gravação das abas, criação da planilha, publicação, formatação BR |
| `Code.gs`, `Index.html` | Página dos investidores (vão dentro do instalador e são publicadas pelo programa) |
| `setup.py`, `build.bat` | Build com cx_Freeze → `.exe` e `.msi` |
| `.github/workflows/release.yml` | Gera o `.msi` na nuvem e publica no Releases a cada tag |
| `demo.html` | Prévia estática da página do investidor (abre no navegador) |

### Onde ficam os dados locais
| Execução | Pasta |
|---|---|
| Instalado (.msi) | `%LOCALAPPDATA%\GerenciadorInvestidor\` |
| Código-fonte | a própria pasta do projeto |
| Qualquer uma | a variável de ambiente `GERENCIADOR_DADOS` sobrepõe |

Arquivos dessa pasta: `client_secret*.json` (a credencial OAuth da pessoa), `token.json` e `estado.json` (IDs da planilha, do script e do deployment, e o link). **Todos estão no `.gitignore`. Nunca publique esses arquivos.**

### Como o salvamento evita perda de dados
1. Antes de gravar, o programa relê a planilha e compara com o que foi carregado. Se alguém editou por fora, ele pergunta antes de substituir.
2. A gravação escreve primeiro e só depois limpa as linhas que sobraram. Se cair no meio, nada é apagado.
3. Colunas extras criadas na planilha são preservadas e aparecem no formulário.

---

## Rodar do código-fonte
```
rodar.bat
```
Esse comando instala as dependências na primeira vez e abre o programa. Precisa de Python 3.10+. Para instalar manualmente: `pip install -r requirements.txt` e depois `python gerenciador.py`.

## Gerar o instalador localmente
```
build.bat msi
```
O resultado sai em `dist\GerenciadorInvestidor-<versão>-win64.msi`.

- **Sem `client_secret*.json` na pasta** (padrão): cada usuário cria a própria credencial no primeiro uso.
- **Com `client_secret*.json` na pasta:** a credencial vai junto no instalador e o assistente pula essa etapa. Use só em distribuição **privada**. Nesse caso, publique o app na tela de consentimento, porque em modo *Testing* o login expira em 7 dias.

## Publicar uma versão nova (automático)
```
git tag v2.1.0
git push origin v2.1.0
```
O GitHub Actions gera o `.msi` com a versão da tag e publica em **Releases**. O link "baixar a última versão" (`/releases/latest`) passa a apontar para ele sozinho. O `upgrade_code` fixo no `setup.py` faz o novo `.msi` substituir o anterior.

Depois de atualizar `Code.gs` ou `Index.html`, cada usuário clica em **Configurações → Atualizar página do investidor**.

## Histórico de problemas resolvidos
| Problema | Causa | Solução |
|---|---|---|
| `Syntax error` no upload do script | runtime Rhino | `"runtimeVersion": "V8"` no manifest |
| `getActiveSpreadsheet()` null no Web App | contexto de Web App | `openById(SHEET_ID)` |
| `getDados` retornava null / datas deslocadas | serialização de `Date` | `getDisplayValues()` |
| Clique em "Entrar" não fazia nada | `onclick` inline bloqueado (CSP) | `addEventListener` |
| Valores salvos como texto (`"5000.00"`) | upload de strings com locale pt_BR | o gerenciador grava as colunas numéricas como número |
| "Subir" com a tabela vazia apagava a aba | versão antiga do gerenciador | salvar só depois de carregar + gravação sem `clear` prévio |

## Segurança
- As senhas nunca ficam em texto puro na planilha, só o hash SHA-256 (sem *salt*). Use senhas geradas pelo programa.
- O Web App é público (`ANYONE_ANONYMOUS`). Sem login válido, ninguém vê dados.
- As sessões abertas expiram sozinhas em até 6 h. Excluir um investidor ou trocar a senha dele impede novos logins, mas uma sessão já aberta dura até expirar.
- Para revogar o acesso do programa à conta Google: <https://myaccount.google.com/permissions>.
