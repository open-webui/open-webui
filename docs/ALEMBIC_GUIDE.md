# Alembic 使用攻略 - Open WebUI

## 🚀 快速开始

### 当前项目配置
- **自动迁移**: 应用启动时自动执行 `alembic upgrade head`
- **位置**: `backend/open_webui/config.py:53-70`
- **结论**: 拉取代码后重启应用即可，无需手动执行迁移

### 工具脚本
```bash
./scripts/migrate.sh current      # 查看当前版本
./scripts/migrate.sh upgrade      # 手动升级
./scripts/check-status.sh         # 检查数据库与代码一致性
```

---

## 📝 开发协作流程

### 场景1: 添加新表

```bash
# 1. 创建迁移脚本
cd backend/open_webui
python -m alembic revision -m "add_user_credits_table"

# 2. 编辑生成的文件 migrations/versions/xxxx_add_user_credits_table.py
```

```python
def upgrade():
    op.create_table(
        'user_credits',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('credits', sa.NUMERIC(20, 6), server_default='0', nullable=False),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_credits_user_id', 'user_credits', ['user_id'])

def downgrade():
    op.drop_index('idx_user_credits_user_id', 'user_credits')
    op.drop_table('user_credits')
```

```bash
# 3. 测试迁移
source venv/bin/activate
cd open_webui
python -m alembic upgrade head        # 升级
python -m alembic downgrade -1        # 降级测试
python -m alembic upgrade head        # 重新升级

# 4. 验证
python -c "
from open_webui.internal.db import get_db
from sqlalchemy import inspect
with get_db() as db:
    print(inspect(db.bind).get_table_names())
"

# 5. 提交
git add migrations/versions/xxxx_add_user_credits_table.py
git add open_webui/models/credits.py
git commit -m "feat: add user credits system"
git push
```

### 场景2: 修改现有表

```bash
# 1. 创建迁移
python -m alembic revision -m "add_email_verified_to_user"

# 2. 编辑迁移文件
```

```python
def upgrade():
    # 添加字段
    op.add_column('user', sa.Column('email_verified', sa.Boolean(),
                  server_default='false', nullable=False))

    # 添加索引
    op.create_index('idx_user_email_verified', 'user', ['email_verified'])

def downgrade():
    op.drop_index('idx_user_email_verified', 'user')
    op.drop_column('user', 'email_verified')
```

```bash
# 3. 测试并提交（同场景1步骤3-5）
```

### 场景3: 数据迁移

```python
from sqlalchemy import text

def upgrade():
    connection = op.get_bind()

    # 1. 添加新字段
    op.add_column('user', sa.Column('full_name', sa.String(), nullable=True))

    # 2. 迁移数据
    connection.execute(text("""
        UPDATE user
        SET full_name = name
        WHERE full_name IS NULL
    """))

    # 3. 设置为NOT NULL
    op.alter_column('user', 'full_name', nullable=False)

def downgrade():
    op.drop_column('user', 'full_name')
```

### 场景4: 多人协作冲突

**问题**: 两个分支同时创建迁移，产生多个head

```bash
# 1. 发现问题
python -m alembic heads
# 输出: abc123 (head), def456 (head)  ← 两个头部

# 2. 合并迁移
python -m alembic merge -m "merge_feature_branches" heads

# 3. 编辑生成的合并迁移
# migrations/versions/xxx_merge_feature_branches.py
# down_revision = ('abc123', 'def456')  # 已自动填充

# 4. 应用合并
python -m alembic upgrade head

# 5. 提交
git add migrations/versions/xxx_merge_feature_branches.py
git commit -m "chore: merge migration branches"
```

---

## 🏭 生产环境迁移

### 方式1: 自动迁移（推荐）

```bash
# Docker 环境
git pull
docker-compose restart
# ✅ 应用启动时自动执行迁移

# Systemd 环境
git pull
systemctl restart open-webui
# ✅ 应用启动时自动执行迁移

# 验证
./scripts/check-status.sh
```

**优点**: 零停机、自动化、幂等性
**适用**: 小型迁移、添加字段、创建索引

### 方式2: 手动迁移（安全）

```bash
# 1. 备份数据库（PostgreSQL）
pg_dump -U user -d openwebui_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# 2. 记录当前版本
cd backend/open_webui
python -m alembic current > migration_before.txt

# 3. 拉取代码
git pull

# 4. 查看待执行的迁移
python -m alembic history | grep -A5 "$(cat migration_before.txt | awk '{print $1}')"

# 5. 手动执行迁移
python -m alembic upgrade head

# 6. 验证
python -m alembic current > migration_after.txt
diff migration_before.txt migration_after.txt

# 7. 重启应用
systemctl restart open-webui

# 8. 功能验证
curl http://localhost:8080/health
```

**优点**: 可控、可验证、可回滚
**适用**: 大型迁移、数据迁移、高风险变更

### 方式3: 蓝绿部署（零停机）

```bash
# 1. 部署新版本到绿环境（不启动）
git clone /app/open-webui /app/open-webui-green
cd /app/open-webui-green
git pull

# 2. 在绿环境执行迁移
cd backend/open_webui
python -m alembic upgrade head

# 3. 启动绿环境（连接同一数据库）
systemctl start open-webui-green

# 4. 切换流量（Nginx/负载均衡）
# 从 localhost:8080 → localhost:8081

# 5. 停止蓝环境
systemctl stop open-webui

# 6. 验证后删除蓝环境
rm -rf /app/open-webui
mv /app/open-webui-green /app/open-webui
```

