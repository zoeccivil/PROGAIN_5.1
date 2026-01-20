# PHASE 2 - Accounts CRUD Implementation

## Objective
Implement complete CRUD (Create, Read, Update, Delete) operations for accounts in FirebaseClient.

## Implementation Summary

### Methods Implemented

#### 1. `get_cuentas_by_proyecto(proyecto_id: str)` ✅ (Already existed)
**Purpose**: Get all accounts for a project

**Returns**: List of account dictionaries

**Firestore Path**: `proyectos/{proyecto_id}/cuentas`

**Example**:
```python
cuentas = firebase_client.get_cuentas_by_proyecto("proyecto_123")
# Returns: [
#   {
#     'id': 'cuenta_001',
#     'nombre': 'Efectivo',
#     'tipo': 'efectivo',
#     'saldo_inicial': 5000.00,
#     'moneda': 'RD$',
#     'is_principal': True,
#     'activo': True
#   },
#   ...
# ]
```

#### 2. `create_cuenta(...)` ✅ NEW
**Purpose**: Create a new account in a project

**Parameters**:
- `proyecto_id`: Project ID (required)
- `nombre`: Account name (required)
- `tipo`: Account type (required) - efectivo, banco, tarjeta, inversion, ahorro
- `saldo_inicial`: Initial balance (default: 0.0)
- `moneda`: Currency code (default: "RD$")
- `is_principal`: Main account flag (default: False)

**Returns**: Account ID if successful, None otherwise

**Firestore Document Created**:
```json
{
  "nombre": "Banco Popular",
  "tipo": "banco",
  "saldo_inicial": 25000.00,
  "moneda": "RD$",
  "is_principal": false,
  "fecha_creacion": "2024-01-15T10:30:00",
  "activo": true
}
```

**Example**:
```python
cuenta_id = firebase_client.create_cuenta(
    proyecto_id="proyecto_123",
    nombre="Banco Popular",
    tipo="banco",
    saldo_inicial=25000.00,
    moneda="RD$",
    is_principal=False
)
# Returns: "cuenta_002" (new ID)
```

**Features**:
- Normalizes `tipo` to lowercase
- Auto-adds `fecha_creacion` timestamp
- Sets `activo=True` by default

#### 3. `update_cuenta(proyecto_id, cuenta_id, updates)` ✅ NEW
**Purpose**: Update an existing account

**Parameters**:
- `proyecto_id`: Project ID (required)
- `cuenta_id`: Account ID to update (required)
- `updates`: Dictionary with fields to update (required)

**Returns**: True if successful, False otherwise

**Example**:
```python
success = firebase_client.update_cuenta(
    proyecto_id="proyecto_123",
    cuenta_id="cuenta_002",
    updates={
        'nombre': 'Banco Popular - Cuenta Corriente',
        'saldo_inicial': 30000.00
    }
)
# Returns: True
```

**Features**:
- Normalizes `tipo` if present in updates
- Auto-adds `fecha_modificacion` timestamp
- Only updates specified fields (partial update)

**Valid Update Fields**:
- `nombre`: Account name
- `tipo`: Account type
- `saldo_inicial`: Initial balance
- `moneda`: Currency
- `is_principal`: Main account flag
- `activo`: Active status

#### 4. `delete_cuenta(proyecto_id, cuenta_id, soft_delete=True)` ✅ NEW
**Purpose**: Delete or deactivate an account

**Parameters**:
- `proyecto_id`: Project ID (required)
- `cuenta_id`: Account ID to delete (required)
- `soft_delete`: If True, soft delete (default: True)

**Returns**: True if successful, False otherwise

**Soft Delete** (default):
```python
success = firebase_client.delete_cuenta(
    proyecto_id="proyecto_123",
    cuenta_id="cuenta_002"
)
# Sets activo=False, adds fecha_eliminacion timestamp
# Account remains in database but marked inactive
```

**Hard Delete**:
```python
success = firebase_client.delete_cuenta(
    proyecto_id="proyecto_123",
    cuenta_id="cuenta_002",
    soft_delete=False
)
# Permanently removes account from Firestore
```

**Best Practice**: Use soft delete to preserve historical data and prevent breaking references in transactions.

#### 5. `get_cuenta_by_id(proyecto_id, cuenta_id)` ✅ NEW
**Purpose**: Get a specific account by ID

**Parameters**:
- `proyecto_id`: Project ID (required)
- `cuenta_id`: Account ID (required)

**Returns**: Account dictionary or None if not found

**Example**:
```python
cuenta = firebase_client.get_cuenta_by_id(
    proyecto_id="proyecto_123",
    cuenta_id="cuenta_002"
)
# Returns: {
#   'id': 'cuenta_002',
#   'nombre': 'Banco Popular',
#   'tipo': 'banco',
#   ...
# }
```

