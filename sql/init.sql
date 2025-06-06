
CREATE SCHEMA IF NOT EXISTS antifraude;
CREATE SCHEMA IF NOT EXISTS autenticacao;
CREATE SCHEMA IF NOT EXISTS data_lake;
CREATE SCHEMA IF NOT EXISTS liquidacoes;
CREATE SCHEMA IF NOT EXISTS tokenizacao;


CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA antifraude;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA autenticacao;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA data_lake;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA liquidacoes;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA tokenizacao;


CREATE TABLE antifraude.transacoes (
    id_transacao VARCHAR PRIMARY KEY,
    id_cartao VARCHAR NOT NULL,
    id_usuario VARCHAR NOT NULL,
    valor DECIMAL NOT NULL,
    data_transacao TIMESTAMP NOT NULL,
    local_transacao VARCHAR NOT NULL,
    status_transacao VARCHAR NOT NULL
);

CREATE TABLE antifraude.analise_fraude (
    id_analise VARCHAR PRIMARY KEY,
    id_transacao VARCHAR NOT NULL,
    score_fraude FLOAT NOT NULL,
    resultado_analise VARCHAR NOT NULL,
    data_analise TIMESTAMP NOT NULL,
    CONSTRAINT fk_transacao_analise FOREIGN KEY (id_transacao)
        REFERENCES antifraude.transacoes (id_transacao) ON DELETE CASCADE
);

CREATE TABLE antifraude.padroes_suspeitos (
    id_padrao VARCHAR PRIMARY KEY,
    id_transacao VARCHAR NOT NULL,
    tipo_padrao VARCHAR NOT NULL,
    detalhes TEXT NOT NULL,
    CONSTRAINT fk_transacao_padrao FOREIGN KEY (id_transacao)
        REFERENCES antifraude.transacoes (id_transacao) ON DELETE CASCADE
);

CREATE TABLE antifraude.regras_ml (
    id_regra VARCHAR PRIMARY KEY,
    nome_regra VARCHAR NOT NULL,
    parametros TEXT NOT NULL,
    data_criacao TIMESTAMP NOT NULL
);

CREATE TABLE antifraude.historico_fraudes (
    id_fraude VARCHAR PRIMARY KEY,
    id_transacao VARCHAR NOT NULL,
    id_usuario VARCHAR NOT NULL,
    data_fraude TIMESTAMP NOT NULL,
    detalhes_fraude TEXT NOT NULL,
    CONSTRAINT fk_transacao_fraude FOREIGN KEY (id_transacao)
        REFERENCES antifraude.transacoes (id_transacao) ON DELETE CASCADE
);


CREATE TABLE autenticacao.usuarios (
    id_usuario VARCHAR PRIMARY KEY,
    nome VARCHAR NOT NULL,
    cpf VARCHAR NOT NULL,
    data_cadastro TIMESTAMP NOT NULL
);

CREATE TABLE autenticacao.cartoes (
    id_cartao VARCHAR PRIMARY KEY,
    id_usuario VARCHAR NOT NULL,
    numero_cartao VARCHAR NOT NULL,
    data_validade DATE NOT NULL,
    status_cartao VARCHAR NOT NULL,
    CONSTRAINT fk_usuario_cartao FOREIGN KEY (id_usuario)
        REFERENCES autenticacao.usuarios (id_usuario) ON DELETE CASCADE
);

CREATE TABLE autenticacao.limites (
    id_limite VARCHAR PRIMARY KEY,
    id_cartao VARCHAR NOT NULL,
    limite_total DECIMAL NOT NULL,
    limite_disponivel DECIMAL NOT NULL,
    data_atualizacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_cartao_limite FOREIGN KEY (id_cartao)
        REFERENCES autenticacao.cartoes (id_cartao) ON DELETE CASCADE
);

