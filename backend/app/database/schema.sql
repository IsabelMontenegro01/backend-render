-- 1. Drone
CREATE TABLE drone (
  id SERIAL PRIMARY KEY,
  numero_serie VARCHAR UNIQUE NOT NULL,
  nome VARCHAR NOT NULL,
  modelo VARCHAR DEFAULT 'DJI Tello',
  status VARCHAR DEFAULT 'ativo'
);

-- 2. Voo
CREATE TABLE voo (
  id SERIAL PRIMARY KEY,
  id_drone INT REFERENCES drone(id),
  timestamp_inicio TIMESTAMPTZ DEFAULT now(),
  timestamp_fim TIMESTAMPTZ,
  area_monitorada VARCHAR,
  status_voo VARCHAR DEFAULT 'em_andamento',
  tempo_total_motores INT
);

-- 3. Telemetria
CREATE TABLE telemetria (
  id SERIAL PRIMARY KEY,
  id_voo INT REFERENCES voo(id),
  timestamp TIMESTAMPTZ DEFAULT now(),
  pitch FLOAT, roll FLOAT, yaw FLOAT,
  velocidade_x FLOAT, velocidade_y FLOAT, velocidade_z FLOAT,
  altura INT, altura_tof INT, barometro FLOAT,
  bateria INT,
  temperatura_min INT, temperatura_max INT,
  aceleracao_x FLOAT, aceleracao_y FLOAT, aceleracao_z FLOAT,
  latitude DECIMAL(10,7),
  longitude DECIMAL(10,7),
  precisao_gps_m FLOAT,
  fonte_localizacao VARCHAR DEFAULT 'vgps'
);

-- 4. Deteccao
CREATE TABLE deteccao (
  id SERIAL PRIMARY KEY,
  id_voo INT REFERENCES voo(id),
  id_telemetria INT REFERENCES telemetria(id),
  timestamp TIMESTAMPTZ DEFAULT now(),
  id_veiculo CHAR(64),
  imagem_path VARCHAR,
  placa_lida VARCHAR,
  confianca_ocr FLOAT,
  modelo_veiculo VARCHAR,
  ano_veiculo INT,
  marca_veiculo VARCHAR
);

-- 5. ConsultaPier
CREATE TABLE consulta_pier (
  id SERIAL PRIMARY KEY,
  id_deteccao INT REFERENCES deteccao(id),
  placa_consultada VARCHAR,
  timestamp_consulta TIMESTAMPTZ DEFAULT now(),
  resultado VARCHAR,  -- 'achado' ou 'nao_achado'
  resposta_raw JSONB  -- resposta completa da Pier API
);

-- 6. Alerta
CREATE TABLE alerta (
  id SERIAL PRIMARY KEY,
  id_consulta INT REFERENCES consulta_pier(id),
  timestamp TIMESTAMPTZ DEFAULT now(),
  status_alerta VARCHAR DEFAULT 'pendente',
  operador_notificado VARCHAR
);
