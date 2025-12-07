"""Change billing amounts to integer (milli-yuan precision)

Revision ID: f8c9d0e4a3b2
Revises: e5f8a9b3c2d1
Create Date: 2025-12-06 12:00:00.000000

将金额字段从 DECIMAL/REAL 改为 INTEGER，以毫为单位存储（1元 = 10000毫，精度0.0001元）
- user.balance: Decimal -> Integer (毫)
- user.total_consumed: Decimal -> Integer (毫)
- model_pricing.input_price: Decimal -> Integer (毫/百万tokens)
- model_pricing.output_price: Decimal -> Integer (毫/百万tokens)
- billing_log.total_cost: Decimal -> Integer (毫)
- billing_log.balance_after: Decimal -> Integer (毫)
- recharge_log.amount: Decimal -> Integer (毫)

注意：现有数据将乘以10000转换（元 -> 毫）
"""

from alembic import op
import sqlalchemy as sa


revision = "f8c9d0e4a3b2"
down_revision = "607801a77d0d"  # merge billing and reply_to heads
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库：将金额字段改为整数（分）"""
    connection = op.get_bind()
    is_sqlite = connection.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite 不支持直接修改列类型，需要重建表
        # 1. user 表
        with op.batch_alter_table("user") as batch_op:
            # SQLite: 先转换现有数据（元 * 10000 = 毫）
            connection.execute(sa.text("""
                UPDATE user
                SET balance = CAST(balance * 10000 AS INTEGER),
                    total_consumed = CAST(total_consumed * 10000 AS INTEGER)
            """))

            # 修改列类型
            batch_op.alter_column("balance",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False,
                                existing_server_default="0")
            batch_op.alter_column("total_consumed",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False,
                                existing_server_default="0")

        # 2. model_pricing 表
        with op.batch_alter_table("model_pricing") as batch_op:
            connection.execute(sa.text("""
                UPDATE model_pricing
                SET input_price = CAST(input_price * 10000 AS INTEGER),
                    output_price = CAST(output_price * 10000 AS INTEGER)
            """))

            batch_op.alter_column("input_price",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False)
            batch_op.alter_column("output_price",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False)

        # 3. billing_log 表
        with op.batch_alter_table("billing_log") as batch_op:
            connection.execute(sa.text("""
                UPDATE billing_log
                SET total_cost = CAST(total_cost * 10000 AS INTEGER),
                    balance_after = CAST(COALESCE(balance_after, 0) * 10000 AS INTEGER)
            """))

            batch_op.alter_column("total_cost",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False)
            batch_op.alter_column("balance_after",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=True)

        # 4. recharge_log 表
        with op.batch_alter_table("recharge_log") as batch_op:
            connection.execute(sa.text("""
                UPDATE recharge_log
                SET amount = CAST(amount * 10000 AS INTEGER)
            """))

            batch_op.alter_column("amount",
                                existing_type=sa.REAL,
                                type_=sa.Integer(),
                                existing_nullable=False)

    else:
        # PostgreSQL 支持直接修改
        # 1. 先转换数据（元 * 10000 = 毫）
        connection.execute(sa.text("""
            UPDATE "user"
            SET balance = CAST(balance * 10000 AS INTEGER),
                total_consumed = CAST(total_consumed * 10000 AS INTEGER)
        """))
        connection.execute(sa.text("""
            UPDATE model_pricing
            SET input_price = CAST(input_price * 10000 AS INTEGER),
                output_price = CAST(output_price * 10000 AS INTEGER)
        """))
        connection.execute(sa.text("""
            UPDATE billing_log
            SET total_cost = CAST(total_cost * 10000 AS INTEGER),
                balance_after = CAST(COALESCE(balance_after, 0) * 10000 AS INTEGER)
        """))
        connection.execute(sa.text("""
            UPDATE recharge_log
            SET amount = CAST(amount * 10000 AS INTEGER)
        """))

        # 2. 修改列类型
        op.alter_column("user", "balance", type_=sa.Integer())
        op.alter_column("user", "total_consumed", type_=sa.Integer())
        op.alter_column("model_pricing", "input_price", type_=sa.Integer())
        op.alter_column("model_pricing", "output_price", type_=sa.Integer())
        op.alter_column("billing_log", "total_cost", type_=sa.Integer())
        op.alter_column("billing_log", "balance_after", type_=sa.Integer())
        op.alter_column("recharge_log", "amount", type_=sa.Integer())


def downgrade():
    """降级数据库：将整数（分）改回 Decimal（元）"""
    connection = op.get_bind()
    is_sqlite = connection.dialect.name == "sqlite"
    is_postgresql = connection.dialect.name == "postgresql"

    numeric_type = sa.NUMERIC(20, 6) if is_postgresql else sa.REAL

    if is_sqlite:
        # SQLite 降级
        with op.batch_alter_table("user") as batch_op:
            batch_op.alter_column("balance", type_=sa.REAL)
            batch_op.alter_column("total_consumed", type_=sa.REAL)

        with op.batch_alter_table("model_pricing") as batch_op:
            batch_op.alter_column("input_price", type_=sa.REAL)
            batch_op.alter_column("output_price", type_=sa.REAL)

        with op.batch_alter_table("billing_log") as batch_op:
            batch_op.alter_column("total_cost", type_=sa.REAL)
            batch_op.alter_column("balance_after", type_=sa.REAL)

        with op.batch_alter_table("recharge_log") as batch_op:
            batch_op.alter_column("amount", type_=sa.REAL)

        # 转换数据（毫 / 10000 = 元）
        connection.execute(sa.text("""
            UPDATE user
            SET balance = CAST(balance AS REAL) / 10000.0,
                total_consumed = CAST(total_consumed AS REAL) / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE model_pricing
            SET input_price = CAST(input_price AS REAL) / 10000.0,
                output_price = CAST(output_price AS REAL) / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE billing_log
            SET total_cost = CAST(total_cost AS REAL) / 10000.0,
                balance_after = CAST(balance_after AS REAL) / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE recharge_log
            SET amount = CAST(amount AS REAL) / 10000.0
        """))

    else:
        # PostgreSQL 降级
        op.alter_column("user", "balance", type_=numeric_type)
        op.alter_column("user", "total_consumed", type_=numeric_type)
        op.alter_column("model_pricing", "input_price", type_=numeric_type)
        op.alter_column("model_pricing", "output_price", type_=numeric_type)
        op.alter_column("billing_log", "total_cost", type_=numeric_type)
        op.alter_column("billing_log", "balance_after", type_=numeric_type)
        op.alter_column("recharge_log", "amount", type_=numeric_type)

        connection.execute(sa.text("""
            UPDATE "user"
            SET balance = balance / 10000.0,
                total_consumed = total_consumed / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE model_pricing
            SET input_price = input_price / 10000.0,
                output_price = output_price / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE billing_log
            SET total_cost = total_cost / 10000.0,
                balance_after = balance_after / 10000.0
        """))
        connection.execute(sa.text("""
            UPDATE recharge_log
            SET amount = amount / 10000.0
        """))