## Account Types

The following account types are supported (normalized to lowercase):

| Type | Display Name | Icon |
|------|--------------|------|
| `efectivo` | Efectivo | 💵 |
| `banco` | Banco | 🏦 |
| `tarjeta` | Tarjeta de Crédito | 💳 |
| `inversion` | Inversión | 📈 |
| `ahorro` | Ahorro | 🏦 |

**Note**: The `tipo` field is automatically normalized to lowercase by `create_cuenta` and `update_cuenta`.

## Data Model

### Account Document Structure

```typescript
{
  // Auto-generated
  id: string,                    // Firestore document ID
  
  // Required fields
  nombre: string,                // Account name
  tipo: string,                  // Account type (lowercase)
  saldo_inicial: number,         // Initial balance
  moneda: string,                // Currency code
  is_principal: boolean,         // Main account flag
  activo: boolean,               // Active status
  
  // Timestamps (auto-added)
  fecha_creacion: Timestamp,     // Creation date
  fecha_modificacion?: Timestamp,// Last update (optional)
  fecha_eliminacion?: Timestamp  // Deletion date (soft delete)
}
```

### Firestore Path

```
proyectos/{proyecto_id}/cuentas/{cuenta_id}
```

## Error Handling

All methods include comprehensive error handling:

1. **Not Initialized**: Returns empty list, None, or False if Firebase not initialized
2. **Network Errors**: Logged and returns safe defaults
3. **Not Found**: `get_cuenta_by_id` returns None, logs warning
4. **Update Errors**: Returns False, logs error with details

**Example Error Log**:
```
ERROR - Error getting accounts for project proyecto_123: Connection timeout
ERROR - Error creating account in project proyecto_123: Invalid credentials
```

## Usage Examples

### Creating an Account Workflow

```python
# 1. Create account
cuenta_id = firebase_client.create_cuenta(
    proyecto_id="mi_proyecto",
    nombre="Efectivo Principal",
    tipo="efectivo",
    saldo_inicial=10000.00,
    is_principal=True
)

if cuenta_id:
    print(f"Account created: {cuenta_id}")
    
    # 2. Get account to verify
    cuenta = firebase_client.get_cuenta_by_id("mi_proyecto", cuenta_id)
    print(f"Account details: {cuenta}")
    
    # 3. Update if needed
    success = firebase_client.update_cuenta(
        "mi_proyecto",
        cuenta_id,
        {'saldo_inicial': 12000.00}
    )
    
    if success:
        print("Account updated")
```

### Listing Active Accounts

```python
# Get all accounts
all_cuentas = firebase_client.get_cuentas_by_proyecto("mi_proyecto")

# Filter active accounts (in Python)
active_cuentas = [c for c in all_cuentas if c.get('activo', True)]

# Filter by type
bancos = [c for c in active_cuentas if c['tipo'] == 'banco']
```

### Soft Delete with Recovery Option

```python
# Soft delete account
firebase_client.delete_cuenta("mi_proyecto", "cuenta_001", soft_delete=True)

# Later, to recover the account
firebase_client.update_cuenta(
    "mi_proyecto",
    "cuenta_001",
    {'activo': True}
)
```

## Integration with UI

The MainWindow4 already uses `get_cuentas_by_proyecto()` to populate the accounts sidebar and combo box (PHASE 3 integration already exists).

Future UI components can use the new CRUD methods:
- **Create Account Dialog**: Call `create_cuenta()`
- **Edit Account Dialog**: Call `get_cuenta_by_id()` to load, `update_cuenta()` to save
- **Delete Account**: Call `delete_cuenta()` with confirmation

## Testing Checklist

To test PHASE 2 implementation:

- [ ] Create account with all fields
- [ ] Create account with minimal fields (defaults)
- [ ] List all accounts for a project
- [ ] Get specific account by ID
- [ ] Update account fields
- [ ] Soft delete account
- [ ] Hard delete account
- [ ] Verify account appears in UI sidebar
- [ ] Test error handling (invalid proyecto_id, etc.)

## Security Considerations

1. **Soft Delete by Default**: Prevents accidental data loss
2. **Timestamps**: All operations logged with timestamps
3. **Type Normalization**: Prevents inconsistent data (tipo lowercase)
4. **Validation**: Returns None/False on errors, never raises exceptions to UI

## Performance Notes

- **List Accounts**: Single Firestore query, O(n) where n = number of accounts
- **Create/Update/Delete**: Single document operation, O(1)
- **Batch Operations**: Not yet implemented (future enhancement)

## Next Steps

**PHASE 3** will focus on:
- UI already displays accounts (done in initial structure)
- May need account management dialogs (Create/Edit Account)
- Account deletion confirmation

**PHASE 4-5** will implement:
- Transactions CRUD
- Transactions filtering by account (already supported in read)
