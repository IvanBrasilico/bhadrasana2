## Modelo de permissões

Descrição do modelo de permissões de  acesso do Sistema. 
Implementado com o cadastro de Perfis para o  Usuário.

#####Regras gerais
- As Fichas e verificações físicas só podem ser editadas pelo responsável atual
- O Perfil Supervisor pode atribuir qualquer Ficha, podendo portanto avocar uma Ficha para editar
- Se a Ficha está concluída ou arquivada, não pode mais ser editada. Podem ser adicionados Eventos, que terão
caráter meramente informativo
- Supervisor do Setor pode atribuir Ficha concluída ou arquivada, caso em que ela poderá ser editada novamente 
e deve ser arquivada/concluída novamente depois
- Usuário só pode atribuir no próprio Setor
- Usuário com a Ficha pode repassá-la para outro Setor. A Ficha "entra" no novo Setor com fase "Iniciada" e sem 
responsável atribuído.
- Ficha na fase 0 e "liberada" pode ser atribuída por qualquer um do Setor (como se fosse uma Caixa de Entrada)
- Eventos informados pelo Usuário ou por ações (inclusão de TG, RVF, lavratura de Auto, etc) mudam a Fase atual da Ficha
- Existe um tipo de Evento "Meramente informativo" que não altera a Fase/Status. Serve para incluir Eventos "parciais" que
  não concluem a fase atual ou para incluir anotações em Fichas concluídas. Este Evento pode ser anotado mesmo que o 
  Usuário não esteja como responsável na Ficha
- Nas consultas:
  - Em "Minhas Fichas" o Usuário só vê seus Setores, suas Fichas atuais ou as que já interagiu
  - Em "kanban" o Usuário vê suas Fichas, mas pode escolher olhar qualquer Setor da Unidade
  - Em "Pesquisa Fichas" os filtros são de dados da Unidade, mas a pesquisa sem filtros ou por documento, declaração, CE,
    etc pode mostrar qualquer Ficha de qualquer Unidade
 
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
 
Pode modificar Setor da Ficha (enviar para outra Equipe). <-- Hoje ainda não está restrito - definir se será restrito

Possui acesso às telas Marca, RepresentanteMarca, Recinto e RoteiroOperacaoOVR na interface administrativa.

####Cadastrador

Possui acesso às telas Usuario, Perfil, Setor, PerfilUsuario e TipoEventoOVR na interface administrativa.

*Implementar: Cadastrador não possuir nenhum acesso no Sistema fora da interface administrativa.*
