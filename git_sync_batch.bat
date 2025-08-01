@echo off
setlocal enabledelayedexpansion

rem Git Sync Batch Tool for Windows - One-time repeated execution
set SCRIPT_DIR=%~dp0
set CONFIG_LIST=batch_configs.txt
set LOG_DIR=%SCRIPT_DIR%logs

set RUN_ONCE=false
set VERBOSE=false
set SHOW_HELP=false
set COUNT=1
set INTERVAL=3600

:parse_args
if "%~1"=="" goto after_args
if "%~1"=="--help"  set SHOW_HELP=true
if "%~1"=="-h"      set SHOW_HELP=true
if "%~1"=="--once"  set RUN_ONCE=true
if "%~1"=="-o"      set RUN_ONCE=true
if "%~1"=="--verbose" set VERBOSE=true
if "%~1"=="-v"      set VERBOSE=true
if "%~1"=="--config-list" (
    set CONFIG_LIST=%~2
    shift
)
if "%~1"=="-c" (
    set CONFIG_LIST=%~2
    shift
)
if "%~1"=="--count" (
    set COUNT=%~2
    shift
)
if "%~1"=="-n" (
    set COUNT=%~2
    shift
)
if "%~1"=="--interval" (
    set INTERVAL=%~2
    shift
)
if "%~1"=="-t" (
    set INTERVAL=%~2
    shift
)
shift
goto parse_args
:after_args

if /i "%SHOW_HELP%"=="true" goto :show_help

if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo [INFO] Created log dir %LOG_DIR%
)

if not exist "%CONFIG_LIST%" (
    echo [ERROR] Config list file not found: %CONFIG_LIST%
    exit /b 1
)

if /i "%RUN_ONCE%"=="true" (
    echo [INFO] Starting batch synchronization...
    echo [INFO] Execution count: %COUNT%
    if %INTERVAL% GTR 0 (
        echo [INFO] Interval between executions: %INTERVAL% seconds
    )
    echo.
    
    set /a ROUND=0
    :execute_loop
    set /a ROUND+=1
    echo [INFO] === Execution Round !ROUND! / %COUNT% ===
    
    set /a TOTAL=0
    set /a OK=0
    
    REM Generate date for log file (format: batch_YYYYMMDD.log)
    REM Use wmic to get reliable date format
    for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value ^| find "="') do set datetime=%%i
    set YEAR=!datetime:~0,4!
    set MONTH=!datetime:~4,2!
    set DAY=!datetime:~6,2!
    set LOG_FILE=%LOG_DIR%\batch_!YEAR!!MONTH!!DAY!.log
    
    for /f "usebackq tokens=* delims=" %%L in ("%CONFIG_LIST%") do (
        set "LINE=%%L"
        if not "!LINE!"=="" if "!LINE:~0,1!" NEQ "#" (
            set /a TOTAL+=1
            echo [INFO] Executing: !LINE!
            echo Running: !LINE! >> "!LOG_FILE!"
            cmd /c !LINE!
            if !errorlevel! NEQ 0 (
                echo [ERROR] Command failed: !LINE!
            ) else (
                set /a OK+=1
            )
        )
    )
    
    set /a FAILED=!TOTAL! - !OK!
    echo [INFO] Round !ROUND! - Total: !TOTAL!, Success: !OK!, Failed: !FAILED!
    echo.
    
    if !ROUND! lss %COUNT% (
        if %INTERVAL% gtr 0 (
            echo [INFO] Waiting %INTERVAL% seconds before next execution...
            timeout /t %INTERVAL% /nobreak >nul
            echo.
        )
        goto execute_loop
    )
    
    echo [INFO] All executions completed.
    exit /b 0
) else (
    echo [ERROR] Must specify --once parameter
    goto show_help
)



:show_help
echo.
echo Git Sync Batch Tool - Windows Edition
echo.
echo Usage:
echo     git_sync_batch.bat [OPTIONS]
echo.
echo OPTIONS:
echo     -o, --once               Run synchronization and exit
echo     -n, --count NUMBER       Number of execution rounds (default: 1)
echo     -t, --interval SECONDS   Wait time between executions in seconds (default: 3600)
echo     -c, --config-list FILE   Specify config list file (default: batch_configs.txt)
echo     -v, --verbose            Enable verbose logging
echo     -h, --help               Show this help message
echo.
echo Example config list:
echo     python ./git_sync.py --config sync_project.yaml
echo     python ./git_sync.py --config sync_another.yaml
echo.
exit /b 0
