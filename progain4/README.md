# PROGRAIN 4.0 / 5.0

Firebase-based personal finance management application.

## Overview

PROGRAIN 4.0/5.0 is a complete rewrite of the PROGRAIN application using Firebase as the backend:
- **Firestore**: Database for projects, accounts, categories, and transactions
- **Firebase Storage**: File storage for transaction attachments
- **PyQt6**: Modern UI framework

## Project Structure

```
progain4/
├── main_ynab.py              # Application entry point
├── requirements.txt           # Python dependencies
├── services/
│   ├── __init__.py
│   └── firebase_client.py    # Firebase service layer
├── ui/
│   ├── __init__.py
│   ├── main_window4.py       # Main application window
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── firebase_config_dialog.py   # Firebase configuration
│   │   └── project_dialog.py           # Project selection
│   └── widgets/
│       ├── __init__.py
│       └── transactions_widget.py      # Transactions table
└── capturas/                 # UI screenshots (for reference)
```

## Installation

1. Install Python 3.8 or higher
2. Install dependencies:
   ```bash
   pip install -r progain4/requirements.txt
   ```

3. Set up Firebase:
   - Create a Firebase project at https://console.firebase.google.com
   - Enable Firestore Database
   - Enable Firebase Storage
   - Download service account credentials JSON file
   - Note your Storage bucket name (usually `project-id.appspot.com`)

## Running the Application

### First Time Setup

On first launch, the application will prompt you to configure Firebase:

1. Run: `python progain4/main_ynab.py`
2. Enter Firebase credentials path (JSON file)
3. Enter Storage bucket name
4. Configuration is automatically saved for future launches

### Using Environment Variables (Optional)

You can override saved configuration with environment variables:

```bash
export FIREBASE_CREDENTIALS="/path/to/your/credentials.json"
export FIREBASE_STORAGE_BUCKET="your-project.appspot.com"
python progain4/main_ynab.py
```

### Subsequent Launches

After initial configuration, simply run:
```bash
python progain4/main_ynab.py
```

The application will automatically use your saved credentials.

### Configuration Storage

Credentials are stored using Qt's QSettings:
- **Windows**: Registry (`HKCU\Software\PROGRAIN\PROGRAIN 4.0`)
- **macOS**: `~/Library/Preferences/com.PROGRAIN.PROGRAIN 4.0.plist`
- **Linux**: `~/.config/PROGRAIN/PROGRAIN 4.0.conf`

**Note**: Only the path to credentials is stored, not the credentials themselves.

## Firestore Data Structure

The application uses the following Firestore structure:

```
proyectos/{proyecto_id}
  - nombre: string
  - descripcion: string
  - fecha_creacion: timestamp
  - activo: boolean

proyectos/{proyecto_id}/cuentas/{cuenta_id}
  - nombre: string
  - tipo: string (efectivo, banco, tarjeta, etc.)
  - is_principal: boolean
  - saldo_inicial: number
  - moneda: string

proyectos/{proyecto_id}/categorias/{categoria_id}
  - nombre: string
  - tipo: string (ingreso, gasto)
  - icono: string (optional)

proyectos/{proyecto_id}/transacciones/{transaccion_id}
  - fecha: timestamp
  - tipo: string (ingreso, gasto)
  - cuenta_id: string
  - categoria_id: string
  - subcategoria_id: string (optional)
  - monto: number
  - descripcion: string
  - comentario: string
  - adjuntos: array (optional)
```

## Development Phases

This application is being developed in phases:

- [x] **Phase 0**: Understand current structure
- [x] **Phase 1**: Persistent credentials configuration
- [ ] **Phase 2**: Accounts logic in FirebaseClient
- [ ] **Phase 3**: Accounts in UI (sidebar + combo)
- [ ] **Phase 4**: Transactions logic in FirebaseClient
- [ ] **Phase 5**: Transactions in UI (table)
- [ ] **Phase 6**: Transaction dialogs improvements
- [ ] **Phase 7**: Menu bar structure
- [ ] **Phase 8**: Firebase inspection tool
- [ ] **Phase 9**: Reports and dashboards migration

## Key Features

- **100% Firebase Backend**: No local SQLite database
- **Multi-Project Support**: Manage multiple financial projects
- **Account Management**: Track multiple accounts per project
- **Transaction Tracking**: Record income and expenses with categories
- **Real-time Sync**: Data synced with cloud automatically
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Notes

- The old PROGRAIN 3.0 application (in the repository root) uses SQLite and serves as functional reference only
- High DPI scaling is pre-configured and should not be modified
- Firebase credentials are never stored in the repository

## License

[To be determined]
