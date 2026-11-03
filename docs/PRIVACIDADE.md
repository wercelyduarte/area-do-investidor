# Política de privacidade: Área do Investidor

*Última atualização: 3 de novembro de 2026*

O **Área do Investidor** (programa "Gerenciador do Investidor") é gratuito e de código aberto. Ele não tem servidor próprio, não exibe anúncios e **não envia nenhum dado ao desenvolvedor**.

## Onde ficam os seus dados
- **Na sua conta Google:** os investidores, as aplicações e as senhas (guardadas só como hash SHA-256) ficam numa planilha do Google Sheets criada na **sua** conta. A página de acesso dos investidores é um Google Apps Script publicado também na **sua** conta.
- **No seu computador:** as configurações (`estado.json`), a autorização do Google (`token.json`) e a credencial que você cria (`client_secret*.json`) ficam na pasta de dados do programa, dentro de `%LOCALAPPDATA%`. Esses arquivos nunca saem do seu computador, exceto para o próprio Google durante o login.

## Permissões do Google
O programa pede acesso apenas para:
- criar e editar a planilha que ele mesmo cria (Google Sheets e `drive.file`, que dá acesso só aos arquivos criados pelo programa);
- criar e publicar o Apps Script da página dos investidores.

O programa usa essas permissões só para as funções descritas acima. Para revogar o acesso a qualquer momento, acesse <https://myaccount.google.com/permissions>.

## Dados dos investidores
Quem usa o programa (o administrador) é o responsável pelos dados dos investidores que cadastra e por informá-los sobre esse uso. Cada investidor vê somente as próprias aplicações, depois de entrar com usuário e senha.

## O que o programa não faz
- Não coleta estatísticas de uso nem telemetria.
- Não compartilha dados com terceiros, além do Google, onde os dados ficam guardados na sua conta.
- Não faz operações financeiras: ele só registra e organiza informações.

## Como excluir os dados
- **Planilha e página:** apague-as no seu Google Drive e no Apps Script.
- **Dados locais:** desinstale o programa. A versão da Microsoft Store apaga a pasta de dados automaticamente.

## Contato
Dúvidas ou problemas: abra uma *issue* em <https://github.com/wercelyduarte/area-do-investidor/issues>.
