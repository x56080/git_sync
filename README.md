# Git Sync Tool - Python 2.7 Implementation

一个用Python 2.7实现的高性能Git仓库同步工具，支持全量/增量同步、分支映射、LFS处理、智能错误处理等企业级功能。

## 🚀 核心特性

### 同步功能
- **智能同步模式**：自动检测全量/增量同步需求，支持强制全量同步
- **统一工作目录架构**：单一工作目录 + 多 remote 设计，减少75%网络传输和磁盘I/O
- **Cherry-pick 同步策略**：保护目标分支现有提交，精确同步源分支变更
- **分支映射与过滤**：支持复杂分支名映射和模式匹配过滤
- **标签同步**：自动同步Git标签到目标仓库

### 高级功能
- **智能LFS检测**：自动检测大文件并启用LFS，支持二进制文件过滤
- **多重认证支持**：HTTP/SSH认证，支持全局和仓库级配置覆盖
- **空仓库处理**：智能处理空仓库和无效HEAD引用情况
- **分支优先级**：master/main分支自动优先处理
- **状态管理**：基于source+dest组合键的精确同步状态跟踪

### 企业级特性
- **详细报告系统**：包含成功/失败/跳过/忽略分支的完整统计
- **健壮错误处理**：push失败、认证错误、网络异常的智能恢复
- **调试支持**：详细的行号日志和调试信息
- **幂等执行**：可安全重复执行，支持中断恢复

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
    password: "your_password_or_token"

repositories:
  - name: "project1"
    source_repo: "group/project1.git"
    dest_repo: "project1.git"
    clean_history: false
    enable_lfs: true
    branch_map:
      "develop": "main"
      "feature/*": "feat/*"
      "release/v*": "rel/v*"
    ignore_branches:
      - "temp/*"
      - "experimental"
      - "sync_state"  # 内部状态分支自动忽略
      
  - name: "project2"
    source_repo: "https://custom-gitlab.com/group/project2.git"
    dest_repo: "project2-mirror.git"
    clean_history: true  # 全量同步时清理历史
    workspace: "./custom-workspace"
    auth:  # 仓库级认证覆盖全局配置
      type: "ssh"
      ssh_private_key: "~/.ssh/project2_key"
    branch_map:
      "master": "main"
    ignore_branches:
      - "hotfix/*"
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

#### 成功同步示例
```
[INFO:156] Starting Git synchronization...
[INFO:172] Loading configuration from 'config.yaml'...
[INFO:245] Repository 'project1' configured with unified work directory
[INFO:253] Configuration loaded successfully. Found 2 repositories.
============================================================
[INFO:890] Starting synchronization for repository: project1
[INFO:944] Fetching latest changes from source remote with tags
[INFO:950] Found 5 branches in source repository: ['main', 'develop', 'feature/auth', 'release/v1.0', 'temp/test']
[INFO:965] Will sync 3 branches after filtering (ignored: temp/test, sync_state)
[INFO:988] Syncing branch: main -> main
[INFO:1033] Branch main -> main synchronized successfully
[INFO:988] Syncing branch: develop -> main  # 分支映射
[INFO:1158] Using cherry-pick strategy for incremental sync
[INFO:1288] Branch develop -> main synchronized successfully
[INFO:1025] Pushing tags to origin
[INFO:1049] Repository 'project1' synchronized successfully!
[INFO:1050] Branches synced: 2, Skipped: 1, New branches: 0, Failed: 0

-------------------- Synchronization Report --------------------
Repository           | Mode        | Synced   | Skipped  | New      | Failed | Ignored | LFS   | Status
---------------------------------------------------------------------------------------------
project1             | incremental | 2        | 1        | 0        | 0      | 2       | true  | success
project2             | full        | 1        | 0        | 1        | 0      | 1       | false | success
---------------------------------------------------------------------------------------------
Total: 2 repositories, Successful: 2, Failed: 0
```

#### 部分失败示例
```
[ERROR:1301] Failed to push branch feature/new: Git command failed: git push origin "feature/new" --tags --force
[ERROR:1016] Branch feature/new synchronization failed
[INFO:1049] Repository 'project1' synchronized with failures!
[INFO:1050] Branches synced: 1, Skipped: 0, New branches: 1, Failed: 1

-------------------- Synchronization Report --------------------
Repository           | Mode        | Synced   | Skipped  | New      | Failed | Ignored | LFS   | Status
---------------------------------------------------------------------------------------------
project1             | incremental | 1        | 0        | 1        | 1      | 0       | false | partial_success
---------------------------------------------------------------------------------------------
Total: 1 repositories, Successful: 0, Failed: 1
```

## 🛡️ 错误处理与恢复

### 智能错误处理
工具内置多层错误处理机制：

