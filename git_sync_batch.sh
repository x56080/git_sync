#!/bin/bash

# Git Sync Batch Tool
# Batch synchronization script for multiple git repositories
# Author: XJH
# Version: 1.0

# Default configuration
DEFAULT_INTERVAL=86400  # 24 hours in seconds
DEFAULT_CONFIG_LIST="batch_configs.txt"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
PID_FILE="${SCRIPT_DIR}/git_sync_batch.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Git Sync Batch Tool - Batch synchronization for multiple repositories

Usage: $0 [OPTIONS]

OPTIONS:
    -c, --config-list FILE    Specify config list file (default: batch_configs.txt)
    -i, --interval SECONDS    Set sync interval in seconds (default: 86400 = 24 hours)
    -o, --once               Run synchronization once and exit
    -d, --daemon             Run as daemon (background process)
    -s, --stop               Stop running daemon
    -t, --status             Show daemon status
    -l, --log-dir DIR        Specify log directory (default: ./logs)
    -v, --verbose            Enable verbose output
    -h, --help               Show this help message

EXAMPLES:
    # Run once with default config list
    $0 --once

    # Run as daemon with 12-hour interval
    $0 --daemon --interval 43200

    # Run once with custom config list
    $0 --once --config-list my_configs.txt

    # Stop daemon
    $0 --stop

    # Check daemon status
    $0 --status

CONFIG LIST FORMAT:
    Each line in the config list file should contain a sync command:
    python ./git_sync.py --config sync_sdb_mirror.yaml
    python ./git_sync.py --config sync_sac_to_github.yaml
    python ./git_sync.py --config sync_sdb_mygithub.yaml

EOF
}

# Function to create log directory
create_log_dir() {
    if [[ ! -d "$LOG_DIR" ]]; then
        mkdir -p "$LOG_DIR"
        log_info "Created log directory: $LOG_DIR"
    fi
}

# Function to check if daemon is running
is_daemon_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            # PID file exists but process is not running, remove stale PID file
            rm -f "$PID_FILE"
            return 1
        fi
    fi
    return 1
}

# Function to stop daemon
stop_daemon() {
    if is_daemon_running; then
        local pid=$(cat "$PID_FILE")
        log_info "Stopping daemon (PID: $pid)..."
        kill "$pid"
        
        # Wait for process to stop
        local count=0
        while ps -p "$pid" > /dev/null 2>&1 && [[ $count -lt 30 ]]; do
            sleep 1
            ((count++))
        done
        
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warning "Process did not stop gracefully, forcing termination..."
            kill -9 "$pid"
        fi
        
        rm -f "$PID_FILE"
        log_success "Daemon stopped successfully"
    else
        log_warning "Daemon is not running"
    fi
}

# Function to show daemon status
show_status() {
    if is_daemon_running; then
        local pid=$(cat "$PID_FILE")
        log_success "Daemon is running (PID: $pid)"
        
        # Show process information
        if command -v ps > /dev/null; then
            echo "Process details:"
            ps -p "$pid" -o pid,ppid,cmd,etime,pcpu,pmem
        fi
        
        # Show recent log entries if log file exists
        local log_file="${LOG_DIR}/batch_$(date '+%Y%m%d').log"
        if [[ -f "$log_file" ]]; then
            echo ""
            echo "Recent log entries (last 10 lines):"
            tail -10 "$log_file"
        fi
    else
        log_info "Daemon is not running"
    fi
}

# Function to validate config list file
validate_config_list() {
    local config_file="$1"
    
    if [[ ! -f "$config_file" ]]; then
        log_error "Config list file not found: $config_file"
        return 1
    fi
    
    if [[ ! -r "$config_file" ]]; then
        log_error "Config list file is not readable: $config_file"
        return 1
    fi
    
    # Check if file has content
    if [[ ! -s "$config_file" ]]; then
        log_error "Config list file is empty: $config_file"
        return 1
    fi
    
    # Validate each line
    local line_num=0
    local valid_lines=0
    
    while IFS= read -r line; do
        ((line_num++))
        
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        # Check if line contains python command
        if [[ "$line" =~ ^[[:space:]]*python[[:space:]] ]]; then
            ((valid_lines++))
        else
            log_warning "Line $line_num may not be a valid sync command: $line"
        fi
    done < "$config_file"
    
    if [[ $valid_lines -eq 0 ]]; then
        log_error "No valid sync commands found in config list file"
        return 1
    fi
    
    log_info "Found $valid_lines valid sync command(s) in config list"
    return 0
}

