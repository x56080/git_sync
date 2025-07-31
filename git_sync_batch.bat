@echo off
setlocal enabledelayedexpansion

REM Git Sync Batch Tool for Windows
REM Batch synchronization script for multiple git repositories
REM Author: Git Sync Tool Team
REM Version: 1.0

REM Default configuration
set DEFAULT_INTERVAL=86400
set DEFAULT_CONFIG_LIST=batch_configs.txt
set SCRIPT_DIR=%~dp0
set LOG_DIR=%SCRIPT_DIR%logs
set PID_FILE=%SCRIPT_DIR%git_sync_batch.pid

REM Initialize variables
set CONFIG_LIST=%DEFAULT_CONFIG_LIST%
set INTERVAL=%DEFAULT_INTERVAL%
set RUN_ONCE=false
set RUN_DAEMON=false
set STOP_DAEMON=false
set SHOW_STATUS=false
set VERBOSE=false

REM Function to show usage
:show_usage
echo Git Sync Batch Tool - Batch synchronization for multiple repositories
echo.
echo Usage: %~nx0 [OPTIONS]
echo.
echo OPTIONS:
echo     -c, --config-list FILE    Specify config list file (default: batch_configs.txt)
echo     -i, --interval SECONDS    Set sync interval in seconds (default: 86400 = 24 hours)
echo     -o, --once               Run synchronization once and exit
echo     -d, --daemon             Run as daemon (background process)
echo     -s, --stop               Stop running daemon
echo     -t, --status             Show daemon status
echo     -l, --log-dir DIR        Specify log directory (default: .\logs)
echo     -v, --verbose            Enable verbose output
echo     -h, --help               Show this help message
echo.
echo EXAMPLES:
echo     # Run once with default config list
echo     %~nx0 --once
echo.
echo     # Run as daemon with 12-hour interval
echo     %~nx0 --daemon --interval 43200
echo.
echo     # Run once with custom config list
echo     %~nx0 --once --config-list my_configs.txt
echo.
echo     # Stop daemon
echo     %~nx0 --stop
echo.
echo     # Check daemon status
echo     %~nx0 --status
echo.
echo CONFIG LIST FORMAT:
echo     Each line in the config list file should contain a sync command:
echo     python ./git_sync.py --config sync_sdb_mirror.yaml
echo     python ./git_sync.py --config sync_sac_to_github.yaml
echo     python ./git_sync.py --config sync_sdb_mygithub.yaml
echo.
goto :eof

REM Function to log messages
:log_info
echo [INFO] %date% %time% %~1
goto :eof

:log_success
echo [SUCCESS] %date% %time% %~1
goto :eof

:log_warning
echo [WARNING] %date% %time% %~1
goto :eof

:log_error
echo [ERROR] %date% %time% %~1
goto :eof

REM Function to create log directory
:create_log_dir
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    call :log_info "Created log directory: %LOG_DIR%"
)
goto :eof

REM Function to check if daemon is running
:is_daemon_running
if exist "%PID_FILE%" (
    set /p DAEMON_PID=<"%PID_FILE%"
    tasklist /FI "PID eq !DAEMON_PID!" 2>nul | find /I "!DAEMON_PID!" >nul
    if !errorlevel! equ 0 (
        exit /b 0
    ) else (
        del "%PID_FILE%" 2>nul
        exit /b 1
    )
) else (
    exit /b 1
)

REM Function to stop daemon
:stop_daemon
call :is_daemon_running
if !errorlevel! equ 0 (
    set /p DAEMON_PID=<"%PID_FILE%"
    call :log_info "Stopping daemon (PID: !DAEMON_PID!)..."
    taskkill /PID !DAEMON_PID! /F >nul 2>&1
    del "%PID_FILE%" 2>nul
    call :log_success "Daemon stopped successfully"
) else (
    call :log_warning "Daemon is not running"
)
goto :eof

REM Function to show daemon status
:show_status
call :is_daemon_running
if !errorlevel! equ 0 (
    set /p DAEMON_PID=<"%PID_FILE%"
    call :log_success "Daemon is running (PID: !DAEMON_PID!)"
    
    REM Show recent log entries if log file exists
    for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set LOG_DATE=%%c%%a%%b
    set LOG_FILE=%LOG_DIR%\batch_!LOG_DATE!.log
    if exist "!LOG_FILE!" (
        echo.
        echo Recent log entries (last 10 lines):
        powershell "Get-Content '!LOG_FILE!' | Select-Object -Last 10"
    )
) else (
    call :log_info "Daemon is not running"
)
goto :eof