- **Push失败恢复**：自动检测push失败，正确统计失败分支
- **认证错误处理**：详细的认证失败诊断和建议
- **网络异常恢复**：支持网络中断后的重试和恢复
- **空仓库处理**：智能处理空仓库和无效HEAD引用
- **分支冲突解决**：Cherry-pick冲突的自动检测和清理

### 状态管理
- **精确状态跟踪**：基于source+dest组合键的状态管理
- **中断恢复**：支持同步过程中断后的安全恢复
- **状态验证**：自动验证同步状态的一致性

## ⚠️ 重要注意事项

### 使用前准备
1. **备份重要数据**：首次使用前请备份重要的Git仓库
2. **测试配置**：建议先在测试仓库上验证配置
3. **权限检查**：确保对源和目标仓库都有适当的访问权限
4. **依赖验证**：确认Git、Git LFS等依赖工具已正确安装

### 性能考虑
1. **大型仓库**：超过5000个提交的仓库建议使用clean_history模式
2. **网络稳定性**：大型仓库同步需要稳定的网络连接
3. **磁盘空间**：确保有足够的磁盘空间用于工作目录
4. **并发限制**：避免同时对同一仓库运行多个同步进程

## 🔧 故障排除指南

### 常见错误类型

#### 1. 认证相关错误
```bash
# 错误示例
fatal: Authentication failed for 'https://github.com/user/repo.git/'

# 解决方案
- 检查用户名和密码/token是否正确
- 确认token有足够的权限（repo权限）
- 验证SSH密钥是否正确配置
```

#### 2. Push失败错误
```bash
# 错误示例
[ERROR:1301] Failed to push branch main: Git command failed: git push origin "main" --tags --force

# 解决方案
- 检查目标仓库的push权限
- 确认分支保护规则设置
- 验证网络连接稳定性
```

#### 3. 空仓库错误
```bash
# 错误示例
fatal: ambiguous argument 'HEAD': unknown revision or path not in the working tree

# 解决方案
- 工具已自动处理此类错误
- 确保源仓库至少有一个提交
- 检查工作目录是否损坏
```

#### 4. LFS相关错误
```bash
# 错误示例
Git LFS: (0 of 1 files) 0 B / 100.0 MB

# 解决方案
- 确保Git LFS已正确安装：git lfs install
- 检查LFS服务器连接
- 验证LFS配额和权限
```

### 高级调试技巧

```bash
# 启用详细输出查看详细日志（包含行号）
python git_sync.py --config config.yaml -v

# 检查Git和LFS版本兼容性
git --version
git lfs version

# 测试仓库连接和认证
git ls-remote <repository_url>

# 验证SSH密钥
ssh -T git@github.com

# 检查工作目录状态
cd workspace && git status

# 手动清理损坏的工作目录
rm -rf workspace && mkdir workspace

# 测试LFS功能
git lfs env
git lfs ls-files
```

### 性能监控

```bash
# 监控同步过程的资源使用
top -p $(pgrep -f git_sync.py)

# 检查磁盘空间使用
du -sh workspace/

# 网络连接测试
ping github.com
curl -I https://api.github.com
```

## 📈 性能优化建议

### 架构优势
- **统一工作目录**：减少75%的网络传输和磁盘I/O
- **智能LFS检测**：只在需要时启用LFS，避免不必要的开销
- **Cherry-pick策略**：保护目标分支历史，减少冲突
- **批量操作**：优化Git命令执行，减少系统调用

### 配置优化
```yaml
# 大型仓库优化配置
repositories:
  - name: "large-repo"
    clean_history: true  # 清理历史减少传输
    lfs_file_threshold_mb: 50  # 降低LFS阈值
    ignore_branches:  # 过滤不必要的分支
      - "feature/*"
      - "temp/*"
```

## 🔄 版本更新日志

### v2.0 (最新)
- ✅ 统一工作目录架构，大幅提升性能
- ✅ 智能push失败处理和统计
- ✅ 空仓库和无效HEAD引用处理
- ✅ 详细的失败分支报告
- ✅ 标签自动同步
- ✅ 二进制文件智能过滤
- ✅ 分支优先级处理（master/main优先）
- ✅ 增强的错误处理和恢复机制

### v1.x (历史版本)
- 基础同步功能
- 分支映射和过滤
- LFS支持
- 基本错误处理

## 📞 技术支持

### 获取帮助
- 启用详细日志：`python git_sync.py --config config.yaml -v`
- 查看配置示例：参考 `config_example.yaml`
- 检查系统兼容性：确保Python 2.7和Git版本兼容

### 贡献代码
欢迎提交Issue和Pull Request来改进这个工具！

## 📄 许可证

Apache License 2.0 - 详见LICENSE文件

Copyright 2025 Git Sync Tool Contributors

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