# Function to execute sync commands
execute_sync_batch() {
    local config_file="$1"
    local log_file="${LOG_DIR}/batch_$(date '+%Y%m%d').log"
    local success_count=0
    local total_count=0
    local start_time=$(date '+%s')
    
    log_info "Starting batch synchronization..."
    log_info "Config file: $config_file"
    log_info "Log file: $log_file"
    
    # Create detailed log entry
    {
        echo "=========================================="
        echo "Batch Sync Started: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Config File: $config_file"
        echo "=========================================="
    } >> "$log_file"
    
    while IFS= read -r line; do
        # Skip empty lines and comments
        if [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]]; then
            continue
        fi
        
        ((total_count++))
        local cmd_start_time=$(date '+%s')
        
        log_info "Executing: $line"
        echo "Command $total_count: $line" >> "$log_file"
        
        # Execute the command and capture output
        if [[ "$VERBOSE" == "true" ]]; then
            # In verbose mode, show output in real-time
            if eval "cd '$SCRIPT_DIR' && $line" 2>&1 | tee -a "$log_file"; then
                ((success_count++))
                log_success "Command completed successfully"
            else
                log_error "Command failed with exit code $?"
            fi
        else
            # In normal mode, capture output to log only
            if eval "cd '$SCRIPT_DIR' && $line" >> "$log_file" 2>&1; then
                ((success_count++))
                log_success "Command completed successfully"
            else
                local exit_code=$?
                log_error "Command failed with exit code $exit_code"
                echo "ERROR: Command failed with exit code $exit_code" >> "$log_file"
            fi
        fi
        
        local cmd_duration=$(($(date '+%s') - cmd_start_time))
        echo "Duration: ${cmd_duration}s" >> "$log_file"
        echo "----------------------------------------" >> "$log_file"
        
    done < "$config_file"
    
    local total_duration=$(($(date '+%s') - start_time))
    
    # Summary
    log_info "Batch synchronization completed"
    log_info "Total commands: $total_count"
    log_success "Successful: $success_count"
    
    if [[ $((total_count - success_count)) -gt 0 ]]; then
        log_error "Failed: $((total_count - success_count))"
    fi
    
    log_info "Total duration: ${total_duration}s"
    
    # Write summary to log
    {
        echo "=========================================="
        echo "Batch Sync Completed: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Total Commands: $total_count"
        echo "Successful: $success_count"
        echo "Failed: $((total_count - success_count))"
        echo "Duration: ${total_duration}s"
        echo "=========================================="
        echo ""
    } >> "$log_file"
    
    return $((total_count - success_count))
}

# Function to run as daemon
run_daemon() {
    local config_file="$1"
    local interval="$2"
    
    # Check if already running
    if is_daemon_running; then
        log_error "Daemon is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi
    
    log_info "Starting daemon mode..."
    log_info "Sync interval: ${interval}s ($(($interval / 3600))h $(($interval % 3600 / 60))m)"
    log_info "Config file: $config_file"
    
    # Fork to background
    (
        # Trap signals for graceful shutdown
        trap 'log_info "Daemon shutting down..."; rm -f "$PID_FILE"; exit 0' TERM INT
        
        log_info "Daemon started (PID: $$)"
        
        while true; do
            execute_sync_batch "$config_file"
            
            log_info "Next sync in ${interval}s ($(date -d "+${interval} seconds" '+%Y-%m-%d %H:%M:%S'))"
            
            # Sleep with interruption check
            local remaining=$interval
            while [[ $remaining -gt 0 ]]; do
                if [[ $remaining -gt 60 ]]; then
                    sleep 60
                    remaining=$((remaining - 60))
                else
                    sleep $remaining
                    remaining=0
                fi
                
                # Check if we should exit
                if [[ ! -f "$PID_FILE" ]]; then
                    exit 0
                fi
            done
        done
    ) &
    
    # Save the actual background process PID
    echo $! > "$PID_FILE"
    
    # Wait a moment to ensure daemon started
    sleep 2
    
    if is_daemon_running; then
        log_success "Daemon started successfully (PID: $(cat "$PID_FILE"))"
    else
        log_error "Failed to start daemon"
        exit 1
    fi
}

# Parse command line arguments
CONFIG_LIST="$DEFAULT_CONFIG_LIST"
INTERVAL="$DEFAULT_INTERVAL"
RUN_ONCE=false
RUN_DAEMON=false
STOP_DAEMON=false
SHOW_STATUS=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config-list)
            CONFIG_LIST="$2"
            shift 2
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -o|--once)
            RUN_ONCE=true
            shift
            ;;
        -d|--daemon)
            RUN_DAEMON=true
            shift
            ;;
        -s|--stop)
            STOP_DAEMON=true
            shift
            ;;
        -t|--status)
            SHOW_STATUS=true
            shift
            ;;
        -l|--log-dir)
            LOG_DIR="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate interval
if ! [[ "$INTERVAL" =~ ^[0-9]+$ ]] || [[ "$INTERVAL" -lt 1 ]]; then
    log_error "Invalid interval: $INTERVAL (must be a positive integer)"
    exit 1
fi

# Create log directory
create_log_dir

# Handle different modes
if [[ "$STOP_DAEMON" == "true" ]]; then
    stop_daemon
    exit 0
fi

if [[ "$SHOW_STATUS" == "true" ]]; then
    show_status
    exit 0
fi

# Convert relative config list path to absolute
if [[ ! "$CONFIG_LIST" =~ ^/ ]]; then
    CONFIG_LIST="${SCRIPT_DIR}/${CONFIG_LIST}"
fi

# Validate config list file
if ! validate_config_list "$CONFIG_LIST"; then
    exit 1
fi

# Execute based on mode
if [[ "$RUN_ONCE" == "true" ]]; then
    execute_sync_batch "$CONFIG_LIST"
    exit $?
elif [[ "$RUN_DAEMON" == "true" ]]; then
    run_daemon "$CONFIG_LIST" "$INTERVAL"
    exit 0
else
    log_error "Please specify either --once or --daemon mode"
    show_usage
    exit 1
fi
