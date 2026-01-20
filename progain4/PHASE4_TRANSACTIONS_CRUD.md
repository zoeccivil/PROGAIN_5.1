# PHASE 4 - Transactions CRUD Implementation

## Objective
Implement complete CRUD (Create, Read, Update, Delete) operations for transactions in FirebaseClient.

## Implementation Summary

### Methods Implemented

#### 1. `get_transacciones_by_proyecto(...)` ✅ (Already existed)
**Purpose**: Get all transactions for a project with optional filters

**Parameters**:
- `proyecto_id`: Project ID (required)
- `cuenta_id`: Filter by account (optional, None = all accounts)
- `periodo`: Filter by period (optional, not yet implemented)
- `texto`: Search in description/comment (optional, in-memory filter)

**Returns**: List of transaction dictionaries

**Firestore Path**: `proyectos/{proyecto_id}/transacciones`

**Example**:
```python
# All transactions
all_trans = firebase_client.get_transacciones_by_proyecto("proyecto_123")

# Filter by account
account_trans = firebase_client.get_transacciones_by_proyecto(
    "proyecto_123",
    cuenta_id="cuenta_001"
)

# Search text
search_trans = firebase_client.get_transacciones_by_proyecto(
    "proyecto_123",
    texto="supermercado"
)
```

**Features**:
- Ordered by date (most recent first)
- Account filtering in Firestore query (efficient)
- Text filtering in-memory (descripcion + comentario)
- Returns empty list if no transactions

#### 2. `create_transaccion(...)` ✅ NEW
**Purpose**: Create a new transaction in a project

**Parameters**:
- `proyecto_id`: Project ID (required)
- `fecha`: Transaction date (datetime, required)
- `tipo`: Transaction type - 'ingreso' or 'gasto' (required)
- `cuenta_id`: Account ID (required)
- `categoria_id`: Category ID (required)
- `monto`: Amount (float, required, will be made positive)
- `descripcion`: Description (optional, default "")
- `comentario`: Additional comments (optional, default "")
- `subcategoria_id`: Subcategory ID (optional)
- `adjuntos`: List of attachment URLs (optional)

**Returns**: Transaction ID if successful, None otherwise

**Firestore Document Created**:
```json
{
  "fecha": "2024-01-15T14:30:00",
  "tipo": "gasto",
  "cuenta_id": "cuenta_001",
  "categoria_id": "cat_alimentacion",
  "subcategoria_id": "subcat_supermercado",
  "monto": 3500.00,
  "descripcion": "Compra en supermercado",
  "comentario": "Compra semanal",
  "adjuntos": [],
  "fecha_creacion": "2024-01-15T14:35:00",
  "activo": true
}
```

**Example**:
```python
from datetime import datetime

trans_id = firebase_client.create_transaccion(
    proyecto_id="proyecto_123",
    fecha=datetime(2024, 1, 15, 14, 30),
    tipo="gasto",
    cuenta_id="cuenta_001",
    categoria_id="cat_alimentacion",
    monto=3500.00,
    descripcion="Compra en supermercado",
    comentario="Compra semanal",
    subcategoria_id="subcat_supermercado"
)
# Returns: "trans_001" (new ID)
```

**Features**:
- Validates `tipo` (must be 'ingreso' or 'gasto')
- Normalizes `tipo` to lowercase
- Ensures `monto` is positive (uses abs())
- Auto-adds `fecha_creacion` timestamp
- Sets `activo=True` by default
- Only includes optional fields if provided

#### 3. `update_transaccion(proyecto_id, transaccion_id, updates)` ✅ NEW
**Purpose**: Update an existing transaction

**Parameters**:
- `proyecto_id`: Project ID (required)
- `transaccion_id`: Transaction ID to update (required)
- `updates`: Dictionary with fields to update (required)

**Returns**: True if successful, False otherwise

**Example**:
```python
success = firebase_client.update_transaccion(
    proyecto_id="proyecto_123",
    transaccion_id="trans_001",
    updates={
        'monto': 4000.00,
        'descripcion': 'Compra en supermercado (actualizado)',
        'comentario': 'Incluye productos de limpieza'
    }
)
# Returns: True
```

**Features**:
- Validates `tipo` if present in updates
- Normalizes `tipo` to lowercase if present
- Ensures `monto` is positive if present (uses abs())
- Auto-adds `fecha_modificacion` timestamp
- Partial updates (only specified fields)

**Valid Update Fields**:
- `fecha`: Transaction date
- `tipo`: Transaction type ('ingreso' or 'gasto')
- `cuenta_id`: Account ID
- `categoria_id`: Category ID
- `subcategoria_id`: Subcategory ID
- `monto`: Amount
- `descripcion`: Description
- `comentario`: Comments
- `adjuntos`: Attachments list
- `activo`: Active status

#### 4. `delete_transaccion(proyecto_id, transaccion_id, soft_delete=True)` ✅ NEW
**Purpose**: Delete or deactivate a transaction

