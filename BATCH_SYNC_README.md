# Git Sync Batch Tool 使用说明

## 概述

Git Sync Batch Tool 提供跨平台的批量同步解决方案，支持一次性执行多个 Git 仓库的同步任务。根据不同平台的特点，提供了两种不同的实现方式。

## 文件说明

- `git_sync_batch.sh` - Linux/Unix/macOS 版本（完整功能版）
- `git_sync_batch.bat` - Windows 版本（简化版）
- `batch_configs.txt` - 默认的配置列表文件，包含要执行的同步命令

## 版本差异

### 📋 功能对比

| 功能特性 | Linux/Unix/macOS (.sh) | Windows (.bat) |
|---------|----------------------|----------------|
| 一次性批量同步 | ✅ `--once` | ✅ `--once` |
| 守护进程模式 | ✅ `--daemon` | ❌ 已移除 |
| 循环执行模式 | ✅ `--count` + `--interval` | ✅ `--count` + `--interval` |
| 多轮执行控制 | ✅ `-n/--count` 参数 | ✅ `-n/--count` 参数 |
| 进程管理 | ✅ `--stop`, `--status` | ❌ 已移除 |
| 日志目录设置 | ✅ `--log-dir` | ✅ `--log-dir` |
| 详细输出 | ✅ `--verbose` | ✅ `--verbose` |
| 命令输出控制 | 仅日志记录 | 仅日志记录 |

### 🏗️ 架构特点

**Linux/Unix/macOS 版本**：
- **完整功能**：保留传统的守护进程架构
- **后台运行**：支持真正的守护进程模式
- **进程管理**：完整的启动、停止、状态查询功能
- **灵活配置**：支持自定义日志目录等高级选项

**Windows 版本**：
- **简化架构**：移除复杂的守护进程逻辑，专注核心功能
- **循环执行**：支持设置执行轮数和间隔时间
- **稳定可靠**：优化的错误处理和参数验证
- **易于使用**：简洁的命令行界面和清晰的输出

## 使用方法

### 基本语法

**Linux/Unix/macOS:**
```bash
./git_sync_batch.sh [OPTIONS]
```

**Windows:**
```cmd
git_sync_batch.bat [OPTIONS]
```

### 命令行选项

#### Linux/Unix/macOS 版本 (.sh)

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-o, --once` | 执行一次批量同步后退出 | - |
| `-d, --daemon` | 以守护进程模式运行 | - |
| `-s, --stop` | 停止正在运行的守护进程 | - |
| `-t, --status` | 查看守护进程状态 | - |
| `-n, --count NUMBER` | 设置执行轮数（兼容所有模式） | `1` |
| `-c, --config-list FILE` | 指定配置列表文件 | `batch_configs.txt` |
| `-i, --interval SECONDS` | 设置同步间隔（秒） | `86400` (24小时) |
| `-l, --log-dir DIR` | 指定日志目录 | `./logs` |
| `-v, --verbose` | 启用详细输出 | - |
| `-h, --help` | 显示帮助信息 | - |

#### Windows 版本 (.bat)

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-o, --once` | 执行一次批量同步后退出 | - |
| `-n, --count NUMBER` | 设置执行轮数 | `1` |
| `-t, --interval SECONDS` | 设置执行间隔（秒） | `3600` |
| `-c, --config-list FILE` | 指定配置列表文件 | `batch_configs.txt` |
| `-l, --log-dir DIR` | 指定日志目录 | `./logs` |
| `-v, --verbose` | 启用详细输出 | - |
| `-h, --help` | 显示帮助信息 | - |

**架构说明**：
- **Linux 版本**：保留完整的守护进程功能，适合服务器环境长期运行
- **Windows 版本**：简化为循环执行模式，专注批量同步核心功能

## 配置文件格式

配置列表文件（如 `batch_configs.txt`）的格式：

```bash
# Git Sync Batch Configuration List
# 每行包含一个要执行的同步命令
# 以 # 开头的行是注释，会被忽略
# 空行也会被忽略

# 示例同步命令
python ./git_sync.py --config sync_sdb_mirror_to_github.yaml
python ./git_sync.py --config sync_sac_to_github.yaml
python ./git_sync.py --config sync_sdb_mygithub.yaml

# 可以为特定配置添加详细模式
python ./git_sync.py --config sync_config.yaml --verbose

# 也可以指定不同的 Python 版本
python3 ./git_sync_py3.py --config sync_config.yaml
```

## 使用示例

### 1. 一次性批量同步（两个版本通用）

**Linux/Unix/macOS:**
```bash
# 使用默认配置文件执行一次同步
./git_sync_batch.sh --once

# 使用自定义配置文件
./git_sync_batch.sh --once --config-list my_configs.txt

# 启用详细输出
./git_sync_batch.sh --once --verbose
```

