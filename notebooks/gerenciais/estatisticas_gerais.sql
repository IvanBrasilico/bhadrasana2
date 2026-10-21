-- =====================================================================================================================
-- Fichas (bhadrasana2) — estatísticas GERAIS do sistema
-- =====================================================================================================================
-- Só leitura, no banco do Fichas (tabelas ovr_*). Cada bloco é independente: rode um de cada vez ou todos.
-- Sem CTE e sem função de janela (vale para MySQL 5.7 e MariaDB antigos).
-- MariaDB, se quiser um teto por consulta:  SET SESSION max_statement_time = 300;
--
-- Datas usadas
--   Ficha (ovr_ovrs)   datahora = data da Ficha (a que a tela mostra; nas FMAs, a data de emissão da FMA);
--                      create_date = registro no sistema
--   RVF                datahora; sem ela, create_date (como a própria tela faz)
--   Foto, TG,          create_date (registro no sistema); a apreensão também pela data da RVF (bloco 5)
--   apreensão, resultado
--
-- Enumerados (ficam no código, bhadrasana/models/ovr.py)
--   tipooperacao    0 Mercadoria Abandonada (FMA) | 1 Repressão importação | 2 Repressão exportação |
--                   3 Pesquisa e seleção importação | 4 Pesquisa e seleção exportação | 5 Demanda externa |
--                   6 Operação de outros países | 7 Vigilância | 8 Operação de outros órgãos
--   fase            0 Iniciada | 1 Ativa | 2 Suspensa | 3 Concluída | 4 Arquivada
--   tipo_resultado  1 Apreensão | 2 Perdimento | 3 Crédito | 4 Sanção | 5 DARF | 6 Multa RFB | 7 Multa outro órgão
--
-- Recortes opcionais (no WHERE das Fichas, alias "o"):
--   AND o.tipooperacao NOT IN (6, 8)    -- só operações da RFB (os relatórios de apreensão do Fichas excluem 6 e 8)
--   AND o.setor_id IN ('1', '2')        -- só alguns setores (ver ovr_setores)
-- =====================================================================================================================


-- 1. PAINEL GERAL — uma linha por indicador (valor: kg nas apreensões, R$ nos TGs e resultados)
SELECT 'Fichas' AS indicador, COUNT(*) AS quantidade, NULL AS valor,
       MIN(datahora) AS primeira, MAX(datahora) AS ultima
  FROM ovr_ovrs
UNION ALL
SELECT 'Fichas com RVF', COUNT(DISTINCT ovr_id), NULL, NULL, NULL FROM ovr_verificacoesfisicas
UNION ALL
SELECT 'RVFs', COUNT(*), NULL, MIN(COALESCE(datahora, create_date)), MAX(COALESCE(datahora, create_date))
  FROM ovr_verificacoesfisicas
UNION ALL
SELECT 'RVFs de inspeção não invasiva', COUNT(*), NULL,
       MIN(COALESCE(datahora, create_date)), MAX(COALESCE(datahora, create_date))
  FROM ovr_verificacoesfisicas WHERE inspecaonaoinvasiva = 1
UNION ALL
SELECT 'Fotos de RVF', COUNT(*), NULL, MIN(create_date), MAX(create_date) FROM ovr_imagensrvf
UNION ALL
SELECT 'RVFs com foto', COUNT(DISTINCT rvf_id), NULL, NULL, NULL FROM ovr_imagensrvf
UNION ALL
SELECT 'Apreensões (valor = peso total, kg)', COUNT(*), SUM(peso), MIN(create_date), MAX(create_date)
  FROM ovr_apreensoes_rvf
UNION ALL
SELECT 'RVFs com apreensão', COUNT(DISTINCT rvf_id), NULL, NULL, NULL FROM ovr_apreensoes_rvf
UNION ALL
SELECT 'Fichas com apreensão', COUNT(DISTINCT v.ovr_id), NULL, NULL, NULL
  FROM ovr_apreensoes_rvf a JOIN ovr_verificacoesfisicas v ON v.id = a.rvf_id
UNION ALL
SELECT 'TGs (valor = R$)', COUNT(*), SUM(valor), MIN(create_date), MAX(create_date) FROM ovr_tgovr
UNION ALL
SELECT 'Fichas com TG', COUNT(DISTINCT ovr_id), NULL, NULL, NULL FROM ovr_tgovr
UNION ALL
SELECT 'Itens de TG (valor = soma de valor x qtde, R$)', COUNT(*), SUM(valor * qtde), MIN(create_date),
       MAX(create_date)
  FROM ovr_itenstg
