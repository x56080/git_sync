# Git Sync Batch Tool 使用说明

## 概述

Git Sync Batch Tool 是一个批量同步脚本，可以自动执行多个 Git 仓库的同步任务。支持一次性执行和定时循环执行两种模式。

## 文件说明

- `git_sync_batch.sh` - Linux/Unix/macOS 版本的批量同步脚本
- `git_sync_batch.bat` - Windows 版本的批量同步脚本
- `batch_configs.txt` - 默认的配置列表文件，包含要执行的同步命令

## 功能特性

### 🚀 核心功能
- **批量执行**：从配置文件中读取多个同步命令并依次执行
- **定时同步**：支持设置间隔时间，自动循环执行批量同步
- **后台运行**：支持守护进程模式，在后台持续运行
- **日志记录**：详细的执行日志，包含成功/失败统计
- **进程管理**：启动、停止、状态查询等完整的进程管理功能

### 🛡️ 安全特性
- **PID 管理**：防止重复启动守护进程
- **优雅关闭**：支持信号处理和优雅关闭
- **错误处理**：完善的错误处理和恢复机制
- **日志轮转**：按日期分割日志文件

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

| 选项 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config-list FILE` | 指定配置列表文件 | `batch_configs.txt` |
| `-i, --interval SECONDS` | 设置同步间隔（秒） | `86400` (24小时) |
| `-o, --once` | 执行一次同步后退出 | - |
| `-d, --daemon` | 以守护进程模式运行 | - |
| `-s, --stop` | 停止正在运行的守护进程 | - |
| `-t, --status` | 查看守护进程状态 | - |
| `-l, --log-dir DIR` | 指定日志目录 | `./logs` |
| `-v, --verbose` | 启用详细输出 | - |
| `-h, --help` | 显示帮助信息 | - |

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

### 1. 一次性批量同步

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

### 2. 定时循环同步

**Linux/Unix/macOS:**
```bash
# 每24小时同步一次（默认）
./git_sync_batch.sh --daemon

# 每12小时同步一次
./git_sync_batch.sh --daemon --interval 43200

# 每6小时同步一次
./git_sync_batch.sh --daemon --interval 21600

# 每小时同步一次
./git_sync_batch.sh --daemon --interval 3600
```

**Windows:**
```cmd
# 每24小时同步一次（默认）
git_sync_batch.bat --daemon

# 每12小时同步一次
git_sync_batch.bat --daemon --interval 43200

# 每6小时同步一次
git_sync_batch.bat --daemon --interval 21600
```

### 3. 守护进程管理

**查看状态:**
```bash
./git_sync_batch.sh --status        # Linux/Unix/macOS
git_sync_batch.bat --status         # Windows
```

**停止守护进程:**
```bash
./git_sync_batch.sh --stop          # Linux/Unix/macOS
git_sync_batch.bat --stop           # Windows
```

## 日志系统

### 日志文件位置
- 默认日志目录：`./logs/`
- 日志文件命名：`batch_YYYYMMDD.log`
- 每天自动创建新的日志文件

### 日志内容
- 执行时间戳
- 命令执行详情
- 成功/失败状态
- 错误信息和堆栈
- 执行统计摘要

### 日志示例
```
==========================================
Batch Sync Started: 2024-01-15 09:00:00
Config File: batch_configs.txt
==========================================
Command 1: python ./git_sync.py --config sync_sdb_mirror_to_github.yaml
[SUCCESS] Sync completed successfully
Duration: 45s
----------------------------------------
Command 2: python ./git_sync.py --config sync_sac_to_github.yaml
[SUCCESS] Sync completed successfully
Duration: 32s
----------------------------------------
==========================================
Batch Sync Completed: 2024-01-15 09:01:17
Total Commands: 2
Successful: 2
Failed: 0
Duration: 77s
==========================================
```

## 常见使用场景

### 1. 每日自动同步
```bash
# 设置每天凌晨2点自动同步
./git_sync_batch.sh --daemon --interval 86400
```

### 2. 开发环境快速同步
```bash
# 开发期间每小时同步一次
./git_sync_batch.sh --daemon --interval 3600
```

### 3. 手动批量同步
```bash
# 需要时手动执行一次完整同步
./git_sync_batch.sh --once --verbose
```

### 4. 测试配置
```bash
# 使用测试配置文件验证设置
./git_sync_batch.sh --once --config-list test_configs.txt
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

3. **守护进程已在运行**
   ```
   [ERROR] Daemon is already running (PID: 12345)
   ```
   - 先停止现有守护进程：`--stop`
   - 或查看状态：`--status`

4. **权限问题**
   - Linux/Unix/macOS：确保脚本有执行权限 `chmod +x git_sync_batch.sh`
   - Windows：以管理员身份运行命令提示符

### 调试技巧

1. **启用详细输出**
   ```bash
   ./git_sync_batch.sh --once --verbose
   ```

2. **查看日志文件**
   ```bash
   tail -f logs/batch_$(date +%Y%m%d).log
   ```

3. **测试单个命令**
   ```bash
   python ./git_sync.py --config sync_config.yaml --verbose
   ```

## 最佳实践

### 1. 配置管理
- 为不同环境创建不同的配置列表文件
- 使用有意义的文件名，如：`prod_configs.txt`、`dev_configs.txt`
- 在配置文件中添加详细注释

### 2. 监控和维护
- 定期检查日志文件
- 监控守护进程状态
- 设置日志文件清理策略

### 3. 安全考虑
- 确保配置文件权限设置正确
- 定期更新认证信息
- 在生产环境中使用专用用户运行

### 4. 性能优化
- 根据仓库大小调整同步间隔
- 避免在高峰时段执行大量同步
- 考虑网络带宽限制

## 系统要求

- **Linux/Unix/macOS**: Bash 4.0+
- **Windows**: Windows 7+ with PowerShell 3.0+
- **Python**: 2.7+ 或 3.6+
- **Git**: 2.0+
- **网络**: 稳定的网络连接

## 故障排除

如果遇到问题，请按以下步骤排查：

1. 检查系统要求是否满足
2. 验证配置文件格式和内容
3. 测试单个同步命令是否正常
4. 查看详细日志输出
5. 检查网络连接和认证信息

## 技术支持

如需帮助，请：
1. 查看日志文件获取详细错误信息
2. 使用 `--verbose` 模式获取更多调试信息
3. 检查 Git Sync Tool 的主要文档和故障排除指南

---

**注意**: 这个批量同步工具是 Git Sync Tool 的扩展功能，请确保已正确配置和测试基础的 Git 同步功能后再使用批量工具。
