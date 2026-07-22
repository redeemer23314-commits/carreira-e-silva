@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   Atualizar site no GitHub - Carreira ^& Silva
echo ============================================
echo.

REM Verifica se ha alteracoes (inclui ficheiros novos/nao rastreados)
set "temmudancas="
for /f "delims=" %%i in ('git status --porcelain') do set "temmudancas=1"
if not defined temmudancas (
  echo Nao ha nada de novo para enviar. Esta tudo atualizado.
  echo.
  pause
  exit /b
)

echo Alteracoes encontradas:
git status --short
echo.

set /p msg="Escreve uma descricao do que mudaste (ou Enter para 'atualizacao'): "
if "%msg%"=="" set msg=atualizacao

echo.
echo A enviar para o GitHub...
git add -A
git commit -m "%msg%"
git push

echo.
if %errorlevel%==0 (
  echo ============================================
  echo   Enviado com sucesso!
  echo ============================================
) else (
  echo ============================================
  echo   Algo correu mal. Ve a mensagem acima.
  echo ============================================
)
echo.
pause