REM Function to validate config list file
:validate_config_list
set CONFIG_FILE=%~1
if not exist "%CONFIG_FILE%" (
    call :log_error "Config list file not found: %CONFIG_FILE%"
    exit /b 1
)

REM Check if file has content
for %%A in ("%CONFIG_FILE%") do set FILE_SIZE=%%~zA
if !FILE_SIZE! equ 0 (
    call :log_error "Config list file is empty: %CONFIG_FILE%"
    exit /b 1
)

set VALID_LINES=0
for /f "usebackq delims=" %%a in ("%CONFIG_FILE%") do (
    set LINE=%%a
    REM Skip empty lines and comments
    if not "!LINE!"=="" (
        if not "!LINE:~0,1!"=="#" (
            echo !LINE! | find /i "python" >nul
            if !errorlevel! equ 0 (
                set /a VALID_LINES+=1
            )
        )
    )
)

if !VALID_LINES! equ 0 (
    call :log_error "No valid sync commands found in config list file"
    exit /b 1
)

call :log_info "Found !VALID_LINES! valid sync command(s) in config list"
exit /b 0

REM Function to execute sync commands
:execute_sync_batch
set CONFIG_FILE=%~1
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set LOG_DATE=%%c%%a%%b
set LOG_FILE=%LOG_DIR%\batch_!LOG_DATE!.log
set SUCCESS_COUNT=0
set TOTAL_COUNT=0

call :log_info "Starting batch synchronization..."
call :log_info "Config file: %CONFIG_FILE%"
call :log_info "Log file: %LOG_FILE%"

REM Create detailed log entry
echo ========================================== >> "%LOG_FILE%"
echo Batch Sync Started: %date% %time% >> "%LOG_FILE%"
echo Config File: %CONFIG_FILE% >> "%LOG_FILE%"
echo ========================================== >> "%LOG_FILE%"

for /f "usebackq delims=" %%a in ("%CONFIG_FILE%") do (
    set LINE=%%a
    REM Skip empty lines and comments
    if not "!LINE!"=="" (
        if not "!LINE:~0,1!"=="#" (
            set /a TOTAL_COUNT+=1
            
            call :log_info "Executing: !LINE!"
            echo Command !TOTAL_COUNT!: !LINE! >> "%LOG_FILE%"
            
            REM Execute the command
            cd /d "%SCRIPT_DIR%"
            if "%VERBOSE%"=="true" (
                !LINE! 2>&1 | tee -a "%LOG_FILE%"
            ) else (
                !LINE! >> "%LOG_FILE%" 2>&1
            )
            
            if !errorlevel! equ 0 (
                set /a SUCCESS_COUNT+=1
                call :log_success "Command completed successfully"
            ) else (
                call :log_error "Command failed with exit code !errorlevel!"
                echo ERROR: Command failed with exit code !errorlevel! >> "%LOG_FILE%"
            )
            
            echo ---------------------------------------- >> "%LOG_FILE%"
        )
    )
)

REM Summary
call :log_info "Batch synchronization completed"
call :log_info "Total commands: !TOTAL_COUNT!"
call :log_success "Successful: !SUCCESS_COUNT!"

set /a FAILED_COUNT=!TOTAL_COUNT!-!SUCCESS_COUNT!
if !FAILED_COUNT! gtr 0 (
    call :log_error "Failed: !FAILED_COUNT!"
)

REM Write summary to log
echo ========================================== >> "%LOG_FILE%"
echo Batch Sync Completed: %date% %time% >> "%LOG_FILE%"
echo Total Commands: !TOTAL_COUNT! >> "%LOG_FILE%"
echo Successful: !SUCCESS_COUNT! >> "%LOG_FILE%"
echo Failed: !FAILED_COUNT! >> "%LOG_FILE%"
echo ========================================== >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

exit /b !FAILED_COUNT!

REM Function to run as daemon
:run_daemon
set CONFIG_FILE=%~1
set DAEMON_INTERVAL=%~2

call :is_daemon_running
if !errorlevel! equ 0 (
    set /p DAEMON_PID=<"%PID_FILE%"
    call :log_error "Daemon is already running (PID: !DAEMON_PID!)"
    exit /b 1
)

