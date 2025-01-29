"""Recreate ParamSpiderResult model

Revision ID: 014c88308272
Revises: 5fca9ee2282d
Create Date: 2025-01-27 10:25:44.177170

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014c88308272'
down_revision = '5fca9ee2282d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('paramspider_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('target_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('crawler_id', sa.Integer(), nullable=False),
    sa.Column('level', sa.String(length=10), nullable=False),
    sa.Column('exclude', sa.String(length=255), nullable=True),
    sa.Column('threads', sa.Integer(), nullable=True),
    sa.Column('result_text', sa.Text(), nullable=True),
    sa.Column('total_urls', sa.Integer(), nullable=True),
    sa.Column('unique_parameters', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['crawler_id'], ['crawler.id'], ),
    sa.ForeignKeyConstraint(['target_id'], ['target.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('param_spider_result')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('param_spider_result',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('crawler_id', sa.INTEGER(), nullable=False),
    sa.Column('target_id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('level', sa.VARCHAR(length=20), nullable=True),
    sa.Column('exclude', sa.VARCHAR(length=255), nullable=True),
    sa.Column('threads', sa.INTEGER(), nullable=True),
    sa.Column('parameters', sa.TEXT(), nullable=True),
    sa.Column('total_urls', sa.INTEGER(), nullable=True),
    sa.Column('unique_parameters', sa.INTEGER(), nullable=True),
    sa.Column('status', sa.VARCHAR(length=20), nullable=True),
    sa.Column('error_message', sa.TEXT(), nullable=True),
    sa.Column('start_time', sa.DATETIME(), nullable=True),
    sa.Column('end_time', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['crawler_id'], ['crawler.id'], name='fk_paramspider_crawler'),
    sa.ForeignKeyConstraint(['target_id'], ['target.id'], name='fk_paramspider_target'),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name='fk_paramspider_user'),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('paramspider_results')
    # ### end Alembic commands ###
