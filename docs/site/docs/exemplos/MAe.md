Holmes (supervisor) entra no Sistema

1. Consulta as fichas do tipo “Mercadoria Abandonada” com Status “FMA cadastrada por importação automática”
2. Após informar no Siscomex Carga que foi emitida FMA para a carga, informa evento “Bloqueio de CE incluído”
3. Verifica se é o caso de carga perecível e adiciona Alerta se for o caso
4. Se não é perecível, informa evento “Aguardando distribuição”.

Watson (AT ou apoio) verifica todas as fichas do tipo “Mercadoria Abandonada” com bloqueio de CE incluído

1. Verifica as fichas de carga perecível e após prazo de aproximadamente 15 (quinze) dias, se não houver pedido de retomada de despacho (IN69), elabora ofício para órgão anuente;
2. Informa evento “Aguardando manifestação de órgão anuente” e anexa o ofício;
3. Quando receber a resposta, informa “Recebimento de manifestação de órgão anuente”;
4. Tendo o órgão anuente afirmado que a mercadoria não está em condições de comercialização e consumo, abre-se um dossiê com os documentos e a ficha é distribuída ao fiscal responsável pelos procedimentos da Lei 12.715. Nesse caso informa-se no sistema “Aguardando procedimentos da lei 12.715”.
5. Tendo o órgão anuente liberado a comercialização da mercadoria, após consulta ao supervisor, a ficha é distribuída ao responsável pela conferência física (Irene Adler).

Irene Adler entra no sistema

1. Consulta suas fichas;
2. Agenda verificação física e informa evento “Em verificação física”;
3. Informar RVF carregando fotos;
4. Registra Termo de Guarda;
5. Informa a Emissão de Auto de Infração;

Com esse evento, Watson volta a atuar:

1. Abre processo no SIEF e informa evento “Processo aberto no SIEF”;
2. Em “Informar processo” registra o nº do processo de perdimento;
3. Anexa os documentos de integração ao CTMA no e-processo e informa evento “Geração de documentos de integração ao CTMA”.

Irene Adler entra no sistema

1. Monta o processo e informa evento “Montagem de processo”.

Watson (supervisor) entra no Sistema

1. Altera o bloqueio no Siscomex Carga e informa evento “Bloqueio de CE atualizado”
2. Informa evento “Encerramento com resultado”.

Holmes (supervisor) entra no Sistema para saber

1. Acompanha fichas do Setor

Holmes (supervisor) precisa informar gerenciais/produtividade

1. Roda relatórios

Holmes (supervisor) precisa pesquisar cargas perecíveis (ou outra pesquisa)

1. Roda pesquisa Ficha
