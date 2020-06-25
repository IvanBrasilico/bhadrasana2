## Modelo de permissóes

Descrição do modelo de permissões de  acesso do Sistema. 
Implementado com o cadastro de Perfis para o  Usuário.

#####Regras gerais
- As Fichas e verificações físicas só podem ser editadas pela carga (responsável) atual
- Se a Ficha está concluída ou arquivada, não pode mais ser editada
- ?? Fazer função de bloqueio de edição para verificação física mesmo sem ficha concluída???
 
###Perfis

####Consulta

Consegue realizar todas as pesquisas, consultar a API e o Telegram, visualizar tudo. (?? exceto ??)

Não edita nem cria nada.

####Operador

Além das funções de consulta, cria Fichas, eventos, verificações físicas, TGs, Taseda, etc.

Edita somente Fichas que estejam para si atribuídas. Consegue repassar atribuição.

####Supervisor

Funções do Operador, podendo se auto-atribuir Fichas do seu Setor, bem como desfazer arquivamento e
conclusão, pois tem permissão de informar Evento mesmo em Fichas concluídas.
 
Pode modificar Setor da Ficha (enviar para outra Equipe).

Possui acesso às telas Marca, Recinto e RoteiroOperacaoOVR na interface administrativa.

####Cadastrador

Possui acesso às telas Usuario, Perfil, Setor e TipoEventoOVR na interface administrativa.

Não possui nenhum acesso no Sistema.