CREATE TABLE autenticacao.autorizacoes (
    id_autorizacao VARCHAR PRIMARY KEY,
    id_transacao VARCHAR UNIQUE NOT NULL,
    id_cartao VARCHAR NOT NULL,
    valor DECIMAL NOT NULL,
    status_autorizacao VARCHAR NOT NULL,
    data_autorizacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_cartao_autorizacao FOREIGN KEY (id_cartao)
        REFERENCES autenticacao.cartoes(id_cartao) ON DELETE CASCADE
);

CREATE TABLE autenticacao.negacoes (
    id_negacao VARCHAR PRIMARY KEY,
    id_transacao VARCHAR NOT NULL,
    motivo VARCHAR NOT NULL,
    data_negacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_transacao_negacao FOREIGN KEY (id_transacao)
        REFERENCES autenticacao.autorizacoes(id_transacao) ON DELETE CASCADE
);

CREATE TABLE autenticacao.regras (
    id_regra VARCHAR PRIMARY KEY,
    nome_regra VARCHAR NOT NULL,
    condicao TEXT NOT NULL,
    acao VARCHAR NOT NULL
);


CREATE TABLE liquidacoes.lotes (
    id_lote VARCHAR PRIMARY KEY,
    data_criacao TIMESTAMP NOT NULL,
    quantidade_transacoes INT NOT NULL,
    valor_total_lote DECIMAL NOT NULL
);

CREATE TABLE liquidacoes.liquidacoes (
    id_liquidacao VARCHAR PRIMARY KEY,
    id_lote VARCHAR NOT NULL,
    valor_total DECIMAL NOT NULL,
    data_liquidacao TIMESTAMP NOT NULL,
    status_liquidacao VARCHAR NOT NULL,
    CONSTRAINT fk_lote_liquidacao FOREIGN KEY (id_lote)
        REFERENCES liquidacoes.lotes (id_lote) ON DELETE CASCADE
);

CREATE TABLE liquidacoes.transacoes_lote (
    id_transacao_lote VARCHAR PRIMARY KEY,
    id_lote VARCHAR NOT NULL,
    id_transacao VARCHAR NOT NULL,
    valor_transacao DECIMAL NOT NULL,
    CONSTRAINT fk_lote_transacao FOREIGN KEY (id_lote)
        REFERENCES liquidacoes.lotes (id_lote) ON DELETE CASCADE
);

CREATE TABLE liquidacoes.compensacoes (
    id_compensacao VARCHAR PRIMARY KEY,
    id_liquidacao VARCHAR NOT NULL,
    valor_compensado DECIMAL NOT NULL,
    data_compensacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_liquidacao_compensacao FOREIGN KEY (id_liquidacao)
        REFERENCES liquidacoes.liquidacoes (id_liquidacao) ON DELETE CASCADE
);

CREATE TABLE liquidacoes.conciliacoes (
    id_conciliacao VARCHAR PRIMARY KEY,
    id_liquidacao VARCHAR NOT NULL,
    status_conciliacao VARCHAR NOT NULL,
    data_conciliacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_liquidacao_conciliacao FOREIGN KEY (id_liquidacao)
        REFERENCES liquidacoes.liquidacoes (id_liquidacao) ON DELETE CASCADE
);

CREATE TABLE liquidacoes.ajustes (
    id_ajuste VARCHAR PRIMARY KEY,
    id_liquidacao VARCHAR NOT NULL,
    valor_ajuste DECIMAL NOT NULL,
    motivo VARCHAR NOT NULL,
    data_ajuste TIMESTAMP NOT NULL,
    CONSTRAINT fk_liquidacao_ajuste FOREIGN KEY (id_liquidacao)
        REFERENCES liquidacoes.liquidacoes (id_liquidacao) ON DELETE CASCADE
);


CREATE TABLE tokenizacao.tokens (
    id_token VARCHAR PRIMARY KEY,
    id_cartao VARCHAR NOT NULL,
    valor_token VARCHAR NOT NULL,
    data_criacao TIMESTAMP NOT NULL,
    data_expiracao TIMESTAMP NOT NULL,
    status_token VARCHAR NOT NULL
);

