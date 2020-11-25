# Sistema AJNA

## Visão computacional aplicada - Aduana Brasileira

### Ficha de Controle de Carga - Manual de usuário - roteiro de exportação

### Roteiro base

1. Demandante cadastra Ficha de Operação e encaminha para Setor ou Atribui para Servidor
    * Usar tipo de operação "Análise de risco na exportação", informar recinto, CE-Mercante e/ou DUE, fiscalizado, etc, 
   conforme [exemplo](../exemplos/fluxo_importacao/221ba.md) 
2. Servidor ou Supervisor consulta o ["Pesquisa Fichas"](../pesquisas/pesquisa.md), 
o ["Minhas Fichas"](../pesquisas/minhasfichas.md),
 ou o ["Kanban"](../pesquisas/kanban.md), 
3. Servidor ou Supervisor atribui responsabilidade da Ficha, informa auditor responsável
    1. Se for Setor COV, realiza a verificação de forma sumária, apenas com análise de imagem. 
 Se houver recomendação de abertura, encaminha para o Setor de abertura (volta ao passo 2).
 Senão, direto para o passo 9.
4. Servidor realiza a verificação física [(exemplo)](../exemplos/fluxo_importacao/221bb.md)
    * Se for necessário imprimir formulário em papel antes, abrir RVF, colocar apenas dados, sem descrição 
   e eventuais apreensões. Clicar nos botões OVR e/ou em Taseda para gerar os formulários pelo Sistema
    * O Servidor também pode realizar a verificação física pelo celular (ver manuais sobre interface Telegram)
5. Servidor preenche tela da verificação física [(exemplo)](../images/rvf.png)
    * Informar dados (CE, contêiner, etc) se não informados no passo anterior
    * Carregar fotos se não informado no passo anterior
    * Revisar/informar descrição dos fatos verificados
    * Se houverem, é importante informar
    * Se houver, informar apreensão de drogas no botão específico e gerar Taseda. Enquanto não for possível gerar pelo Telegram,
   recomenda-se pedir a alguém na Alfândega ou em trabalho remoto que gere em tempo real e envie para o Recinto para impressão. 
6. Encaminhar OVR e Taseda para assinatura, no canal específico
    * A recomendação é imprimir antes ou na hora o Taseda pelo Sistema, e preencher em papel, pegando as assinaturas.
    * Já o OVR, gerar depois, já com todas as informações no Sistema, e mandar pelo e-Assina para o Recinto
7. Se houver necessidade, utilizar gera docx para gerar formulários extras ou personalizados [Gerador de .docx](../../exemplos/gera_docx/)
8. Anexar formulários assinados em Eventos para registro 
9. Encaminhar Ficha para o Supervisor
10. Supervisor consulta sua caixa com frequência, acompanha ações, devolve para revisão ou complementação se necessário.
11. Supervisor arquiva. Pasta "Concluídos" para ações com resultado e "Arquivada" para ações sem resultado.
12. Setor de origem pode acompanhar todo o andamento das ações nas telas "Criado por mim" ou "Passaram por mim". Se tiver 
acesso, pode também acompanhar pelo Kanban do Setor específico

### Exemplo

Este exemplo utiliza a estrutura descrita a seguir e tem por objetivo mostrar como é possível
diversos Setores interagirem com todos podendo manter o rastreamento das ações.

Setores demandantes:  NUPEI - ALFSTS - ALFTS/SERAD - ALFTS/EQREXP - ALFTS/COV

Setores Executores: NUPEI - ALFSTS - ALFTS/SERAD - ALFTS/EQREXP - ALFTS/COV

Ver video explicativo: [parte1](parte1.mp4)  [parte2](parte2.mp4)  [parte3](parte3.mp4)

1. Servidor do NUPEI seleciona CE 001 e encaminha para análise de imagem
2. Servidor do SERAD seleciona CE 001, vê que já tem Operação iniciada e aborta
3. Servidor do COV visualiza entrada de fichas/operações (pelo Minhas Fichas ou pelo Kanban)
4. Servidor do SERAD seleciona CE 002 e encaminha para análise de imagem
5. Servidor do NUPEI seleciona CE 003 e encaminha para verificação física diretamente
6. Mostrar visão de Supervisores da DIREP, EQREXP e COV
7. Servidor do COV analisa imagens. Devolve 001 e encaminha 002 para EQREXP
8. Mostrar visão de Supervisores da DIREP, EQREXP, COV, NUPEI e ESPEI
