---
name: estudos-de-caso-fichas
description: Monta uma apresentação PowerPoint (.pptx) didática de estudos de caso de fiscalização aduaneira a partir do pacote ZIP gerado pelo script estudo_de_caso.py do Navi-Fichas (dados do CE Mercante e do BL, imagem de escaneamento do contêiner e fotos da verificação física). Use quando receber esse ZIP (ele tem indice.json e pastas caso_NN_ficha_ID) e for pedida uma apresentação, slides ou um PPTX.
---

# Estudos de caso a partir do pacote do Navi-Fichas

O pacote traz, para cada caso, os dados já extraídos e formatados do Navi-Fichas (o sistema de acompanhamento das
fiscalizações da Receita Federal), a imagem de escaneamento do contêiner e uma amostra das fotos da verificação física.
Seu trabalho é transformar isso numa apresentação **didática**, de aula ou de treinamento: cada caso mostra os
documentos da carga, a imagem do escâner e o que a verificação encontrou.

## O que há no ZIP

```
SKILL.md                          estas instruções
indice.json                       origem dos casos, critério de escolha, lista dos casos
caso_01_ficha_<id>/
    dados.json                    tudo do caso; os blocos slide_* já vêm prontos para os slides
    resumo.md                     o mesmo, em texto, para conferência
    escaneamento_<contêiner>.jpg  imagem de escaneamento (raio X) do contêiner
    fotos/foto_01.jpg ...         miniaturas das fotos da verificação física (RVF)
caso_02_ficha_<id>/ ...
```

Leia primeiro o `indice.json` (ordem dos casos) e depois o `dados.json` de cada caso. Os campos que importam:

| Campo do `dados.json` | Uso |
|---|---|
| `titulo_sugerido` | título do caso ("Estudo de caso 1 – POLUS") |
| `slide_abertura.campos` | pares `[rótulo, valor]` da tabela de documentos, na ordem de exibição |
| `slide_abertura.mercadorias` | linhas `ncm`, `posicao` (descrição oficial da posição da NCM), `descricao` (do CE), `volumes`, `marca` |
| `slide_escaneamento.imagens` | `arquivo`, `conteiner`, `data`, `legenda_sugerida`, `regra`, `dias_da_referencia` |
| `slide_escaneamento.sem_imagem` | contêineres sem escaneamento encontrado |
| `slide_resultado.destaques` | pares `[rótulo, valor]` com os números do resultado (valor retido, quantidade, apreensões) |
| `slide_resultado.infracoes`, `.marcas` | listas de texto |
| `slide_resultado.mercadorias_retidas` | `descricao`, `quantidade`, `valor` dos Termos de Guarda |
| `slide_resultado.descricao_rvf` | o que a equipe registrou na verificação física (resumo) |
| `slide_resultado.fotos` | `arquivo`, `legenda`, `marca`, `conteiner` de cada foto |
| `operacao` | só quando o caso veio de uma Operação: nome, totais, fiscalizados, outras Fichas |
| `fatos` | fatos objetivos para sugerir indicadores de risco (ver abaixo) |
| `avisos` | o que faltou ou precisa de conferência |
| `ficha`, `conhecimento`, `rvfs`, `tgs` | os dados completos, para as notas do apresentador |

## Regras de fidelidade (obrigatórias)

1. **Use só o que está no pacote.** Não invente números, nomes, datas, marcas, quantidades nem conclusões. Não pesquise
   as empresas fora do pacote.
2. **Copie os valores como vêm.** Moeda, pesos, datas, CNPJ e NCM já estão formatados no padrão brasileiro
   (`R$ 5.397.750,00`, `16.225,000 kg`, `20/07/2026`). Não arredonde nem converta.
3. **Campo vazio não aparece.** Se um dado não está no pacote, a linha some; não escreva "não informado".
4. **Imagens:** não descreva o que "aparece" na foto ou no escaneamento além do que dizem a `legenda`, a `marca`, a
   `descricao_rvf` e as `infracoes`. Nunca corte nem distorça uma imagem: mantenha a proporção.
5. **Escaneamento:** a imagem foi achada pelo contêiner e pela data (`regra`, `dias_da_referencia`), o que não garante
   que é a mesma viagem. Ponha a `legenda_sugerida` no slide e a regra nas notas do apresentador.
6. **Dados pessoais e de empresas:** o pacote é de uso interno da Receita Federal e traz CNPJ, nomes e números de CE.
   Não mascare por conta própria. Se o pedido falar em público externo (curso, evento, outro órgão), pergunte ao
   usuário se deve trocar nomes e CNPJ por "Empresa A", "Empresa B"... antes de montar.
7. Os `avisos` vão para as notas do apresentador do caso, para a pessoa conferir antes de apresentar.

## A apresentação

Formato 16:9 (13,333 × 7,5 polegadas). Se o usuário mandar um modelo (.pptx/.potx) ou a apresentação de referência,
use os layouts, as cores, o logotipo e as fontes dela. Sem modelo: fundo branco, títulos em azul-marinho (`1F3864`),
um tom de destaque (`C00000` para os números do resultado), fontes Calibri (corpo) e Cambria (títulos).

### Slide de abertura da apresentação

Título do tema (pergunte se não foi dado; sugestão: "Estudos de caso"), subtítulo com a origem do `indice.json`
(por exemplo "Operações de maior valor – Fichas abertas de 01/01/2026 a 31/12/2026") e a data. Se houver mais de três
casos, um slide de sumário com os títulos.

