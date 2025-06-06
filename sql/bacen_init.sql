
CREATE SCHEMA IF NOT EXISTS bacen;

CREATE TABLE bacen.usuarios (
    id_usuario VARCHAR PRIMARY KEY,
    nome VARCHAR NOT NULL,
    cpf VARCHAR NOT NULL,
    data_cadastro TIMESTAMP NOT NULL
);

CREATE TABLE bacen.cartoes (
    id_cartao VARCHAR PRIMARY KEY,
    id_usuario VARCHAR NOT NULL,
    numero_cartao VARCHAR NOT NULL,
    data_validade DATE NOT NULL,
    status_cartao VARCHAR NOT NULL,
    CONSTRAINT fk_usuario_cartao FOREIGN KEY (id_usuario)
        REFERENCES bacen.usuarios (id_usuario) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS bacen.instituicoes_financeiras (
    id_instituicao VARCHAR(255) PRIMARY KEY,
    nome_instituicao VARCHAR(255) NOT NULL,
    codigo_banco VARCHAR(10) NOT NULL UNIQUE,
    data_cadastro TIMESTAMP NOT NULL
);


CREATE TABLE IF NOT EXISTS bacen.transacoes_reportadas (
    id_transacao VARCHAR(255) PRIMARY KEY,
    id_instituicao VARCHAR(255) NOT NULL,
    valor DECIMAL NOT NULL,
    data_transacao TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    CONSTRAINT fk_instituicao FOREIGN KEY (id_instituicao) 
        REFERENCES bacen.instituicoes_financeiras(id_instituicao) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS bacen.bancos (
    id_banco VARCHAR(255) PRIMARY KEY,
    nome_banco VARCHAR(255) NOT NULL,
    codigo_banco VARCHAR(10) NOT NULL UNIQUE,
    data_cadastro TIMESTAMP NOT NULL
);


CREATE TABLE IF NOT EXISTS bacen.transacoes (
    id_transacao VARCHAR(255) PRIMARY KEY,
    id_instituicao VARCHAR(255) NOT NULL,
    valor DECIMAL NOT NULL,
    data_transacao TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL,
    CONSTRAINT fk_banco FOREIGN KEY (id_instituicao) 
        REFERENCES bacen.bancos(id_banco) ON DELETE CASCADE
);


TRUNCATE TABLE bacen.instituicoes_financeiras CASCADE;
TRUNCATE TABLE bacen.bancos CASCADE;
TRUNCATE TABLE bacen.transacoes_reportadas CASCADE;
TRUNCATE TABLE bacen.transacoes CASCADE;


TRUNCATE TABLE bacen.usuarios CASCADE;
INSERT INTO bacen.usuarios (
    id_usuario, nome, cpf, data_cadastro
)
SELECT
    'usuario_' || gen.id,
    'Nome_' || gen.id,
    '123.456.789-00',
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);

TRUNCATE TABLE bacen.cartoes CASCADE;
INSERT INTO bacen.cartoes (
    id_cartao, id_usuario, numero_cartao, data_validade, status_cartao
)
SELECT
    'cartao_' || gen.id,
    'usuario_' || gen.id,
    '**** **** **** ' || lpad((gen.id % 10000)::text, 4, '0'),
    CURRENT_DATE + (gen.id || ' days')::interval,
    CASE WHEN random() > 0.5 THEN 'ativo' ELSE 'bloqueado' END
FROM generate_series(1, 1000) AS gen(id);


INSERT INTO bacen.instituicoes_financeiras (
    id_instituicao, nome_instituicao, codigo_banco, data_cadastro
)
SELECT
    'inst_' || gen.id,
    'Instituição ' || gen.id,
    'BC' || lpad((gen.id % 1000)::text, 3, '0'),
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);


INSERT INTO bacen.bancos (
    id_banco, nome_banco, codigo_banco, data_cadastro
)
SELECT
    'banco_' || gen.id,
    'Banco ' || gen.id,
    'BN' || lpad((gen.id % 1000)::text, 3, '0'),
    NOW() - (random() * (interval '365 days'))
FROM generate_series(1, 1000) AS gen(id);


INSERT INTO bacen.transacoes_reportadas (
    id_transacao, id_instituicao, valor, data_transacao, status
)
SELECT
    'trans_rep_' || gen.id || '_' || trunc(random() * 100000)::text,
    (SELECT id_instituicao FROM bacen.instituicoes_financeiras ORDER BY random() LIMIT 1),
    ROUND((random() * 10000)::numeric, 2),
    NOW() - (random() * (interval '365 days')),
    CASE 
        WHEN random() < 0.5 THEN 'aprovada' 
        WHEN random() < 0.8 THEN 'pendente' 
        ELSE 'rejeitada' 
    END
FROM generate_series(1, 1000) AS gen(id);


INSERT INTO bacen.transacoes (
    id_transacao, id_instituicao, valor, data_transacao, status
)
SELECT
    'trans_' || gen.id || '_' || trunc(random() * 100000)::text,
    (SELECT id_banco FROM bacen.bancos ORDER BY random() LIMIT 1),
    ROUND((random() * 10000)::numeric, 2),
    NOW() - (random() * (interval '365 days')),
    CASE 
        WHEN random() < 0.5 THEN 'aprovada' 
        WHEN random() < 0.8 THEN 'pendente' 
        ELSE 'rejeitada' 
    END
FROM generate_series(1, 1000) AS gen(id);


CREATE ROLE api_bacen WITH LOGIN PASSWORD 'senha_bacen';


GRANT USAGE ON SCHEMA bacen TO api_bacen;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bacen TO api_bacen;