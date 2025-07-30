# Git Sync Tool - Python 2.7 Implementation

一个用Python 2.7实现的Git仓库同步工具，支持全量/增量同步、分支映射、LFS处理等功能。

## 功能特性

- **全量和增量同步**：自动检测是否需要全量同步或增量同步
- **分支映射**：支持将源分支映射到不同的目标分支名
- **分支过滤**：可以忽略指定的分支模式
- **Git LFS支持**：自动检测大文件并启用LFS
- **多种认证方式**：支持HTTP和SSH认证
- **配置继承**：支持全局配置和仓库级配置的继承与覆盖
- **详细报告**：提供同步过程的详细进度和结果报告
- **幂等执行**：可以安全地重复执行
- **历史清理**：支持在全量同步时清理Git历史

## 系统要求

- Python 2.7
- Git (必需)
- Git LFS (可选，仅在使用LFS功能时需要)
- PyYAML库

## 安装依赖

```bash
# 安装PyYAML
pip install PyYAML

# 确保Git已安装
git --version

# 如果需要LFS支持，安装Git LFS
git lfs install
```

## 使用方法

### 基本用法

```bash
# 使用配置文件进行同步
python git_sync.py --config config.yaml

# 强制全量同步所有仓库
python git_sync.py --config config.yaml --force-full

# 启用详细输出
python git_sync.py --config config.yaml -v
```

### 配置文件

配置文件使用YAML格式，包含全局设置和仓库列表。参考 `config_example.yaml` 了解完整配置选项。

#### 基本配置结构

```yaml
global:
  source_base_url: "https://gitlab.example.com/"
  dest_base_url: "https://github.com/myorg/"
  commit_user_name: "Git Sync Bot"
  commit_user_email: "sync-bot@example.com"
  lfs_file_threshold_mb: 100
  lfs_total_threshold_mb: 500
  workspace: "./workspace"
  auth:
    type: "http"
    username: "your_username"
    password: "your_password"

repositories:
  - name: "project1"
    source_repo: "group/project1.git"
    dest_repo: "project1.git"
    clean_history: false
    enable_lfs: true
    branch_map:
      "develop": "main"
    ignore_branches:
      - "temp/*"
      - "experimental"
```

### 配置说明

#### 全局配置 (global)

- `source_base_url`: 源仓库的基础URL
- `dest_base_url`: 目标仓库的基础URL
- `commit_user_name`: Git提交的用户名
- `commit_user_email`: Git提交的邮箱
- `lfs_file_threshold_mb`: 单个文件LFS阈值(MB)
- `lfs_total_threshold_mb`: 总变更LFS阈值(MB)
- `workspace`: 本地工作目录
- `auth`: 认证配置

#### 仓库配置 (repositories)

- `name`: 仓库名称（必需）
- `source_repo`: 源仓库路径或完整URL
- `dest_repo`: 目标仓库路径或完整URL
- `clean_history`: 是否在全量同步时清理历史
- `workspace`: 自定义工作目录（可选）
- `enable_lfs`: 是否启用LFS
- `lfs_file_threshold_mb`: 自定义文件LFS阈值
- `lfs_total_threshold_mb`: 自定义总量LFS阈值
- `auth`: 仓库级认证配置（覆盖全局配置）
- `branch_map`: 分支映射配置
- `ignore_branches`: 要忽略的分支模式列表

### 认证配置

#### HTTP认证

```yaml
auth:
  type: "http"
  username: "your_username"
  password: "your_password"
```

#### SSH认证

```yaml
auth:
  type: "ssh"
  ssh_private_key: "~/.ssh/id_rsa"
```

### 同步模式

#### 全量同步

- 首次同步时自动使用
- 使用 `--force-full` 参数强制全量同步
- 如果配置了 `clean_history: true`，将清理Git历史

#### 增量同步

- 后续同步时自动使用
- 只同步自上次同步以来的新提交
- 新分支会自动进行全量同步

### LFS处理

工具会自动检测大文件并启用LFS：

1. 当单个文件超过 `lfs_file_threshold_mb` 时，该文件使用LFS
2. 当总变更超过 `lfs_total_threshold_mb` 时，按提交逐个同步
3. LFS检测延迟到实际使用时进行

### 输出示例

```
[INFO] Starting Git synchronization...
[INFO] Loading configuration from 'config.yaml'...
[INFO] Repository 'project1' configured.
[INFO] Configuration loaded successfully. Found 1 repositories.
============================================================
[INFO] Starting synchronization for repository: project1
[INFO] Processing source repository for 'project1'...
[INFO] Processing destination repository for 'project1'...
[INFO] Sync mode: INCREMENTAL
[INFO] Found 3 branches in source repository
[INFO] Will sync 2 branches (after filtering)
[INFO] Syncing branch: main -> main
[INFO] Branch main -> main synchronized successfully
[INFO] Repository 'project1' synchronized successfully!
[INFO] Branches synced: 2, New branches: 0

================================================================================
SYNCHRONIZATION SUMMARY REPORT
================================================================================
Total repositories: 1
Successful: 1
Failed: 0
Start time: 2024-07-24T17:51:03
End time: 2024-07-24T17:52:15

Repository Details:
----------------------------------------
✓ project1 [INCREMENTAL]
    Branches synced: 2
    New branches: 0
================================================================================
```

## 错误处理

工具提供详细的错误信息和日志：

- 使用 `-v` 参数获取详细调试信息
- 检查依赖工具是否正确安装
- 验证配置文件格式和认证信息
- 确保网络连接和仓库访问权限

## 注意事项

1. **备份重要数据**：首次使用前请备份重要的Git仓库
2. **测试配置**：建议先在测试仓库上验证配置
3. **网络稳定性**：大型仓库同步需要稳定的网络连接
4. **权限要求**：确保对源和目标仓库都有适当的访问权限
5. **Python 2.7兼容性**：代码专为Python 2.7设计

## 故障排除

### 常见问题

1. **认证失败**：检查用户名、密码或SSH密钥配置
2. **LFS错误**：确保Git LFS已正确安装和配置
3. **网络超时**：检查网络连接和仓库URL
4. **权限错误**：确保对目标仓库有推送权限

### 调试技巧

```bash
# 启用详细输出查看详细日志
python git_sync.py --config config.yaml -v

# 检查Git和LFS版本
git --version
git lfs version

# 测试仓库连接
git ls-remote <repository_url>
```

## 许可证

MIT License