**Parameters**:
- `proyecto_id`: Project ID (required)
- `transaccion_id`: Transaction ID to delete (required)
- `soft_delete`: If True, soft delete (default: True)

**Returns**: True if successful, False otherwise

**Soft Delete** (default):
```python
success = firebase_client.delete_transaccion(
    proyecto_id="proyecto_123",
    transaccion_id="trans_001"
)
# Sets activo=False, adds fecha_eliminacion timestamp
# Transaction remains in database for historical records
```

**Hard Delete**:
```python
success = firebase_client.delete_transaccion(
    proyecto_id="proyecto_123",
    transaccion_id="trans_001",
    soft_delete=False
)
# Permanently removes transaction from Firestore
```

**Best Practice**: Use soft delete to:
- Preserve historical data
- Allow undo operations
- Maintain audit trail
- Keep balances calculable

#### 5. `get_transaccion_by_id(proyecto_id, transaccion_id)` ✅ NEW
**Purpose**: Get a specific transaction by ID

**Parameters**:
- `proyecto_id`: Project ID (required)
- `transaccion_id`: Transaction ID (required)

**Returns**: Transaction dictionary or None if not found

**Example**:
```python
trans = firebase_client.get_transaccion_by_id(
    proyecto_id="proyecto_123",
    transaccion_id="trans_001"
)
# Returns: {
#   'id': 'trans_001',
#   'fecha': datetime(2024, 1, 15, 14, 30),
#   'tipo': 'gasto',
#   'cuenta_id': 'cuenta_001',
#   'categoria_id': 'cat_alimentacion',
#   'monto': 3500.00,
#   ...
# }
```

**Use Cases**:
- Loading transaction for edit dialog
- Verifying transaction details
- Displaying transaction detail view

## Transaction Types

The application supports two transaction types:

| Type | Spanish | Purpose | Display Color |
|------|---------|---------|---------------|
| `ingreso` | Ingreso | Income | Green |
| `gasto` | Gasto | Expense | Red |

**Note**: The `tipo` field is automatically normalized to lowercase and validated.

## Data Model

### Transaction Document Structure

```typescript
{
  // Auto-generated
  id: string,                    // Firestore document ID
  
  // Required fields
  fecha: Timestamp,              // Transaction date
  tipo: string,                  // 'ingreso' or 'gasto' (lowercase)
  cuenta_id: string,             // Account ID reference
  categoria_id: string,          // Category ID reference
  monto: number,                 // Amount (always positive)
  
  // Optional fields
  descripcion: string,           // Description (default "")
  comentario: string,            // Comments (default "")
  subcategoria_id?: string,      // Subcategory ID (optional)
  adjuntos?: string[],           // Attachment URLs (optional)
  
  // Status
  activo: boolean,               // Active status
  
  // Timestamps (auto-added)
  fecha_creacion: Timestamp,     // Creation date
  fecha_modificacion?: Timestamp,// Last update
  fecha_eliminacion?: Timestamp  // Deletion date (soft delete)
}
```

### Firestore Path

```
proyectos/{proyecto_id}/transacciones/{transaccion_id}
```

### Indexes Required

For optimal query performance, create these Firestore indexes:

1. **Account + Date Index**:
   - Collection: `transacciones`
   - Fields: `cuenta_id` (Ascending), `fecha` (Descending)
   - Used by: Filtered account queries

2. **Active Status + Date Index** (future):
   - Collection: `transacciones`
   - Fields: `activo` (Ascending), `fecha` (Descending)
   - Used by: Filtering active transactions only

## Error Handling

All methods include comprehensive error handling:

1. **Not Initialized**: Returns safe defaults (empty list, None, False)
2. **Invalid Type**: Logs error and returns None/False
3. **Network Errors**: Caught and logged
4. **Not Found**: Returns None with warning log
5. **Validation Errors**: Returns None/False with error log

**Example Error Logs**:
```
ERROR - Invalid transaction type: deposito
ERROR - Error creating transaction in project proyecto_123: Permission denied
WARNING - Transaction trans_999 not found in project proyecto_123
```

## Usage Examples

### Creating a Transaction Workflow

```python
from datetime import datetime

# 1. Create income transaction
trans_id = firebase_client.create_transaccion(
    proyecto_id="mi_proyecto",
    fecha=datetime.now(),
    tipo="ingreso",
    cuenta_id="cuenta_banco",
    categoria_id="cat_salario",
    monto=50000.00,
    descripcion="Salario de enero",
    comentario="Pago quincenal"
)

if trans_id:
    print(f"Transaction created: {trans_id}")
    
    # 2. Load for verification
    trans = firebase_client.get_transaccion_by_id("mi_proyecto", trans_id)
    print(f"Details: {trans}")
    
    # 3. Update if needed
    success = firebase_client.update_transaccion(
        "mi_proyecto",
        trans_id,
        {'comentario': 'Pago quincenal - incluye bono'}
    )
```

