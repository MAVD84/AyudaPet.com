-- UBICAN ID hardening notes
-- 1. Rotate any key that was committed before applying this file.
-- 2. Use SUPABASE_SERVICE_ROLE_KEY only on the Flask server.
-- 3. Do not expose service-role keys in browser code.

DROP POLICY IF EXISTS usuarios_all ON usuarios;
DROP POLICY IF EXISTS mascotas_all ON mascotas;
DROP POLICY IF EXISTS otps_all ON otps;

-- With the Flask backend using the service-role key, direct public access can stay closed.
CREATE POLICY usuarios_no_anon_access
ON usuarios
FOR ALL
USING (false)
WITH CHECK (false);

CREATE POLICY otps_no_anon_access
ON otps
FOR ALL
USING (false)
WITH CHECK (false);

-- Public reads are optional. Enable only if reports are meant to be visible without login.
CREATE POLICY mascotas_public_read
ON mascotas
FOR SELECT
USING (true);

CREATE POLICY mascotas_no_anon_write
ON mascotas
FOR INSERT
WITH CHECK (false);

CREATE OR REPLACE FUNCTION set_actualizado_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_mascotas_actualizado_at ON mascotas;

CREATE TRIGGER trg_mascotas_actualizado_at
BEFORE UPDATE ON mascotas
FOR EACH ROW
EXECUTE FUNCTION set_actualizado_at();
