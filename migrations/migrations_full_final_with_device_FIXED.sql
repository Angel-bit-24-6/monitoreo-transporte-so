-- migrations_full_final_with_device.sql
-- Migraciones completas para sistema de Monitoreo de Transporte (Postgres + PostGIS)
-- Versión CORREGIDA con fixes críticos
-- Fecha: 2025-10
-- Requisitos: PostgreSQL 12+ (recomendado 14+), PostGIS, pgcrypto

-- ============================================================================
-- 000_extensions.sql
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 001_types.sql
-- ============================================================================
-- Tipo de evento
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'evento_tipo') THEN
    CREATE TYPE evento_tipo AS ENUM (
      'OUT_OF_BOUND',      -- Fuera de ruta
      'STOP_LONG',         -- Detención prolongada
      'SPEEDING',          -- Exceso de velocidad
      'GENERAL_ALERT',     -- Alerta general
      'INFO'               -- Información
    );
  END IF;
END
$$;

-- ============================================================================
-- 002_schema_core.sql
-- Tablas principales (fiel al esquema robusto original)
-- ============================================================================
-- Unidades (vehículos)
CREATE TABLE IF NOT EXISTS unidad (
  id TEXT PRIMARY KEY,
  placa TEXT,
  chofer TEXT,
  activo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- -----------------------------
-- unidad_token: diseño seguro y extensible
-- - id BIGSERIAL PK (permite multiples tokens por unidad)
-- - device_id TEXT (opcional): vincula token a un dispositivo específico
-- - token_hash BYTEA: almacena digest SHA-256 del token (NO se guarda token en claro)
-- - expires_at, last_used, revoked: control y rotación
-- -----------------------------
CREATE TABLE IF NOT EXISTS unidad_token (
  id BIGSERIAL PRIMARY KEY,
  unidad_id TEXT NOT NULL REFERENCES unidad(id) ON DELETE CASCADE,
  device_id TEXT NULL,                 -- identificador del dispositivo (ej: IMEI, HWID, "GPS-01")
  token_hash BYTEA NOT NULL,           -- SHA-256 digest del token (BYTEA)
  created_at TIMESTAMPTZ DEFAULT now(),
  expires_at TIMESTAMPTZ NULL,
  last_used TIMESTAMPTZ NULL,
  revoked BOOLEAN DEFAULT FALSE
);

-- índices útiles
CREATE UNIQUE INDEX IF NOT EXISTS ux_unidad_token_token_hash ON unidad_token (token_hash);
CREATE INDEX IF NOT EXISTS idx_unidad_token_unidad_id ON unidad_token (unidad_id);
CREATE INDEX IF NOT EXISTS idx_unidad_token_device_id ON unidad_token (device_id);
CREATE INDEX IF NOT EXISTS idx_unidad_token_expires_at ON unidad_token (expires_at);

-- Rutas con LineString geográfico
CREATE TABLE IF NOT EXISTS ruta (
  id SERIAL PRIMARY KEY,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  linea GEOGRAPHY(LineString, 4326) NOT NULL,
  distancia_m FLOAT8,   -- longitud en metros (puede calcularse con ST_Length)
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Asignación de unidad a ruta (histórico)
CREATE TABLE IF NOT EXISTS unidad_ruta_assignment (
  id SERIAL PRIMARY KEY,
  unidad_id TEXT REFERENCES unidad(id) ON DELETE CASCADE,
  ruta_id INTEGER REFERENCES ruta(id) ON DELETE SET NULL,
  start_ts TIMESTAMPTZ NOT NULL,
  end_ts TIMESTAMPTZ NULL, -- null = actualmente asignada
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Tabla de posiciones: particionable por ts
CREATE TABLE IF NOT EXISTS posicion (
  id BIGSERIAL,
  unidad_id TEXT NOT NULL REFERENCES unidad(id) ON DELETE CASCADE,
  ts TIMESTAMPTZ NOT NULL,
  geom GEOGRAPHY(Point, 4326) NOT NULL,
  speed NUMERIC,
  heading NUMERIC,
  seq BIGINT,
  raw_payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (id, ts)
) PARTITION BY RANGE (ts);

-- Eventos (incidentes / alertas)
CREATE TABLE IF NOT EXISTS evento (
  id BIGSERIAL PRIMARY KEY,
  unidad_id TEXT REFERENCES unidad(id) ON DELETE SET NULL,
  tipo evento_tipo NOT NULL,
  detalle TEXT,
  ts TIMESTAMPTZ NOT NULL,
  posicion_id BIGINT,  -- Referencia soft a posicion (sin FK constraint por PRIMARY KEY compuesto)
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Estado por unidad (persistente) para detecciones incrementales
CREATE TABLE IF NOT EXISTS unidad_state (
  unidad_id TEXT PRIMARY KEY REFERENCES unidad(id) ON DELETE CASCADE,
  last_pos_id BIGINT,
  last_ts TIMESTAMPTZ,
  last_speed NUMERIC,
  stop_start_ts TIMESTAMPTZ,
  last_event_ts TIMESTAMPTZ,
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Configuración del sistema (parámetros ajustables)
CREATE TABLE IF NOT EXISTS sistema_config (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT INTO sistema_config (key, value) VALUES
  ('OUT_OF_ROUTE_THRESHOLD_M', '200'),
  ('STOP_SPEED_THRESHOLD', '1.5'),
  ('STOP_TIME_THRESHOLD_S', '120'),
  ('SPEED_LIMIT_MS', '22.22')  -- 80 km/h (22.22 m/s)
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- 003_indexes.sql
-- Índices generales y espaciales
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_ruta_linea_gist ON ruta USING GIST (linea);
CREATE INDEX IF NOT EXISTS idx_ruta_nombre ON ruta (lower(nombre));
CREATE INDEX IF NOT EXISTS idx_event_unidad_ts ON evento (unidad_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_pos_unidad_ts ON posicion (unidad_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_pos_geom_gist ON posicion USING GIST (geom);

-- ============================================================================
-- 004_partitions_posicion.sql
-- Ejemplo de particiones mensuales (ajusta/automatiza en producción)
-- ============================================================================
CREATE TABLE IF NOT EXISTS posicion_2025_10 PARTITION OF posicion
  FOR VALUES FROM ('2025-10-01 00:00:00+00') TO ('2025-11-01 00:00:00+00');

CREATE TABLE IF NOT EXISTS posicion_2025_11 PARTITION OF posicion
  FOR VALUES FROM ('2025-11-01 00:00:00+00') TO ('2025-12-01 00:00:00+00');

CREATE INDEX IF NOT EXISTS idx_pos_2025_10_geom ON posicion_2025_10 USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_pos_2025_10_unidad_ts ON posicion_2025_10 (unidad_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_pos_2025_11_geom ON posicion_2025_11 USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_pos_2025_11_unidad_ts ON posicion_2025_11 (unidad_id, ts DESC);

-- ============================================================================
-- 005_functions_tokens.sql
-- Funciones para creación/verificación/revocación/limpieza de tokens
-- ============================================================================
-- Nota: estas funciones usan pgcrypto::digest('sha256') y NO almacenan tokens en texto plano.
--       Entregar el token_plain debe hacerse por el servidor a device de forma segura UNA VEZ.

-- 5.1 – Crear token para unidad (sin device_id) — retrocompatibilidad
CREATE OR REPLACE FUNCTION fn_create_unidad_token(
  p_unidad_id TEXT,
  p_ttl_seconds INT DEFAULT 86400,
  p_revoke_old BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(token_plain TEXT, token_hash BYTEA, token_id BIGINT)
LANGUAGE plpgsql AS
$$
DECLARE
  v_plain TEXT;
  v_hash BYTEA;
  v_expires TIMESTAMPTZ;
  v_attempt INT;
BEGIN
  IF p_unidad_id IS NULL THEN
    RAISE EXCEPTION 'p_unidad_id no puede ser NULL';
  END IF;

  IF p_ttl_seconds > 0 THEN
    v_expires := now() + (p_ttl_seconds || ' seconds')::interval;
  ELSE
    v_expires := NULL;
  END IF;

  IF p_revoke_old THEN
    UPDATE unidad_token SET revoked = TRUE WHERE unidad_id = p_unidad_id AND revoked = FALSE;
  END IF;

  FOR v_attempt IN 1..5 LOOP
    v_plain := encode(gen_random_bytes(32), 'hex');
    v_hash := digest(v_plain, 'sha256');

    BEGIN
      INSERT INTO unidad_token (unidad_id, token_hash, created_at, expires_at, revoked)
      VALUES (p_unidad_id, v_hash, now(), v_expires, FALSE)
      RETURNING id INTO token_id;

      token_plain := v_plain;
      token_hash := v_hash;
      RETURN NEXT;
      RETURN;
    EXCEPTION WHEN unique_violation THEN
      IF v_attempt = 5 THEN
        RAISE EXCEPTION 'No se pudo generar token único tras % intentos', v_attempt;
      END IF;
    END;
  END LOOP;
END;
$$;

-- 5.2 – Crear token para unidad y device (recomendado)
CREATE OR REPLACE FUNCTION fn_create_unidad_token_for_device(
  p_unidad_id TEXT,
  p_device_id TEXT,
  p_ttl_seconds INT DEFAULT 86400,
  p_revoke_old BOOLEAN DEFAULT FALSE
)
RETURNS TABLE(token_plain TEXT, token_hash BYTEA, token_id BIGINT)
LANGUAGE plpgsql AS
$$
DECLARE
  v_plain TEXT;
  v_hash BYTEA;
  v_expires TIMESTAMPTZ;
  v_attempt INT;
BEGIN
  IF p_unidad_id IS NULL THEN
    RAISE EXCEPTION 'p_unidad_id no puede ser NULL';
  END IF;

  IF p_ttl_seconds > 0 THEN
    v_expires := now() + (p_ttl_seconds || ' seconds')::interval;
  ELSE
    v_expires := NULL;
  END IF;

  -- Si solicitaste revocar tokens antiguos para el mismo device, marcarlos
  IF p_revoke_old AND p_device_id IS NOT NULL THEN
    UPDATE unidad_token SET revoked = TRUE WHERE unidad_id = p_unidad_id AND device_id = p_device_id AND revoked = FALSE;
  ELSIF p_revoke_old THEN
    -- Si p_device_id es NULL, revocar todos los tokens de la unidad (comportamiento legacy)
    UPDATE unidad_token SET revoked = TRUE WHERE unidad_id = p_unidad_id AND revoked = FALSE;
  END IF;

  FOR v_attempt IN 1..5 LOOP
    v_plain := encode(gen_random_bytes(32), 'hex');
    v_hash := digest(v_plain, 'sha256');

    BEGIN
      INSERT INTO unidad_token (unidad_id, device_id, token_hash, created_at, expires_at, revoked)
      VALUES (p_unidad_id, p_device_id, v_hash, now(), v_expires, FALSE)
      RETURNING id INTO token_id;

      token_plain := v_plain;
      token_hash := v_hash;
      RETURN NEXT;
      RETURN;
    EXCEPTION WHEN unique_violation THEN
      IF v_attempt = 5 THEN
        RAISE EXCEPTION 'No se pudo generar token único tras % intentos', v_attempt;
      END IF;
    END;
  END LOOP;
END;
$$;

-- 5.3 – Verificar token (se invoca en capa servidor antes de insertar posición)
CREATE OR REPLACE FUNCTION fn_verify_unidad_token(
  p_unidad_id TEXT,
  p_token_plain TEXT
) RETURNS BOOLEAN LANGUAGE plpgsql AS
$$
DECLARE
  v_id BIGINT;
BEGIN
  SELECT id INTO v_id
  FROM unidad_token
  WHERE unidad_id = p_unidad_id
    AND token_hash = digest(p_token_plain, 'sha256')
    AND (expires_at IS NULL OR expires_at > now())
    AND revoked = FALSE
  LIMIT 1;

  IF FOUND THEN
    UPDATE unidad_token SET last_used = now() WHERE id = v_id;
    RETURN TRUE;
  ELSE
    RETURN FALSE;
  END IF;
END;
$$;

-- 5.4 – Revocar token por token_plain
CREATE OR REPLACE FUNCTION fn_revoke_token_by_plain(p_token_plain TEXT)
RETURNS BOOLEAN LANGUAGE plpgsql AS
$$
DECLARE
  v_hash BYTEA := digest(p_token_plain, 'sha256');
  v_count INT;
BEGIN
  UPDATE unidad_token SET revoked = TRUE WHERE token_hash = v_hash AND revoked = FALSE;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count > 0;
END;
$$;

-- 5.5 – Revocar tokens por device_id (útil para rotación selectiva)
CREATE OR REPLACE FUNCTION fn_revoke_tokens_for_device(p_unidad_id TEXT, p_device_id TEXT)
RETURNS INT LANGUAGE plpgsql AS
$$
DECLARE
  v_count INT;
BEGIN
  UPDATE unidad_token SET revoked = TRUE
  WHERE unidad_id = p_unidad_id AND device_id = p_device_id AND revoked = FALSE;
  GET DIAGNOSTICS v_count = ROW_COUNT;
  RETURN v_count;
END;
$$;

-- 5.6 – Cleanup: borrar tokens expirados y revocados (job)
CREATE OR REPLACE FUNCTION fn_cleanup_expired_tokens(p_older_than_days INT DEFAULT 30)
RETURNS INT LANGUAGE plpgsql AS
$$
DECLARE
  v_cut TIMESTAMPTZ := now() - (p_older_than_days || ' days')::interval;
  v_deleted INT;
BEGIN
  DELETE FROM unidad_token
  WHERE (revoked = TRUE OR (expires_at IS NOT NULL AND expires_at < now()))
    AND created_at < v_cut;
  GET DIAGNOSTICS v_deleted = ROW_COUNT;
  RETURN v_deleted;
END;
$$;

-- ============================================================================
-- 006_fn_insert_position_and_detect.sql
-- (Se mantiene sin verificación de token: la autenticación ocurre en la capa servidor)
-- ============================================================================
CREATE OR REPLACE FUNCTION fn_insert_position_and_detect(
  p_unidad_id TEXT,
  p_ts TIMESTAMPTZ,
  p_lat DOUBLE PRECISION,
  p_lon DOUBLE PRECISION,
  p_speed NUMERIC,
  p_heading NUMERIC,
  p_seq BIGINT,
  p_raw JSONB
) RETURNS TABLE (
  posicion_id BIGINT,
  created_event_id BIGINT
) LANGUAGE plpgsql AS
$$
DECLARE
  v_geom GEOGRAPHY;
  v_pos_id BIGINT;
  v_threshold_m DOUBLE PRECISION := (SELECT (value::double precision) FROM sistema_config WHERE key = 'OUT_OF_ROUTE_THRESHOLD_M');
  v_stop_speed_threshold DOUBLE PRECISION := (SELECT (value::double precision) FROM sistema_config WHERE key = 'STOP_SPEED_THRESHOLD');
  v_stop_time_threshold INT := (SELECT (value::int) FROM sistema_config WHERE key = 'STOP_TIME_THRESHOLD_S');
  v_speed_limit DOUBLE PRECISION := (SELECT (value::double precision) FROM sistema_config WHERE key = 'SPEED_LIMIT_MS');
  v_ruta_id INT;
  v_dist DOUBLE PRECISION;
  v_event_id BIGINT := NULL;
  v_last_state unidad_state%ROWTYPE;
  v_now TIMESTAMPTZ := now();
BEGIN
  IF p_lat IS NULL OR p_lon IS NULL THEN
    RAISE EXCEPTION 'Lat/Lon no pueden ser null';
  END IF;

  v_geom := ST_SetSRID(ST_MakePoint(p_lon, p_lat)::geometry, 4326)::geography;

  INSERT INTO posicion (unidad_id, ts, geom, speed, heading, seq, raw_payload)
  VALUES (p_unidad_id, p_ts, v_geom, p_speed, p_heading, p_seq, p_raw)
  RETURNING id INTO v_pos_id;

  SELECT ruta_id INTO v_ruta_id
  FROM unidad_ruta_assignment
  WHERE unidad_id = p_unidad_id
    AND start_ts <= p_ts
    AND (end_ts IS NULL OR end_ts >= p_ts)
  ORDER BY start_ts DESC
  LIMIT 1;

  IF v_ruta_id IS NOT NULL THEN
    SELECT ST_Distance(linea, v_geom) INTO v_dist FROM ruta WHERE id = v_ruta_id;
    IF v_dist IS NULL THEN v_dist := 1e9; END IF;

    IF v_dist > v_threshold_m THEN
      INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
      VALUES (p_unidad_id, 'OUT_OF_BOUND', 'Distancia a ruta: ' || round(v_dist::numeric,2) || ' m', p_ts, v_pos_id,
              jsonb_build_object('ruta_id', v_ruta_id, 'distance_m', v_dist))
      RETURNING id INTO v_event_id;
    END IF;
  END IF;

  -- Detectar exceso de velocidad (SPEEDING)
  IF p_speed IS NOT NULL AND v_speed_limit IS NOT NULL AND p_speed > v_speed_limit THEN
    INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
    VALUES (p_unidad_id, 'SPEEDING',
            'Velocidad: ' || round((p_speed * 3.6)::numeric, 2) || ' km/h (Límite: ' || round((v_speed_limit * 3.6)::numeric, 2) || ' km/h)',
            p_ts, v_pos_id,
            jsonb_build_object('speed_ms', p_speed, 'speed_kmh', round((p_speed * 3.6)::numeric, 2), 'limit_ms', v_speed_limit, 'limit_kmh', round((v_speed_limit * 3.6)::numeric, 2)))
    RETURNING id INTO v_event_id;
  END IF;

  SELECT * INTO v_last_state FROM unidad_state WHERE unidad_id = p_unidad_id;

  IF NOT FOUND THEN
    -- FIX: Usar p_ts en lugar de v_event_id para last_event_ts
    INSERT INTO unidad_state (unidad_id, last_pos_id, last_ts, last_speed, stop_start_ts, last_event_ts, updated_at)
    VALUES (p_unidad_id, v_pos_id, p_ts, p_speed, NULL,
            CASE WHEN v_event_id IS NOT NULL THEN p_ts ELSE NULL END,
            v_now);
  ELSE
    IF COALESCE(p_speed,0) <= v_stop_speed_threshold THEN
      IF v_last_state.stop_start_ts IS NULL THEN
        UPDATE unidad_state SET last_pos_id=v_pos_id, last_ts=p_ts, last_speed=p_speed, stop_start_ts=p_ts, updated_at=v_now WHERE unidad_id=p_unidad_id;
      ELSE
        UPDATE unidad_state SET last_pos_id=v_pos_id, last_ts=p_ts, last_speed=p_speed, updated_at=v_now WHERE unidad_id=p_unidad_id;
        IF EXTRACT(EPOCH FROM (p_ts - v_last_state.stop_start_ts)) >= v_stop_time_threshold THEN
          IF NOT EXISTS (
            SELECT 1 FROM evento WHERE unidad_id=p_unidad_id AND tipo='STOP_LONG' AND ts >= (p_ts - make_interval(secs=>v_stop_time_threshold))
          ) THEN
            INSERT INTO evento (unidad_id, tipo, detalle, ts, posicion_id, metadata)
            VALUES (p_unidad_id, 'STOP_LONG', 'Detención superior a ' || v_stop_time_threshold || ' s', p_ts, v_pos_id,
                    jsonb_build_object('stop_started_at', v_last_state.stop_start_ts))
            RETURNING id INTO v_event_id;

            -- FIX: Actualizar last_event_ts cuando se crea un evento
            UPDATE unidad_state SET last_event_ts=p_ts WHERE unidad_id=p_unidad_id;
          END IF;
        END IF;
      END IF;
    ELSE
      IF v_last_state.stop_start_ts IS NOT NULL THEN
        UPDATE unidad_state SET stop_start_ts=NULL, last_pos_id=v_pos_id, last_ts=p_ts, last_speed=p_speed, updated_at=v_now WHERE unidad_id=p_unidad_id;
      ELSE
        UPDATE unidad_state SET last_pos_id=v_pos_id, last_ts=p_ts, last_speed=p_speed, updated_at=v_now WHERE unidad_id=p_unidad_id;
      END IF;
    END IF;

    -- FIX: Actualizar last_event_ts si se creó un evento en esta iteración
    IF v_event_id IS NOT NULL THEN
      UPDATE unidad_state SET last_event_ts=p_ts WHERE unidad_id=p_unidad_id;
    END IF;
  END IF;

  RETURN QUERY SELECT v_pos_id, v_event_id;
END;
$$;

-- ============================================================================
-- 007_views.sql
-- ============================================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_last_position AS
SELECT DISTINCT ON (p.unidad_id)
  p.unidad_id,
  p.id AS posicion_id,
  p.ts,
  p.geom,
  p.speed,
  p.heading
FROM posicion p
ORDER BY p.unidad_id, p.ts DESC;

CREATE INDEX IF NOT EXISTS idx_mv_last_position_unidad ON mv_last_position (unidad_id);

-- ============================================================================
-- 008_roles_and_grants.sql
-- ============================================================================
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user WITH LOGIN PASSWORD 'app_user';
  END IF;
END$$;

-- FIX CRÍTICO: Reemplazar current_database() con nombre literal
GRANT CONNECT ON DATABASE transporte_db TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- Permisos básicos en tablas
GRANT SELECT, INSERT ON unidad, ruta, unidad_ruta_assignment, posicion, evento, unidad_state, sistema_config, unidad_token TO app_user;
GRANT UPDATE ON unidad_state TO app_user;
GRANT UPDATE (last_used) ON unidad_token TO app_user;
GRANT SELECT ON TABLE poi TO app_user;

-- Permisos de ejecución en funciones (las funciones manejan UPDATE en unidad_token)
GRANT EXECUTE ON FUNCTION fn_create_unidad_token(TEXT, INT, BOOLEAN) TO app_user;
GRANT EXECUTE ON FUNCTION fn_create_unidad_token_for_device(TEXT, TEXT, INT, BOOLEAN) TO app_user;
GRANT EXECUTE ON FUNCTION fn_verify_unidad_token(TEXT, TEXT) TO app_user;
GRANT EXECUTE ON FUNCTION fn_revoke_token_by_plain(TEXT) TO app_user;
GRANT EXECUTE ON FUNCTION fn_revoke_tokens_for_device(TEXT, TEXT) TO app_user;
GRANT EXECUTE ON FUNCTION fn_cleanup_expired_tokens(INT) TO app_user;
GRANT EXECUTE ON FUNCTION fn_insert_position_and_detect(TEXT, TIMESTAMPTZ, DOUBLE PRECISION, DOUBLE PRECISION, NUMERIC, NUMERIC, BIGINT, JSONB) TO app_user;

-- Permisos en secuencias (necesarios para INSERT con SERIAL/BIGSERIAL)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_admin') THEN
    CREATE ROLE app_admin NOLOGIN;
  END IF;
END$$;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO app_admin;

-- ============================================================================
-- 010_create_pois.sql
-- Tabla de Puntos de Interés (POIs) para Tapachula
-- ============================================================================

-- Crear tabla de POIs
CREATE TABLE IF NOT EXISTS poi (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    direccion TEXT,
    telefono VARCHAR(20),
    horario TEXT,
    ubicacion GEOGRAPHY(POINT, 4326) NOT NULL,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice espacial para búsquedas rápidas por ubicación
CREATE INDEX IF NOT EXISTS idx_poi_ubicacion ON poi USING GIST(ubicacion);

-- Índice para búsquedas por categoría
CREATE INDEX IF NOT EXISTS idx_poi_categoria ON poi(categoria) WHERE activo = TRUE;

-- Índice para búsquedas por nombre (case-insensitive)
CREATE INDEX IF NOT EXISTS idx_poi_nombre ON poi USING gin(to_tsvector('spanish', nombre));

-- ============================================================================
-- INSERTAR POIs DE TAPACHULA
-- ============================================================================

-- HOSPITALES/CLÍNICAS (4)
INSERT INTO poi (nombre, categoria, direccion, telefono, horario, ubicacion) VALUES
(
    'Hospital General de Tapachula',
    'hospital',
    '2a Calle Pte. S/N, Centro',
    '+52 962 626 1386',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2631 14.9067)')
),
(
    'Hospital Regional Tapachula',
    'hospital',
    '10a. Av. Sur 147, Centro',
    '+52 962 628 0050',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2610 14.9050)')
),
(
    'Clínica de Especialidades',
    'hospital',
    'Boulevard Díaz Ordaz 117, El Palmar',
    '+52 962 625 2100',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2680 14.9120)')
),
(
    'Hospital Regional del Instituto Mexicano del Seguro Social',
    'hospital',
    'Calzada Dr. Manuel Velasco Suárez S/N, Centro',
    '+52 962 628 0000',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2760 14.8945)')
);

-- FARMACIAS (5)
INSERT INTO poi (nombre, categoria, direccion, telefono, horario, ubicacion) VALUES
(
    'Farmacias Similares',
    'farmacia',
    'Av. Central Nte. 129, Centro',
    '+52 962 626 5500',
    'Lunes a Sábado: 8:00–21:00, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2605 14.9090)')
),
(
    'Farmacias del Ahorro',
    'farmacia',
    '4a Calle Pte. 11, Centro',
    '+52 962 625 5555',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2618 14.9085)')
),
(
    'Farmacias Guadalajara',
    'farmacia',
    '8a Av. Nte. 27, Centro',
    '+52 962 628 0088',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2595 14.9095)')
),
(
    'Farmacias Similares Sucursal 2',
    'farmacia',
    '12a Av. Nte. S/N, Centro',
    '+52 962 626 0000',
    'Lunes a Sábado: 8:00–21:00, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2580 14.9105)')
),
(
    'Farmacias del Ahorro Sucursal 2',
    'farmacia',
    '14a Av. Nte. 15, Centro',
    '+52 962 625 1111',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2570 14.9110)')
);

-- PAPELERÍAS (3)
INSERT INTO poi (nombre, categoria, direccion, telefono, horario, ubicacion) VALUES
(
    'Papelería El Fénix',
    'papeleria',
    '6a Av. Nte. S/N, Centro',
    '+52 962 626 4444',
    'Lunes a Sábado: 8:00–20:00, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2600 14.9088)')
),
(
    'Papelería La Gran Sur',
    'papeleria',
    '8a Av. Nte. 29, Centro',
    '+52 962 625 3333',
    'Lunes a Sábado: 8:30–20:30, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2593 14.9096)')
),
(
    'Papelería El Mundo',
    'papeleria',
    '10a Av. Nte. 17, Centro',
    '+52 962 626 2222',
    'Lunes a Sábado: 9:00–20:00, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2585 14.9100)')
);