UNION ALL
SELECT 'Resultados (valor = R$)', COUNT(*), SUM(valor), MIN(create_date), MAX(create_date) FROM ovr_resultados
UNION ALL
SELECT 'Fichas com resultado', COUNT(DISTINCT ovr_id), NULL, NULL, NULL FROM ovr_resultados
UNION ALL
SELECT 'Processos', COUNT(*), NULL, MIN(create_date), MAX(create_date) FROM ovr_processos
UNION ALL
SELECT 'Eventos do histórico (sem os excluídos)', COUNT(*), NULL, MIN(create_date), MAX(create_date)
  FROM ovr_eventos WHERE COALESCE(excluido, 0) = 0
UNION ALL
SELECT 'Anexos nos eventos', COUNT(*), NULL, MIN(create_date), MAX(create_date)
  FROM ovr_eventos WHERE COALESCE(excluido, 0) = 0 AND anexo_filename IS NOT NULL AND anexo_filename <> ''
UNION ALL
SELECT 'Marcas encontradas em RVF (RVF x marca)', COUNT(*), NULL, NULL, NULL FROM ovr_marcasencontradas
UNION ALL
SELECT 'Infrações encontradas em RVF (RVF x infração)', COUNT(*), NULL, NULL, NULL FROM ovr_infracoesencontradas
UNION ALL
SELECT 'Lacres verificados (RVF x lacre)', COUNT(*), NULL, NULL, NULL FROM ovr_lacresverificados
UNION ALL
SELECT 'Cães utilizados (RVF x K9)', COUNT(*), NULL, NULL, NULL FROM ovr_k9sutilizados
UNION ALL
SELECT 'Usuários cadastrados', COUNT(*), NULL, NULL, NULL FROM ovr_usuarios
UNION ALL
SELECT 'Usuários que já abriram Ficha', COUNT(DISTINCT user_name), NULL, NULL, NULL FROM ovr_ovrs
UNION ALL
SELECT 'Setores', COUNT(*), NULL, NULL, NULL FROM ovr_setores;


-- 2. FICHAS POR TIPO DE OPERAÇÃO — quantidade, datas inicial e final, fase e o que foi produzido em cada tipo
SELECT o.tipooperacao,
       CASE o.tipooperacao
            WHEN 0 THEN 'Mercadoria Abandonada (FMA)'
            WHEN 1 THEN 'Repressão - análise de risco na importação'
            WHEN 2 THEN 'Repressão - análise de risco na exportação'
            WHEN 3 THEN 'Pesquisa e seleção na importação'
            WHEN 4 THEN 'Pesquisa e seleção na exportação'
            WHEN 5 THEN 'Demanda externa'
            WHEN 6 THEN 'Operação de outros países'
            WHEN 7 THEN 'Vigilância'
            WHEN 8 THEN 'Operação de outros órgãos'
            ELSE '(não informado)' END AS tipo,
       COUNT(*) AS fichas,
       MIN(o.datahora) AS datahora_inicial, MAX(o.datahora) AS datahora_final,
       MIN(o.create_date) AS cadastro_inicial, MAX(o.create_date) AS cadastro_final,
       SUM(o.fase IN (0, 1, 2)) AS em_andamento, SUM(o.fase = 3) AS concluidas, SUM(o.fase = 4) AS arquivadas,
       SUM(r.rvfs IS NOT NULL) AS fichas_com_rvf, SUM(r.rvfs) AS rvfs, SUM(r.fotos) AS fotos,
       SUM(r.apreensoes) AS apreensoes, SUM(r.peso_apreendido) AS peso_apreendido_kg,
       SUM(t.tgs IS NOT NULL) AS fichas_com_tg, SUM(t.tgs) AS tgs, SUM(t.valor) AS valor_tg,
       COUNT(DISTINCT o.user_name) AS usuarios
  FROM ovr_ovrs o
  LEFT JOIN (SELECT v.ovr_id, COUNT(*) AS rvfs, SUM(f.fotos) AS fotos, SUM(a.apreensoes) AS apreensoes,
                    SUM(a.peso) AS peso_apreendido
               FROM ovr_verificacoesfisicas v
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS fotos FROM ovr_imagensrvf GROUP BY rvf_id) f
                      ON f.rvf_id = v.id
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS apreensoes, SUM(peso) AS peso
                            FROM ovr_apreensoes_rvf GROUP BY rvf_id) a
                      ON a.rvf_id = v.id
              GROUP BY v.ovr_id) r ON r.ovr_id = o.id
  LEFT JOIN (SELECT ovr_id, COUNT(*) AS tgs, SUM(valor) AS valor FROM ovr_tgovr GROUP BY ovr_id) t
         ON t.ovr_id = o.id
 GROUP BY 1, 2
 ORDER BY 1;


