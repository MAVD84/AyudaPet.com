CREATE TABLE IF NOT EXISTS usuarios (
  telefono VARCHAR(10) PRIMARY KEY,
  creado BIGINT NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  nombre VARCHAR(160) NULL,
  foto VARCHAR(500) NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS otps (
  telefono VARCHAR(10) PRIMARY KEY,
  code VARCHAR(6) NOT NULL,
  expires DOUBLE NOT NULL,
  INDEX idx_otps_expira (expires)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mascotas (
  id CHAR(32) PRIMARY KEY,
  reportado_por VARCHAR(10) NOT NULL,
  tipo_reporte VARCHAR(30) NULL DEFAULT 'extravio',
  tipo_mascota VARCHAR(40) NULL,
  nombre VARCHAR(160) NOT NULL,
  descripcion TEXT NULL,
  contacto VARCHAR(160) NULL,
  principal VARCHAR(500) NULL,
  secundarias JSON NULL,
  fecha VARCHAR(40) NULL,
  edad VARCHAR(120) NULL,
  raza VARCHAR(160) NULL,
  genero VARCHAR(80) NULL,
  color VARCHAR(120) NULL,
  collar VARCHAR(120) NULL,
  docil VARCHAR(120) NULL,
  direccion VARCHAR(500) NULL,
  ubicacion_lat DECIMAL(9,6) NULL,
  ubicacion_lng DECIMAL(9,6) NULL,
  calles VARCHAR(240) NULL,
  dueno VARCHAR(160) NULL,
  recompensa VARCHAR(160) NULL,
  encontrado TINYINT(1) NOT NULL DEFAULT 0,
  vistas INT UNSIGNED NOT NULL DEFAULT 0,
  impulsado_hasta DATETIME NULL,
  stripe_session_id VARCHAR(255) NULL,
  stripe_payment_status VARCHAR(50) NULL,
  creado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_mascotas_usuario (reportado_por),
  INDEX idx_mascotas_encontrado (encontrado),
  INDEX idx_mascotas_impulsado (impulsado_hasta),
  INDEX idx_mascotas_fecha (creado_at),
  CONSTRAINT fk_mascotas_usuario FOREIGN KEY (reportado_por)
    REFERENCES usuarios(telefono) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
