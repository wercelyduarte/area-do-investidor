/************************************************************************
 *  Apps Script - Area do Investidor (login + planilha central)
 *
 *  Como usar:
 *    1. Abra a planilha no Google Sheets (conta do mestre).
 *    2. Menu: Extensões -> Apps Script.
 *    3. Apague tudo em Códigos.gs e cole este arquivo.
 *    4. Crie um arquivo HTML chamado "Index" (+ -> HTML) e cole o Index.html.
 *    5. Rode gerarHashSenha("sua_senha") no editor para gerar hashes.
 *    6. Implantar -> Nova implantação -> App da Web.
 *
 *  Abas esperadas na planilha:
 *    - "Aplicacoes": coluna "Investidor" + colunas de dados (Valor, Data, etc.)
 *    - "Usuarios": colunas "usuario" e "senha_hash"
 ************************************************************************/

const ABA_APLIC = 'Aplicacoes';
const ABA_USERS = 'Usuarios';
// ID da planilha do mestre. Usamos openById (mais robusto no Web App) em vez de
// getActiveSpreadsheet(), que pode retornar null no contexto de Web App.
const SHEET_ID = 'PREENCHIDO_AUTOMATICAMENTE_PELO_GERENCIADOR';

// Serve a pagina HTML quando alguem abre a URL do Web App.
function doGet(e) {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Area do Investidor')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

// Abre a planilha do mestre (sempre por ID - funciona em qualquer contexto).
function _planilha() {
  return SpreadsheetApp.openById(SHEET_ID);
}

// Hash SHA-256 (hex). Nunca guarde senha em texto puro.
function _hash(s) {
  const raw = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(s));
  return raw.map(b => ('0' + (b & 0xff).toString(16)).slice(-2)).join('');
}

// Utilitario: rode no editor (Executar) passando uma senha para gerar o hash
// e cole o resultado na coluna senha_hash da aba Usuarios.
function gerarHashSenha(senha) {
  return _hash(senha);
}

// Valida login. Retorna {ok, token, usuario} ou {ok:false, msg}.
function login(usuario, senha) {
  try {
    var ss = _planilha();
    var sh = ss.getSheetByName(ABA_USERS);
    if (!sh) return { ok: false, msg: 'Aba "Usuarios" nao encontrada.' };
    var rows = sh.getDataRange().getValues();
    var hashTentativa = _hash(senha);
    for (var i = 1; i < rows.length; i++) {
      var u = rows[i][0];
      var hash = rows[i][1];
      if (String(u).trim().toLowerCase() === String(usuario).trim().toLowerCase()
          && hash && String(hash).trim() === hashTentativa) {
        var token = Utilities.getUuid();
        CacheService.getScriptCache().put('tok_' + token, String(u), 60 * 60 * 6);
        return { ok: true, token: token, usuario: String(u) };
      }
    }
    return { ok: false, msg: 'Usuario ou senha invalidos.' };
  } catch (e) {
    return { ok: false, msg: 'Erro no login: ' + e.toString() };
  }
}

// Busca os dados. So retorna as linhas do investidor logado.
// Usa getDisplayValues() (valores como aparecem na planilha) em vez de getValues()
// pra evitar: (1) problemas de serializacao de Date e (2) deslocamento de fuso
// horario nas datas. Tudo vem como string formatada (ex.: "R$ 5.000,00", "01/03/2026").
function getDados(token) {
  try {
    var usuario = CacheService.getScriptCache().get('tok_' + token);
    if (!usuario) return { ok: false, msg: 'Sessao expirada. Faca login novamente.' };

    var ss = _planilha();
    var sh = ss.getSheetByName(ABA_APLIC);
    if (!sh) return { ok: false, msg: 'Aba "Aplicacoes" nao encontrada.' };

    var data = sh.getDataRange().getDisplayValues();
    if (data.length < 2) {
      return { ok: true, headers: _normalizaHeaders(data[0]), linhas: [], usuario: usuario };
    }

    var headers = _normalizaHeaders(data[0]);

    // Acha o indice da coluna "Investidor" (case-insensitive).
    var invIdx = -1;
    for (var k = 0; k < headers.length; k++) {
      if (headers[k].toLowerCase() === 'investidor') { invIdx = k; break; }
    }

    // Admin ve tudo (sem filtro); outros usuarios veem so as proprias linhas.
    var isAdmin = String(usuario).trim().toLowerCase() === 'admin';

    var linhas = [];
    for (var i = 1; i < data.length; i++) {
      var row = data[i];
      if (!isAdmin && invIdx >= 0
          && String(row[invIdx]).trim().toLowerCase() !== String(usuario).trim().toLowerCase()) {
        continue;  // filtra: so as linhas deste investidor (admin ve todas)
      }
      var obj = {};
      for (var j = 0; j < headers.length; j++) {
        obj[headers[j]] = row[j];
      }
      linhas.push(obj);
    }
    return { ok: true, headers: headers, linhas: linhas, usuario: usuario };
  } catch (e) {
    return { ok: false, msg: 'Erro no getDados: ' + e.toString() + ' (linha ' + (e.lineNumber || '?') + ')' };
  }
}

// Garante que os cabecalhos sejam strings simples.
function _normalizaHeaders(arr) {
  var out = [];
  for (var i = 0; i < arr.length; i++) {
    out.push(String(arr[i] == null ? '' : arr[i]));
  }
  return out;
}