-- GASOLINERAS (5)
INSERT INTO poi (nombre, categoria, direccion, telefono, horario, ubicacion) VALUES
(
    'Pemex Estación 5555',
    'gasolinera',
    '4a Calle Pte. S/N, Centro',
    '+52 962 626 8888',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2620 14.9082)')
),
(
    'G500 Estación 7777',
    'gasolinera',
    'Carretera Costera Km 240, Las Cruces',
    '+52 962 625 7777',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2450 14.9200)')
),
(
    'Estación de Servicio',
    'gasolinera',
    '8a Av. Sur 19, Centro',
    '+52 962 626 9999',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2615 14.9040)')
),
(
    'Estación Tapachula',
    'gasolinera',
    'Boulevard Díaz Ordaz S/N, Coapante',
    '+52 962 625 4444',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2700 14.9150)')
),
(
    'BP',
    'gasolinera',
    '10a Av. Nte. S/N, Centro',
    '+52 962 626 1111',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2583 14.9102)')
);

-- BANCOS/CAJEROS (5)
INSERT INTO poi (nombre, categoria, direccion, telefono, horario, ubicacion) VALUES
(
    'BBVA Sucursal Centro',
    'banco',
    '4a Calle Pte. 12, Centro',
    '+52 962 626 0101',
    'Lunes a Viernes: 9:00–16:00, Sábado: Cerrado, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2617 14.9087)')
),
(
    'Citibanamex Sucursal Tapachula',
    'banco',
    '6a Calle Pte. 1, Centro',
    '+52 962 625 0202',
    'Lunes a Viernes: 9:00–16:00, Sábado: Cerrado, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2625 14.9080)')
),
(
    'Santander Tapachula',
    'banco',
    '8a Calle Pte. 5, Centro',
    '+52 962 626 0303',
    'Lunes a Viernes: 9:00–16:00, Sábado: Cerrado, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2630 14.9075)')
),
(
    'Banorte Sucursal Tapachula',
    'banco',
    'Av. Central Nte. 3, Centro',
    '+52 962 625 0404',
    'Lunes a Viernes: 9:00–16:00, Sábado: Cerrado, Domingo: Cerrado',
    ST_GeogFromText('SRID=4326;POINT(-92.2608 14.9092)')
),
(
    'Cajero Automático Bancomer',
    'banco',
    'Boulevard Díaz Ordaz 182, Coapante (Dentro de Soriana Mercado)',
    'No aplica',
    'Abierto las 24 horas',
    ST_GeogFromText('SRID=4326;POINT(-92.2685 14.9130)')
);