---

## 🔧 常用命令速查

### 查看状态
```bash
python -m alembic current             # 当前版本
python -m alembic heads               # 最新版本
python -m alembic history             # 历史记录
python -m alembic branches            # 分支情况
```

### 执行迁移
```bash
python -m alembic upgrade head        # 升级到最新
python -m alembic upgrade +1          # 升级1个版本
python -m alembic upgrade abc123      # 升级到指定版本
python -m alembic downgrade -1        # 降级1个版本
python -m alembic downgrade abc123    # 降级到指定版本
```

### 创建迁移
```bash
python -m alembic revision -m "description"              # 创建空迁移
python -m alembic merge -m "merge branches" heads        # 合并分支
```

---

## ⚠️ 注意事项

### 1. 禁止使用 autogenerate
```bash
# ❌ 不要用（循环依赖问题）
python -m alembic revision --autogenerate -m "auto"

# ✅ 手动编写
python -m alembic revision -m "add_feature"
# 然后手动编写 upgrade/downgrade 函数
```

### 2. 数据库类型（PostgreSQL）

```python
# 使用 PostgreSQL 特定类型
from sqlalchemy.dialects import postgresql

def upgrade():
    op.add_column('user',
        sa.Column('balance', postgresql.NUMERIC(20, 6),
                  server_default='0', nullable=False))
```

### 3. 大表索引创建

```python
# PostgreSQL - 在线创建索引
op.create_index(
    'idx_large_table_field',
    'large_table',
    ['field'],
    postgresql_concurrently=True  # 不锁表
)

# 注意: CONCURRENTLY 需要在事务外执行
# 在迁移文件顶部添加:
# revision = 'xxx'
# down_revision = 'yyy'
# branch_labels = None
# depends_on = None
#
# # 禁用事务
# def upgrade():
#     op.execute('COMMIT')
#     ...
```

### 4. 必须编写 downgrade

```python
# ❌ 错误
def downgrade():
    pass

# ✅ 正确
def downgrade():
    op.drop_index('idx_user_balance')
    op.drop_column('user', 'balance')
```

---

## 🚨 故障处理

### 迁移失败恢复

```bash
# 1. 查看当前状态
python -m alembic current

# 2. 检查数据库是否处于中间状态
psql -U user -d dbname
\dt  # 查看表
# 手动删除失败迁移创建的表/字段

# 3. 标记为指定版本（谨慎使用）
python -m alembic stamp <version_id>

# 4. 重新执行
python -m alembic upgrade head
```

### 回滚到指定版本

```bash
# 1. 查看历史
python -m alembic history

# 2. 回滚
python -m alembic downgrade <version_id>

# 3. 重启应用
systemctl restart open-webui
```

### 强制重新初始化（危险）

```bash
# ⚠️ 会丢失所有数据
# 1. 删除 alembic_version 表
psql -U user -d dbname -c "DROP TABLE alembic_version;"

# 2. 删除所有业务表
psql -U user -d dbname -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 3. 重新执行所有迁移
python -m alembic upgrade head
```

---

## ✅ 最佳实践检查清单

### 开发阶段
- [ ] 修改模型后立即创建迁移脚本
- [ ] 迁移脚本命名清晰（描述变更内容）
- [ ] 编写完整的 upgrade 和 downgrade 函数
- [ ] 使用 PostgreSQL 特定类型（NUMERIC, JSONB 等）
- [ ] 测试升级和降级流程
- [ ] Code Review 检查迁移逻辑
- [ ] 提交迁移脚本到 Git

### 部署阶段
- [ ] 备份生产数据库
- [ ] 记录当前迁移版本
- [ ] 查看待执行的迁移内容
- [ ] 评估迁移风险（大表、数据迁移）
- [ ] 选择合适的迁移方式（自动/手动）
- [ ] 执行迁移
- [ ] 验证迁移版本
- [ ] 重启应用
- [ ] 功能验证
- [ ] 监控应用日志

---

## 📊 迁移决策树

```
新功能需要数据库变更
    ↓
修改 models/*.py
    ↓
创建迁移脚本 (alembic revision -m "xxx")
    ↓
编写 upgrade/downgrade 函数
    ↓
┌─────────────────────────────┐
│  影响是否 > 1000万行数据？   │
└─────────┬───────────────────┘
          │
    ┌─────┴─────┐
    NO         YES
    │           │
    │      使用分批迁移/在线DDL
    ↓           ↓
测试升降级   准备回滚方案
    │           │
    └─────┬─────┘
          ↓
提交代码 (git commit)
          ↓
    ┌───────────┐
    │ 生产部署  │
    └─────┬─────┘
          │
    ┌─────┴─────┐
   风险评估
    │
┌───┴───┐
低     高
│       │
│   手动迁移
│   + 备份
自动   + 蓝绿
迁移
```

---

## 📚 参考资源

- **项目文档**: `docs/DATABASE_CONSISTENCY_GUIDE.md` - 完整指南
- **迁移工具**: `scripts/migrate.sh` - 便捷脚本
- **状态检查**: `scripts/check-status.sh` - 一致性验证
- **Alembic 官方文档**: https://alembic.sqlalchemy.org/

---

**版本**: v1.0
**更新**: 2025-12-06
**适用**: Open WebUI Next