### Três slides por caso, nesta ordem

**1. Documentos** – título `slide_abertura.titulo`.

- Tabela em **quatro colunas**: `Campo | Informação | Campo | Informação`, com os pares de `slide_abertura.campos`
  divididos ao meio (primeira metade à esquerda, segunda à direita, mantendo a ordem). Cabeçalho escuro com texto
  branco, linhas finas, fonte 10–11 pt, rótulos em negrito.
- Abaixo (ou à direita, se couber), a tabela **Mercadoria**: colunas `Mercadoria` (a `descricao`; vazia, a `posicao`)
  e `NCM`; com espaço, `Volumes`. No máximo 8 linhas; se `mercadorias_total` for maior, a última linha diz
  "… e mais N".
- Se não couber tudo em fonte 10 pt, tire primeiro "CE master", "Tipo de contêiner (ISO)", "Pagamento do frete",
  "Porto de carregamento" e "Recinto", nessa ordem, e ponha o que saiu nas notas. Nunca deixe texto vazar da tabela.
- Caso de Operação: os campos "Operação", "Fichas na Operação" e "Valor da Operação" já vêm em `campos`.

**2. Escaneamento** – título `slide_escaneamento.titulo`.

- A imagem `escaneamento_<contêiner>.jpg` ocupa a largura útil do slide (margens de 0,5"), centralizada na vertical,
  com a proporção mantida; a `legenda_sugerida` logo abaixo, em 12 pt.
- Dois ou três contêineres: as imagens empilhadas (escaneamentos são largos), cada uma com a legenda.
- Sem imagem (`imagens` vazio): mantenha o slide com um quadro cinza claro e o texto "Imagem de escaneamento não
  localizada para o contêiner X – inserir manualmente". Este slide é essencial: não o remova.
- Notas: `regra`, `referencia`, `dias_da_referencia` e `escaneamentos_do_conteiner`.

**3. Resultado** – título `slide_resultado.titulo`.

- Lado esquerdo (cerca de 60%): grade de fotos de `slide_resultado.fotos`, na ordem do pacote. Até 4 fotos: 2×2; até 6:
  3×2; até 8: 4×2. Com mais de 8, use as 8 primeiras e cite as outras nas notas. Fotos com proporção mantida,
  centralizadas na célula. Com `legenda` ou `marca`, uma legenda de 9–10 pt sob a foto.
- Lado direito: os `destaques` como números grandes (28–36 pt, cor de destaque) com o rótulo pequeno embaixo, como no
  exemplo "Valor da apreensão R$ 5.397.750,00 / Peso apreendido 16.225 kg". Até três destaques; os demais em lista.
- Abaixo dos destaques: "Infrações" (`infracoes`) e "Marcas" (`marcas`) em listas curtas, e, se houver espaço, a
  `descricao_rvf` em uma ou duas frases (sem mudar o sentido).
- Sem fotos: os destaques e as listas ocupam o slide inteiro.
- Notas: a `descricao_rvf` completa, as `mercadorias_retidas`, os `avisos`, o número da Ficha (`ficha.id`) e, no caso
  de Operação, os `fiscalizados` e as `outras_fichas`.

### Indicadores de risco (opcional, com cuidado)

A apresentação de referência destaca lições como "NCM único = escâner" ou "mercadoria com habitualidade em
falsificação = verificação física completa". Você pode sugerir **até três** frases assim no slide de resultado, **só**
quando um fato do pacote as sustentar, por exemplo:

- `fatos.posicoes_ncm_declaradas` = 1 e há escaneamento → "NCM único: o escâner mostra a divergência";
- `fatos.posicoes_ncm_declaradas` alto → "Diversidade de mercadorias no mesmo embarque";
- `fatos.diferenca_peso_rvf_declarado_pct` com módulo acima de 10 → "Divergência entre o peso declarado e o
  verificado (X%)";
- `infracoes` com contrafação e `marcas` preenchidas → "Marcas com histórico de falsificação".

Escreva nas notas "Indicadores sugeridos a partir dos dados – confirmar com a equipe". Se nenhum fato sustentar, não
escreva indicador.

## Conferência final

- Todos os casos do `indice.json` têm os três slides, na ordem.
- Nenhum texto vaza de caixa ou tabela; nada abaixo de 9 pt; títulos na mesma posição em todos os slides de caso.
- Nenhuma imagem distorcida ou cortada; os escaneamentos com legenda.
- Cada número do slide aparece igual no `dados.json`.
- Os `avisos` de cada caso estão nas notas.

## Dica de implementação (python-pptx)

```python
from PIL import Image
from pptx.util import Inches

def encaixa(slide, caminho, x, y, largura, altura):
    """Insere a imagem dentro da caixa (polegadas), centralizada e sem distorcer."""
    with Image.open(caminho) as imagem:
        proporcao = imagem.width / imagem.height
    if largura / altura > proporcao:
        w, h = altura * proporcao, altura
    else:
        w, h = largura, largura / proporcao
    slide.shapes.add_picture(caminho, Inches(x + (largura - w) / 2), Inches(y + (altura - h) / 2),
                             Inches(w), Inches(h))
```

Com pptxgenjs, use `sizing: { type: "contain", w, h }` no `addImage`.
