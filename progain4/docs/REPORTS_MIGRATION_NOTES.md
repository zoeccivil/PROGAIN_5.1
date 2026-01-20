# Reports & Dashboards Migration Notes

## Overview

This document tracks the migration of reports and dashboards from PROGRAIN 3.0 (SQLite) to PROGRAIN 4.0/5.0 (Firebase).

## Old App Files (Reference)

Located in repository root (outside `progain4/`):

### Reports
1. **reporte_detallado_fecha.py** - Detailed report by date range
2. **gastos_categoria_window.py** - Expenses by category report
3. **resumen_por_cuenta_window.py** - Summary by account

### Dashboards
1. **dashboard_gastos_avanzado.py** - Advanced expenses dashboard
2. **dashboard_global_cuentas.py** - Global accounts dashboard
3. **dashboard_ingresos_vs_gastos.py** - Income vs expenses dashboard

## Migration Strategy

### Phase 9.1: Documentation & Analysis ✅
- [x] Document existing reports
- [x] Identify data requirements
- [x] Map SQLite queries to Firebase queries

### Phase 9.2: Simple Reports (Implemented)
- [x] Resumen por Cuenta (Summary by Account)
- [x] Reporte Detallado por Fecha (Detailed Report by Date)

---

## Report #1: Resumen por Cuenta (Summary by Account) ✅

### Purpose
Shows transaction summary for each account in the project

### Firebase Implementation
```python
# Get all accounts
cuentas = firebase_client.get_cuentas_by_proyecto(proyecto_id)

# For each account, aggregate transactions
for cuenta in cuentas:
    transacciones = firebase_client.get_transacciones_by_proyecto(
        proyecto_id,
        cuenta_id=cuenta['id']
    )
    total_ingresos = sum(t['monto'] for t in transacciones if t['tipo'] == 'ingreso')
    total_gastos = sum(t['monto'] for t in transacciones if t['tipo'] == 'gasto')
```

### UI Components
- Table with columns: Cuenta, # Trans, Ingresos, Gastos, Balance
- Refresh button
- Simple, clear layout

---

## Report #2: Reporte Detallado por Fecha (Detailed Report by Date) ✅

### Purpose
Lists all transactions within a date range

### Firebase Implementation
```python
# Get all transactions
transacciones = firebase_client.get_transacciones_by_proyecto(proyecto_id)

# Get mappings
cuentas = {c['id']: c['nombre'] for c in firebase_client.get_cuentas_by_proyecto(proyecto_id)}
categorias = {c['id']: c['nombre'] for c in firebase_client.get_categorias_by_proyecto(proyecto_id)}

# Filter and display
for t in transacciones:
    t['cuenta_nombre'] = cuentas.get(t['cuenta_id'], 'Unknown')
    t['categoria_nombre'] = categorias.get(t['categoria_id'], 'Unknown')
```

### UI Components
- Table: Fecha, Tipo, Cuenta, Categoría, Descripción, Monto
- Total summary at bottom
- Refresh button

---

## Implementation Status

| Feature | Status | New Location |
|---------|--------|--------------|
| Account Summary | ✅ Complete | ui/reports/account_summary_report.py |
| Detailed by Date | ✅ Complete | ui/reports/detailed_date_report.py |
| Expenses by Category | ⚪ Future | ui/dashboards/ |
| Income vs Expenses | ⚪ Future | ui/dashboards/ |

**Legend:**
- ✅ Complete
- ⚪ Not Started (Future phases)

---

**Last Updated**: November 22, 2024