-- ============================================================================
-- 009_seed_example.sql
-- Datos iniciales para Tapachula, Chiapas, México
-- ============================================================================
INSERT INTO unidad (id, placa, chofer)
VALUES ('UNIT-001','ABC-123','Juan Perez'),
       ('UNIT-002','DEF-456','María López'),
       ('UNIT-003','GHI-789','Carlos Ruiz')
ON CONFLICT (id) DO NOTHING;

-- Ruta principal en Tapachula con 489 puntos (movimiento fluido)
INSERT INTO ruta (nombre, descripcion, linea)
VALUES (
  'Ruta 1 - Tapachula Centro',
  'Ruta principal en Tapachula, Chiapas, México - 489 puntos para movimiento fluido y realista',
  ST_GeogFromText('SRID=4326;LINESTRING(-92.26454108004582 14.91251472418935,-92.2644555771808 14.912625526184499,-92.26439116334798 14.912718434666502,-92.26433511228625 14.912792056399383,-92.26427587594902 14.912868642993473,-92.26421410458704 14.912954344594354,-92.26416980394411 14.913020134147445,-92.26409886418578 14.912980715095912,-92.26401004451955 14.912937669790367,-92.26393592582365 14.91289591453237,-92.26386015727515 14.91285733796974,-92.26379250378952 14.91282216378302,-92.26369700085414 14.91277137086513,-92.26363241567206 14.912739275021266,-92.26356191185269 14.912702188993975,-92.26347638500329 14.91265808739395,-92.26339436584463 14.912616746755774,-92.26329688781858 14.912566057631594,-92.26320697478607 14.912519830335327,-92.26309819604387 14.912468703762713,-92.26305027380812 14.91253512534982,-92.2630078309477 14.912606854826976,-92.262967483871 14.912669786456334,-92.26292636553524 14.912735261772056,-92.26287426148606 14.912811326807699,-92.26283028612387 14.912880191526625,-92.26279191081092 14.912945670011155,-92.262742539755 14.913029690124219,-92.26268758226475 14.91310649372835,-92.2626503068376 14.913169852934018,-92.26259533904751 14.913254608563761,-92.26254321515964 14.913346577036407,-92.26249165122452 14.913429534061052,-92.26244371895007 14.913503907225305,-92.26239116581468 14.913588241286348,-92.26235158665034 14.913651279560426,-92.26231090425357 14.913719087641041,-92.26225769054655 14.913805223378773,-92.26222359742718 14.91386826805595,-92.26217643306514 14.913942747999016,-92.26213211589564 14.914021790628155,-92.26208945504243 14.914092352907744,-92.26204964452356 14.914164826970065,-92.26200258759033 14.914241215890527,-92.26195805224681 14.914319091595914,-92.26191725584579 14.914390292123457,-92.26187304952617 14.914468592389426,-92.26182752829989 14.914545194553781,-92.26178794578955 14.91461088315799,-92.26174407784973 14.91468165644379,-92.26169811733843 14.914758576088758,-92.26165788426596 14.914818114440237,-92.261613130972 14.914894823675581,-92.26156784110083 14.914961989787528,-92.26152737667381 14.915030963980755,-92.26148032296938 14.91510470148171,-92.26142414514774 14.915192317579965,-92.26138016978557 14.915261181536692,-92.26133223076428 14.91534085552459,-92.26127814515196 14.91542232439599,-92.26120359049352 14.915378236457457,-92.2611314501733 14.915333727167123,-92.26105996381838 14.915292717531969,-92.26099198505203 14.915254468654211,-92.26092148799734 14.915212081951083,-92.26084813719025 14.915170433949498,-92.26078070836708 14.915131125454664,-92.26071207222734 14.91509202750754,-92.26064025724563 14.915050593341505,-92.26057074600051 14.915009479955103,-92.26049904169048 14.914967303738976,-92.26042810193213 14.914927885045415,-92.26036330212693 14.914891972388574,-92.26029115525023 14.914852764337482,-92.26020694970467 14.914805060072922,-92.26013009479259 14.914758000702733,-92.2600487395808 14.914712208218333,-92.2599683737682 14.914665038657418,-92.25989480499193 14.91462222402076,-92.2598101635761 14.914572186693633,-92.2597564398252 14.914540846094297,-92.25968649286955 14.91449739964149,-92.25961237749668 14.91445299395653,-92.25954779920481 14.914415597196253,-92.25948618170679 14.914379370131968,-92.25940625835484 14.914329232240746,-92.25934058739134 14.914288653550315,-92.2592637323423 14.914241593973358,-92.25920189687511 14.914204200350596,-92.25914718389598 14.914174236855018,-92.2590664893819 14.914126642603847,-92.25899982177846 14.914092742084819,-92.25892898999278 14.914055231861767,-92.2588532247909 14.914014004889225,-92.25878096717754 14.913975538691417,-92.25870213434848 14.913931233450072,-92.25862066847908 14.913886182834531,-92.25854183220845 14.91384452820219,-92.2584717676741 14.913807124808741,-92.25838701302064 14.913760480096926,-92.25831738777188 14.913722759132042,-92.2582532418742 14.91369034587207,-92.25817242359763 14.913654096040133,-92.25810004528736 14.913624323693085,-92.25801462314212 14.913584781680214,-92.2579362136881 14.913553411880201,-92.25787074658938 14.913524601892306,-92.257794753379 14.913490160159213,-92.25772040385907 14.913457840822204,-92.25763443113358 14.91341935835662,-92.25754670540529 14.913379495517816,-92.25746534015478 14.913341654620822,-92.25737684275566 14.913304335392752,-92.2572995350363 14.913268195669872,-92.25722650616393 14.913232273036499,-92.25714612750765 14.913195705445887,-92.25707693485121 14.913162968082219,-92.25700346669383 14.913127362989002,-92.25690993312566 14.913081767581161,-92.25683043232732 14.91304456498139,-92.25674194182896 14.913001944431073,-92.25665552981908 14.912963779441867,-92.25657767946544 14.912923397966992,-92.25649696812249 14.91288905660089,-92.25640091270651 14.912841974051688,-92.25631252893285 14.912801262098526,-92.25621537618757 14.912753648140608,-92.25610680935772 14.912708989360652,-92.25600175951926 14.912659139535549,-92.25590613938323 14.912614390010148,-92.2558238955621 14.912577184096733,-92.2557116032655 14.912528597925998,-92.25561356860415 14.91248426966402,-92.25552354555569 14.912438784529215,-92.2554058771455 14.912389449895556,-92.25527472930747 14.912328012399456,-92.25518196272132 14.912282524023311,-92.25509072926059 14.912239900092274,-92.25500902869001 14.912206935785804,-92.25492283622664 14.912169937052113,-92.25481833298477 14.912121678134241,-92.25472391705297 14.912079368439478,-92.25463267959834 14.912039395158132,-92.25453519903184 14.911991356350597,-92.25443946810766 14.91194734877135,-92.25435316703941 14.911908441471368,-92.25427135915726 14.91187356852059,-92.25416323896731 14.911823290739179,-92.2540762770142 14.911786185152778,-92.25399151148672 14.911747491758874,-92.25388415573653 14.911699971435283,-92.25379050723373 14.911657768694155,-92.253701348855 14.91162225088111,-92.25358676390815 14.911565391677101,-92.2534789710475 14.911515538354223,-92.25335451025144 14.911459197458626,-92.25321809483354 14.911398919527358,-92.25312093539615 14.911356606561483,-92.25300206746272 14.911302180962679,-92.2528715737951 14.911244242819322,-92.25274886689009 14.911189282689335,-92.25264732464018 14.911142193332353,-92.25253920329959 14.91109191537491,-92.25243700044888 14.911046627665584,-92.25232503614792 14.910998465710762,-92.25222579428917 14.910954347763578,-92.25211986244456 14.910907783342637,-92.25199747943572 14.910855898135637,-92.25190043065592 14.910812843008657,-92.25178419139513 14.910761813199514,-92.25167453073628 14.910713971992479,-92.25153109573003 14.9106508231106,-92.25141617368865 14.910598840639878,-92.25130849824791 14.910542943722533,-92.25119434411893 14.91049106815791,-92.25108633667372 14.910437397388591,-92.25099356339489 14.910397209938779,-92.25090672127467 14.910354060687268,-92.25080155408537 14.910310253701937,-92.25071394491678 14.910264346871685,-92.2506194191173 14.910222778924705,-92.25051206554167 14.91017260772756,-92.25042642682945 14.910131898554909,-92.25032718831672 14.910085129762649,-92.25023397909894 14.910042609142579,-92.25014318121596 14.91000231788692,-92.25003198138626 14.909956913315028,-92.24994009366041 14.909910789296717,-92.24985367161122 14.909880575768028,-92.24976627071207 14.909843787397847,-92.24968204508791 14.909811986044446,-92.24959005995557 14.909756001419083,-92.24950706830005 14.909702784050111,-92.24940981872435 14.90964530886393,-92.24934404976896 14.909594868475153,-92.2492681975601 14.909535828037619,-92.24919486402983 14.909480925795052,-92.24914214623908 14.909434953893253,-92.24906137162674 14.90936424486081,-92.24899232978396 14.909298956736478,-92.24892713442323 14.90922890199856,-92.24886512853615 14.909153231806627,-92.24879895375854 14.909076602072915,-92.24875840902028 14.909035733968508,-92.24871525488314 14.908975565577094,-92.24866794626085 14.908903835490378,-92.24861636851202 14.908823936025613,-92.24857398228725 14.90876387450804,-92.24853446987929 14.908687170131458,-92.24849486014068 14.908600604957769,-92.24845293674608 14.908521671207922,-92.24842790730368 14.908445089754494,-92.24839411246988 14.908358955986671,-92.24835965010955 14.908279924717519,-92.24834459348958 14.9082126853788,-92.24832419496673 14.908118190754934,-92.2483001714845 14.908026978501326,-92.24827833108715 14.907944781430729,-92.24827196624338 14.907858679263086,-92.24826647996964 14.90777194192863,-92.24825769404302 14.907691562297188,-92.24825307295453 14.90761479255184,-92.24824453506235 14.907511723387117,-92.24824081931457 14.907413112846115,-92.24823283807689 14.907303682544537,-92.24822485352142 14.907196902701102,-92.24821479979536 14.90707771557156,-92.24821195592551 14.906983771108315,-92.24820789816559 14.9068953386504,-92.24819704645664 14.906799900896715,-92.2481938839987 14.906697579685911,-92.24818651988743 14.906620806352066,-92.24817863594498 14.906521236264723,-92.24817380023335 14.906440648818489,-92.24816402507392 14.9063616459499,-92.24815218085719 14.90627023534229,-92.24815022225002 14.906170353959453,-92.24814629522572 14.90606527479801,-92.24813490707068 14.9059602927465,-92.2481285556123 14.905863586908751,-92.24812316661139 14.905786709576773,-92.2481187700936 14.905705804154664,-92.24811218058798 14.905623835958139,-92.24810243216383 14.905523626973078,-92.24809683188583 14.90544028149506,-92.24808664412019 14.905340389960699,-92.24808193579818 14.905245806366437,-92.24806748930999 14.905129793300503,-92.24806148990363 14.905014956489424,-92.24805415917507 14.904911675191116,-92.24805031938433 14.90482440846182,-92.24803990720828 14.904728651879822,-92.24802986365552 14.904601510660669,-92.2480195015141 14.904465992653257,-92.24801030615383 14.904362072441543,-92.24800518197085 14.904249250817472,-92.24799643277187 14.904139711724412,-92.24798909208583 14.904044382289754,-92.24798043689027 14.903947354785942,-92.24797508779943 14.903838667328074,-92.24796448091813 14.903723188216986,-92.24795758620976 14.903622239533362,-92.24794928637995 14.903504430321448,-92.24794172772414 14.903407934017821,-92.24793363920315 14.903296592820126,-92.24792784425325 14.903193524466346,-92.24791952103112 14.903094270335103,-92.24790953794121 14.903006147384971,-92.24790046343189 14.90289353203984,-92.2478946619161 14.902795765168264,-92.24789290120069 14.902712953313483,-92.24788345457083 14.902634373408134,-92.24787985282728 14.902532367790641,-92.24787448725047 14.902436933942084,-92.24786319637565 14.902341811245236,-92.24784481706749 14.902211872089197,-92.24782294665353 14.902056482806131,-92.24780273676751 14.901907725651967,-92.2477721043528 14.901788881790637,-92.24773184936281 14.90165461578168,-92.24767602635751 14.901513701040727,-92.24761685362846 14.90138192131657,-92.24752544578118 14.901226449455962,-92.24741066658396 14.901076684344503,-92.24730252337866 14.900957928051469,-92.24716970513003 14.900849177670835,-92.24702872577849 14.900741851201502,-92.2469008851831 14.90065747757832,-92.24677193184046 14.900571668946853,-92.24664947567673 14.90048228413201,-92.24653200991459 14.900403836095663,-92.24642103883669 14.90032181172431,-92.24628653333872 14.900228828247407,-92.24615535841737 14.900140149653836,-92.24599565542786 14.900029575212812,-92.24585021029806 14.899934428567263,-92.24567457839707 14.899810753766985,-92.2455102385401 14.899700173663163,-92.24536756739847 14.899613093936466,-92.24521081039302 14.899518292168295,-92.245098354493 14.899437340902963,-92.24493809625918 14.89932604863803,-92.24476744873424 14.89921779043705,-92.24460200524479 14.899101295176393,-92.2444263648236 14.898982099821623,-92.24424904895069 14.898869712086835,-92.24410101951962 14.898765243510795,-92.24389518615101 14.898621999702087,-92.24372564941467 14.898515176053635,-92.2435409301825 14.89839023525225,-92.24336918317887 14.898271581692327,-92.2432015055408 14.898161176023919,-92.24308736649051 14.89809151186455,-92.24309432544838 14.898013747363692,-92.24305994188285 14.8979289451717,-92.24297325508317 14.897852862094439,-92.2428872258632 14.897843442260083,-92.24277350670255 14.897882015167227,-92.24271332614597 14.897961329889611,-92.24269427872143 14.898066856282881,-92.24273105957104 14.898162234045344,-92.2428198035545 14.898224521045194,-92.24291622653223 14.89822642672145,-92.24301417957625 14.898191419016314,-92.2431525745616 14.898289425368716,-92.24329524271889 14.898380985471732,-92.2434314218469 14.898471641886346,-92.24357223121916 14.898566784288448,-92.24373232059195 14.89866589119184,-92.2438883124806 14.898779149831398,-92.24407767337192 14.898899615870917,-92.2442103274599 14.898991701505622,-92.24437578334697 14.899099236640694,-92.24453381553596 14.89921213920482,-92.24470110807223 14.899334012576077,-92.24485229309722 14.899435079388681,-92.24500273112331 14.899541163268779,-92.24513521516141 14.899621062914932,-92.24526121011203 14.899700058850016,-92.24541092834838 14.899788759486015,-92.245568784832 14.899893955945728,-92.24569605957343 14.899986571996848,-92.24581982169265 14.900071657948601,-92.2459474828854 14.900152806099811,-92.24608570788578 14.900238625828749,-92.24622650590433 14.900342726753578,-92.24637213239544 14.900441098997476,-92.24651555427522 14.900523161580864,-92.24664041982149 14.900614161549385,-92.24679290937536 14.900710928979592,-92.24692036658499 14.900806770866453,-92.24704191278146 14.900884506776478,-92.24715581415936 14.900995743584886,-92.24725305345625 14.901085457004712,-92.24735453771537 14.901191123978734,-92.24741652661557 14.901295131548238,-92.24748498757867 14.901413482478489,-92.24755771624076 14.901529867264145,-92.24760485691536 14.901644608989429,-92.24764070833716 14.901741776041533,-92.24768521407259 14.901887515711422,-92.2476943669657 14.90198160483314,-92.24772795722109 14.902107261340277,-92.24772302126605 14.902198108218315,-92.24773066119464 14.902315670215543,-92.24774382100111 14.902467285918604,-92.24775328571772 14.902608145384107,-92.24776923946726 14.902749908392664,-92.24777776910058 14.902897038430652,-92.24779355279605 14.903026615721842,-92.24780298357987 14.903194354147601,-92.2478137014331 14.903371232952708,-92.24783365643687 14.903575001807297,-92.2478408432073 14.903757790000938,-92.24785837264973 14.903973382508823,-92.24786148470369 14.904152402147204,-92.24786904532098 14.904332681130057,-92.24789367024205 14.904509575551899,-92.24790125913614 14.904667454952019,-92.24790956781997 14.904842716941317,-92.24791826790101 14.905002031715725,-92.24792215605024 14.905153634596516,-92.24794236593576 14.905302389507753,-92.24796533023928 14.905472650891127,-92.24797011388358 14.905649341619082,-92.24798174362377 14.905837867050025,-92.2479986271049 14.905977837441029,-92.2480135892124 14.906170667151613,-92.24803039886564 14.9063688746606,-92.2480439213942 14.906526938885122,-92.24806295895202 14.906723537028284,-92.2480721800973 14.906910445944632,-92.24809875993535 14.907154178329407,-92.24810386105807 14.907373157437434,-92.24812183805497 14.90752800071651,-92.24812440577603 14.907697340272094,-92.24814849799515 14.907855595917042,-92.24818015587344 14.908043067875482,-92.2482259027884 14.90823378195222,-92.2482802126933 14.90839816459058,-92.24833860295197 14.90856183506149,-92.2484026151027 14.90867892241397,-92.24849216424278 14.908837970505516,-92.24855117218685 14.908953080707391,-92.2486283607238 14.90906176140895,-92.24874703300128 14.909212062966262,-92.24886202230297 14.909342649359928,-92.24898019088796 14.909451915746459,-92.24911465586628 14.909576252522882,-92.24925286390078 14.909675507753974,-92.24941478950733 14.909788946931627,-92.24959509996935 14.909881263175407,-92.24974149714929 14.909956695631706,-92.24987660507641 14.910014554124047,-92.2500052181247 14.910075988650561,-92.25018295531741 14.910150024464514,-92.2503495676522 14.910223151188276,-92.25049838347633 14.910291239091677,-92.25070037101452 14.910398095151322,-92.25087144347209 14.910463521891714,-92.25104398397403 14.910541314512187,-92.251241721027 14.910636697304255,-92.25141036792375 14.910713947620039,-92.2516036679997 14.910799111556841,-92.2517860297106 14.910882112042515,-92.25196005484702 14.910958831042734,-92.25210991760844 14.911028140309043,-92.25228700507255 14.911118056043733,-92.25252839936009 14.91122958811546,-92.25274469870757 14.911326911953125,-92.252992301268 14.911435652804329,-92.25324971504014 14.911560404966693,-92.2534393021121 14.911648078863479,-92.2536073263307 14.911721937057692,-92.25380632781986 14.91179650443948,-92.25400914829906 14.911878812283987,-92.25420881607775 14.911973895635995,-92.25442206163456 14.91206966958103,-92.25464468976172 14.912177563030127,-92.25488160441904 14.912273028440254,-92.25510076459695 14.9123708273044,-92.25537557122632 14.912504008113771,-92.25563300622974 14.912611942377367,-92.25587616531816 14.912723895907789,-92.25611723939117 14.912833156156594,-92.25639308886302 14.912967683624785,-92.25630548708837 14.913154924750359,-92.25620076922267 14.913390242861865,-92.2561291879528 14.913570102923941,-92.25605764914494 14.913716328449112,-92.25599131310183 14.913877694931926,-92.25621226033248 14.913938497331245,-92.25643320756313 14.913999299713396,-92.25665206878837 14.91405740870421,-92.25686848433128 14.914123587210938,-92.25702536015851 14.914205503660526,-92.25722882964166 14.914325145473057,-92.25743612881261 14.914444119041747,-92.25761908856576 14.914542883272887,-92.25781873905888 14.914654784509423,-92.25799854870057 14.91476632541243,-92.25822813395654 14.914877589135727,-92.25842255067984 14.91499957430024,-92.25859924477062 14.915098667232527,-92.25881000886082 14.915227733592658,-92.25900234056824 14.915347025365008,-92.25916198226217 14.915443743643351,-92.25932787900285 14.915548541448985,-92.25950629645266 14.915661089814932,-92.25964229027733 14.915741299355716,-92.2597566886868 14.915557791475592,-92.25986201309442 14.915393444574732,-92.2599872088428 14.915204231662699,-92.26010751124703 14.915031157248166,-92.26022120774147 14.914852356652958,-92.26034255265338 14.91468062855543,-92.26046459964785 14.914504192345234,-92.26060512443455 14.914303897386773,-92.2607386708612 14.914117047766908,-92.26082828334238 14.91399136080237,-92.26096183072974 14.913804509808301,-92.26109884510565 14.913627754179217,-92.26124527389781 14.913437892054816,-92.26136137442431 14.913284655624977,-92.2614677305278 14.913130061840548,-92.2616214470145 14.912923048349214,-92.26171706463879 14.912789933207947,-92.2618069974903 14.912636314668475,-92.26189932401991 14.91252526876022,-92.26197125537229 14.912414198751549,-92.26204809848595 14.912289732820994,-92.26213638578982 14.912147148649723,-92.2622717255938 14.911944012202028,-92.26241471257066 14.911752524356089,-92.26254592193371 14.911561022448055,-92.2627044875825 14.911344059079468,-92.2628621045134 14.91139045393949,-92.26303534513363 14.911472898886458,-92.26318648624725 14.911547993779266,-92.26332807965294 14.911623077390402,-92.26347120208968 14.911697055635742,-92.26360708783635 14.911755525331174,-92.2637551596733 14.911842057228512,-92.26389140729393 14.911916396341425,-92.26401811885479 14.911981498010007,-92.26417458245761 14.912075789439953,-92.26434060541601 14.91216086592847,-92.26449821305505 14.912256635214334,-92.26466766759718 14.91234614423368,-92.26458848491758 14.91244716959018)')
)
ON CONFLICT DO NOTHING;

