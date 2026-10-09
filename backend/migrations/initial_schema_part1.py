"""Frozen initial schema operations, in dependency order."""
from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('audit_logs',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('actor_id', sa.String(length=32), nullable=False),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('target_type', sa.String(length=40), nullable=False),
    sa.Column('target_id', sa.String(length=32), nullable=False),
    sa.Column('details', sa.String(length=1000), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_actor_id'), 'audit_logs', ['actor_id'], unique=False)
    op.create_table('platform_settings',
    sa.Column('key', sa.String(length=64), nullable=False),
    sa.Column('value', sa.String(length=500), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('key')
    )
    op.create_table('skills',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('category', sa.String(length=60), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('name')
    )
    op.create_table('users',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('phone', sa.String(length=40), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('professional_title', sa.String(length=160), nullable=False),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('email_verified', sa.Boolean(), nullable=False),
    sa.Column('failed_attempts', sa.Integer(), nullable=False),
    sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('token_version', sa.Integer(), nullable=False),
    sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_status'), 'users', ['status'], unique=False)
    op.create_table('blocks',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('blocked_user_id', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['blocked_user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'blocked_user_id')
    )
    op.create_index(op.f('ix_blocks_blocked_user_id'), 'blocks', ['blocked_user_id'], unique=False)
    op.create_index(op.f('ix_blocks_user_id'), 'blocks', ['user_id'], unique=False)
    op.create_table('certifications',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('issuer', sa.String(length=200), nullable=False),
    sa.Column('issue_date', sa.String(length=20), nullable=False),
    sa.Column('credential_id', sa.String(length=120), nullable=False),
    sa.Column('credential_url', sa.String(length=500), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_certifications_user_id'), 'certifications', ['user_id'], unique=False)
    op.create_table('companies',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=220), nullable=False),
    sa.Column('industry', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('website', sa.String(length=500), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('phone', sa.String(length=60), nullable=False),
    sa.Column('founded', sa.String(length=20), nullable=False),
    sa.Column('size', sa.String(length=20), nullable=False),
    sa.Column('logo', sa.String(length=32), nullable=False),
    sa.Column('cover', sa.String(length=32), nullable=False),
    sa.Column('owner_id', sa.String(length=32), nullable=False),
    sa.Column('verified', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_companies_owner_id'), 'companies', ['owner_id'], unique=False)
    op.create_index(op.f('ix_companies_slug'), 'companies', ['slug'], unique=False)
    op.create_index(op.f('ix_companies_status'), 'companies', ['status'], unique=False)
    op.create_table('connections',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('requester_id', sa.String(length=32), nullable=False),
    sa.Column('addressee_id', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('message', sa.String(length=300), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['addressee_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('requester_id', 'addressee_id')
    )
    op.create_index('ix_connections_addressee_status', 'connections', ['addressee_id', 'status'], unique=False)
    op.create_index(op.f('ix_connections_requester_id'), 'connections', ['requester_id'], unique=False)
    op.create_table('conversations',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('created_by', sa.String(length=32), nullable=True),
    sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversations_last_message_at'), 'conversations', ['last_message_at'], unique=False)
    op.create_table('educations',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('school', sa.String(length=200), nullable=False),
    sa.Column('degree', sa.String(length=200), nullable=False),
    sa.Column('field', sa.String(length=200), nullable=False),
    sa.Column('start_year', sa.String(length=10), nullable=False),
    sa.Column('end_year', sa.String(length=10), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_educations_user_id'), 'educations', ['user_id'], unique=False)
    op.create_table('experiences',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('company', sa.String(length=150), nullable=False),
    sa.Column('location', sa.String(length=150), nullable=False),
    sa.Column('start_date', sa.String(length=20), nullable=False),
    sa.Column('end_date', sa.String(length=20), nullable=False),
    sa.Column('current', sa.Boolean(), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_experiences_user_id'), 'experiences', ['user_id'], unique=False)
    op.create_table('follows',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('follower_id', sa.String(length=32), nullable=False),
    sa.Column('following_id', sa.String(length=32), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['follower_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['following_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('follower_id', 'following_id')
    )
    op.create_index(op.f('ix_follows_follower_id'), 'follows', ['follower_id'], unique=False)
    op.create_index(op.f('ix_follows_following_id'), 'follows', ['following_id'], unique=False)
    op.create_table('job_alerts',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('keywords', sa.String(length=200), nullable=False),
    sa.Column('location', sa.String(length=120), nullable=False),
    sa.Column('employment_type', sa.String(length=30), nullable=False),
    sa.Column('work_arrangement', sa.String(length=30), nullable=False),
    sa.Column('min_salary', sa.Float(), nullable=True),
    sa.Column('frequency', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_job_alerts_user_id'), 'job_alerts', ['user_id'], unique=False)
    op.create_table('media_files',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('owner_id', sa.String(length=32), nullable=False),
    sa.Column('folder', sa.String(length=40), nullable=False),
    sa.Column('filename', sa.String(length=200), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('storage_path', sa.String(length=500), nullable=False),
    sa.Column('visibility', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_files_owner_id'), 'media_files', ['owner_id'], unique=False)
    op.create_table('notifications',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('type', sa.String(length=40), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('body', sa.String(length=500), nullable=False),
    sa.Column('link', sa.String(length=300), nullable=False),
    sa.Column('actor_id', sa.String(length=32), nullable=True),
    sa.Column('is_read', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)
    op.create_table('profiles',
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('headline', sa.String(length=220), nullable=False),
    sa.Column('about', sa.Text(), nullable=False),
    sa.Column('location', sa.String(length=150), nullable=False),
    sa.Column('country', sa.String(length=80), nullable=False),
    sa.Column('region', sa.String(length=80), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('profile_photo', sa.String(length=32), nullable=False),
    sa.Column('cover_photo', sa.String(length=32), nullable=False),
    sa.Column('website', sa.String(length=500), nullable=False),
    sa.Column('languages', sa.String(length=500), nullable=False),
    sa.Column('achievements', sa.Text(), nullable=False),
    sa.Column('interests', sa.String(length=1000), nullable=False),
    sa.Column('services', sa.String(length=1000), nullable=False),
    sa.Column('contact_email', sa.String(length=255), nullable=False),
    sa.Column('contact_phone', sa.String(length=40), nullable=False),
    sa.Column('profile_visibility', sa.String(length=20), nullable=False),
    sa.Column('contact_visibility', sa.String(length=20), nullable=False),
    sa.Column('location_visibility', sa.String(length=20), nullable=False),
    sa.Column('completion_pct', sa.Integer(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id')
    )
    op.create_table('projects',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=False),
    sa.Column('url', sa.String(length=500), nullable=False),
    sa.Column('start_date', sa.String(length=20), nullable=False),
    sa.Column('end_date', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_user_id'), 'projects', ['user_id'], unique=False)
    op.create_table('refresh_tokens',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('remember', sa.Boolean(), nullable=False),
    sa.Column('user_agent', sa.String(length=250), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_refresh_tokens_user_id'), 'refresh_tokens', ['user_id'], unique=False)
    op.create_table('reports',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('reporter_id', sa.String(length=32), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('target_id', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.String(length=120), nullable=False),
    sa.Column('details', sa.String(length=1500), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('reviewed_by', sa.String(length=32), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_index(op.f('ix_reports_status'), 'reports', ['status'], unique=False)
    op.create_table('stories',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('file_id', sa.String(length=32), nullable=False),
    sa.Column('type', sa.String(length=20), nullable=False),
    sa.Column('caption', sa.String(length=300), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stories_expires_at'), 'stories', ['expires_at'], unique=False)
    op.create_index(op.f('ix_stories_user_id'), 'stories', ['user_id'], unique=False)
    op.create_table('user_skills',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('skill_name', sa.String(length=80), nullable=False),
    sa.Column('level', sa.String(length=30), nullable=False),
    sa.Column('endorsements', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'skill_name')
    )
    op.create_index(op.f('ix_user_skills_user_id'), 'user_skills', ['user_id'], unique=False)
    op.create_table('verification_codes',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('purpose', sa.String(length=20), nullable=False),
    sa.Column('code_hash', sa.String(length=64), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('window_started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('window_count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'purpose')
    )
    op.create_index(op.f('ix_verification_codes_user_id'), 'verification_codes', ['user_id'], unique=False)
    op.create_table('company_locations',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('address', sa.String(length=400), nullable=False),
    sa.Column('country', sa.String(length=80), nullable=False),
    sa.Column('region', sa.String(length=80), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('area', sa.String(length=150), nullable=False),
    sa.Column('ghana_post_gps', sa.String(length=40), nullable=False),
    sa.Column('landmark', sa.String(length=200), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('phone', sa.String(length=60), nullable=False),
    sa.Column('email', sa.String(length=200), nullable=False),
    sa.Column('opening_time', sa.String(length=20), nullable=False),
    sa.Column('closing_time', sa.String(length=20), nullable=False),
    sa.Column('is_hq', sa.Boolean(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_locations_company_id'), 'company_locations', ['company_id'], unique=False)
    op.create_table('company_members',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('company_id', 'user_id')
    )
    op.create_index(op.f('ix_company_members_company_id'), 'company_members', ['company_id'], unique=False)
    op.create_index(op.f('ix_company_members_user_id'), 'company_members', ['user_id'], unique=False)
    op.create_table('company_offerings',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('description', sa.String(length=800), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_company_offerings_company_id'), 'company_offerings', ['company_id'], unique=False)
    op.create_table('conversation_members',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('conversation_id', sa.String(length=32), nullable=False),
    sa.Column('user_id', sa.String(length=32), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('pinned', sa.Boolean(), nullable=False),
    sa.Column('muted', sa.Boolean(), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conversation_id', 'user_id')
    )
    op.create_index(op.f('ix_conversation_members_conversation_id'), 'conversation_members', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_members_user_id'), 'conversation_members', ['user_id'], unique=False)
    op.create_table('events',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=250), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('organizer_id', sa.String(length=32), nullable=False),
    sa.Column('company_id', sa.String(length=32), nullable=True),
    sa.Column('event_date', sa.Date(), nullable=False),
    sa.Column('start_time', sa.String(length=20), nullable=False),
    sa.Column('end_time', sa.String(length=20), nullable=False),
    sa.Column('location_name', sa.String(length=250), nullable=False),
    sa.Column('address', sa.String(length=400), nullable=False),
    sa.Column('city', sa.String(length=100), nullable=False),
    sa.Column('region', sa.String(length=80), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('cover_image', sa.String(length=32), nullable=False),
    sa.Column('registration_required', sa.Boolean(), nullable=False),
    sa.Column('max_attendees', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_company_id'), 'events', ['company_id'], unique=False)
    op.create_index(op.f('ix_events_event_date'), 'events', ['event_date'], unique=False)
    op.create_index(op.f('ix_events_organizer_id'), 'events', ['organizer_id'], unique=False)
    op.create_table('messages',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('conversation_id', sa.String(length=32), nullable=False),
    sa.Column('sender_id', sa.String(length=32), nullable=False),
    sa.Column('body', sa.String(length=4000), nullable=False),
    sa.Column('attachment_file_id', sa.String(length=32), nullable=False),
    sa.Column('attachment_type', sa.String(length=20), nullable=False),
    sa.Column('reply_to', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('deleted', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sender_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_messages_sender_id'), 'messages', ['sender_id'], unique=False)
