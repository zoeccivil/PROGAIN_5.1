@echo off
echo ========================================
echo  Compilando PROGRAIN 5.0... 
echo ========================================
py -m PyInstaller --name "progain_app" --onefile --windowed --clean --icon="icons/icono-progain. ico" --paths="." --hidden-import="pandas" --hidden-import="plotly" --hidden-import="fpdf" --hidden-import="openpyxl" --hidden-import="progain4.services.report_generator" progain4\main_ynab.py
echo. 
echo ========================================
echo  Compilación completada!
echo  Ejecutable: dist\progain_app.exe
echo ========================================
pause