-- 3. FICHAS POR FASE e POR STATUS ATUAL (último tipo de evento)
SELECT o.fase,
       CASE o.fase WHEN 0 THEN 'Iniciada' WHEN 1 THEN 'Ativa' WHEN 2 THEN 'Suspensa'
                   WHEN 3 THEN 'Concluída' WHEN 4 THEN 'Arquivada' ELSE '(não informada)' END AS fase_nome,
       COUNT(*) AS fichas, MIN(o.datahora) AS datahora_inicial, MAX(o.datahora) AS datahora_final
  FROM ovr_ovrs o
 GROUP BY 1, 2
 ORDER BY 1;

SELECT COALESCE(te.nome, '(sem status)') AS status_atual, COUNT(*) AS fichas,
       MIN(o.datahora) AS datahora_inicial, MAX(o.datahora) AS datahora_final
  FROM ovr_ovrs o
  LEFT JOIN ovr_tiposevento te ON te.id = o.tipoevento_id
 GROUP BY 1
 ORDER BY 2 DESC;


-- 4. EVOLUÇÃO POR ANO — uma linha por ano, uma coluna por indicador
SELECT ano,
       SUM(CASE WHEN indicador = 'fichas' THEN n END) AS fichas,
       SUM(CASE WHEN indicador = 'fichas_fma' THEN n END) AS fichas_fma,
       SUM(CASE WHEN indicador = 'rvfs' THEN n END) AS rvfs,
       SUM(CASE WHEN indicador = 'fotos' THEN n END) AS fotos,
       SUM(CASE WHEN indicador = 'apreensoes' THEN n END) AS apreensoes,
       SUM(CASE WHEN indicador = 'apreensoes' THEN v END) AS peso_apreendido_kg,
       SUM(CASE WHEN indicador = 'tgs' THEN n END) AS tgs,
       SUM(CASE WHEN indicador = 'tgs' THEN v END) AS valor_tg,
       SUM(CASE WHEN indicador = 'resultados' THEN n END) AS resultados,
       SUM(CASE WHEN indicador = 'resultados' THEN v END) AS valor_resultados
  FROM (SELECT YEAR(COALESCE(datahora, create_date)) AS ano, 'fichas' AS indicador, COUNT(*) AS n, NULL AS v
          FROM ovr_ovrs GROUP BY 1
        UNION ALL
        SELECT YEAR(COALESCE(datahora, create_date)), 'fichas_fma', COUNT(*), NULL
          FROM ovr_ovrs WHERE tipooperacao = 0 GROUP BY 1
        UNION ALL
        SELECT YEAR(COALESCE(datahora, create_date)), 'rvfs', COUNT(*), NULL FROM ovr_verificacoesfisicas GROUP BY 1
        UNION ALL
        SELECT YEAR(create_date), 'fotos', COUNT(*), NULL FROM ovr_imagensrvf GROUP BY 1
        UNION ALL
        SELECT YEAR(create_date), 'apreensoes', COUNT(*), SUM(peso) FROM ovr_apreensoes_rvf GROUP BY 1
        UNION ALL
        SELECT YEAR(create_date), 'tgs', COUNT(*), SUM(valor) FROM ovr_tgovr GROUP BY 1
        UNION ALL
        SELECT YEAR(create_date), 'resultados', COUNT(*), SUM(valor) FROM ovr_resultados GROUP BY 1) x
 GROUP BY ano
 ORDER BY ano;


-- 5. APREENSÕES POR TIPO — quantidade, peso, RVFs e Fichas, datas pela RVF e pelo registro
SELECT COALESCE(t.descricao, '(sem tipo)') AS tipo_apreensao, COUNT(*) AS apreensoes,
       SUM(a.peso) AS peso_total_kg, COUNT(DISTINCT a.rvf_id) AS rvfs, COUNT(DISTINCT v.ovr_id) AS fichas,
       MIN(COALESCE(v.datahora, v.create_date)) AS primeira_rvf, MAX(COALESCE(v.datahora, v.create_date)) AS ultima_rvf,
       MIN(a.create_date) AS primeiro_registro, MAX(a.create_date) AS ultimo_registro
  FROM ovr_apreensoes_rvf a
  LEFT JOIN ovr_tiposapreensao t ON t.id = a.tipo_id
  LEFT JOIN ovr_verificacoesfisicas v ON v.id = a.rvf_id
 GROUP BY 1
 ORDER BY 2 DESC;


-- 6. RESULTADOS POR TIPO (apreensão, perdimento, crédito, multas...)
SELECT r.tipo_resultado,
       CASE r.tipo_resultado WHEN 1 THEN 'Apreensão' WHEN 2 THEN 'Perdimento' WHEN 3 THEN 'Crédito'
                             WHEN 4 THEN 'Sanção' WHEN 5 THEN 'DARF' WHEN 6 THEN 'Multa RFB'
                             WHEN 7 THEN 'Multa de outro órgão' ELSE '(não informado)' END AS tipo,
       COUNT(*) AS resultados, COUNT(DISTINCT r.ovr_id) AS fichas, SUM(r.valor) AS valor_total,
       MIN(r.create_date) AS primeiro, MAX(r.create_date) AS ultimo
  FROM ovr_resultados r
 GROUP BY 1, 2
 ORDER BY 1;


