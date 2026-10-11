"""protect backend tables from direct API access

Revision ID: 5c77d694ca7a
Revises: 449a623ea1e9
Create Date: 2026-10-09 15:06:21.523483

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '5c77d694ca7a'
down_revision: Union[str, Sequence[str], None] = '449a623ea1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Frozen initial-schema tables; never import live models into a migration.
TABLES = (
    "audit_logs", "blocks", "certifications", "comments", "companies", "company_locations",
    "company_members", "company_offerings", "connections", "conversation_members", "conversations",
    "educations", "event_attendees", "events", "experiences", "follows", "job_alerts",
    "job_applications", "job_skills", "jobs", "location_photos", "media_files", "message_reactions",
    "messages", "notifications", "platform_settings", "post_media", "posts", "profiles", "projects",
    "reactions", "refresh_tokens", "reports", "saved_jobs", "saved_posts", "skills", "stories",
    "story_views", "user_skills", "users", "verification_codes", "verification_requests",
    "alembic_version",
)


def upgrade() -> None:
    """FastAPI owns authorization; deny direct Data API access to its tables."""
    if op.get_context().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'REVOKE ALL ON TABLE public."{table}" FROM PUBLIC')
        # Supabase roles do not exist in plain local PostgreSQL installations.
        op.execute(f"""
            DO $block$
            DECLARE api_role text;
            BEGIN
                FOR api_role IN SELECT rolname FROM pg_roles
                    WHERE rolname IN ('anon', 'authenticated', 'service_role')
                LOOP
                    EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', '{table}', api_role);
                END LOOP;
            END $block$;
        """)


def downgrade() -> None:
    """Retain protection on rollback; the initial migration drops the tables."""
    pass