-- Calcular distancia automáticamente
UPDATE ruta SET distancia_m = ST_Length(linea) WHERE distancia_m IS NULL;

-- Asignar ruta a todas las unidades activas
INSERT INTO unidad_ruta_assignment (unidad_id, ruta_id, start_ts, end_ts)
SELECT
  u.id,
  (SELECT id FROM ruta WHERE nombre = 'Ruta 1 - Tapachula Centro'),
  NOW(),
  NULL
FROM unidad u
WHERE u.activo = TRUE
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 010_demo_insert_call.sql (ejemplos de uso)
-- ============================================================================
-- 1) Crear token para device:
-- SELECT * FROM fn_create_unidad_token_for_device('UNIT-001', 'GPS-01', 86400, FALSE);

-- 2) Verificar token (en servidor, antes de insertar posición):
-- SELECT fn_verify_unidad_token('UNIT-001', 'token_plain_recibido');

-- 3) Insertar posición tras verificación:
-- SELECT * FROM fn_insert_position_and_detect('UNIT-001', now()::timestamptz, -1.6702, -78.6505, 0.4, 140, 1, '{"sim":"demo"}'::jsonb);

-- 4) Revocar token antiguo por plain:
-- SELECT fn_revoke_token_by_plain('token_plain_antiguo');

-- 5) Revocar tokens de un device:
-- SELECT fn_revoke_tokens_for_device('UNIT-001', 'GPS-01');

-- 6) Cleanup tokens viejos (job periódco/cron):
-- SELECT fn_cleanup_expired_tokens(30);

-- ============================================================================
-- FIN del archivo migrations_full_final_with_device_FIXED.sql
-- ============================================================================
