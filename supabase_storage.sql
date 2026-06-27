-- Bucket publico para fotos de reportes.
-- Ejecuta esto en el SQL editor de Supabase antes de usar carga de imagenes.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'mascotas',
    'mascotas',
    TRUE,
    10485760,
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']
)
ON CONFLICT (id) DO UPDATE SET
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS mascotas_storage_public_read ON storage.objects;
DROP POLICY IF EXISTS mascotas_storage_public_insert ON storage.objects;
DROP POLICY IF EXISTS mascotas_storage_public_update ON storage.objects;

CREATE POLICY mascotas_storage_public_read
ON storage.objects
FOR SELECT
USING (bucket_id = 'mascotas');

-- Si usas solo SUPABASE_ANON_KEY en Coolify, esta politica permite subir imagenes.
-- Si usas service_role en el servidor, puedes cerrar esta politica despues.
CREATE POLICY mascotas_storage_public_insert
ON storage.objects
FOR INSERT
WITH CHECK (bucket_id = 'mascotas');

CREATE POLICY mascotas_storage_public_update
ON storage.objects
FOR UPDATE
USING (bucket_id = 'mascotas')
WITH CHECK (bucket_id = 'mascotas');
