### Interface de administração

####Acesso
Pelo menu "Administração", dentro da lista "Pesquisas" no menu da tela inicial, 
é possível administrar algumas tabelas do Sistema.

![Menu inicical](../images/menu.png)

#### Tela inicial
Então, caso o Usuário possua o perfil de "Supervisor" e/ou de "Cadastrador" 
terá acesso à seguinte tela:

![Tela completa de administracao](../images/admincompleto.png)

Nesta tela é possível gerenciar várias tabelas de Sistema, entre elas a lista de 
marcas cadastradas, o cadastro de Recintos, Setores, Usuários, Perfis de Acesso, 
opções de Tipos de Evento a informar no Sistema e os roteiros/check-lists.

É possível listar, pesquisar, filtrar (por exemplo, visualizar Usuários de um Setor), 
editar, incluir e em alguns casos incluir

#### Cadastro de Marcas

Lista de marcas

![Tela de Marcas](../images/marcas1.png)

Busca pelo nome

![Tela de Marcas](../images/marcas2.png)

Edição

![Tela de Marcas](../images/marcas3.png)


#### Cadastro de Setores

Os Setores podem ser cadastrados em formato de "árvore". Por exemplo, pode ser cadastrado um
Setor DIREP e duas equipes EQREP1 e EQREP2. Usuários cadastrados no Setor DIREP poderá ver Fichas
do Setor DIREP e dos dois Setores Filhos. Já os Usuários cadastrados nos Setores Filhos verão apenas
Fichas de suas Equipes.

Várias telas são influenciadas pela propriedade de árvore do Setor. Para exemplo, olhar a parte de
Roteiros deste manual.

É possível pesquisar por nome.

![Tela de Setores](../images/setor1.png)

![Tela de Setores](../images/setor2.png)


#### Cadastro de Tipos de Evento

Normalmente não será necessária a manutenção desta tabela, mas há a opção. Deve se tomar 
cuidado especial com os Eventos com campo "TipoEventoEspecial", pois estes Eventos são utilizados
dentro do código para diferenciar os seguintes código de Evento Especial, e a aplicação faz as atualizações
necessárias com base neste cadastro.

EventoEspecial
- Responsavel = 1
- RVF = 2
- TG = 3
- Autuação = 4

É possível pesquisar por nome e filtrar for fase.

![Lista de Tipos de Evento](../images/eventos1.png)

#### Cadastro de Recintos

O campo cod_dte é necessário para integração automática das FMAs do Porto de Santos. 
Esta tabela deve ser importada automaticamente do SISCOMEX quando possível e também não precisa
de manutenção regular. 

É possível pesquisar por nome.

![Tela de Recintos](../images/recintos1.png)

 
