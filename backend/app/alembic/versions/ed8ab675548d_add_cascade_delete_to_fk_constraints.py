"""Add cascade delete to FK constraints

Revision ID: ed8ab675548d
Revises: 14028be804b3
Create Date: 2026-10-09 01:22:18.043131

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'ed8ab675548d'
down_revision = '14028be804b3'
branch_labels = None
depends_on = None


def upgrade():
    # documents.audit_id
    op.drop_constraint('documents_audit_id_fkey', 'documents', type_='foreignkey')
    op.create_foreign_key('documents_audit_id_fkey', 'documents', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # claims.audit_id
    op.drop_constraint('claims_audit_id_fkey', 'claims', type_='foreignkey')
    op.create_foreign_key('claims_audit_id_fkey', 'claims', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # claims.document_id
    op.drop_constraint('claims_document_id_fkey', 'claims', type_='foreignkey')
    op.create_foreign_key('claims_document_id_fkey', 'claims', 'documents', ['document_id'], ['id'], ondelete='CASCADE')

    # flags.audit_id
    op.drop_constraint('flags_audit_id_fkey', 'flags', type_='foreignkey')
    op.create_foreign_key('flags_audit_id_fkey', 'flags', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # flags.document_id
    op.drop_constraint('flags_document_id_fkey', 'flags', type_='foreignkey')
    op.create_foreign_key('flags_document_id_fkey', 'flags', 'documents', ['document_id'], ['id'], ondelete='CASCADE')

    # flags.claim_id
    op.drop_constraint('flags_claim_id_fkey', 'flags', type_='foreignkey')
    op.create_foreign_key('flags_claim_id_fkey', 'flags', 'claims', ['claim_id'], ['id'], ondelete='SET NULL')

    # evidence.claim_id
    op.drop_constraint('evidence_claim_id_fkey', 'evidence', type_='foreignkey')
    op.create_foreign_key('evidence_claim_id_fkey', 'evidence', 'claims', ['claim_id'], ['id'], ondelete='CASCADE')

    # evidence.source_document_id
    op.drop_constraint('evidence_source_document_id_fkey', 'evidence', type_='foreignkey')
    op.create_foreign_key('evidence_source_document_id_fkey', 'evidence', 'documents', ['source_document_id'], ['id'], ondelete='CASCADE')

    # passports.audit_id
    op.drop_constraint('passports_audit_id_fkey', 'passports', type_='foreignkey')
    op.create_foreign_key('passports_audit_id_fkey', 'passports', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # audit_log.audit_id
    op.drop_constraint('audit_log_audit_id_fkey', 'audit_log', type_='foreignkey')
    op.create_foreign_key('audit_log_audit_id_fkey', 'audit_log', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # audit_log.actor_id
    op.drop_constraint('audit_log_actor_id_fkey', 'audit_log', type_='foreignkey')
    op.create_foreign_key('audit_log_actor_id_fkey', 'audit_log', 'users', ['actor_id'], ['id'], ondelete='SET NULL')

    # challenges.audit_id
    op.drop_constraint('challenges_audit_id_fkey', 'challenges', type_='foreignkey')
    op.create_foreign_key('challenges_audit_id_fkey', 'challenges', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # challenges.flag_id
    op.drop_constraint('challenges_flag_id_fkey', 'challenges', type_='foreignkey')
    op.create_foreign_key('challenges_flag_id_fkey', 'challenges', 'flags', ['flag_id'], ['id'], ondelete='SET NULL')

    # challenges.raised_by
    op.drop_constraint('challenges_raised_by_fkey', 'challenges', type_='foreignkey')
    op.create_foreign_key('challenges_raised_by_fkey', 'challenges', 'users', ['raised_by'], ['id'], ondelete='CASCADE')

    # decisions.audit_id
    op.drop_constraint('decisions_audit_id_fkey', 'decisions', type_='foreignkey')
    op.create_foreign_key('decisions_audit_id_fkey', 'decisions', 'audits', ['audit_id'], ['id'], ondelete='CASCADE')

    # decisions.flag_id
    op.drop_constraint('decisions_flag_id_fkey', 'decisions', type_='foreignkey')
    op.create_foreign_key('decisions_flag_id_fkey', 'decisions', 'flags', ['flag_id'], ['id'], ondelete='CASCADE')

    # decisions.actor_id
    op.drop_constraint('decisions_actor_id_fkey', 'decisions', type_='foreignkey')
    op.create_foreign_key('decisions_actor_id_fkey', 'decisions', 'users', ['actor_id'], ['id'], ondelete='CASCADE')

    # notifications.user_id
    op.drop_constraint('notifications_user_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_user_id_fkey', 'notifications', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # notifications.audit_id
    op.drop_constraint('notifications_audit_id_fkey', 'notifications', type_='foreignkey')
    op.create_foreign_key('notifications_audit_id_fkey', 'notifications', 'audits', ['audit_id'], ['id'], ondelete='SET NULL')

    # facts.document_id
    op.drop_constraint('facts_document_id_fkey', 'facts', type_='foreignkey')
    op.create_foreign_key('facts_document_id_fkey', 'facts', 'documents', ['document_id'], ['id'], ondelete='CASCADE')

    # items.owner_id
    op.drop_constraint('items_owner_id_fkey', 'items', type_='foreignkey')
    op.create_foreign_key('items_owner_id_fkey', 'items', 'users', ['owner_id'], ['id'], ondelete='CASCADE')


def downgrade():
    pass
