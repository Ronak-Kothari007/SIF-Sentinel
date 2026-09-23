"""Initial schema: 9 tables for SIF Sentinel

Revision ID: 5dd82151203b
Revises: 
Create Date: 2026-09-11 21:56:48.574815

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5dd82151203b'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # 2. reports
    op.create_table(
        'reports',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('report_text', sa.Text(), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=False),
        sa.Column('severity_self_rated', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('submitted_by_user_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. predictions
    op.create_table(
        'predictions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('sif_probability', sa.Float(), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('activity', sa.String(length=100), nullable=True),
        sa.Column('hazard', sa.String(length=100), nullable=True),
        sa.Column('barrier', sa.String(length=100), nullable=True),
        sa.Column('barrier_status', sa.String(length=50), nullable=True),
        sa.Column('model_name', sa.String(length=50), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('escalated', sa.Boolean(), nullable=False),
        sa.Column('escalation_reason', sa.Text(), nullable=True),
        sa.Column('factor_scores_json', sa.Text(), nullable=True),
        sa.Column('governance_notice', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. entities
    op.create_table(
        'entities',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('surface_text', sa.String(length=200), nullable=False),
        sa.Column('normalized_value', sa.String(length=100), nullable=False),
        sa.Column('start_char', sa.Integer(), nullable=False),
        sa.Column('end_char', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. triggered_rules
    op.create_table(
        'triggered_rules',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('rule_id', sa.String(length=50), nullable=False),
        sa.Column('rule_name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.Integer(), nullable=False),
        sa.Column('severity_label', sa.String(length=20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('triggered_signals_json', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. hse_reviews
    op.create_table(
        'hse_reviews',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('reviewer_id', sa.String(length=100), nullable=False),
        sa.Column('decision', sa.String(length=50), nullable=False),
        sa.Column('original_priority', sa.String(length=20), nullable=False),
        sa.Column('final_priority', sa.String(length=20), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 7. feedback
    op.create_table(
        'feedback',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('report_id', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=True),
        sa.Column('feedback_type', sa.String(length=50), nullable=False),
        sa.Column('user_suggested_priority', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 8. risk_patterns
    op.create_table(
        'risk_patterns',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('cluster_name', sa.String(length=100), nullable=False),
        sa.Column('hazard', sa.String(length=100), nullable=False),
        sa.Column('barrier', sa.String(length=100), nullable=False),
        sa.Column('barrier_status', sa.String(length=50), nullable=False),
        sa.Column('occurrences', sa.Integer(), nullable=False),
        sa.Column('risk_band', sa.String(length=20), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('last_detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 9. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.String(length=100), nullable=False),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('risk_patterns')
    op.drop_table('feedback')
    op.drop_table('hse_reviews')
    op.drop_table('triggered_rules')
    op.drop_table('entities')
    op.drop_table('predictions')
    op.drop_table('reports')
    op.drop_table('users')