-- 7. TERMOS DE GUARDA POR TIPO DE MERCADORIA
SELECT COALESCE(m.nome, '(não informado)') AS tipo_mercadoria, COUNT(*) AS tgs,
       COUNT(DISTINCT tg.ovr_id) AS fichas, SUM(tg.valor) AS valor_total,
       MIN(tg.create_date) AS primeiro, MAX(tg.create_date) AS ultimo
  FROM ovr_tgovr tg
  LEFT JOIN ovr_tiposmercadoria m ON m.id = tg.tipomercadoria_id
 GROUP BY 1
 ORDER BY 4 DESC;


-- 8. POR SETOR — Fichas, datas e produção (RVF, fotos, apreensões, TG)
SELECT o.setor_id, COALESCE(s.nome, '(sem setor)') AS setor, COUNT(*) AS fichas,
       MIN(o.datahora) AS datahora_inicial, MAX(o.datahora) AS datahora_final,
       SUM(r.rvfs) AS rvfs, SUM(r.fotos) AS fotos, SUM(r.apreensoes) AS apreensoes,
       SUM(t.tgs) AS tgs, SUM(t.valor) AS valor_tg, COUNT(DISTINCT o.user_name) AS usuarios
  FROM ovr_ovrs o
  LEFT JOIN ovr_setores s ON s.id = o.setor_id
  LEFT JOIN (SELECT v.ovr_id, COUNT(*) AS rvfs, SUM(f.fotos) AS fotos, SUM(a.apreensoes) AS apreensoes
               FROM ovr_verificacoesfisicas v
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS fotos FROM ovr_imagensrvf GROUP BY rvf_id) f
                      ON f.rvf_id = v.id
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS apreensoes FROM ovr_apreensoes_rvf GROUP BY rvf_id) a
                      ON a.rvf_id = v.id
              GROUP BY v.ovr_id) r ON r.ovr_id = o.id
  LEFT JOIN (SELECT ovr_id, COUNT(*) AS tgs, SUM(valor) AS valor FROM ovr_tgovr GROUP BY ovr_id) t
         ON t.ovr_id = o.id
 GROUP BY 1, 2
 ORDER BY 3 DESC;


-- 9. POR RECINTO (os 30 com mais Fichas)
SELECT o.recinto_id, COALESCE(rc.nome, '(sem recinto)') AS recinto, COUNT(*) AS fichas,
       SUM(o.tipooperacao = 0) AS fichas_fma,
       MIN(o.datahora) AS datahora_inicial, MAX(o.datahora) AS datahora_final,
       SUM(r.rvfs) AS rvfs, SUM(r.fotos) AS fotos, SUM(r.apreensoes) AS apreensoes
  FROM ovr_ovrs o
  LEFT JOIN ovr_recintos rc ON rc.id = o.recinto_id
  LEFT JOIN (SELECT v.ovr_id, COUNT(*) AS rvfs, SUM(f.fotos) AS fotos, SUM(a.apreensoes) AS apreensoes
               FROM ovr_verificacoesfisicas v
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS fotos FROM ovr_imagensrvf GROUP BY rvf_id) f
                      ON f.rvf_id = v.id
               LEFT JOIN (SELECT rvf_id, COUNT(*) AS apreensoes FROM ovr_apreensoes_rvf GROUP BY rvf_id) a
                      ON a.rvf_id = v.id
              GROUP BY v.ovr_id) r ON r.ovr_id = o.id
 GROUP BY 1, 2
 ORDER BY 3 DESC
 LIMIT 30;


-- 10. QUALIDADE DAS DATAS — MIN/MAX são sensíveis a digitação: conferir antes de divulgar as datas inicial e final
SELECT o.tipooperacao, COUNT(*) AS fichas,
       SUM(o.datahora IS NULL) AS sem_datahora,
       SUM(o.datahora > CURRENT_TIMESTAMP) AS datahora_no_futuro,
       SUM(o.datahora < '2010-01-01') AS datahora_antes_de_2010
  FROM ovr_ovrs o
 GROUP BY 1
 ORDER BY 1;

(SELECT 'mais antigas' AS ponta, id, tipooperacao, datahora, create_date, user_name
   FROM ovr_ovrs WHERE datahora IS NOT NULL ORDER BY datahora LIMIT 5)
UNION ALL
(SELECT 'mais recentes', id, tipooperacao, datahora, create_date, user_name
   FROM ovr_ovrs WHERE datahora IS NOT NULL ORDER BY datahora DESC LIMIT 5);
