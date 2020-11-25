# Sistema AJNA

## Visão computacional aplicada - Aduana Brasileira

### Ficha de Controle de Carga - Manual de usuário - Gerador de documentos


O Fichas possui internamente um motor gerador de documentos, acessível no menu Admnistração->Gerador de documentos.
Ele pode utilizar modelos no formato .docx, contendo tags, e preenchê-los com dados do Sistema. 

Atualmente, há estas opções de dados:

- Uma RVF com seus campos (RVF)
- Uma Ficha com os campos Filhos das RVFs e imagens (Ficha) 
- Uma Ficha com os campos Filhos dos TGs e RVFs, e as imagens
- Uma Ficha, RVFs e marcas, divididos por Representante de Marca

E as seguintes opções de tags:

{nome do campo} - campo simples

<nome do filho:campo do filho 1:campo do filho 2> - gera tabelas mestre-detalhe com os campos do detalhe

{{nome do filho:campo do filho 1:campo do filho 2}} - gera parágrafos com os campos do detalhe

<<nome do filho:campo do filho 1:campo do filho 2>> - gera páginas com os campos do detalhe (para imprimir imagens)

A melhor maneira de aprender a utilizar o gerador de docx é olhar os modelos disponíveis e tentar criar os próprios.
Estes vídeos demonstrativos podem ajudar a começar:


