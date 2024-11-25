"""reset

Revision ID: 4334050a65d5
Revises: 074b4a964b75
Create Date: 2024-11-25 14:59:24.590684

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4334050a65d5'
down_revision = '074b4a964b75'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('proveedor_material')
    op.drop_table('proveedor')
    with op.batch_alter_table('pared', schema=None) as batch_op:
        batch_op.add_column(sa.Column('altura', sa.Float(), nullable=False))
        batch_op.add_column(sa.Column('ancho', sa.Float(), nullable=False))

    with op.batch_alter_table('proyecto', schema=None) as batch_op:
        batch_op.alter_column('fecha_creacion',
               existing_type=sa.DATE(),
               type_=sa.DateTime(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('proyecto', schema=None) as batch_op:
        batch_op.alter_column('fecha_creacion',
               existing_type=sa.DateTime(),
               type_=sa.DATE(),
               existing_nullable=False)

    with op.batch_alter_table('pared', schema=None) as batch_op:
        batch_op.drop_column('ancho')
        batch_op.drop_column('altura')

    op.create_table('proveedor',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('nombre', mysql.VARCHAR(length=255), nullable=False),
    sa.Column('contacto', mysql.VARCHAR(length=255), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    op.create_table('proveedor_material',
    sa.Column('id_proveedor', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('id_material', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['id_material'], ['material.id'], name='proveedor_material_ibfk_1'),
    sa.ForeignKeyConstraint(['id_proveedor'], ['proveedor.id'], name='proveedor_material_ibfk_2'),
    sa.PrimaryKeyConstraint('id_proveedor', 'id_material'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###