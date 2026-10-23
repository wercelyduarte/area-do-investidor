# Área do Investidor

Programa gratuito para quem administra aplicações de investidores.

- **Você** cadastra investidores e aplicações num programa simples, no seu computador.
- **Cada investidor** recebe um link, entra com usuário e senha e vê **só as aplicações dele**, pelo celular ou computador.
- Tudo fica guardado numa planilha do **Google Sheets na sua conta**. Não tem mensalidade nem servidor para pagar.

![Tela principal](docs/img/aplicacoes.png)

---

## Como começar (3 passos)

### 1. Baixe e instale
**[⬇ Baixar o instalador (.msi)](https://github.com/wercelyduarte/area-do-investidor/releases/latest)**: na página que abrir, clique no arquivo `GerenciadorInvestidor-...-win64.msi`.

Dê dois cliques no arquivo baixado e avance até o fim. Se o Windows mostrar *"O Windows protegeu o computador"*, clique em **Mais informações → Executar assim mesmo**. Isso aparece porque o programa é gratuito e não tem assinatura digital paga.

Funciona no Windows 10 e 11. **Não precisa instalar Python nem mais nada.**

### 2. Abra o programa e siga o assistente
Abra o **Gerenciador do Investidor** pelo atalho na Área de Trabalho. Na primeira vez, um assistente guia tudo:

1. **Credencial do Google** (uns 10 minutos, só uma vez): o programa tem um botão para cada passo e abre a página certa do Google. O arquivo baixado é encontrado automaticamente.
   👉 Se travar em algum passo, veja o **[guia com imagens](docs/GUIA_GOOGLE.md)**.
2. **Conectar sua conta Google**: autorize no navegador.
3. **Criar a planilha**: escolha a senha do usuário `admin` e clique em **Criar planilha e página**.

O programa cria a planilha e publica a página dos investidores sozinho.

### 3. Cadastre e envie o acesso
- Aba **Investidores** → **Novo investidor**: o programa gera a senha e monta a mensagem com link, usuário e senha. É só clicar em **Copiar mensagem** e enviar por WhatsApp ou e-mail.
- Aba **Aplicações** → **Nova aplicação**: escolha o investidor, o valor, a data, o prazo e a %. O lucro é calculado sozinho.
- Clique em **💾 Salvar na planilha** (ou aperte **Ctrl+S**).

📘 Manual completo: **[Como usar no dia a dia](docs/COMO_USAR.md)**

---

## Perguntas rápidas

| Pergunta | Resposta |
|---|---|
| Quanto custa? | Nada. Usa só serviços gratuitos do Google. |
| Onde ficam os dados? | Numa planilha **na sua conta Google**. O programa e o autor não têm acesso. |
| O investidor vê os dados dos outros? | Não. Cada um vê só as próprias aplicações. Apenas o `admin` vê tudo. |
| As senhas ficam expostas na planilha? | Não. A planilha guarda só uma versão embaralhada (hash SHA-256). |
| Posso editar direto no Google Sheets? | Pode. Clique em **Descartar alterações** no programa para recarregar. Antes de salvar, o programa avisa se a planilha foi mudada por fora. |
| Deu erro, e agora? | Veja **[Problemas comuns](docs/COMO_USAR.md#problemas-comuns)**. |

---

## Para desenvolvedores
Código-fonte, build do instalador e como a página funciona: **[docs/DESENVOLVEDORES.md](docs/DESENVOLVEDORES.md)**.

Licença: [MIT](LICENSE).