**Windows:**
```cmd
# 使用默认配置文件执行一次同步
git_sync_batch.bat --once

# 使用自定义配置文件
git_sync_batch.bat --once --config-list my_configs.txt

# 启用详细输出
git_sync_batch.bat --once --verbose
```

### 2. Linux/Unix/macOS 版本：守护进程模式

```bash
# 每24小时同步一次（默认）
./git_sync_batch.sh --daemon

# 每12小时同步一次
./git_sync_batch.sh --daemon --interval 43200

# 每6小时同步一次
./git_sync_batch.sh --daemon --interval 21600

# 使用自定义配置文件启动守护进程
./git_sync_batch.sh --daemon --config-list prod_configs.txt

# 查看守护进程状态
./git_sync_batch.sh --status

# 停止守护进程
./git_sync_batch.sh --stop
```

### 3. Linux/Unix/macOS 版本：多轮执行模式（-n 参数）

```bash
# 一次性执行3轮同步，每轮间隔300秒
./git_sync_batch.sh --once --count 3 --interval 300

# 直接执行2轮同步，每轮间隔600秒
./git_sync_batch.sh --count 2 --interval 600

# 守护进程模式：每个周期执行2轮同步，周期间隔3600秒
./git_sync_batch.sh --daemon --count 2 --interval 3600

# 守护进程模式：每个周期执行3轮同步（轮间无等待），周期间隔7200秒
./git_sync_batch.sh --daemon --count 3 --interval 7200
```

**-n 参数行为说明**：
- **非守护进程模式**：执行指定轮数后退出，轮间有用户指定的间隔
- **守护进程模式**：每个周期内连续执行指定轮数（轮间无等待），周期间有间隔
- **--once 模式**：与 --count 结合，一次性执行多轮后退出

### 4. Windows 版本：循环执行模式

```cmd
# 执行2轮同步，每轮间隔60秒（默认）
git_sync_batch.bat --count 2

# 执行3轮同步，每轮间隔300秒（5分钟）
git_sync_batch.bat --count 3 --interval 300

# 执行5轮同步，每轮间隔1800秒（30分钟）
git_sync_batch.bat --count 5 --interval 1800

# 使用自定义配置文件进行循环同步
git_sync_batch.bat --count 3 --config-list my_configs.txt
```

## 日志系统

### 日志输出特性

#### 平台差异
- **Linux/Unix/macOS 版本**：
  - 屏幕显示：执行信息、统计信息、错误信息
  - 日志文件：完整记录所有执行过程和命令输出
  
- **Windows 版本**：
  - 屏幕显示：仅显示统计信息和等待信息（保持简洁）
  - 日志文件：完整记录执行信息、命令输出、成功/失败状态

#### 共同特性
- **统计信息**：每轮显示总数、成功数、失败数
- **时间记录**：详细的时间戳和持续时间
- **错误处理**：失败命令的详细错误信息
- **日志文件**：按日期自动分割（格式：batch_YYYYMMDD.log）

### 日志示例
```
[INFO] Starting batch sync - Round 1 of 2
[INFO] Config file: batch_configs.txt
[INFO] Found 3 sync commands

[INFO] Executing command 1/3: python ./git_sync.py --config sync_config1.yaml
[SUCCESS] Command completed successfully

[INFO] Executing command 2/3: python ./git_sync.py --config sync_config2.yaml
[SUCCESS] Command completed successfully

[INFO] Executing command 3/3: python ./git_sync.py --config sync_config3.yaml
[SUCCESS] Command completed successfully

[INFO] Round 1 completed - Total: 3, Success: 3, Failed: 0
[INFO] Waiting 60 seconds until next sync...

[INFO] Starting batch sync - Round 2 of 2
[INFO] Round 2 completed - Total: 3, Success: 3, Failed: 0

[INFO] All rounds completed successfully!
```

## 常见使用场景

### Linux/Unix/macOS 版本场景

#### 1. 服务器环境长期运行
```bash
# 生产环境每天凌晨2点自动同步
./git_sync_batch.sh --daemon --interval 86400

# 开发环境每6小时同步一次
./git_sync_batch.sh --daemon --interval 21600
```

#### 2. 守护进程管理
```bash
# 启动守护进程
./git_sync_batch.sh --daemon --config-list prod_configs.txt

# 监控运行状态
./git_sync_batch.sh --status

# 维护时停止服务
./git_sync_batch.sh --stop
```

### Windows 版本场景

#### 1. 定时批量同步
```cmd
# 每天执行3轮同步，每轮间隔8小时
git_sync_batch.bat --count 3 --interval 28800

# 工作日每2小时同步一次，连续4轮
git_sync_batch.bat --count 4 --interval 7200
```

#### 2. 开发环境快速同步
```cmd
# 开发期间每30分钟同步一次，连续执行5轮
git_sync_batch.bat --count 5 --interval 1800
```

### 通用场景

#### 3. 手动批量同步
```bash
# Linux/macOS
./git_sync_batch.sh --once --verbose

# Windows
git_sync_batch.bat --once --verbose
```