### Expense Transaction

```python
# Create expense
trans_id = firebase_client.create_transaccion(
    proyecto_id="mi_proyecto",
    fecha=datetime(2024, 1, 15),
    tipo="gasto",
    cuenta_id="cuenta_tarjeta",
    categoria_id="cat_alimentacion",
    subcategoria_id="subcat_restaurant",
    monto=1500.00,
    descripcion="Cena en restaurante",
    comentario="Cena familiar"
)
```

### Filtering Transactions

```python
# By account
trans_cuenta = firebase_client.get_transacciones_by_proyecto(
    "mi_proyecto",
    cuenta_id="cuenta_tarjeta"
)

# Search text
trans_search = firebase_client.get_transacciones_by_proyecto(
    "mi_proyecto",
    texto="restaurante"
)

# All transactions
all_trans = firebase_client.get_transacciones_by_proyecto("mi_proyecto")

# Filter by type in Python
ingresos = [t for t in all_trans if t['tipo'] == 'ingreso']
gastos = [t for t in all_trans if t['tipo'] == 'gasto']
```

### Transaction with Attachments

```python
trans_id = firebase_client.create_transaccion(
    proyecto_id="mi_proyecto",
    fecha=datetime.now(),
    tipo="gasto",
    cuenta_id="cuenta_efectivo",
    categoria_id="cat_servicios",
    monto=2500.00,
    descripcion="Pago de factura eléctrica",
    adjuntos=[
        "gs://mi-bucket/facturas/luz_enero.pdf",
        "gs://mi-bucket/facturas/comprobante.jpg"
    ]
)
```

## Integration with UI

The TransactionsWidget already uses `get_transacciones_by_proyecto()` to display transactions (PHASE 5 integration already exists).

Future UI components can use the new CRUD methods:
- **Add Transaction Dialog**: Call `create_transaccion()`
- **Edit Transaction Dialog**: Call `get_transaccion_by_id()` to load, `update_transaccion()` to save
- **Delete Transaction**: Call `delete_transaccion()` with confirmation

## Testing Checklist

To test PHASE 4 implementation:

- [ ] Create income transaction
- [ ] Create expense transaction
- [ ] Create transaction with all optional fields
- [ ] Create transaction with minimal fields
- [ ] List all transactions
- [ ] List transactions filtered by account
- [ ] Search transactions by text
- [ ] Get specific transaction by ID
- [ ] Update transaction fields
- [ ] Soft delete transaction
- [ ] Hard delete transaction
- [ ] Verify transactions appear in UI table
- [ ] Test error handling (invalid tipo, etc.)
- [ ] Test monto validation (negative → positive)

## Amount Handling

**Important**: The `monto` field is always stored as a positive number.

- The sign (income vs expense) is determined by the `tipo` field
- When creating/updating, `monto` is automatically made positive using `abs()`
- For calculations:
  ```python
  if trans['tipo'] == 'ingreso':
      balance += trans['monto']
  else:  # gasto
      balance -= trans['monto']
  ```

## Date Handling

Transactions use Python `datetime` objects which are automatically converted to Firestore timestamps:

```python
from datetime import datetime

# Current time
fecha=datetime.now()

# Specific date and time
fecha=datetime(2024, 1, 15, 14, 30)

# From string (requires parsing)
from datetime import datetime
fecha=datetime.strptime("2024-01-15 14:30", "%Y-%m-%d %H:%M")
```

## Security Considerations

1. **Soft Delete by Default**: Prevents accidental data loss
2. **Timestamps**: All operations logged with timestamps
3. **Type Validation**: Prevents invalid transaction types
4. **Amount Validation**: Ensures amounts are always positive
5. **Audit Trail**: fecha_creacion, fecha_modificacion, fecha_eliminacion

## Performance Notes

- **List All Transactions**: Single Firestore query, O(n)
- **List by Account**: Indexed query, O(n) where n = transactions for account
- **Text Search**: In-memory filter after query, O(n)
- **Create/Update/Delete**: Single document operation, O(1)
- **Batch Operations**: Not yet implemented (future enhancement)

## Future Enhancements

Potential improvements for future phases:

1. **Period Filtering**: Implement `periodo` parameter (by month, year, custom range)
2. **Batch Operations**: Create multiple transactions at once
3. **Transaction Templates**: Save frequently used transaction patterns
4. **Recurring Transactions**: Auto-create based on schedule
5. **Transfer Helper**: Create two linked transactions (withdrawal + deposit)
6. **Attachments Upload**: Upload files to Storage and link to transaction

## Next Steps

**PHASE 5** will focus on:
- Verifying transactions UI integration (already implemented)
- May need transaction management dialogs (Create/Edit Transaction)
- Transaction deletion confirmation
- Date range filtering

**PHASE 6** will implement:
- Complete transaction dialog with all fields
- Category/subcategory selection
- File attachment upload
- Form validation