call :log_info "Starting daemon mode..."
set /a HOURS=!DAEMON_INTERVAL!/3600
set /a MINUTES=(!DAEMON_INTERVAL! %% 3600)/60
call :log_info "Sync interval: !DAEMON_INTERVAL!s (!HOURS!h !MINUTES!m)"
call :log_info "Config file: %CONFIG_FILE%"

REM Start daemon in background using PowerShell
powershell -Command "Start-Process -FilePath '%~f0' -ArgumentList '--daemon-worker', '%CONFIG_FILE%', '%DAEMON_INTERVAL%' -WindowStyle Hidden"

REM Wait a moment and check if daemon started
timeout /t 3 /nobreak >nul
call :is_daemon_running
if !errorlevel! equ 0 (
    set /p DAEMON_PID=<"%PID_FILE%"
    call :log_success "Daemon started successfully (PID: !DAEMON_PID!)"
) else (
    call :log_error "Failed to start daemon"
    exit /b 1
)
goto :eof

REM Internal daemon worker function
:daemon_worker
set CONFIG_FILE=%~1
set DAEMON_INTERVAL=%~2

REM Save PID
echo %$PID% > "%PID_FILE%"

call :log_info "Daemon worker started"

:daemon_loop
call :execute_sync_batch "%CONFIG_FILE%"

call :log_info "Next sync in %DAEMON_INTERVAL%s"
timeout /t %DAEMON_INTERVAL% /nobreak >nul

REM Check if we should continue
if not exist "%PID_FILE%" goto :eof

goto daemon_loop

REM Parse command line arguments
:parse_args
if "%~1"=="" goto :end_parse

if "%~1"=="-c" (
    set CONFIG_LIST=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--config-list" (
    set CONFIG_LIST=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-i" (
    set INTERVAL=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--interval" (
    set INTERVAL=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-o" (
    set RUN_ONCE=true
    shift
    goto :parse_args
)
if "%~1"=="--once" (
    set RUN_ONCE=true
    shift
    goto :parse_args
)
if "%~1"=="-d" (
    set RUN_DAEMON=true
    shift
    goto :parse_args
)
if "%~1"=="--daemon" (
    set RUN_DAEMON=true
    shift
    goto :parse_args
)
if "%~1"=="--daemon-worker" (
    call :daemon_worker %~2 %~3
    goto :eof
)
if "%~1"=="-s" (
    set STOP_DAEMON=true
    shift
    goto :parse_args
)
if "%~1"=="--stop" (
    set STOP_DAEMON=true
    shift
    goto :parse_args
)
if "%~1"=="-t" (
    set SHOW_STATUS=true
    shift
    goto :parse_args
)
if "%~1"=="--status" (
    set SHOW_STATUS=true
    shift
    goto :parse_args
)
if "%~1"=="-l" (
    set LOG_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="--log-dir" (
    set LOG_DIR=%~2
    shift
    shift
    goto :parse_args
)
if "%~1"=="-v" (
    set VERBOSE=true
    shift
    goto :parse_args
)
if "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto :parse_args
)
if "%~1"=="-h" (
    call :show_usage
    exit /b 0
)
if "%~1"=="--help" (
    call :show_usage
    exit /b 0
)

call :log_error "Unknown option: %~1"
call :show_usage
exit /b 1

:end_parse

REM Main execution
call :parse_args %*

REM Create log directory
call :create_log_dir

REM Handle different modes
if "%STOP_DAEMON%"=="true" (
    call :stop_daemon
    exit /b 0
)

if "%SHOW_STATUS%"=="true" (
    call :show_status
    exit /b 0
)

REM Convert relative config list path to absolute
if not "%CONFIG_LIST:~1,1%"==":" (
    set CONFIG_LIST=%SCRIPT_DIR%%CONFIG_LIST%
)

REM Validate config list file
call :validate_config_list "%CONFIG_LIST%"
if !errorlevel! neq 0 exit /b 1

REM Execute based on mode
if "%RUN_ONCE%"=="true" (
    call :execute_sync_batch "%CONFIG_LIST%"
    exit /b !errorlevel!
) else if "%RUN_DAEMON%"=="true" (
    call :run_daemon "%CONFIG_LIST%" "%INTERVAL%"
    exit /b 0
) else (
    call :log_error "Please specify either --once or --daemon mode"
    call :show_usage
    exit /b 1
)
