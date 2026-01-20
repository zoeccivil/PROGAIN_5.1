# UNDO/REDO System - User Interface Guide

## Visual Overview

This guide describes the user interface elements added for the undo/redo functionality.

## Menu Bar - "Editar" (Edit) Menu

The Edit menu now includes undo/redo options at the top:

```
┌─ Editar ─────────────────────────────────┐
│ ⟲ Deshacer: Crear transacción...  Ctrl+Z │
│ ⟳ Rehacer: Eliminar transacción... Ctrl+Y│
│ ───────────────────────────────────────── │
│ 📜 Ver historial de cambios...            │
│ ───────────────────────────────────────── │
│   Gestionar cuentas maestras...           │
│   Gestionar cuentas del proyecto...       │
│   (... other menu items ...)              │
└───────────────────────────────────────────┘
```

### Dynamic Menu Text

- When undo is available: "Deshacer: [action description]"
- When undo is not available: "Deshacer" (grayed out)
- Same behavior for redo

The description is truncated to 50 characters if too long.

## Toolbar Buttons

Two new buttons are added to the main toolbar after the "Transferencia" button:

```
┌──────────────────────────────────────────────────────────────────┐
│ Proyecto: [Project Combo▼] │ Cuenta: [Account Combo▼]            │
│ 🔄 Actualizar │ ➕ Nueva Transacción │ 🔄 Transferencia │         │
│ ⏪ Deshacer │ ⏩ Rehacer │                                        │
└──────────────────────────────────────────────────────────────────┘
```

### Button States

**Enabled** (when actions are available):
- ⏪ Deshacer - Clickable, tooltip shows action description
- ⏩ Rehacer - Clickable, tooltip shows action description

**Disabled** (when no actions available):
- ⏪ Deshacer - Grayed out, tooltip shows "Deshacer (Ctrl+Z)"
- ⏩ Rehacer - Grayed out, tooltip shows "Rehacer (Ctrl+Y)"

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+Z** | Undo last action |
| **Ctrl+Y** | Redo last undone action |
| **Ctrl+Shift+Z** | Redo last undone action (alternative) |

These shortcuts work globally within the main window.

## History Dialog

Access via: **Editar → Ver historial de cambios...**

```
┌─ Historial de Cambios ──────────────────────────────────────┐
│ 📜 Historial de acciones (más recientes primero)             │
│                                                               │
│ ┌───────────────────────────────────────────────────────────┐│
│ │ Timestamp         │Type         │Description       │Masiva││
│ ├───────────────────┼─────────────┼──────────────────┼──────┤│
│ │2026-01-20 14:30:15│CreateTrans..│Crear transacción:│      ││
│ │                   │             │Compra superm...   │      ││
│ ├───────────────────┼─────────────┼──────────────────┼──────┤│
│ │2026-01-20 14:25:10│UpdateTrans..│Editar transacción│      ││
│ │                   │             │Pago renta...      │      ││
│ ├───────────────────┼─────────────┼──────────────────┼──────┤│
│ │2026-01-20 14:20:05│Batch        │Importar 25 trans │ ✅ Sí││
│ └───────────────────┴─────────────┴──────────────────┴──────┘│
│                                                               │
│ Total: 25 │ Disponibles para deshacer: 25 │ Límite: 25       │
│                                                               │
│                                    [     Cerrar     ]         │
└───────────────────────────────────────────────────────────────┘
```

### Dialog Features

- **Sortable columns**: Click headers to sort
- **Alternating row colors**: Easier to read
- **Batch indicator**: Shows ✅ Sí for batch operations
- **Statistics bar**: Shows total actions, undo/redo counts, and limit
- **Modal**: Blocks interaction with main window until closed

## Status Bar Messages

After performing undo or redo, a message appears in the status bar:

```
┌────────────────────────────────────────────┐
│ ✅ Deshecho: Crear transacción: Compra...  │ (3 seconds)
└────────────────────────────────────────────┘
```

```
┌────────────────────────────────────────────┐
│ ✅ Rehecho: Eliminar transacción: Pago...  │ (3 seconds)
└────────────────────────────────────────────┘
```

## Confirmation Dialogs

### Batch Operation Confirmation

When undoing or redoing a batch operation (marked with is_batch=True), the user is prompted:

```
┌─ Confirmar Deshacer ─────────────────────┐
│                                           │
│  ⚠️  ¿Deshacer operación masiva?         │
│                                           │
│  Importar 25 transacciones (25 cambios)  │
│                                           │
│  Esta acción afectará múltiples registros.│
│                                           │
│               [  Sí  ]  [  No  ]          │
└───────────────────────────────────────────┘
```

**Individual operations do NOT show confirmation** - they execute immediately.

## Behavior on Project Change

When the user changes projects (via combo box or menu):
1. The undo/redo history is automatically cleared
2. A log message is recorded: "Cleared undo/redo history on project change"
3. The undo/redo buttons and menu items are disabled (grayed out)
4. The history dialog (if open) would show an empty list

This prevents accidentally undoing actions from a previous project.

## Error Handling

If an undo or redo operation fails:
- The operation is rolled back
- The command is restored to its original stack
- A status message may be shown (if implemented)

## Performance Notes

- **Lightweight**: Only command metadata is kept in memory
- **Fast**: Undo/redo operations are nearly instantaneous
- **Persistent**: History survives application restarts
- **Limited**: Stack size prevents excessive memory use

## Usage Tips for End Users

1. **Don't be afraid to experiment**: You can always undo!
2. **Check the history**: Use "Ver historial de cambios" to see what you've done
3. **Batch confirmations**: Pay attention when undoing imports - they affect multiple records
4. **Keyboard shortcuts**: Learn Ctrl+Z and Ctrl+Y for faster workflow
5. **Project changes**: Remember that changing projects clears the history

## Usage Tips for Developers

1. **Always use commands**: Don't directly modify Firebase - use Command objects
2. **Capture snapshots**: Before updating or deleting, capture the current state
3. **Batch operations**: Group related operations with BatchCommand
4. **Test thoroughly**: Use the test suite to verify new command types
5. **Update UI state**: Call `_update_undo_redo_state()` after operations

## Accessibility

- **Keyboard navigation**: Full support via Ctrl+Z / Ctrl+Y
- **Screen readers**: Menu items and buttons have clear labels
- **Visual feedback**: Status messages and tooltips provide confirmation
- **Color independence**: No information conveyed solely by color

## Future Enhancements

Possible future improvements:
- [ ] Undo/redo directly from history dialog
- [ ] Keyboard shortcuts in history dialog (Del to undo selected)
- [ ] Visual indicators in transaction list (e.g., recently undone)
- [ ] Undo/redo animations for better feedback
- [ ] Context menu options (right-click to undo specific action)
- [ ] Undo/redo statistics in dashboard
- [ ] Export history to CSV for auditing

---

**Note**: This is a living document that may be updated as the UI evolves.