CREATE TABLE tokenizacao.tokens_temporarios (
    id_token_temp VARCHAR PRIMARY KEY,
    id_cartao VARCHAR NOT NULL,
    valor_token_temp VARCHAR NOT NULL,
    data_criacao TIMESTAMP NOT NULL,
    data_expiracao TIMESTAMP NOT NULL
);

CREATE TABLE tokenizacao.manutencao_tokens (
    id_manutencao VARCHAR PRIMARY KEY,
    id_token VARCHAR NOT NULL,
    acao VARCHAR NOT NULL,
    data_manutencao TIMESTAMP NOT NULL,
    CONSTRAINT fk_token_manutencao FOREIGN KEY (id_token)
        REFERENCES tokenizacao.tokens (id_token) ON DELETE CASCADE
);

CREATE TABLE tokenizacao.chaves_criptograficas (
    id_chave VARCHAR PRIMARY KEY,
    valor_chave VARCHAR NOT NULL,
    data_criacao TIMESTAMP NOT NULL,
    data_expiracao TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.perfil_usuario (
    id_perfil VARCHAR PRIMARY KEY,
    id_usuario VARCHAR NOT NULL,
    comportamento VARCHAR NOT NULL,
    data_atualizacao TIMESTAMP NOT NULL,
    CONSTRAINT fk_usuario FOREIGN KEY (id_usuario) REFERENCES autenticacao.usuarios (id_usuario)
);

CREATE TABLE IF NOT EXISTS data_lake.eventos_sistema (
    id_evento VARCHAR PRIMARY KEY,
    tipo_evento VARCHAR NOT NULL,
    data_evento TIMESTAMP NOT NULL,
    detalhes_evento TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.logs_api (
    id_log VARCHAR PRIMARY KEY,
    endpoint VARCHAR NOT NULL,
    metodo VARCHAR NOT NULL,
    codigo_resposta INTEGER NOT NULL,
    data_log TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.metricas_desempenho (
    id_metrica VARCHAR PRIMARY KEY,
    nome_metrica VARCHAR NOT NULL,
    valor_metrica DECIMAL NOT NULL,
    data_metrica TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.consolidados (
    id_consolidado VARCHAR PRIMARY KEY,
    data_arquivo DATE NOT NULL,
    total_transacoes INTEGER NOT NULL,
    valor_total_transacoes DECIMAL NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.backup_sistema (
    id_backup VARCHAR PRIMARY KEY,
    data_backup DATE NOT NULL,
    nome_arquivo VARCHAR NOT NULL,
    tipo_banco VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS data_lake.logs_completos (
    id_log VARCHAR PRIMARY KEY DEFAULT gen_random_uuid(),
    data_log DATE NOT NULL,
    log JSONB NOT NULL
);


TRUNCATE TABLE antifraude.transacoes CASCADE;
INSERT INTO antifraude.transacoes (
    id_transacao, id_cartao, id_usuario, valor, data_transacao, local_transacao, status_transacao
)
SELECT
    'trans_' || gen.id || '_' || trunc(random() * 100000)::text,
    'cartao_' || gen.id,
    'usuario_' || gen.id,
    ROUND((random() * 100)::numeric, 2),
    NOW() - (random() * (interval '30 days')),
    CASE WHEN random() > 0.5 THEN 'São Paulo' ELSE 'Rio de Janeiro' END,
    CASE WHEN random() > 0.7 THEN 'rejeitada' ELSE 'aprovada' END
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE antifraude.analise_fraude CASCADE;
INSERT INTO antifraude.analise_fraude (
    id_analise, id_transacao, score_fraude, resultado_analise, data_analise
)
SELECT
    gen_random_uuid()::text,
    t.id_transacao,
    ROUND((random() * 100)::numeric, 2),
    CASE WHEN random() > 0.7 THEN 'suspeita' ELSE 'segura' END,
    NOW() - (random() * (interval '15 days'))
FROM (
    SELECT id_transacao
    FROM antifraude.transacoes
    ORDER BY random()
    LIMIT 1000
) AS t;

TRUNCATE TABLE antifraude.padroes_suspeitos CASCADE;
INSERT INTO antifraude.padroes_suspeitos (
    id_padrao, id_transacao, tipo_padrao, detalhes
)
SELECT
    gen_random_uuid()::text,
    t.id_transacao,
    CASE 
        WHEN random() < 0.5 THEN 'local incomum' 
        ELSE 'valor fora do padrão' 
    END,
    'Detectado comportamento suspeito na transação.'
FROM (
    SELECT id_transacao
    FROM antifraude.transacoes
    ORDER BY random()
    LIMIT 1000
) AS t;

TRUNCATE TABLE antifraude.historico_fraudes CASCADE;
INSERT INTO antifraude.historico_fraudes (
    id_fraude, id_transacao, id_usuario, data_fraude, detalhes_fraude
)
SELECT
    gen_random_uuid()::text,
    t.id_transacao,
    t.id_usuario,
    NOW() - (random() * (interval '90 days')),
    'Fraude detectada e confirmada por sistema automatizado.'
FROM (
    SELECT id_transacao, id_usuario
    FROM antifraude.transacoes
    ORDER BY random()
    LIMIT 1000
) AS t;

TRUNCATE TABLE antifraude.regras_ml CASCADE;
INSERT INTO antifraude.regras_ml (
    id_regra, nome_regra, parametros, data_criacao
)
SELECT
    gen_random_uuid()::text,
    'Regra_' || gen.id,
    '{"limite_valor": 500, "limite_tentativas": 3}',
    NOW() - (random() * (interval '60 days'))
FROM generate_series(1, 1000) AS gen(id);


TRUNCATE TABLE autenticacao.usuarios CASCADE;
INSERT INTO autenticacao.usuarios (
    id_usuario, nome, cpf, data_cadastro
)
SELECT
    'usuario_' || gen.id,
    'Nome_' || gen.id,
    '123.456.789-00',
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE autenticacao.cartoes CASCADE;
INSERT INTO autenticacao.cartoes (
    id_cartao, id_usuario, numero_cartao, data_validade, status_cartao
)
SELECT
    'cartao_' || gen.id,
    'usuario_' || gen.id,
    '**** **** **** ' || lpad((gen.id % 10000)::text, 4, '0'),
    CURRENT_DATE + (gen.id || ' days')::interval,
    CASE WHEN random() > 0.5 THEN 'ativo' ELSE 'bloqueado' END
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE autenticacao.limites CASCADE;
INSERT INTO autenticacao.limites (
    id_limite, id_cartao, limite_total, limite_disponivel, data_atualizacao
)
SELECT
    'limite_' || gen.id,
    'cartao_' || gen.id,
    ROUND((random() * 10000)::numeric, 2),
    ROUND((random() * 5000)::numeric, 2),
    NOW() - (random() * interval '30 days')
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE autenticacao.autorizacoes CASCADE;
INSERT INTO autenticacao.autorizacoes (
    id_autorizacao, id_transacao, id_cartao, valor, status_autorizacao, data_autorizacao
)
SELECT
    'autorizacao_' || gen.id,
    'transacao_' || gen.id,
    'cartao_' || ((random() * 999)::int + 1),
    ROUND((random() * 5000)::numeric, 2),
    CASE WHEN random() > 0.5 THEN 'autorizada' ELSE 'negada' END,
    NOW() - (random() * interval '30 days')
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE autenticacao.negacoes CASCADE;
INSERT INTO autenticacao.negacoes (
    id_negacao, id_transacao, motivo, data_negacao
)
SELECT
    'negacao_' || ROW_NUMBER() OVER (),
    a.id_transacao,
    CASE WHEN random() > 0.5 THEN 'limite excedido' ELSE 'suspeita de fraude' END,
    NOW() - (random() * interval '15 days')
FROM autenticacao.autorizacoes a
WHERE a.status_autorizacao = 'negada'
LIMIT 200;

TRUNCATE TABLE autenticacao.regras CASCADE;
INSERT INTO autenticacao.regras (
    id_regra, nome_regra, condicao, acao
)
SELECT
    'regra_' || gen.id,
    'Regra_' || gen.id,
    'valor > 5000',
    CASE
        WHEN random() > 0.5 THEN 'negar'
        ELSE 'revisar'
    END
FROM generate_series(1, 1000) AS gen(id);


TRUNCATE TABLE liquidacoes.lotes CASCADE;
INSERT INTO liquidacoes.lotes (
    id_lote, data_criacao, quantidade_transacoes, valor_total_lote
)
SELECT
    'lote_' || gen.id,
    NOW() - (random() * (interval '365 days')),
    (random() * 100)::int,
    (random() * 10000)
FROM generate_series(1, 1000) AS gen(id);


TRUNCATE TABLE liquidacoes.liquidacoes CASCADE;
INSERT INTO liquidacoes.liquidacoes (
    id_liquidacao, id_lote, valor_total, data_liquidacao, status_liquidacao
)
SELECT
    'liquidacao_' || gen.id,
    'lote_' || ((random() * 999)::int + 1),
    (random() * 10000),
    NOW() - (random() * (interval '365 days')),
    CASE WHEN random() > 0.5 THEN 'pendente' ELSE 'concluída' END
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE liquidacoes.transacoes_lote CASCADE;
INSERT INTO liquidacoes.transacoes_lote (
    id_transacao_lote, id_lote, id_transacao, valor_transacao
)
SELECT
    'transacao_lote_' || gen.id,
    'lote_' || ((random() * 999)::int + 1),
    'transacao_' || gen.id,
    (random() * 500)
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE liquidacoes.compensacoes CASCADE;
INSERT INTO liquidacoes.compensacoes (
    id_compensacao, id_liquidacao, valor_compensado, data_compensacao
)
SELECT
    'compensacao_' || gen.id,
    'liquidacao_' || ((random() * 999)::int + 1),
    (random() * 5000),
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE liquidacoes.conciliacoes CASCADE;
INSERT INTO liquidacoes.conciliacoes (
    id_conciliacao, id_liquidacao, status_conciliacao, data_conciliacao
)
SELECT
    'conciliacao_' || gen.id,
    'liquidacao_' || ((random() * 999)::int + 1),
    CASE WHEN random() > 0.5 THEN 'conciliada' ELSE 'pendente' END,
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE liquidacoes.ajustes CASCADE;
INSERT INTO liquidacoes.ajustes (
    id_ajuste, id_liquidacao, valor_ajuste, motivo, data_ajuste
)
SELECT
    'ajuste_' || gen.id,
    'liquidacao_' || ((random() * 999)::int + 1),
    (random() * 1000),
    CASE
        WHEN random() > 0.5 THEN 'erro de cálculo'
        ELSE 'ajuste manual'
    END,
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);


TRUNCATE TABLE tokenizacao.tokens CASCADE;
INSERT INTO tokenizacao.tokens (
    id_token, id_cartao, valor_token, data_criacao, data_expiracao, status_token
)
SELECT
    'token_' || gen.id || '_' || trunc(random() * 100000)::text,
    'cartao_' || gen.id,
    'valorToken_' || trunc(random() * 100000)::text,
    NOW() - (random() * (interval '365 days')),
    NOW() + (random() * (interval '30 days')),
    CASE WHEN random() > 0.5 THEN 'ativo' ELSE 'expirado' END
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE tokenizacao.tokens_temporarios CASCADE;
INSERT INTO tokenizacao.tokens_temporarios (
    id_token_temp, id_cartao, valor_token_temp, data_criacao, data_expiracao
)
SELECT
    'tokentemp_' || gen.id || '_' || trunc(random() * 100000)::text,
    'cartao_' || gen.id,
    'valorTemp_' || trunc(random() * 100000)::text,
    NOW() - (random() * (interval '30 days')),
    NOW() + (random() * (interval '1 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE tokenizacao.chaves_criptograficas CASCADE;
INSERT INTO tokenizacao.chaves_criptograficas (
    id_chave, valor_chave, data_criacao, data_expiracao
)
SELECT
    'chave_' || gen.id || '_' || trunc(random() * 100000)::text,
    'valorChave_' || trunc(random() * 100000)::text,
    NOW() - (random() * (interval '365 days')),
    NOW() + (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE tokenizacao.manutencao_tokens CASCADE;
INSERT INTO tokenizacao.manutencao_tokens (
    id_manutencao, id_token, acao, data_manutencao
)
SELECT
    gen_random_uuid()::text,
    tokens.id_token,
    CASE
        WHEN random() < 0.33 THEN 'renovacao'
        WHEN random() < 0.66 THEN 'revogacao'
        ELSE 'revalidacao'
    END,
    NOW() - (random() * (interval '90 days'))
FROM (
    SELECT id_token FROM tokenizacao.tokens ORDER BY random() LIMIT 1000
) AS tokens
JOIN generate_series(1, 1000) AS gen(id) ON true;


TRUNCATE TABLE data_lake.perfil_usuario CASCADE;
INSERT INTO data_lake.perfil_usuario (
    id_perfil, id_usuario, comportamento, data_atualizacao
)
SELECT
    'perfil_' || gen.id,
    'usuario_' || gen.id, 
    CASE (random() * 3)::int
        WHEN 0 THEN 'ativo'
        WHEN 1 THEN 'inativo'
        WHEN 2 THEN 'suspenso'
        ELSE 'novo'
    END,
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.eventos_sistema CASCADE;
INSERT INTO data_lake.eventos_sistema (
    id_evento, tipo_evento, data_evento, detalhes_evento
)
SELECT
    'evento_' || gen.id,
    CASE (random() * 4)::int
        WHEN 0 THEN 'login_sucesso'
        WHEN 1 THEN 'tentativa_login_falha'
        WHEN 2 THEN 'item_adicionado_carrinho'
        WHEN 3 THEN 'compra_finalizada'
        ELSE 'erro_inesperado_sistema'
    END,
    NOW() - (random() * (interval '365 days')),
    'Detalhes do evento número ' || gen.id || '. Ocorreu uma ação: ' || md5(random()::text)
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.logs_api CASCADE;
INSERT INTO data_lake.logs_api (
    id_log, endpoint, metodo, codigo_resposta, data_log
)
SELECT
    'apilog_' || gen.id,
    CASE (random() * 3)::int
        WHEN 0 THEN '/api/v1/users/' || (random()*100)::int
        WHEN 1 THEN '/api/v1/products/' || (random()*500)::int
        WHEN 2 THEN '/api/v1/orders'
        ELSE '/api/v1/status'
    END,
    CASE (random() * 3)::int
        WHEN 0 THEN 'GET'
        WHEN 1 THEN 'POST'
        WHEN 2 THEN 'PUT'
        ELSE 'DELETE'
    END,
    CASE (random() * 4)::int
        WHEN 0 THEN 200
        WHEN 1 THEN 201
        WHEN 2 THEN 400
        WHEN 3 THEN 404
        ELSE 500
    END,
    NOW() - (random() * (interval '730 days')) 
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.metricas_desempenho CASCADE;
INSERT INTO data_lake.metricas_desempenho (
    id_metrica, nome_metrica, valor_metrica, data_metrica
)
SELECT
    'metrica_' || gen.id,
    CASE (random() * 3)::int
        WHEN 0 THEN 'cpu_utilization_percent'
        WHEN 1 THEN 'memory_usage_mb'
        WHEN 2 THEN 'avg_response_time_ms'
        ELSE 'disk_io_ops_sec'
    END,
    (random() * 1000)::decimal(10,2),
    NOW() - (random() * (interval '90 days')) 
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.consolidados CASCADE;
INSERT INTO data_lake.consolidados (
    id_consolidado, data_arquivo, total_transacoes, valor_total_transacoes
)
SELECT
    'consolidado_' || gen.id,
    (NOW() - (random() * (interval '365 days')))::date,
    (random() * 5000)::int + 100,
    (random() * 1000000)::decimal(18,2) + 5000
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.backup_sistema CASCADE;
INSERT INTO data_lake.backup_sistema (
    id_backup, data_backup, nome_arquivo, tipo_banco
)
SELECT
    'backup_' || gen.id,
    (NOW() - (random() * (interval '180 days')))::date,
    'backup_db_' || to_char((NOW() - (random() * (interval '180 days')))::date, 'YYYYMMDD') || '_' || gen.id || '.bak',
    CASE (random() * 2)::int
        WHEN 0 THEN 'PostgreSQL'
        WHEN 1 THEN 'MySQL'
        ELSE 'SQLServer'
    END
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE data_lake.logs_completos CASCADE;
INSERT INTO data_lake.logs_completos (
  
    data_log, log
)
SELECT
    (NOW() - (random() * (interval '30 days')))::date, 
    jsonb_build_object(
        'timestamp', NOW() - (random() * (interval '30 days')),
        'level', CASE (random() * 2)::int WHEN 0 THEN 'INFO' WHEN 1 THEN 'ERROR' ELSE 'WARNING' END,
        'service', 'service_' || (random() * 5)::int,
        'message', 'Log message content for entry ' || gen.id || ': ' || md5(random()::text),
        'details', jsonb_build_object(
                        'ip_address', ((random()*254)+1)::text || '.' || ((random()*254)+1)::text || '.' || ((random()*254)+1)::text || '.' || ((random()*254)+1)::text,
                        'user_agent', 'Agent/' || (random()*10)::int || '.0 (' || md5(random()::text) || ')',
                        'request_id', gen_random_uuid()
                   )
    )
FROM generate_series(1, 1000) AS gen(id);


CREATE ROLE api_antifraude WITH LOGIN PASSWORD '1234';
CREATE ROLE api_autenticacao WITH LOGIN PASSWORD '1234';
CREATE ROLE api_liquidacoes WITH LOGIN PASSWORD '1234';
CREATE ROLE api_tokenizacao WITH LOGIN PASSWORD '1234';
CREATE ROLE api_data_lake WITH LOGIN PASSWORD '1234';

GRANT USAGE ON SCHEMA antifraude TO api_antifraude;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA antifraude TO api_antifraude;

GRANT USAGE ON SCHEMA autenticacao TO api_autenticacao;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA autenticacao TO api_autenticacao;

GRANT USAGE ON SCHEMA liquidacoes TO api_liquidacoes;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA liquidacoes TO api_liquidacoes;

GRANT USAGE ON SCHEMA tokenizacao TO api_tokenizacao;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tokenizacao TO api_tokenizacao;

GRANT USAGE ON SCHEMA data_lake TO api_data_lake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA data_lake TO api_data_lake;

GRANT USAGE ON SCHEMA antifraude TO api_data_lake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA antifraude TO api_data_lake;

GRANT USAGE ON SCHEMA autenticacao TO api_data_lake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA autenticacao TO api_data_lake;

GRANT USAGE ON SCHEMA liquidacoes TO api_data_lake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA liquidacoes TO api_data_lake;

GRANT USAGE ON SCHEMA tokenizacao TO api_data_lake;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA tokenizacao TO api_data_lake;