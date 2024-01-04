"""Add timestamp to Message

Revision ID: 988ad325cd7a
Revises: 1d3b2c827b97
Create Date: 2023-12-14 08:23:07.713161

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '988ad325cd7a'
down_revision = '1d3b2c827b97'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.add_column(sa.Column('timestamp', sa.DateTime(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_column('timestamp')

    # ### end Alembic commands ###