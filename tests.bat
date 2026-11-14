@echo off
setlocal EnableExtensions DisableDelayedExpansion
chcp 65001 >nul 2>&1
cd /d "%~dp0" || exit /b 1
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PYTHONDONTWRITEBYTECODE=1"
set "LOG=%TEMP%\config_practice2_%RANDOM%_%RANDOM%.txt"
set /a "checked=0"

where py >nul 2>&1
if errorlevel 1 (
    echo FAIL: Python launcher py not found
    exit /b 1
)

echo === CLI checks for all 5 stages ===
call :case "CSV default" "package: A" 0 ""
if errorlevel 1 goto :failed
call :case "CSV explicit config" "version: 13.0.3" 0 "--config examples/config_nuget.csv"
if errorlevel 1 goto :failed
call :case "CSV missing file" "CSV" 1 "--config examples/missing.csv"
if errorlevel 1 goto :failed
call :case "NuGet invalid mode" "test_mode=false" 1 "--deps"
if errorlevel 1 goto :failed
call :case "DFS basic graph" "A -> B, C" 0 "--graph"
if errorlevel 1 goto :failed
call :case "DFS cycle" "C -> A" 0 "--config examples/config_graph_cycle.csv --graph"
if errorlevel 1 goto :failed
call :case "DFS depth limit" "D ->" 0 "--config examples/config_graph_depth.csv --graph"
if errorlevel 1 goto :failed
call :case "DFS filtering" "A -> C" 0 "--config examples/config_graph_filter.csv --graph"
if errorlevel 1 goto :failed
call :case "Reverse dependencies" "D <- B, C, E" 0 "--config examples/config_reverse.csv --reverse"
if errorlevel 1 goto :failed
call :case "Reverse depth limit" "D <-" 0 "--config examples/config_reverse_depth.csv --reverse"
if errorlevel 1 goto :failed
call :case "Reverse filtering" "D <-" 0 "--config examples/config_reverse_filter.csv --reverse"
if errorlevel 1 goto :failed

call :svg "PlantUML package A" "examples/config_uml_a.csv" "A"
if errorlevel 1 goto :failed
call :svg "PlantUML package C" "examples/config_uml_c.csv" "C"
if errorlevel 1 goto :failed
call :svg "PlantUML package G" "examples/config_uml_g.csv" "G"
if errorlevel 1 goto :failed

echo.
echo === Unit tests with detailed test names ===
echo Command: py -m unittest discover -s tests -p test_*.py -v
py -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :failed

call :scenario "Stage 1 CSV" "tests/scenarios.py"
if errorlevel 1 goto :failed
call :scenario "Stage 2 NuGet local HTTP" "tests/nuget_scenarios.py"
if errorlevel 1 goto :failed
call :scenario "Stage 3 DFS" "tests/graph_scenarios.py"
if errorlevel 1 goto :failed
call :scenario "Stage 4 reverse" "tests/reverse_scenarios.py"
if errorlevel 1 goto :failed
call :scenario "Stage 5 PlantUML and SVG" "tests/uml_scenarios.py"
if errorlevel 1 goto :failed

echo.
echo ALL TESTS PASSED: %checked% batch checks, unit tests, 5 scenarios
del /q "%LOG%" >nul 2>&1
exit /b 0

:case
echo.
echo === %~1 ===
echo Command: run.bat %~4
call "%~dp0run.bat" %~4 >"%LOG%" 2>&1
set "actual=%errorlevel%"
type "%LOG%"
if not "%actual%"=="%~3" (
    echo FAIL: exit code %actual%, expected %~3
    exit /b 1
)
findstr /L /C:"%~2" "%LOG%" >nul 2>&1
if errorlevel 1 (
    echo FAIL: expected text not found: %~2
    exit /b 1
)
set /a "checked+=1" >nul
echo PASS
exit /b 0

:svg
call :case "%~1" "@startuml" 0 "--config %~2 --uml"
if errorlevel 1 exit /b 1
if not exist "output\%~3.svg" (
    echo FAIL: output\%~3.svg not found
    exit /b 1
)
findstr /L /C:"<svg " "output\%~3.svg" >nul 2>&1
if errorlevel 1 (
    echo FAIL: output\%~3.svg is not SVG
    exit /b 1
)
echo SVG OK: output\%~3.svg
exit /b 0

:scenario
echo.
echo === %~1 ===
echo Command: py %~2
py "%~2"
if errorlevel 1 (
    echo FAIL: %~1
    exit /b 1
)
echo PASS
exit /b 0

:failed
echo.
echo TESTING FAILED
if exist "%LOG%" echo Last output: %LOG%
exit /b 1
