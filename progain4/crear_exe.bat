@echo off
cls
echo ========================================================
echo      GENERADOR DE EJECUTABLE - PROGRAIN APP
echo ========================================================
echo.

REM 1. Verificar e Instalar PyInstaller
echo [1/3] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller no encontrado. Instalando...
    pip install pyinstaller
) else (
    echo PyInstaller ya esta instalado.
)

REM 2. Limpiar compilaciones previas para evitar errores
echo.
echo [2/3] Limpiando archivos temporales antiguos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del *.spec

REM 3. Ejecutar PyInstaller
echo.
echo [3/3] Creando progain_app.exe...
echo       Esto puede tardar unos minutos dependiendo de tu PC.
echo.

REM EXPLICACIÓN DE COMANDOS:
REM --noconsole: La app se abre como ventana, sin pantalla negra de fondo.
REM --onefile: Crea un solo archivo .exe portable.
REM --name: Nombre del archivo final.
REM --clean: Limpia caché antes de compilar.
REM --hidden-import: Fuerza la inclusión de librerías que a veces PyInstaller no detecta.
REM --add-data: Incluye las fuentes (ajusta la ruta si tus fuentes están en otro lado, ej: progain4/fonts).

pyinstaller ^
    --noconsole ^
    --onefile ^
    --name "progain_app" ^
    --clean ^
    --hidden-import=pandas ^
    --hidden-import=plotly ^
    --hidden-import=fpdf ^
    --hidden-import=openpyxl ^
    --hidden-import=progain4.services.report_generator ^
    progain4/main_ynab.py

echo.
echo ========================================================
if exist "dist\progain_app.exe" (
    echo [EXITO] El ejecutable se ha creado correctamente.
    echo.
    echo UBICACION: Carpeta "dist\progain_app.exe"
    echo.
    echo IMPORTANTE:
    echo No olvides copiar tu archivo "serviceAccountKey.json" 
    echo dentro de la carpeta "dist" junto al .exe para que funcione.
) else (
    echo [ERROR] Algo fallo durante la creacion del ejecutable.
    echo Revisa los mensajes de error arriba.
)
echo ========================================================
pause