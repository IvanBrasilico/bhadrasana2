# Sistema AJNA

## Visão computacional aplicada - Aduana Brasileira

### Ficha de Controle de Carga - Manual de usuário


1. Demandante cadastra Ficha de Operação e encaminha para Setor ou Atribui para Servidor
2. Servidor consulta o ["Minhas Fichas"](exemplos/fluxo_importacao/221bb), o "Pesquisa Fichas" ou o "Kanban"


Exemplo

Este exemplo utiliza a seguinte estrutura:

Setores demandantes:

NUPEI - ALFSTS - ALFTS/SERAD - ALFTS/EQREXP - ALFTS/COV

Setores Executores:

NUPEI - ALFSTS - ALFTS/SERAD - ALFTS/EQREXP - ALFTS/COV


1. Servidor do NUPEI [seleciona CE 001 e encaminha para análise de imagem](../cadastra_001.md)
2. Servidor do SERAD seleciona CE 001 e vê que já tem Operação iniciada

3. Servidor do COV  visualiza entrada de fichas/operações (pelo Minhas Fichas ou pelo Kanban)

4. Servidor do SERAD seleciona CE 002 e encaminha para análise de imagem

5. Servidor do NUPEI seleciona CE 003 e encaminha para verificação física diretamente

6. Mostrar visão de Supervisores da DIREP, EQREXP e COV

7. Servidor do COV analisa imagens. Devolve 001 e encaminha 002 para EQREXP

8. Mostrar visão de Supervisores da DIREP, EQREXP, COV, NUPEI e ESPEI



 

