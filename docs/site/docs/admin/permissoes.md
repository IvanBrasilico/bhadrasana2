## Modelo de permissões

Descrição do modelo de permissões de  acesso do Sistema. 
Implementado com o cadastro de Perfis para o  Usuário.

#####Regras gerais
- As Fichas e verificações físicas só podem ser editadas pelo responsável atual
- Se a Ficha está concluída ou arquivada, não pode mais ser editada. Podem ser adicionados Eventos, que terão
caráter meramente informativo
- Supervisor do Setor pode atribuir Ficha concluída ou arquivada, caso em que ela poderá ser editada novamente 
e deve ser arquivada/concluída novamente depois
- Usuário só pode atribuir no próprio Setor
- Usuário com a Ficha pode repassá-la para outro Setor. A Ficha "entra" no novo Setor com fase "Iniciada" e sem 
responsável atribuído. 
 
###Perfis

####Consulta 

Consegue realizar todas as pesquisas, consultar a API e o Telegram, visualizar tudo. 
*(Obs.: restringir visualização ao próprio Setor???)*

Não edita nem cria nada.

####Operador (perfil mínimo padrão hoje)

Além das funções de consulta, cria Fichas, eventos, verificações físicas, TGs, Taseda, etc.

Edita somente Fichas que estejam para si atribuídas. Consegue repassar atribuição e consegue atribuir Ficha que esteja 
na fase "Iniciada" e sem responsável atual.

####Supervisor

Funções do Operador, podendo atribuir Fichas do seu Setor mesmo se tiverem responsável, bem como desfazer arquivamento e
conclusão.
 
Pode modificar Setor da Ficha (enviar para outra Equipe).

Possui acesso às telas Marca, RepresentanteMarca, Recinto e RoteiroOperacaoOVR na interface administrativa.

####Cadastrador

Possui acesso às telas Usuario, Perfil, Setor, PerfilUsuario e TipoEventoOVR na interface administrativa.

*Implementar: Cadastrador não possuir nenhum acesso no Sistema fora da interface administrativa.*
