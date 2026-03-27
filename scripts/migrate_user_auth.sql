-- Repeatable compatibility migration for user-service auth fields.
-- If your PHONE_HASH_SALT differs from the application default, update the
-- phone_hash_salt value below before running this script.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
DECLARE
    phone_hash_salt text := 'highermatch_salt';
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'users'
    ) THEN
        RAISE NOTICE 'users table not found. Start user-service once so create_all can create it, then rerun this script.';
        RETURN;
    END IF;

    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS phone_hash VARCHAR(64);
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role VARCHAR(20);
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name VARCHAR(200);
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS company_name VARCHAR(300);
    ALTER TABLE public.users ADD COLUMN IF NOT EXISTS company_size VARCHAR(50);

    UPDATE public.users
    SET role = CASE
        WHEN COALESCE(is_recruiter, FALSE) THEN 'employer'
        WHEN COALESCE(is_candidate, FALSE) THEN 'candidate'
        ELSE 'candidate'
    END
    WHERE role IS NULL OR btrim(role) = '';

    UPDATE public.users
    SET name = full_name
    WHERE (name IS NULL OR btrim(name) = '')
      AND full_name IS NOT NULL
      AND btrim(full_name) <> '';

    WITH ranked_phone_hashes AS (
        SELECT
            id,
            encode(
                digest(
                    phone_hash_salt || ':' || regexp_replace(phone, '[\s-]', '', 'g'),
                    'sha256'
                ),
                'hex'
            ) AS computed_phone_hash,
            ROW_NUMBER() OVER (
                PARTITION BY encode(
                    digest(
                        phone_hash_salt || ':' || regexp_replace(phone, '[\s-]', '', 'g'),
                        'sha256'
                    ),
                    'hex'
                )
                ORDER BY id
            ) AS rn
        FROM public.users
        WHERE phone_hash IS NULL
          AND phone IS NOT NULL
          AND btrim(phone) <> ''
    )
    UPDATE public.users AS users_table
    SET phone_hash = ranked_phone_hashes.computed_phone_hash
    FROM ranked_phone_hashes
    WHERE users_table.id = ranked_phone_hashes.id
      AND ranked_phone_hashes.rn = 1;

    EXECUTE 'CREATE INDEX IF NOT EXISTS idx_users_role ON public.users (role)';
    EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_hash_not_null ON public.users (phone_hash) WHERE phone_hash IS NOT NULL';
END $$;