#### 4. 测试配置
```bash
# Linux/macOS
./git_sync_batch.sh --once --config-list test_configs.txt

# Windows
git_sync_batch.bat --once --config-list test_configs.txt
```

## 错误处理

### 常见错误及解决方案

1. **配置文件不存在**
   ```
   [ERROR] Config list file not found: batch_configs.txt
   ```
   - 检查配置文件路径是否正确
   - 确保配置文件存在且可读

2. **没有有效的同步命令**
   ```
   [ERROR] No valid sync commands found in config list file
   ```
   - 检查配置文件格式
   - 确保至少有一行有效的 python 命令

3. **参数验证错误**
   ```
   [ERROR] Invalid count value. Please provide a positive integer.
   [ERROR] Invalid interval value. Please provide a positive integer.
   ```
   - 确保 --count 和 --interval 参数为正整数
   - 检查参数格式是否正确

4. **权限问题**
   - Linux/Unix/macOS：确保脚本有执行权限 `chmod +x git_sync_batch.sh`
   - Windows：以管理员身份运行命令提示符

### 调试技巧

1. **启用详细输出**
   ```bash
   ./git_sync_batch.sh --once --verbose
   ```

2. **测试单个命令**
   ```bash
   python ./git_sync.py --config sync_config.yaml --verbose
   ```

3. **验证配置文件**
   ```bash
   # 检查配置文件内容
   cat batch_configs.txt
   ```

## 最佳实践

### 1. 配置管理
- 为不同环境创建不同的配置列表文件
- 使用有意义的文件名，如：`prod_configs.txt`、`dev_configs.txt`
- 在配置文件中添加详细注释
- 定期验证配置文件中的命令是否有效

### 2. 执行策略
- 根据仓库大小和网络状况调整执行间隔
- 避免在网络高峰时段执行大量同步
- 对于大型仓库，适当增加执行间隔
- 使用 --verbose 模式进行首次测试

### 3. 安全考虑
- 确保配置文件权限设置正确
- 定期更新认证信息
- 在生产环境中使用专用用户运行
- 避免在配置文件中硬编码敏感信息

### 4. 监控和维护
- 定期检查同步结果和错误信息
- 监控网络连接状态
- 建立同步失败的告警机制
- 定期清理过期的日志文件

## 系统要求

- **Linux/Unix/macOS**: Bash 4.0+
- **Windows**: Windows 7+ （推荐 Windows 10+）
- **Python**: 2.7+ 或 3.6+
- **Git**: 2.0+
- **网络**: 稳定的网络连接

## 故障排除

### 常见问题诊断

1. **脚本无法启动**
   - 检查文件权限：`chmod +x git_sync_batch.sh` (Linux/macOS)
   - 检查文件路径是否正确
   - 确保在正确的目录下执行

2. **参数错误**
   - 使用 `--help` 查看正确的参数格式
   - 确保数值参数为正整数
   - 检查参数拼写是否正确

3. **配置文件问题**
   - 验证配置文件存在：`ls -la batch_configs.txt`
   - 检查文件内容格式：`cat batch_configs.txt`
   - 确保文件不为空且包含有效命令

4. **同步命令失败**
   - 单独测试每个同步命令
   - 检查 Git Sync Tool 的配置是否正确
   - 验证网络连接和认证信息

### 调试步骤

1. **启用详细模式**
   ```bash
   ./git_sync_batch.sh --once --verbose
   ```

2. **逐步排查**
   ```bash
   # 测试配置文件
   cat batch_configs.txt
   
   # 测试单个命令
   python ./git_sync.py --config sync_config.yaml --verbose
   
   # 检查系统环境
   python --version
   git --version
   ```

3. **检查网络和认证**
   - 验证 Git 远程仓库访问权限
   - 检查网络连接稳定性
   - 确认认证信息正确

## 技术支持

### 获取帮助
1. **查看帮助信息**
   ```bash
   ./git_sync_batch.sh --help
   ```

2. **收集调试信息**
   - 使用 `--verbose` 模式获取详细日志
   - 保存错误信息和完整的执行日志
   - 记录系统环境和配置信息

3. **参考文档**
   - 查看 Git Sync Tool 的主要文档
   - 参考故障排除指南
   - 检查配置示例和最佳实践

## 版本信息

### 当前版本特点
- **简化架构**：移除复杂的守护进程功能，专注核心批量同步
- **增强稳定性**：优化错误处理和参数验证
- **改进用户体验**：更清晰的日志输出和统计信息
- **跨平台兼容**：在 Linux/macOS 和 Windows 上稳定运行

### 使用建议
- 首次使用请先测试 `--once` 模式
- 对于大型仓库，建议适当增加执行间隔
- 定期检查同步结果和错误日志
- 在生产环境中使用前请充分测试

---

**注意**: 这个批量同步工具是 Git Sync Tool 的扩展功能，请确保已正确配置和测试基础的 Git 同步功能后再使用批量工具。
