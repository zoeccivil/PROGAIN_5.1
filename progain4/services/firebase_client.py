"""
Firebase Client Service for PROGRAIN 4.0/5.0

Manages all interactions with Firebase Firestore and Storage.
This is the single source of truth for backend operations.

Actual Firestore structure (según explorador firebase_explorer.py):

Colecciones raíz (globales, no anidadas por proyecto):
- proyectos       { id, nombre, moneda, cuenta_principal, createdAt, updatedAt, ... }
- cuentas         { id, nombre, tipo, tipo_cuenta, createdAt, updatedAt, ... }
- categorias      { id, nombre, createdAt, updatedAt, ... }
- subcategorias   { id, nombre, categoria_id, mantenimiento_*, createdAt, updatedAt, ... }

Colección de transacciones por proyecto:
- proyectos/{proyecto_id}/transacciones/{transaccion_id}
    campos típicos:
    - fecha, tipo, cuenta_id, categoria_id, subcategoria_id, monto, descripcion, comentario, ...

IMPORTANTE:
- Las cuentas, categorías y subcategorías son catálogos globales.
- Las transacciones se filtran por proyecto (subcolección transacciones dentro de cada proyecto).
- Los campos id en cuentas/categorias/subcategorias son numéricos; aquí se normalizan a str.
"""
from typing import Union
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from google.cloud.firestore_v1 import FieldFilter
from google.cloud import firestore # Para las constantes como Query.DESCENDING

try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning(
        "Firebase Admin SDK not available. Install with: pip install firebase-admin"
    )

logger = logging.getLogger(__name__)

# Transaction type constants
TIPO_INGRESO = "ingreso"
TIPO_GASTO = "gasto"
VALID_TRANSACTION_TYPES = [TIPO_INGRESO, TIPO_GASTO]


class FirebaseClient:
    """
    Firebase client for PROGRAIN application.

    Handles authentication and CRUD operations for:
    - Projects (proyectos)
    - Accounts (cuentas)
    - Categories (categorias)
    - Subcategories (subcategorias)
    - Transactions (transacciones)
    - File attachments (Storage)
    """

    def __init__(self):
        """Initialize Firebase client (not connected until initialize() is called)"""
        # Nota: los tipos de firestore/storage solo existen si FIREBASE_AVAILABLE es True
        self.db: Optional["firestore.Client"] = None
        self.bucket: Optional["storage.Bucket"] = None
        self._initialized = False

    # ==================== INITIALIZATION ====================

    def initialize(self, credentials_path: str, storage_bucket: str) -> bool:
            """
            Initialize Firebase with credentials.
            """
            if not FIREBASE_AVAILABLE:
                logger.error("Firebase Admin SDK not available")
                return False

            try:
                # --- CORRECCIÓN CRÍTICA AÑADIDA ---
                # Si el bucket viene con el dominio viejo o vacío, lo forzamos al correcto.
                if not storage_bucket or "appspot.com" in storage_bucket:
                    logger.warning(f"Corrigiendo bucket '{storage_bucket}' a 'progain-25fdf.firebasestorage.app'")
                    storage_bucket = "progain-25fdf.firebasestorage.app"
                # -----------------------------------

                # Check if already initialized
                if self._initialized:
                    logger.info("Firebase already initialized")
                    return True

                # Verify credentials file exists
                if not os.path.exists(credentials_path):
                    logger.error("Credentials file not found: %s", credentials_path)
                    return False

                # Initialize Firebase Admin SDK
                cred = credentials.Certificate(credentials_path)

                # Initialize app if not already done
                try:
                    firebase_admin.initialize_app(cred, {"storageBucket": storage_bucket})
                except ValueError:
                    # App already initialized
                    logger.info("Firebase app already initialized")

                # Get Firestore client
                self.db = firestore.client()

                # Get Storage bucket
                self.bucket = storage.bucket()

                self._initialized = True
                logger.info(f"Firebase initialized successfully using bucket: {storage_bucket}")
                return True

            except Exception as e:
                logger.error("Error initializing Firebase: %s", e)
                return False



    def is_initialized(self) -> bool:
        """Check if Firebase is initialized and ready"""
        return self._initialized and self.db is not None

    # ==================== PROJECTS ====================

    def get_proyectos(self) -> List[Dict[str, Any]]:
        """
        Get all projects from Firestore.

        Returns:
            List of project dictionaries with keys at least:
            - id      (string)
            - nombre
            - moneda
            - cuenta_principal
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proyectos_ref = self.db.collection("proyectos")
            docs = proyectos_ref.stream()

            proyectos: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}

                # El campo 'id' existe como numérico en la colección raíz;
                # lo normalizamos a str y, si falta, usamos doc.id.
                raw_id = data.get("id", doc.id)
                proyecto_id = str(raw_id)

                proyecto_data = {
                    "id": proyecto_id,
                    "nombre": data.get("nombre", f"Proyecto {proyecto_id}"),
                    "moneda": data.get("moneda", "RD$"),
                    "cuenta_principal": str(data.get("cuenta_principal", "")),
                    "raw": data,
                }
                proyectos.append(proyecto_data)

            logger.info("Retrieved %d projects from Firebase", len(proyectos))
            return proyectos

        except Exception as e:
            logger.error("Error getting projects: %s", e)
            return []

    def create_proyecto(self, nombre: str, descripcion: str = "") -> Optional[str]:
        """
        Create a new project in Firestore.

        NOTA: la colección raíz actual de 'proyectos' usa un campo 'id' numérico,
        moneda y cuenta_principal. Aquí creamos un documento simple y dejamos que
        la app antigua/migraciones completen otros campos si es necesario.

        Args:
            nombre: Project name
            descripcion: Project description (optional) - se guarda como 'descripcion'

        Returns:
            Project ID (document id) if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            now = datetime.now()
            proyecto_data = {
                "nombre": nombre,
                "descripcion": descripcion,
                "fecha_creacion": now,
                "createdAt": now,
                "updatedAt": now,
                "activo": True,
            }

            doc_ref = self.db.collection("proyectos").document()
            doc_ref.set(proyecto_data)

            logger.info("Created project: %s (ID: %s)", nombre, doc_ref.id)
            return doc_ref.id

        except Exception as e:
            logger.error("Error creating project: %s", e)
            return None

    # ==================== ACCOUNTS (CUENTAS) ====================

    def get_cuentas_by_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
            """
            Obtiene SOLO las cuentas asignadas explícitamente al proyecto actual.
            
            Lógica:
            1. Consulta 'proyectos/{id}/cuentas_proyecto' para ver qué IDs están vinculados.
            2. Obtiene los detalles (nombre, tipo) de la colección global 'cuentas'.
            3. Retorna la lista filtrada.
            """
            if not self.db or not proyecto_id:
                return []

            try:
                # 1. Obtener asignaciones (IDs) desde la subcolección del proyecto
                cuentas_proj_ref = (
                    self.db.collection('proyectos')
                    .document(proyecto_id)
                    .collection('cuentas_proyecto')
                )
                asignaciones = list(cuentas_proj_ref.stream())
                
                if not asignaciones:
                    logger.warning(f"El proyecto {proyecto_id} no tiene cuentas asignadas en 'cuentas_proyecto'.")
                    # Si la lista sale vacía, el usuario deberá ir a "Editar -> Gestionar cuentas del proyecto"
                    return []

                # Crear un set de IDs habilitados (convertidos a string para comparar fácil)
                ids_habilitados = set()
                for doc in asignaciones:
                    data = doc.to_dict()
                    # Buscamos el ID ya sea en el campo 'cuenta_id' o en el ID del documento
                    if 'cuenta_id' in data:
                        ids_habilitados.add(str(data['cuenta_id']))
                    else:
                        ids_habilitados.add(doc.id)

                # 2. Obtener el catálogo maestro de cuentas
                # Nota: Si get_cuentas() no existe internamente, hacemos la query directa aquí:
                todas_cuentas_ref = self.db.collection('cuentas')
                todas_cuentas_docs = todas_cuentas_ref.stream()
                
                cuentas_filtradas = []
                
                # 3. Cruzar datos: Solo agregamos las que están en ids_habilitados
                for doc in todas_cuentas_docs:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    
                    # Normalizar ID a string para comparar
                    c_id_str = str(data.get('id', ''))
                    
                    if c_id_str in ids_habilitados:
                        cuentas_filtradas.append(data)

                # Ordenar alfabéticamente para que se vean bien en el Sidebar
                cuentas_filtradas.sort(key=lambda x: x.get('nombre', '').lower())

                logger.info(f"Cargadas {len(cuentas_filtradas)} cuentas vinculadas al proyecto {proyecto_id}")
                return cuentas_filtradas

            except Exception as e:
                logger.error(f"Error obteniendo cuentas del proyecto {proyecto_id}: {e}")
                return []
            

    def create_cuenta(
        self,
        proyecto_id: str,
        nombre: str,
        tipo: str,
        saldo_inicial: float = 0.0,
        moneda: str = "RD$",
        is_principal: bool = False,
    ) -> Optional[str]:
        """
        Create a new account.

        NOTA:
        - La colección actual de cuentas es raíz ('cuentas'), con 'id' numérico.
        - Esta función crea una cuenta básica en la colección raíz.
        - 'proyecto_id' se incluye en los datos por si en el futuro se quieren
          filtrar cuentas por proyecto, pero en Firestore actual puede no existir.

        Args:
            proyecto_id: Project ID (guardado como campo informativo)
            nombre: Account name
            tipo: Account type (efectivo, banco, tarjeta, inversion, ahorro, etc.)
            saldo_inicial: Initial balance (default 0.0)
            moneda: Currency code (default "RD$")
            is_principal: Whether this is the main account (default False)

        Returns:
            Account document ID if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            now = datetime.now()
            cuenta_data = {
                "nombre": nombre,
                "tipo": tipo.lower(),  # Normalize to lowercase
                "tipo_cuenta": tipo.lower(),
                "saldo_inicial": saldo_inicial,
                "moneda": moneda,
                "is_principal": is_principal,
                "proyecto_id": proyecto_id,
                "fecha_creacion": now,
                "createdAt": now,
                "updatedAt": now,
                "activo": True,
            }

            cuentas_ref = self.db.collection("cuentas")
            doc_ref = cuentas_ref.document()
            doc_ref.set(cuenta_data)

            logger.info(
                "Created account: %s (doc ID: %s) [project=%s]",
                nombre,
                doc_ref.id,
                proyecto_id,
            )
            return doc_ref.id

        except Exception as e:
            logger.error("Error creating account for project %s: %s", proyecto_id, e)
            return None

    def update_cuenta(
        self,
        proyecto_id: str,
        cuenta_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update an existing account in the global 'cuentas' collection.

        Args:
            proyecto_id: Project ID (no se usa para la ruta, solo informativo)
            cuenta_id: Account document ID to update
            updates: Dictionary with fields to update

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            # Normalize tipo if present
            if "tipo" in updates:
                updates["tipo"] = updates["tipo"].lower()
                updates["tipo_cuenta"] = updates["tipo"]

            # Add update timestamp
            updates["fecha_modificacion"] = datetime.now()
            updates["updatedAt"] = datetime.now()

            cuenta_ref = self.db.collection("cuentas").document(cuenta_id)
            cuenta_ref.update(updates)

            logger.info("Updated account %s (project hint: %s)", cuenta_id, proyecto_id)
            return True

        except Exception as e:
            logger.error(
                "Error updating account %s (project %s): %s",
                cuenta_id,
                proyecto_id,
                e,
            )
            return False

    def delete_cuenta(
        self,
        proyecto_id: str,
        cuenta_id: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete an account from the global 'cuentas' collection.

        Args:
            proyecto_id: Project ID (informativo)
            cuenta_id: Account document ID to delete
            soft_delete: If True, marks as inactive instead of deleting (default True)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            cuenta_ref = self.db.collection("cuentas").document(cuenta_id)

            if soft_delete:
                # Soft delete: mark as inactive
                cuenta_ref.update(
                    {
                        "activo": False,
                        "fecha_eliminacion": datetime.now(),
                        "updatedAt": datetime.now(),
                    }
                )
                logger.info(
                    "Soft deleted account %s (project hint: %s)",
                    cuenta_id,
                    proyecto_id,
                )
            else:
                # Hard delete: remove from Firestore
                cuenta_ref.delete()
                logger.info(
                    "Hard deleted account %s (project hint: %s)",
                    cuenta_id,
                    proyecto_id,
                )

            return True

        except Exception as e:
            logger.error(
                "Error deleting account %s (project %s): %s",
                cuenta_id,
                proyecto_id,
                e,
            )
            return False

    def get_cuenta_by_id(
        self,
        proyecto_id: str,
        cuenta_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific account by document ID from the global 'cuentas' collection.

        Args:
            proyecto_id: Project ID (informativo)
            cuenta_id: Account document ID

        Returns:
            Account dictionary or None if not found
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            cuenta_ref = self.db.collection("cuentas").document(cuenta_id)
            doc = cuenta_ref.get()

            if doc.exists:
                data = doc.to_dict() or {}
                raw_id = data.get("id", doc.id)
                acc_id = str(raw_id)
                cuenta_data = {
                    "id": acc_id,
                    "nombre": data.get("nombre", f"Cuenta {acc_id}"),
                    "tipo": data.get("tipo_cuenta") or data.get("tipo", ""),
                    "raw": data,
                }
                logger.info(
                    "Retrieved account %s (project hint: %s)", cuenta_id, proyecto_id
                )
                return cuenta_data

            logger.warning(
                "Account %s not found in 'cuentas' (project hint: %s)",
                cuenta_id,
                proyecto_id,
            )
            return None

        except Exception as e:
            logger.error(
                "Error getting account %s (project %s): %s", cuenta_id, proyecto_id, e
            )
            return None


# ==================== MÉTODOS GLOBALES (Añadir a FirebaseClient) ====================

    def get_cuentas(self) -> List[Dict[str, Any]]:
        """Recupera TODAS las cuentas del catálogo maestro (colección raíz)."""
        if not self.is_initialized(): return []
        try:
            # Reutilizamos lógica o consultamos directo
            docs = self.db.collection("cuentas").stream()
            items = []
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                items.append(d)
            # Ordenar por nombre
            items.sort(key=lambda x: x.get('nombre', '').lower())
            return items
        except Exception as e:
            logger.error(f"Error recuperando cuentas maestras: {e}")
            return []

    def get_categorias(self) -> List[Dict[str, Any]]:
        """Recupera TODAS las categorías del sistema (colección raíz)."""
        if not self.is_initialized(): return []
        try:
            docs = self.db.collection("categorias").stream()
            items = []
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                items.append(d)
            return items
        except Exception as e:
            logger.error(f"Error recuperando categorías globales: {e}")
            return []

    def get_subcategorias(self) -> List[Dict[str, Any]]:
        """Recupera TODAS las subcategorías del sistema (colección raíz)."""
        if not self.is_initialized(): return []
        try:
            docs = self.db.collection("subcategorias").stream()
            items = []
            for doc in docs:
                d = doc.to_dict()
                d["id"] = doc.id
                items.append(d)
            return items
        except Exception as e:
            logger.error(f"Error recuperando subcategorías globales: {e}")
            return []

    # ==================== TRANSACTIONS ====================

    def get_transacciones_by_proyecto(
        self,
        proyecto_id: str,
        cuenta_id: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get transactions from project SUBCOLLECTION (the correct location).
        
        Args:
            proyecto_id: Project ID
            cuenta_id: Optional account ID to filter by
            include_deleted: Whether to include deleted transactions (default False)
            
        Returns:
            List of transaction dictionaries (includes transfers for display)
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            # ✅ PASO 1: Cargar mapa de cuentas ANTES de procesar
            try:
                cuentas_proyecto = self.get_cuentas_by_proyecto(proyecto_id) or []
                cuentas_map = {
                    str(c. get('id')): c.get('nombre', f"Cuenta {c.get('id')}")
                    for c in cuentas_proyecto
                    if 'id' in c
                }
                logger.debug(f"Loaded {len(cuentas_map)} accounts for name resolution")
            except Exception as e: 
                logger.warning(f"Could not load accounts map: {e}")
                cuentas_map = {}
            
            # CORRECCIÓN: Buscar en la SUBCOLECCIÓN del proyecto
            trans_ref = (
                self.db.collection('proyectos')
                .document(str(proyecto_id))
                .collection('transacciones')
            )
            
            # Construir query
            if cuenta_id:
                try:
                    cuenta_id_int = int(cuenta_id)
                    query = trans_ref.where('cuenta_id', '==', cuenta_id_int)
                except (ValueError, TypeError):
                    query = trans_ref.where('cuenta_id', '==', cuenta_id)
                docs = query.stream()
            else:
                # No hay filtro de cuenta, obtener todas
                docs = trans_ref.stream()
            
            # Procesar transacciones
            transacciones = []
            excluded_count = 0
            
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id  # Importante: incluir el ID del documento

                # Filtrar eliminadas si es necesario
                if not include_deleted: 
                    # Solo excluir si está EXPLÍCITAMENTE marcada como eliminada
                    if data.get('deleted') == True or data.get('activo') == False:
                        excluded_count += 1
                        continue
                
                # ✅ Normalizar cuenta_id a STRING para filtros
                if 'cuenta_id' in data:
                    data['cuenta_id'] = str(data['cuenta_id'])
                
                # ✅ PASO 2: Resolver nombres de cuentas en transferencias
                if data.get('es_transferencia') or 'Transferencia' in data. get('descripcion', ''):
                    descripcion_original = data.get('descripcion', '')
                    
                    # Buscar y reemplazar patrones "Cuenta X" con nombres reales
                    import re
                    
                    # Patrón para detectar "Cuenta <número>"
                    pattern = r'Cuenta (\d+)'
                    
                    def replace_cuenta(match):
                        """Función helper para reemplazar cada coincidencia"""
                        cuenta_id_str = match.group(1)
                        cuenta_nombre = cuentas_map.get(cuenta_id_str, f"Cuenta {cuenta_id_str}")
                        return cuenta_nombre
                    
                    # Reemplazar todas las ocurrencias de "Cuenta X" con nombres
                    descripcion_nueva = re.sub(pattern, replace_cuenta, descripcion_original)
                    
                    # Actualizar solo si cambió
                    if descripcion_nueva != descripcion_original:
                        data['descripcion'] = descripcion_nueva
                        logger.debug(f"Resolved:  '{descripcion_original}' → '{descripcion_nueva}'")
                
                # ✅ Asegurar que adjuntos_paths existe
                if 'adjuntos_paths' not in data:
                    data['adjuntos_paths'] = (
                        data.get('adjuntos_paths') or
                        data.get('adjuntos') or
                        data.get('attachments') or
                        []
                    )
                
                transacciones.append(data)
            
            # Contar transacciones con adjuntos y transferencias
            con_adjuntos = sum(1 for t in transacciones if t.get('adjuntos_paths'))
            transferencias = sum(1 for t in transacciones if t.get('es_transferencia'))
            
            logger.info(
                f"Recuperadas {len(transacciones)} transacciones para proyecto {proyecto_id} "
                f"({con_adjuntos} con adjuntos) "
                f"({transferencias} transferencias) "
                f"{f'({excluded_count} excluidas)' if excluded_count > 0 else ''}"
            )
            return transacciones

        except Exception as e:
            logger.error(f"Error getting project transactions from subcollection: {e}", exc_info=True)
            return []


    def create_transaccion(
        self,
        proyecto_id: str,
        fecha: datetime,
        tipo: str,
        cuenta_id: str,
        categoria_id: str,
        monto: float,
        descripcion: str = "",
        comentario: str = "",
        subcategoria_id: Optional[str] = None,
        adjuntos: Optional[List[str]] = None,
        adjuntos_paths: Optional[List[str]] = None,  # ✅ NUEVO PARÁMETRO
    ) -> Optional[str]:
        """
        Create a new transaction in a project. 

        Args:
            proyecto_id: Project ID
            fecha: Transaction date
            tipo: Transaction type ('ingreso' or 'gasto')
            cuenta_id: Account ID (string; se guardará tal cual)
            categoria_id:  Category ID (string)
            monto: Amount (positive number)
            descripcion: Transaction description (optional)
            comentario: Additional comments (optional)
            subcategoria_id: Subcategory ID (optional)
            adjuntos: List of attachment URLs (LEGACY - optional)
            adjuntos_paths: List of attachment storage paths (NEW - optional) ✅

        Returns:
            Transaction ID if successful, None otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            tipo_lower = tipo.lower()
            if tipo_lower not in VALID_TRANSACTION_TYPES:
                logger. error("Invalid transaction type:  %s", tipo)
                return None

            now = datetime.now()

            transaccion_data:  Dict[str, Any] = {
                "fecha": fecha,
                "tipo": tipo_lower,
                "cuenta_id": str(cuenta_id),
                "categoria_id": str(categoria_id),
                "monto":  abs(monto),
                "descripcion": descripcion,
                "comentario": comentario,
                "fecha_creacion": now,
                "createdAt": now,
                "updatedAt": now,
                "activo": True,
            }

            if subcategoria_id:
                transaccion_data["subcategoria_id"] = str(subcategoria_id)

            # ✅ PRIORIDAD: Guardar paths si existen
            if adjuntos_paths:
                transaccion_data["adjuntos_paths"] = adjuntos_paths
                logger.info(f"Saving {len(adjuntos_paths)} attachment paths (NEW format)")
            
            # Legacy: guardar URLs solo si no hay paths
            if adjuntos and not adjuntos_paths: 
                transaccion_data["adjuntos"] = adjuntos
                logger.warning(f"Saving {len(adjuntos)} attachment URLs (LEGACY format)")

            trans_ref = (
                self. db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
            )

            doc_ref = trans_ref. document()
            doc_ref.set(transaccion_data)

            logger.info(
                "Created transaction:  %s (ID: %s) in project %s",
                descripcion,
                doc_ref. id,
                proyecto_id,
            )
            return doc_ref.id

        except Exception as e:
            logger.error("Error creating transaction in project %s: %s", proyecto_id, e)
            return None

    def create_transfer(
        self,
        proyecto_id: str,
        fecha: datetime,
        cuenta_origen_id: Any,
        cuenta_destino_id: Any,
        monto: float,
        nota: str = ""
    ) -> bool:
        """
        Create a transfer between two accounts in the same project.
        
        Creates two linked transactions: 
        - Withdrawal (Gasto) from origin account
        - Deposit (Ingreso) to destination account
        
        ✅ CORREGIDO: Usa NOMBRES de cuentas en descripciones, no IDs. 
        
        Args:
            proyecto_id: Project ID
            fecha: Transfer date
            cuenta_origen_id: Origin account ID
            cuenta_destino_id: Destination account ID
            monto: Transfer amount (positive)
            nota: Optional note/description
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False
        
        try:
            # ✅ PASO 1: Obtener nombres de las cuentas
            try:
                cuentas = self.get_cuentas_by_proyecto(proyecto_id) or []
                cuentas_map = {str(c.get('id')): c.get('nombre', f"Cuenta {c.get('id')}") for c in cuentas}
                
                cuenta_origen_nombre = cuentas_map.get(str(cuenta_origen_id), f"Cuenta {cuenta_origen_id}")
                cuenta_destino_nombre = cuentas_map.get(str(cuenta_destino_id), f"Cuenta {cuenta_destino_id}")
                
                logger.debug(f"Transfer: {cuenta_origen_nombre} → {cuenta_destino_nombre}")
            except Exception as e: 
                logger.warning(f"Could not resolve account names: {e}")
                cuenta_origen_nombre = f"Cuenta {cuenta_origen_id}"
                cuenta_destino_nombre = f"Cuenta {cuenta_destino_id}"
            
            # Normalize IDs
            try:
                cuenta_origen_id = int(cuenta_origen_id)
                cuenta_destino_id = int(cuenta_destino_id)
            except (ValueError, TypeError):
                cuenta_origen_id = str(cuenta_origen_id)
                cuenta_destino_id = str(cuenta_destino_id)
            
            # Validate
            if cuenta_origen_id == cuenta_destino_id: 
                logger.error("Cannot transfer to same account")
                return False
            
            if monto <= 0:
                logger.error("Transfer amount must be positive")
                return False
            
            # Format date
            if isinstance(fecha, datetime):
                fecha_str = fecha.strftime("%Y-%m-%d")
            else:
                fecha_str = str(fecha)
            
            # ✅ PASO 2: Crear descripciones con NOMBRES (no IDs)
            desc_gasto = f"Transferencia a {cuenta_destino_nombre}"
            desc_ingreso = f"Transferencia desde {cuenta_origen_nombre}"
            
            if nota:
                desc_gasto += f" - {nota}"
                desc_ingreso += f" - {nota}"
            
            # Get transaction collection reference
            trans_ref = (
                self.db.collection('proyectos')
                .document(str(proyecto_id))
                .collection('transacciones')
            )
            
            # Create withdrawal transaction (Gasto)
            trans_gasto_ref = trans_ref. document()
            trans_gasto_data = {
                "tipo": "Gasto",
                "cuenta_id": cuenta_origen_id,
                "categoria_id": 0,  # Special category for transfers
                "subcategoria_id": 0,
                "fecha": fecha_str,
                "monto": abs(monto),
                "descripcion": desc_gasto,
                "comentario": nota or "Transferencia automática",
                "proyecto_id": proyecto_id,
                "es_transferencia": True,
                "transferencia_vinculada_id": None,  # Will be set after creating deposit
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
            }
            
            # Create deposit transaction (Ingreso)
            trans_ingreso_ref = trans_ref.document()
            trans_ingreso_data = {
                "tipo": "Ingreso",
                "cuenta_id": cuenta_destino_id,
                "categoria_id":  0,  # Special category for transfers
                "subcategoria_id": 0,
                "fecha": fecha_str,
                "monto":  abs(monto),
                "descripcion": desc_ingreso,
                "comentario": nota or "Transferencia automática",
                "proyecto_id": proyecto_id,
                "es_transferencia": True,
                "transferencia_vinculada_id":  None,  # Will be set after creating withdrawal
                "createdAt": datetime.now(),
                "updatedAt": datetime.now(),
            }
            
            # Link transactions
            trans_gasto_data["transferencia_vinculada_id"] = trans_ingreso_ref.id
            trans_ingreso_data["transferencia_vinculada_id"] = trans_gasto_ref.id
            
            # Save both transactions
            trans_gasto_ref.set(trans_gasto_data)
            trans_ingreso_ref.set(trans_ingreso_data)
            
            logger. info(
                f"✅ Transfer created:  {cuenta_origen_nombre} → {cuenta_destino_nombre} "
                f"(RD$ {monto:,.2f}) on {fecha_str}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Error creating transfer: {e}", exc_info=True)
            return False        

        
    def update_transaccion(
        self,
        proyecto_id: str,
        transaccion_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        """
        Update an existing transaction.

        Args:
            proyecto_id: Project ID
            transaccion_id: Transaction ID to update
            updates: Dictionary with fields to update
                    Puede incluir 'adjuntos_paths' (nuevo) o 'adjuntos' (legacy)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            # Validate tipo if present
            if "tipo" in updates:
                tipo_lower = str(updates["tipo"]).lower()
                if tipo_lower not in VALID_TRANSACTION_TYPES:
                    logger.error("Invalid transaction type: %s", updates["tipo"])
                    return False
                updates["tipo"] = tipo_lower

            # Ensure monto is positive if present
            if "monto" in updates:
                updates["monto"] = abs(float(updates["monto"]))

            # Normalizar IDs a str si vienen en updates
            for key in ("cuenta_id", "categoria_id", "subcategoria_id"):
                if key in updates and updates[key] is not None: 
                    updates[key] = str(updates[key])

            # ✅ Log si se están actualizando adjuntos
            if "adjuntos_paths" in updates:
                logger. info(f"Updating adjuntos_paths:  {len(updates['adjuntos_paths'])} paths")
            elif "adjuntos" in updates: 
                logger.warning(f"Updating adjuntos (LEGACY): {len(updates['adjuntos'])} URLs")

            updates["fecha_modificacion"] = datetime.now()
            updates["updatedAt"] = datetime. now()

            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
                .document(transaccion_id)
            )
            trans_ref.update(updates)

            logger.info(
                "Updated transaction %s in project %s", transaccion_id, proyecto_id
            )
            return True

        except Exception as e: 
            logger.error(
                "Error updating transaction %s in project %s: %s",
                transaccion_id,
                proyecto_id,
                e,
            )
            return False




    def delete_transaccion(
        self,
        proyecto_id: str,
        transaccion_id: str,
        soft_delete: bool = True,
    ) -> bool:
        """
        Delete a transaction.

        Args:
            proyecto_id: Project ID
            transaccion_id: Transaction ID to delete
            soft_delete: If True, marks as inactive instead of deleting (default True)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
                .document(transaccion_id)
            )

            if soft_delete:
                trans_ref.update(
                    {
                        "activo": False,
                        "fecha_eliminacion": datetime.now(),
                        "updatedAt": datetime.now(),
                    }
                )
                logger.info(
                    "Soft deleted transaction %s in project %s",
                    transaccion_id,
                    proyecto_id,
                )
            else:
                trans_ref.delete()
                logger.info(
                    "Hard deleted transaction %s in project %s",
                    transaccion_id,
                    proyecto_id,
                )

            return True

        except Exception as e:
            logger.error(
                "Error deleting transaction %s in project %s: %s",
                transaccion_id,
                proyecto_id,
                e,
            )
            return False

    def get_transaccion_by_id(
        self,
        proyecto_id: str,
        transaccion_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific transaction by ID.

        Args:
            proyecto_id: Project ID
            transaccion_id: Transaction ID

        Returns:
            Transaction dictionary or None if not found
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
                .document(transaccion_id)
            )

            doc = trans_ref.get()

            if doc.exists:
                trans_data = doc.to_dict() or {}
                trans_data["id"] = doc.id

                # Normalizar IDs numéricos a str
                for key in ("cuenta_id", "categoria_id", "subcategoria_id"):
                    if key in trans_data and trans_data[key] is not None:
                        trans_data[key] = str(trans_data[key])

                logger.info(
                    "Retrieved transaction %s from project %s",
                    transaccion_id,
                    proyecto_id,
                )
                return trans_data

            logger.warning(
                "Transaction %s not found in project %s", transaccion_id, proyecto_id
            )
            return None

        except Exception as e:
            logger.error(
                "Error getting transaction %s from project %s: %s",
                transaccion_id,
                proyecto_id,
                e,
            )
            return None


    def get_transacciones_globales(self, limit: int = 1000) -> List[Dict[str, Any]]:
            """
            Recupera las últimas transacciones de TODOS los proyectos usando una Collection Group Query.
            Útil para el reporte global de cuentas y auditoría.
            """
            if not self.db:
                return []

            try:
                # collection_group busca en todas las subcolecciones llamadas 'transacciones'
                # sin importar el documento padre (proyecto).
                query = self.db.collection_group('transacciones')
                
                # Ordenamos por fecha descendente
                query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
                query = query.limit(limit)
                
                docs = query.stream()
                
                resultados = []
                for doc in docs:
                    data = doc.to_dict()
                    data['id'] = doc.id
                    # Normalizar cuenta_id
                    if 'cuenta_id' in data:
                        data['cuenta_id'] = str(data['cuenta_id'])
                    
                    # Intentar obtener el ID del proyecto padre para referencia (opcional)
                    # La referencia es: proyectos/{pid}/transacciones/{tid}
                    try:
                        parent_path = doc.reference.parent.parent.id
                        data['_proyecto_id'] = parent_path
                    except:
                        pass
                        
                    resultados.append(data)
                    
                logger.info(f"Recuperadas {len(resultados)} transacciones globales.")
                return resultados

            except Exception as e:
                logger.error(f"Error en consulta global: {e}")
                if "requires an index" in str(e):
                    logger.critical("FALTA ÍNDICE DE GRUPO DE COLECCIÓN (COLLECTION GROUP INDEX).")
                    logger.critical("Debes crear un índice para 'transacciones' con campo 'fecha' DESC.")
                return []


    # ==================== STORAGE / ATTACHMENTS ====================

    def upload_attachment(
        self,
        proyecto_id: str,
        transaccion_id: str,
        file_path: str,
        file_name: Optional[str] = None,
    ) -> Optional[Tuple[str, str]]: 
        """
        Upload a file attachment to Firebase Storage with PUBLIC permanent URL. 
        
        ✅ MIGRACIÓN:  Ahora usa URLs públicas permanentes (sin tokens que expiren)
        
        Files are stored in:  Proyecto/{proyecto_id}/{year}/{month}/{filename}
        
        Args:
            proyecto_id: Project ID
            transaccion_id: Transaction ID (for organizing)
            file_path: Local path to the file to upload
            file_name: Optional custom filename (defaults to original filename)
            
        Returns:
            Tuple of (public_url, storage_path) if successful, None otherwise
            
        Example:
            url, path = client.upload_attachment("10", "trans123", "/path/to/file.pdf")
            # url:   "https://storage.googleapis.com/bucket/Proyecto/10/2025/01/file.pdf"
            # path: "Proyecto/10/2025/01/file.pdf"
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None
        
        if not self.bucket:
            logger.error("Storage bucket not initialized")
            return None
        
        try:
            import os
            from datetime import datetime
            
            # Get filename
            if not file_name:
                file_name = os.path.basename(file_path)
            
            # Generate storage path:  Proyecto/{proyecto_id}/{year}/{month}/{filename}
            now = datetime.now()
            storage_path = f"Proyecto/{proyecto_id}/{now.year}/{now.month:02d}/{file_name}"
            
            # Upload file
            blob = self.bucket.blob(storage_path)
            
            # Determine content type
            content_type = None
            if file_name.lower().endswith('.pdf'):
                content_type = 'application/pdf'
            elif file_name.lower().endswith(('.jpg', '.jpeg')):
                content_type = 'image/jpeg'
            elif file_name. lower().endswith('.png'):
                content_type = 'image/png'
            elif file_name.lower().endswith('.csv'):
                content_type = 'text/csv'
            elif file_name.lower().endswith('.xlsx'):
                content_type = 'application/vnd. openxmlformats-officedocument.spreadsheetml. sheet'
            
            blob.upload_from_filename(file_path, content_type=content_type)
            
            # ✅ CONSTRUIR URL PÚBLICA PERMANENTE (sin make_public, controlado por reglas)
            bucket_name = self.bucket.name
            public_url = f"https://storage.googleapis.com/{bucket_name}/{storage_path}"
            
            logger.info(f"✅ Uploaded attachment with PUBLIC URL: {file_name} → {storage_path}")
            logger.info(f"   Public URL: {public_url}")
            
            return (public_url, storage_path)
            
        except Exception as e:
            logger.error(f"❌ Error uploading attachment: {e}")
            return None
    
    def get_public_url_from_path(self, storage_path:  str) -> str:
        """
        Construye una URL pública permanente desde un storage_path.
        
        Usa el formato de Firebase Storage API v0 que funciona con reglas públicas.
        
        Args:
            storage_path:  Path relativo en Storage (ej: "Proyecto/10/2025/01/file.pdf")
            
        Returns:  
            URL pública permanente
            
        Example:
            url = client.get_public_url_from_path("Proyecto/10/2025/01/factura.pdf")
            # "https://firebasestorage.googleapis.com/v0/b/bucket/o/Proyecto%2F10%2F2025%2F01%2Ffactura. pdf?alt=media"
        """
        if not self.bucket:
            logger.error("Storage bucket not initialized")
            # Fallback:  usar bucket por defecto
            bucket_name = "progain-25fdf.firebasestorage.app"
        else:
            bucket_name = self.bucket.name
        
        # URL encode del path (/ → %2F)
        import urllib.parse
        encoded_path = urllib.parse.quote(storage_path, safe='')
        
        # Construir URL pública usando Firebase Storage API
        public_url = f"https://firebasestorage.googleapis.com/v0/b/{bucket_name}/o/{encoded_path}?alt=media"
        
        return public_url

    def get_attachment_urls(
        self,
        proyecto_id: str,
        transaccion_id: str,
    ) -> List[Dict[str, str]]:
        """
        Get attachment URLs for a transaction.
        
        ✅ MIGRACIÓN:  Soporta tanto URLs legacy (con tokens) como paths relativos. 
        
        Prioridad: 
        1. Si existe 'adjuntos_paths' → construir URLs públicas desde paths
        2. Si solo existe 'adjuntos' (legacy) → retornar URLs directamente
        
        Args:
            proyecto_id: Project ID
            transaccion_id: Transaction ID
            
        Returns:
            List of dicts with attachment info: 
            [
            {
                "url": "https://storage.googleapis.com/. ../file.pdf",
                "path":  "Proyecto/10/2025/01/file.pdf",
                "filename": "file.pdf"
            }
            ]
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []
        
        try:
            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
                .document(transaccion_id)
            )
            
            doc = trans_ref.get()
            if not doc.exists:
                return []
            
            data = doc.to_dict() or {}
            
            # Estrategia 1: Usar adjuntos_paths (nuevo sistema)
            adjuntos_paths = data.get('adjuntos_paths', [])
            if adjuntos_paths:
                result = []
                for path in adjuntos_paths:
                    if not path: 
                        continue
                    
                    # Construir URL pública desde path
                    url = self.get_public_url_from_path(path)
                    
                    # Extraer filename del path
                    filename = path.split('/')[-1] if '/' in path else path
                    
                    result.append({
                        "url": url,
                        "path": path,
                        "filename": filename
                    })
                
                logger.info(f"Retrieved {len(result)} attachments (new format) for transaction {transaccion_id}")
                return result
            
            # Estrategia 2: Usar adjuntos legacy (URLs con tokens)
            adjuntos_legacy = data.get('adjuntos', [])
            if adjuntos_legacy:
                result = []
                for url in adjuntos_legacy: 
                    if not url:
                        continue
                    
                    # Intentar extraer path de la URL
                    # Formato: https://storage.googleapis.com/{bucket}/{path}? token=...
                    try:
                        if 'storage.googleapis.com' in url:
                            parts = url.split('storage.googleapis.com/')
                            if len(parts) > 1:
                                path_with_token = parts[1]
                                # Remover parámetros de query
                                path = path_with_token.split('?')[0]
                                filename = path. split('/')[-1] if '/' in path else "archivo"
                            else:
                                path = None
                                filename = "archivo"
                        else: 
                            path = None
                            filename = "archivo"
                    except:
                        path = None
                        filename = "archivo"
                    
                    result.append({
                        "url": url,  # URL legacy (puede estar expirada)
                        "path": path,
                        "filename": filename
                    })
                
                logger.warning(f"Retrieved {len(result)} attachments (LEGACY format) for transaction {transaccion_id}")
                logger.warning(f"   ⚠️ URLs may be EXPIRED.  Run migration script to fix.")
                return result
            
            # No hay adjuntos
            return []
            
        except Exception as e:
            logger. error(f"Error getting attachment URLs: {e}")
            return []
    # ==================== CATEGORIES ====================

    def get_categorias_by_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """
        Get all categories for a project.

        Estructura actual:
        - Colección raíz 'categorias' (global).
        - Campos típicos:
            - id        (numérico)
            - nombre
            - createdAt
            - updatedAt

        No están anidadas por proyecto. Por ahora se devuelven todas las categorías
        globales, normalizando 'id' a str.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            categorias_ref = self.db.collection("categorias")
            docs = categorias_ref.stream()

            categorias: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                raw_id = data.get("id", doc.id)
                cat_id = str(raw_id)

                categoria_data = {
                    "id": cat_id,
                    "nombre": data.get("nombre", f"Categoría {cat_id}"),
                    "raw": data,
                }
                categorias.append(categoria_data)

            logger.info(
                "Retrieved %d global categories from 'categorias' collection",
                len(categorias),
            )
            return categorias

        except Exception as e:
            logger.error(
                "Error getting categories from global 'categorias' collection: %s", e
            )
            return []

    # ==================== SUBCATEGORIES ====================

    def get_subcategorias_by_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """
        Get all subcategories for a project.

        Estructura actual:
        - Colección raíz 'subcategorias' (global).
        - Campos:
            - id
            - nombre
            - categoria_id
            - mantenimiento_*
            - createdAt
            - updatedAt

        No están anidadas por proyecto; se devuelven todas, normalizando ids a str.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            sub_ref = self.db.collection("subcategorias")
            docs = sub_ref.stream()

            subcategorias: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                raw_id = data.get("id", doc.id)
                sub_id = str(raw_id)

                sub_data = {
                    "id": sub_id,
                    "nombre": data.get("nombre", f"Subcategoría {sub_id}"),
                    "categoria_id": str(data.get("categoria_id", "")),
                    "raw": data,
                }
                subcategorias.append(sub_data)

            logger.info(
                "Retrieved %d global subcategories from 'subcategorias' collection",
                len(subcategorias),
            )
            return subcategorias

        except Exception as e:
            logger.error("Error getting subcategories from 'subcategorias': %s", e)
            return []

    # ============================================================
    # Cuentas maestras (catálogo global) - usan la colección 'cuentas'
    # ============================================================

    def get_cuentas_maestras(self) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de cuentas maestras desde la colección 'cuentas'.

        Cada documento debe incluir al menos:
        - id (se añade desde doc.id)
        - nombre
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            cuentas: List[Dict[str, Any]] = []
            docs = self.db.collection("cuentas").stream()
            for doc in docs:
                data = doc.to_dict() or {}
                data["id"] = doc.id
                cuentas.append(data)

            # Ordenar por nombre para que la UI sea consistente
            cuentas.sort(key=lambda c: (c.get("nombre") or "").upper())
            return cuentas

        except Exception as e:
            logger.error("Error getting master accounts from 'cuentas': %s", e)
            return []

    def create_cuenta_maestra(self, nombre: str) -> Optional[str]:
        """
        Crea una cuenta maestra nueva en la colección 'cuentas'.
        Ajusta campos extra si tu modelo de cuenta los necesita.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            now = datetime.now()
            doc_ref = self.db.collection("cuentas").document()
            doc_ref.set(
                {
                    "nombre": nombre,
                    "createdAt": now,
                    "updatedAt": now,
                    "activo": True,
                }
            )
            logger.info("Created master account '%s' (ID: %s)", nombre, doc_ref.id)
            return doc_ref.id
        except Exception as e:
            logger.error("Error creating master account '%s': %s", nombre, e)
            return None

    def update_cuenta_maestra(self, cuenta_id: str, nuevo_nombre: str) -> bool:
        """
        Actualiza el nombre de una cuenta maestra existente en 'cuentas'.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            doc_ref = self.db.collection("cuentas").document(cuenta_id)
            doc_ref.update(
                {
                    "nombre": nuevo_nombre,
                    "updatedAt": datetime.now(),
                }
            )
            logger.info("Updated master account %s to '%s'", cuenta_id, nuevo_nombre)
            return True
        except Exception as e:
            logger.error(
                "Error updating master account %s to '%s': %s",
                cuenta_id,
                nuevo_nombre,
                e,
            )
            return False

    def delete_cuenta_maestra(self, cuenta_id: str) -> bool:
        """
        Elimina una cuenta maestra de 'cuentas'.
        OJO: más adelante podemos validar que no esté usada en cuentas de proyecto.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            doc_ref = self.db.collection("cuentas").document(cuenta_id)
            doc_ref.delete()
            logger.info("Deleted master account %s", cuenta_id)
            return True
        except Exception as e:
            logger.error("Error deleting master account %s: %s", cuenta_id, e)
            return False

    # ============================================================
    # Cuentas maestras / cuentas por proyecto
    # ============================================================

    def get_cuentas_por_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """
        Devuelve las cuentas utilizables para un proyecto.

        Por ahora usamos directamente el catálogo global de cuentas,
        porque las transacciones tienen:
          - cuenta_id: número
          - cuentaNombre: string descriptivo

        Retorna lista de dicts:
          {
            "id": int,
            "nombre": str,
            "raw": data_original
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            cuentas_maestras = self.get_cuentas_maestras() or []

            cuentas_normalizadas: List[Dict[str, Any]] = []
            for c in cuentas_maestras:
                raw_id = c.get("id")
                try:
                    cid = int(raw_id)
                except Exception:
                    continue

                cuentas_normalizadas.append(
                    {
                        "id": cid,
                        "nombre": c.get("nombre", f"Cuenta {cid}"),
                        "raw": c,
                    }
                )

            cuentas_normalizadas.sort(key=lambda x: (x["nombre"] or "").upper())

            logger.info(
                "Dashboard cuentas: using %d master accounts for project %s",
                len(cuentas_normalizadas),
                proyecto_id,
            )
            return cuentas_normalizadas

        except Exception as e:
            logger.error("Error getting accounts for project %s: %s", proyecto_id, e)
            return []

    def get_cuentas_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]: 
        """
        Devuelve las cuentas asociadas a un proyecto, enlazando con el catálogo
        global de cuentas para tener nombre y tipo correctos.

        Lee de:
          proyectos/{proyecto_id}/cuentas_proyecto/{doc}:
            - cuenta_id      (numérico o string)
            - cuenta_nombre  (string) opcional
            - principal      (bool)   opcional
        """
        if not self. is_initialized():
            logger. error("Firebase not initialized")
            return []

        try:
            proj_ref = self.db. collection("proyectos").document(str(proyecto_id))
            rel_coll = proj_ref.collection("cuentas_proyecto")
            docs = list(rel_coll.stream())

            # Construir mapa de cuentas maestras (soportando int y str)
            cuentas_maestras = self.get_cuentas_maestras() or []
            cuentas_map = {}
            for c in cuentas_maestras:
                raw_id = c. get("id")
                if raw_id is None:
                    continue
                
                # Normalizar a int si es posible, sino usar string
                try:
                    cid = int(raw_id)
                except (ValueError, TypeError):
                    cid = str(raw_id)
                
                cuentas_map[cid] = c

            result:  List[Dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}
                cid_raw = data.get("cuenta_id")
                if cid_raw is None:
                    continue
                
                # Normalizar a int si es posible, sino usar string
                try:
                    cid = int(cid_raw)
                except (ValueError, TypeError):
                    cid = str(cid_raw)

                principal = bool(data.get("principal", False))
                cat = cuentas_map.get(cid, {})
                nombre = data.get("cuenta_nombre") or cat.get("nombre") or f"Cuenta {cid}"

                result.append(
                    {
                        "cuenta_id": cid,
                        "nombre": nombre,
                        "principal": principal,
                        "raw": data,
                    }
                )

            result.sort(key=lambda x: (not x["principal"], (x["nombre"] or "").upper()))
            
            logger.info("Cargadas %d cuentas vinculadas al proyecto %s", len(result), proyecto_id)
            return result

        except Exception as e:
            logger.error("Error getting project accounts for project %s: %s", proyecto_id, e)
            return []

    def save_cuentas_proyecto(
        self,
        proyecto_id: str,
        cuentas: List[Dict[str, Any]],
    ) -> bool:
        """
        Sobrescribe las cuentas asociadas a un proyecto.

        cuentas: lista de dicts: 
          {
            "cuenta_id": int o str,
            "nombre": str,
            "principal": bool,
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from datetime import datetime

            proj_ref = self. db.collection("proyectos").document(str(proyecto_id))
            rel_coll = proj_ref.collection("cuentas_proyecto")

            # Eliminar cuentas existentes
            existing = list(rel_coll.stream())
            batch = self.db.batch()
            for d in existing:
                batch.delete(d.reference)
            batch.commit()

            # Guardar nuevas cuentas
            now = datetime.now()
            batch = self.db.batch()
            for c in cuentas:
                cid_raw = c.get("cuenta_id")
                if cid_raw is None:
                    continue
                
                # Aceptar tanto int como string
                try:
                    cid = int(cid_raw)
                except (ValueError, TypeError):
                    cid = str(cid_raw)

                doc_ref = rel_coll.document()
                batch. set(
                    doc_ref,
                    {
                        "cuenta_id": cid,  # Puede ser int o str
                        "cuenta_nombre": c.get("nombre", f"Cuenta {cid}"),
                        "principal": bool(c.get("principal", False)),
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )

            batch.commit()
            logger. info(
                "Saved %d project accounts for project %s", len(cuentas), proyecto_id
            )
            return True

        except Exception as e: 
            logger.error("Error saving project accounts for project %s: %s", proyecto_id, e)
            return False
        
    def actualizar_cuentas_de_proyecto(
        self,
        proyecto_id: str,
        ids_cuentas_maestras: List[str],
        id_cuenta_principal: str,
    ) -> bool:
        """
        Sobrescribe las cuentas asociadas a un proyecto, según la lista de IDs
        de cuentas maestras y cuál es principal.

        Guarda en:
          proyectos/{proyecto_id}/cuentas_proyecto/{auto_id}:
            - cuenta_maestra_id
            - is_principal
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            cuentas_coll = proj_ref.collection("cuentas_proyecto")

            # 1. Borramos las actuales
            docs = cuentas_coll.stream()
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()

            # 2. Creamos las nuevas
            batch = self.db.batch()
            now = datetime.now()
            for cuenta_id in ids_cuentas_maestras:
                doc_ref = cuentas_coll.document()  # podríamos usar cuenta_id como id
                batch.set(
                    doc_ref,
                    {
                        "cuenta_maestra_id": cuenta_id,
                        "is_principal": (cuenta_id == id_cuenta_principal),
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()
            logger.info(
                "Updated project accounts for project %s (principal=%s)",
                proyecto_id,
                id_cuenta_principal,
            )
            return True
        except Exception as e:
            logger.error(
                "Error in actualizar_cuentas_de_proyecto for project %s: %s",
                proyecto_id,
                e,
            )
            return False
        

    # ============================================================
    # Categorías maestras (colección global 'categorias')
    # ============================================================

    def get_categorias_maestras(self) -> List[Dict[str, Any]]:
            """
            Devuelve todas las categorías maestras desde la colección global 'categorias'. 
            Cada item: {id, nombre, raw}
            """
            if not self.is_initialized():
                logger.error("Firebase not initialized")
                return []

            try:
                categorias_ref = self.db.collection("categorias")
                docs = categorias_ref.stream()

                categorias: List[Dict[str, Any]] = []
                for doc in docs:
                    data = doc.to_dict() or {}
                    
                    # ✅ PRIORIZAR EL CAMPO "id" (int) SOBRE doc.id (string)
                    raw_id = data.get("id")
                    if raw_id is not None:
                        try:
                            cat_id = int(raw_id)  # Convertir a int si existe
                        except (ValueError, TypeError):
                            cat_id = str(raw_id)
                    else:
                        cat_id = doc.id  # Fallback al document ID
                    
                    categorias. append(
                        {
                            "id": cat_id,  # ✅ Ahora es int si tiene campo "id"
                            "nombre": data.get("nombre", f"Categoría {cat_id}"),
                            "raw":  data,
                        }
                    )

                categorias.sort(key=lambda c: (c. get("nombre") or "").upper())
                
                logger.info(f"Retrieved {len(categorias)} global categories from 'categorias' collection")
                return categorias

            except Exception as e:
                logger.error("Error getting master categories: %s", e)
                return []

    def create_categoria_maestra(self, nombre: str) -> Optional[str]:
        """Crea una categoría maestra en la colección 'categorias'."""
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return None

        try:
            now = datetime.now()
            doc_ref = self.db.collection("categorias").document()
            doc_ref.set(
                {
                    "nombre": nombre,
                    "createdAt": now,
                    "updatedAt": now,
                    "activo": True,
                }
            )
            logger.info("Created master category '%s' (ID: %s)", nombre, doc_ref.id)
            return doc_ref.id
        except Exception as e:
            logger.error("Error creating master category '%s': %s", nombre, e)
            return None

    def update_categoria_maestra(self, categoria_id: str, nuevo_nombre: str) -> bool:
        """Renombra una categoría maestra."""
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            cat_ref = self.db.collection("categorias").document(categoria_id)
            cat_ref.update(
                {
                    "nombre": nuevo_nombre,
                    "updatedAt": datetime.now(),
                }
            )
            logger.info("Updated master category %s to '%s'", categoria_id, nuevo_nombre)
            return True
        except Exception as e:
            logger.error(
                "Error updating master category %s to '%s': %s",
                categoria_id,
                nuevo_nombre,
                e,
            )
            return False

    def delete_categoria_maestra(self, categoria_id: str) -> bool:
        """
        Elimina una categoría maestra.
        NOTA: también deberías decidir qué hacer con las subcategorías de esa categoría.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            # Borrar subcategorías asociadas
            sub_ref = self.db.collection("subcategorias")
            docs = sub_ref.where("categoria_id", "==", categoria_id).stream()
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()

            # Borrar la categoría
            cat_ref = self.db.collection("categorias").document(categoria_id)
            cat_ref.delete()

            logger.info("Deleted master category %s and its subcategories", categoria_id)
            return True
        except Exception as e:
            logger.error("Error deleting master category %s: %s", categoria_id, e)
            return False

    # ============================================================
    # Subcategorías maestras (colección global 'subcategorias')
    # ============================================================

    def get_subcategorias_maestras_by_categoria(
        self, categoria_id: str
    ) -> List[Dict[str, Any]]:
        """Devuelve las subcategorías maestras de una categoría dada."""
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            sub_ref = self.db.collection("subcategorias")

            # Firestore guarda categoria_id como número.
            # Intentamos castear categoria_id a int para que el where coincida.
            try:
                cat_id_num = int(categoria_id)
                query = sub_ref.where("categoria_id", "==", cat_id_num)
            except ValueError:
                # Si no es convertible a int, usamos string (por si acaso en algún doc es string)
                query = sub_ref.where("categoria_id", "==", categoria_id)

            docs = query.stream()

            subcategorias: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                raw_id = data.get("id", doc.id)
                sub_id = str(raw_id)
                subcategorias.append(
                    {
                        "id": sub_id,
                        "nombre": data.get("nombre", f"Subcategoría {sub_id}"),
                        # Normalizamos categoria_id siempre a str para la UI
                        "categoria_id": str(data.get("categoria_id", "")),
                        "raw": data,
                    }
                )

            subcategorias.sort(key=lambda s: (s.get("nombre") or "").upper())
            return subcategorias

        except Exception as e:
            logger.error(
                "Error getting master subcategories for category %s: %s",
                categoria_id,
                e,
            )
            return []

    def create_subcategoria_maestra(
            self, nombre: str, categoria_id:  str
        ) -> Optional[str]:
            """
            Crea una subcategoría maestra con ID numérico autoincremental.
            
            IMPORTANTE: Siempre guarda el campo "id" como número para consistencia.
            """
            if not self.is_initialized():
                logger.error("Firebase not initialized")
                return None

            try:  
                now = datetime.now()
                
                # ✅ 1. NORMALIZAR categoria_id A INT
                try:
                    cat_id_normalized = int(categoria_id)
                except (ValueError, TypeError):
                    cat_id_normalized = categoria_id
                
                # ✅ 2. CALCULAR SIGUIENTE ID NUMÉRICO
                sub_ref = self.db.collection("subcategorias")
                
                # Obtener todas las subcategorías para calcular max ID
                all_docs = list(sub_ref.stream())
                max_id = 0
                
                for doc in all_docs:
                    data = doc. to_dict() or {}
                    # Intentar obtener el campo "id" numérico
                    try:
                        current_id = int(data.get("id", 0))
                        if current_id > max_id: 
                            max_id = current_id
                    except (ValueError, TypeError):
                        # Si no es numérico, ignorar
                        continue
                
                new_id = max_id + 1
                
                logger.info(f"Creating subcategory with id={new_id} (max found was {max_id})")
                
                # ✅ 3. CREAR DOCUMENTO CON CAMPO "id" NUMÉRICO
                doc_ref = sub_ref. document()
                doc_ref.set({
                    "id": new_id,  # ✅ CRÍTICO: Campo numérico para mapeo
                    "nombre": nombre,
                    "categoria_id": cat_id_normalized,
                    "createdAt": now,
                    "updatedAt": now,
                    "activo": True,
                })
                
                logger.info(
                    f"✅ Created subcategory '{nombre}' with id={new_id}, doc_id={doc_ref. id}, categoria_id={cat_id_normalized}"
                )
                return doc_ref.id
                
            except Exception as e:
                logger. error(
                    f"❌ Error creating subcategory '{nombre}' for category {categoria_id}: {e}"
                )
                return None

    def update_subcategoria_maestra(
        self, subcategoria_id: str, nuevo_nombre: str
    ) -> bool:
        """Renombra una subcategoría maestra."""
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            sub_ref = self.db.collection("subcategorias").document(subcategoria_id)
            sub_ref.update(
                {
                    "nombre": nuevo_nombre,
                    "updatedAt": datetime.now(),
                }
            )
            logger.info(
                "Updated master subcategory %s to '%s'",
                subcategoria_id,
                nuevo_nombre,
            )
            return True
        except Exception as e:
            logger.error(
                "Error updating master subcategory %s to '%s': %s",
                subcategoria_id,
                nuevo_nombre,
                e,
            )
            return False

    def delete_subcategoria_maestra(self, subcategoria_id: str) -> bool:
        """Elimina una subcategoría maestra."""
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            sub_ref = self.db.collection("subcategorias").document(subcategoria_id)
            sub_ref.delete()
            logger.info("Deleted master subcategory %s", subcategoria_id)
            return True
        except Exception as e:
            logger.error("Error deleting master subcategory %s: %s", subcategoria_id, e)
            return False
        
    # ============================================================
    # Categorías por proyecto (relación proyecto - categorías maestras)
    # ============================================================

    def get_categorias_por_proyecto(self, proyecto_id:  str) -> List[Dict[str, Any]]:  
        """
        Devuelve las categorías asociadas a un proyecto CON sus nombres correctos.
        
        ✅ CORREGIDO: Filtra categorías huérfanas (sin registro en catálogo maestro).
        
        Lee de:   
            proyectos/{proyecto_id}/categorias_proyecto/{doc_id}
        
        Resuelve nombres desde 'categorias' maestras.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            cat_coll = proj_ref.collection("categorias_proyecto")
            docs = cat_coll.stream()

            # ✅ OBTENER CATÁLOGO DE MAESTRAS CON IDS NORMALIZADOS
            maestras_raw = self.get_categorias_maestras()
            
            # ✅ CREAR MAPA CON AMBOS FORMATOS (INT Y STRING)
            maestras = {}
            for c in maestras_raw: 
                cid = c["id"]
                maestras[cid] = c  # Guardar con tipo original (int)
                maestras[str(cid)] = c  # Guardar también como string

            result:   List[Dict[str, Any]] = []
            categorias_huerfanas = []  # ✅ Para logging
            
            for doc in docs: 
                data = doc.to_dict() or {}
                
                # Obtener ID desde el documento
                cat_master_id_raw = (
                    data.get("categoria_maestra_id") or 
                    data.get("categoria_id") or 
                    doc.id
                )
                
                # ✅ NORMALIZAR A STRING PARA BÚSQUEDA
                cat_master_id_str = str(cat_master_id_raw)
                
                # ✅ BUSCAR EN EL MAPA
                master = maestras.get(cat_master_id_str, {})
                
                # ✅ CRÍTICO: SOLO AGREGAR SI TIENE NOMBRE REAL
                if master and master.get("nombre"):
                    nombre = master["nombre"]
                    
                    result.append({
                        "id": cat_master_id_str,
                        "nombre": nombre,
                        "activa": bool(data.get("activa", True)),
                        "raw": data,
                    })
                else:
                    # ✅ Categoría huérfana (no existe en catálogo maestro)
                    categorias_huerfanas. append(cat_master_id_str)
                    logger.warning(
                        f"⚠️  Categoría huérfana detectada: ID {cat_master_id_str} "
                        f"(existe en proyecto {proyecto_id} pero NO en catálogo maestro)"
                    )
            
            # ✅ LOG RESUMEN
            if categorias_huerfanas: 
                logger.warning(
                    f"❌ {len(categorias_huerfanas)} categorías huérfanas filtradas:  {categorias_huerfanas}"
                )
            
            logger.info(
                f"✅ Loaded {len(result)} valid categories for project {proyecto_id} "
                f"({len(categorias_huerfanas)} orphans filtered)"
            )
            return result

        except Exception as e:
            logger.error(f"Error getting project categories for project {proyecto_id}: {e}")
            return []

    def asignar_categorias_a_proyecto(
        self,
        proyecto_id: str,
        ids_categorias_maestras: List[str],
    ) -> bool:
        """
        Sobrescribe las categorías asociadas a un proyecto según la lista
        de IDs de categorías maestras.

        Guarda en:
          proyectos/{proyecto_id}/categorias_proyecto/{auto_id}:
            - categoria_maestra_id
            - activa = True
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            cat_coll = proj_ref.collection("categorias_proyecto")

            # 1. Borrar existentes
            docs = cat_coll.stream()
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()

            # 2. Crear nuevas
            batch = self.db.batch()
            now = datetime.now()
            for cat_id in ids_categorias_maestras:
                doc_ref = cat_coll.document()
                batch.set(
                    doc_ref,
                    {
                        "categoria_maestra_id": cat_id,
                        "activa": True,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()
            logger.info(
                "Updated project categories for project %s (%d categories)",
                proyecto_id,
                len(ids_categorias_maestras),
            )
            return True
        except Exception as e:
            logger.error(
                "Error assigning project categories for project %s: %s",
                proyecto_id,
                e,
            )
            return False
        

    # ============================================================
    # Subcategorías por proyecto (relación proyecto - subcategorías maestras)
    # ============================================================

    def get_subcategorias_por_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """
        Devuelve las subcategorías asociadas a un proyecto CON nombres correctos. 

        Lee de: 
            proyectos/{proyecto_id}/subcategorias_proyecto/{doc_id}

        Resuelve nombres desde 'subcategorias' maestras.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            sub_coll = proj_ref.collection("subcategorias_proyecto")
            docs = sub_coll.stream()

            # ✅ OBTENER CATÁLOGO DE MAESTRAS CON IDS NORMALIZADOS
            maestras_raw = self.get_subcategorias_maestras() or []
            
            # ✅ CREAR MAPA CON AMBOS FORMATOS (INT Y STRING)
            maestras = {}
            for s in maestras_raw:
                sid = s["id"]
                maestras[sid] = s  # Guardar con tipo original
                maestras[str(sid)] = s  # Guardar también como string

            result:  List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                
                # Obtener IDs desde el documento
                sub_master_id_raw = (
                    data.get("subcategoria_maestra_id") or
                    data.get("subcategoria_id") or
                    doc. id
                )
                
                cat_id_raw = data.get("categoria_id", "")
                
                # ✅ NORMALIZAR A STRING PARA BÚSQUEDA
                sub_master_id_str = str(sub_master_id_raw)
                
                # ✅ BUSCAR EN EL MAPA
                master = maestras.get(sub_master_id_str, {})
                
                # ✅ OBTENER NOMBRE REAL O FALLBACK
                nombre = master.get("nombre", f"Subcategoría {sub_master_id_str}")
                
                # Resolver categoria_id desde el maestro si no está en el documento
                if not cat_id_raw and master: 
                    cat_id_raw = master.get("categoria_id", "")
                
                categoria_id_str = str(cat_id_raw) if cat_id_raw else ""

                result.append({
                    "id": sub_master_id_str,
                    "nombre": nombre,
                    "categoria_id":  categoria_id_str,
                    "activa": bool(data. get("activa", True)),
                    "raw": data,
                })

            logger.info(f"Loaded {len(result)} subcategories for project {proyecto_id} with names resolved")
            return result

        except Exception as e: 
            logger.error(
                f"Error getting project subcategories for project {proyecto_id}: {e}"
            )
            return []

    def asignar_subcategorias_a_proyecto(
        self,
        proyecto_id: str,
        ids_subcategorias_maestras: List[str],
    ) -> bool:
        """
        Sobrescribe las subcategorías asociadas a un proyecto según la lista
        de IDs de subcategorías maestras.

        Guarda en:
          proyectos/{proyecto_id}/subcategorias_proyecto/{auto_id}:
            - subcategoria_maestra_id
            - categoria_id   (copiada desde la maestra)
            - activa = True
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            sub_coll = proj_ref.collection("subcategorias_proyecto")

            # Borrar existentes
            docs = sub_coll.stream()
            batch = self.db.batch()
            for d in docs:
                batch.delete(d.reference)
            batch.commit()

            # Catálogo global para saber la categoria_id de cada subcategoría
            maestras = {s["id"]: s for s in self.get_subcategorias_by_proyecto(proyecto_id)}

            # Crear nuevas
            batch = self.db.batch()
            now = datetime.now()
            for sub_id in ids_subcategorias_maestras:
                master = maestras.get(str(sub_id), {})
                cat_id = str(master.get("categoria_id", ""))

                doc_ref = sub_coll.document()
                batch.set(
                    doc_ref,
                    {
                        "subcategoria_maestra_id": str(sub_id),
                        "categoria_id": cat_id,
                        "activa": True,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()

            logger.info(
                "Updated project subcategories for project %s (%d subcategorías)",
                proyecto_id,
                len(ids_subcategorias_maestras),
            )
            return True

        except Exception as e:
            logger.error(
                "Error assigning project subcategories for project %s: %s",
                proyecto_id,
                e,
            )
            return False
        

    # ============================================================
    # Presupuestos por proyecto
    # ============================================================

    def get_presupuestos_por_proyecto(
        self,
        proyecto_id: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Dict[str, Any]]:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            from datetime import datetime

            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            presup_coll = proj_ref.collection("presupuestos")

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            # Nueva sintaxis: usar FieldFilter con keyword 'filter'
            query = presup_coll
            query = query.where(filter=FieldFilter("fecha_inicio", "==", ini_dt))
            query = query.where(filter=FieldFilter("fecha_fin", "==", fin_dt))

            docs = query.stream()
            result: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                result.append(
                    {
                        "id": doc.id,
                        "categoria_id": str(data.get("categoria_id", "")),
                        "monto": float(data.get("monto", 0.0)),
                        "observaciones": data.get("observaciones", ""),
                        "raw": data,
                    }
                )

            return result

        except Exception as e:
            logger.error(
                "Error getting budgets for project %s in period %s - %s: %s",
                proyecto_id,
                fecha_inicio,
                fecha_fin,
                e,
            )
            return []
                
    def get_gasto_por_categoria_en_periodo(
        self,
        proyecto_id: str,
        categoria_id: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> float:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return 0.0

        try:
            from datetime import datetime

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
            )

            query = trans_ref
            query = query.where(filter=FieldFilter("tipo", "==", TIPO_GASTO))
            query = query.where(filter=FieldFilter("categoria_id", "==", str(categoria_id)))
            query = query.where(filter=FieldFilter("fecha", ">=", ini_dt))
            query = query.where(filter=FieldFilter("fecha", "<=", fin_dt))

            docs = query.stream()
            total = 0.0
            for doc in docs:
                data = doc.to_dict() or {}
                
                # ✅ EXCLUIR TRANSFERENCIAS
                if data.get("es_transferencia") == True:
                    continue
                
                monto = float(data.get("monto", 0.0))
                total += monto

            return total

        except Exception as e:
            logger.error(
                "Error calculating expenses for category %s in project %s: %s",
                categoria_id,
                proyecto_id,
                e,
            )
            return 0.0


    def save_presupuestos_proyecto(
        self,
        proyecto_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        presupuestos: List[Dict[str, Any]],
    ) -> bool:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from datetime import datetime

            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            presup_coll = proj_ref.collection("presupuestos")

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            # 1) Borrar los presupuestos existentes para ese mismo periodo
            try:
                query = presup_coll
                query = query.where(filter=FieldFilter("fecha_inicio", "==", ini_dt))
                query = query.where(filter=FieldFilter("fecha_fin", "==", fin_dt))
                existing = query.stream()

                batch = self.db.batch()
                for d in existing:
                    batch.delete(d.reference)
                batch.commit()
            except Exception as e:
                logger.warning(
                    "Error deleting previous budgets for project %s: %s",
                    proyecto_id,
                    e,
                )

            # 2) Crear los nuevos
            now = datetime.now()
            batch = self.db.batch()
            for p in presupuestos:
                cat_id = str(p.get("categoria_id", ""))
                if not cat_id:
                    continue
                doc_ref = presup_coll.document()
                batch.set(
                    doc_ref,
                    {
                        "categoria_id": cat_id,
                        "monto": float(p.get("monto", 0.0)),
                        "observaciones": p.get("observaciones", ""),
                        "categoria_nombre": p.get("categoria_nombre", ""),
                        "fecha_inicio": ini_dt,
                        "fecha_fin": fin_dt,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()

            logger.info(
                "Saved %d budgets for project %s (period %s - %s)",
                len(presupuestos),
                proyecto_id,
                fecha_inicio,
                fecha_fin,
            )
            return True

        except Exception as e:
            logger.error(
                "Error saving budgets for project %s in period %s - %s: %s",
                proyecto_id,
                fecha_inicio,
                fecha_fin,
                e,
            )
            return False
        
    # ============================================================
    # Presupuestos por SUBCATEGORÍA
    # ============================================================

    def get_presupuestos_subcategorias_por_proyecto(
        self,
        proyecto_id: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve los presupuestos por subcategoría de un proyecto para el periodo dado.

        Lee de:
          proyectos/{proyecto_id}/presupuestos_subcategorias/{doc}:
            - subcategoria_id
            - categoria_id
            - monto
            - observaciones (opcional)
            - fecha_inicio
            - fecha_fin

        Solo trae los que tengan fecha_inicio/fecha_fin EXACTAMENTE iguales
        al rango solicitado (igual que en presupuestos por categoría).
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            from datetime import datetime
            from google.cloud.firestore_v1 import FieldFilter

            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            presup_coll = proj_ref.collection("presupuestos_subcategorias")

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            query = presup_coll
            query = query.where(filter=FieldFilter("fecha_inicio", "==", ini_dt))
            query = query.where(filter=FieldFilter("fecha_fin", "==", fin_dt))

            docs = query.stream()
            result: List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                result.append(
                    {
                        "id": doc.id,
                        "subcategoria_id": str(data.get("subcategoria_id", "")),
                        "categoria_id": str(data.get("categoria_id", "")),
                        "monto": float(data.get("monto", 0.0)),
                        "observaciones": data.get("observaciones", ""),
                        "raw": data,
                    }
                )
            return result

        except Exception as e:
            logger.error(
                "Error getting subcategory budgets for project %s in period %s - %s: %s",
                proyecto_id,
                fecha_inicio,
                fecha_fin,
                e,
            )
            return []

    def get_gasto_por_subcategoria_en_periodo(
        self,
        proyecto_id: str,
        subcategoria_id: str,
        fecha_inicio: date,
        fecha_fin: date,
    ) -> float:
        """
        Calcula el gasto total de una SUBCATEGORÍA en un periodo dado.

        Suma todas las transacciones de tipo 'gasto' cuya:
          - subcategoria_id == subcategoria_id
          - fecha entre fecha_inicio y fecha_fin (inclusive)
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return 0.0

        try:
            from datetime import datetime
            from google.cloud.firestore_v1 import FieldFilter

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            trans_ref = (
                self.db.collection("proyectos")
                .document(proyecto_id)
                .collection("transacciones")
            )

            query = trans_ref
            query = query.where(filter=FieldFilter("tipo", "==", TIPO_GASTO))
            query = query.where(
                filter=FieldFilter("subcategoria_id", "==", str(subcategoria_id))
            )
            query = query.where(filter=FieldFilter("fecha", ">=", ini_dt))
            query = query.where(filter=FieldFilter("fecha", "<=", fin_dt))

            docs = query.stream()
            total = 0.0
            for doc in docs:
                data = doc.to_dict() or {}
                
                # ✅ EXCLUIR TRANSFERENCIAS
                if data.get("es_transferencia") == True:
                    continue
                
                monto = float(data.get("monto", 0.0))
                total += monto

            return total

        except Exception as e:
            logger.error(
                "Error calculating expenses for subcategory %s in project %s: %s",
                subcategoria_id,
                proyecto_id,
                e,
            )
            return 0.0

    def save_presupuestos_subcategorias_proyecto(
        self,
        proyecto_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        presupuestos: List[Dict[str, Any]],
    ) -> bool:
        """
        Sobrescribe los presupuestos por subcategoría de un proyecto para el periodo indicado.

        Args:
            proyecto_id: ID del proyecto
            fecha_inicio, fecha_fin: rango del presupuesto
            presupuestos: lista de dicts:
                {
                  "subcategoria_id": str,
                  "subcategoria_nombre": str,
                  "categoria_id": str,
                  "categoria_nombre": str,
                  "monto": float,
                }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from datetime import datetime
            from google.cloud.firestore_v1 import FieldFilter

            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            presup_coll = proj_ref.collection("presupuestos_subcategorias")

            ini_dt = datetime(fecha_inicio.year, fecha_inicio.month, fecha_inicio.day)
            fin_dt = datetime(fecha_fin.year, fecha_fin.month, fecha_fin.day, 23, 59, 59)

            # 1) Borrar presupuestos existentes para ese periodo
            try:
                query = presup_coll
                query = query.where(filter=FieldFilter("fecha_inicio", "==", ini_dt))
                query = query.where(filter=FieldFilter("fecha_fin", "==", fin_dt))
                existing = query.stream()

                batch = self.db.batch()
                for d in existing:
                    batch.delete(d.reference)
                batch.commit()
            except Exception as e:
                logger.warning(
                    "Error deleting previous subcategory budgets for project %s: %s",
                    proyecto_id,
                    e,
                )

            # 2) Crear nuevos
            now = datetime.now()
            batch = self.db.batch()
            for p in presupuestos:
                sub_id = str(p.get("subcategoria_id", ""))
                if not sub_id:
                    continue
                cat_id = str(p.get("categoria_id", ""))

                doc_ref = presup_coll.document()
                batch.set(
                    doc_ref,
                    {
                        "subcategoria_id": sub_id,
                        "subcategoria_nombre": p.get("subcategoria_nombre", ""),
                        "categoria_id": cat_id,
                        "categoria_nombre": p.get("categoria_nombre", ""),
                        "monto": float(p.get("monto", 0.0)),
                        "observaciones": p.get("observaciones", ""),
                        "fecha_inicio": ini_dt,
                        "fecha_fin": fin_dt,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()

            logger.info(
                "Saved %d subcategory budgets for project %s (period %s - %s)",
                len(presupuestos),
                proyecto_id,
                fecha_inicio,
                fecha_fin,
            )
            return True

        except Exception as e:
            logger.error(
                "Error saving subcategory budgets for project %s in period %s - %s: %s",
                proyecto_id,
                fecha_inicio,
                fecha_fin,
                e,
            )
            return False
        
    # ============================================================
    # Dashboards: Gastos avanzados (por categoría / subcategoría)
    # ============================================================

    def get_cuentas_por_proyecto(self, proyecto_id: str) -> List[Dict[str, Any]]:
        """
        Devuelve las cuentas asociadas a un proyecto (para filtros de dashboards).
        Reutiliza la relación proyecto-cuentas si ya la tienes, o en su defecto
        devuelve todas las cuentas maestras.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            # Si ya tienes una subcolección 'cuentas_proyecto', úsala aquí.
            proj_ref = self.db.collection("proyectos").document(proyecto_id)
            cuentas_coll = proj_ref.collection("cuentas_proyecto")
            docs = cuentas_coll.stream()
            cuentas: List[Dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}
                cuentas.append(
                    {
                        "id": str(data.get("cuenta_id", d.id)),
                        "nombre": data.get("cuenta_nombre", f"Cuenta {d.id}"),
                        "raw": data,
                    }
                )

            # Si no hay nada, como fallback usamos todas las cuentas maestras
            if not cuentas:
                cuentas = self.get_cuentas_maestras()

            return cuentas
        except Exception as e:
            logger.error("Error getting accounts for project %s: %s", proyecto_id, e)
            return []

    # ============================================================
    # Dashboards: rango de fechas de gastos
    # ============================================================

    def get_rango_fechas_transacciones_gasto(
        self, proyecto_id: str
    ) -> tuple[Optional[date], Optional[date]]:
        """
        Devuelve (fecha_min, fecha_max) de las transacciones de tipo Gasto
        para un proyecto dado.

        NOTA: el campo 'fecha' en Firestore es string 'YYYY-MM-DD', así que
        calculamos el rango en Python.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return (None, None)

        try:
            from google.cloud.firestore_v1 import FieldFilter

            trans_ref = (
                self.db.collection("proyectos")
                .document(str(proyecto_id))
                .collection("transacciones")
            )

            query = trans_ref.where(filter=FieldFilter("tipo", "==", "Gasto"))
            docs = list(query.stream())

            if not docs:
                return (None, None)

            fechas: list[date] = []
            for d in docs:
                data = d.to_dict() or {}
                
                # ✅ EXCLUIR TRANSFERENCIAS
                if data.get("es_transferencia") == True:
                    continue
                
                fecha_str = data.get("fecha")
                if not fecha_str:
                    continue
                try:
                    anio, mes, dia = map(int, str(fecha_str).split("-"))
                    fechas.append(date(anio, mes, dia))
                except Exception:
                    continue

            if not fechas:
                return (None, None)

            fecha_min = min(fechas)
            fecha_max = max(fechas)
            logger.info(
                "Dashboard gastos: computed date range %s - %s for project %s",
                fecha_min,
                fecha_max,
                proyecto_id,
            )
            return (fecha_min, fecha_max)

        except Exception as e:
            logger.error(
                "Error getting min/max expense dates for project %s: %s",
                proyecto_id,
                e,
            )
            return (None, None)
                
    # ============================================================
    # Dashboards: gastos agrupados
    # ============================================================

    def get_gastos_agrupados_por_categoria(
            self,
            proyecto_id: str,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[Union[int, str]] = None,
        ) -> List[Dict[str, Any]]:
            """
            Agrupa gastos por categoría para un proyecto y periodo dados.

            - campo 'tipo'        = "Gasto" o "gasto" (string)
            - campo 'fecha'       = "YYYY-MM-DD" (string)
            - campo 'categoria_id' = número o string
            - campo 'cuenta_id'    = número o string
            - ✅ EXCLUYE transferencias internas

            El filtrado de fechas se hace en Python.
            """
            if not self.is_initialized():
                logger.error("Firebase not initialized")
                return []

            try:
                from google. cloud. firestore_v1 import FieldFilter

                trans_ref = (
                    self.db.collection("proyectos")
                    .document(str(proyecto_id))
                    .collection("transacciones")
                )

                # 1) Traer transacciones de tipo Gasto (mayúscula o minúscula)
                query = trans_ref. where(filter=FieldFilter("tipo", "in", ["Gasto", "gasto"]))
                if cuenta_id is not None:
                    query = query.where(filter=FieldFilter("cuenta_id", "==", cuenta_id))

                docs = list(query.stream())
                logger. info(
                    "Dashboard gastos (cat): fetched %d raw expense docs for project %s",
                    len(docs),
                    proyecto_id,
                )

                # Catálogo de categorías maestras:  aceptar IDs int o string
                categorias_maestras = self.get_categorias_maestras() or []
                categorias_map: Dict[Any, Dict[str, Any]] = {}
                for c in categorias_maestras:
                    raw_id = c.get("id")
                    if raw_id is None: 
                        continue

                    # Normalizar a int si es posible, sino usar string
                    try:
                        cid = int(raw_id)
                    except (ValueError, TypeError):
                        cid = str(raw_id)

                    categorias_map[cid] = c

                logger.info(
                    "Dashboard gastos (cat): loaded %d master categories",
                    len(categorias_map),
                )

                totales: Dict[Any, float] = {}
                n_fecha_ok = 0
                n_cat_ok = 0

                for d in docs:
                    data = d. to_dict() or {}

                    # Filtrar solo transacciones activas
                    activo = data.get("activo", True)
                    eliminado = data.get("eliminado", False)
                    if not activo or eliminado: 
                        continue

                    # ✅ EXCLUIR TRANSFERENCIAS (movimientos internos entre cuentas)
                    if data.get("es_transferencia") == True:
                        continue

                    # --- Filtrado de fecha en Python ---
                    fecha_str = data. get("fecha")
                    if not fecha_str:
                        continue
                    try:
                        # Manejar tanto "YYYY-MM-DD" como timestamps
                        fecha_str_clean = str(fecha_str).split()[0]  # Tomar solo la parte de fecha
                        anio, mes, dia = map(int, fecha_str_clean. split("-"))
                        fecha_doc = date(anio, mes, dia)
                    except Exception: 
                        continue

                    if not (fecha_inicio <= fecha_doc <= fecha_fin):
                        continue
                    n_fecha_ok += 1

                    # --- Categoría ---
                    cat_id_raw = data.get("categoria_id")
                    if cat_id_raw is None:
                        continue

                    # ✅ EXCLUIR CATEGORÍA 0 (transferencias sin categoría)
                    if cat_id_raw == 0 or cat_id_raw == '0':
                        continue

                    # Normalizar ID (int o string)
                    try:
                        cat_id = int(cat_id_raw)
                    except (ValueError, TypeError):
                        cat_id = str(cat_id_raw) if cat_id_raw else None

                    if cat_id is None:
                        continue

                    n_cat_ok += 1
                    monto = float(data. get("monto", 0.0))
                    totales[cat_id] = totales.get(cat_id, 0.0) + monto

                logger.info(
                    "Dashboard gastos (cat): after filters: %d docs with date OK, %d with categoria OK (excluding transfers)",
                    n_fecha_ok,
                    n_cat_ok,
                )

                result:  List[Dict[str, Any]] = []
                for cat_id, total in totales.items():
                    cat = categorias_map.get(cat_id, {})
                    nombre = cat.get("nombre", f"Categoría {cat_id}")
                    result.append(
                        {
                            "categoria": nombre,
                            "nombre": nombre,
                            "total_gastado": total,
                        }
                    )

                result.sort(key=lambda x: x["total_gastado"], reverse=True)
                logger.info(
                    "Dashboard gastos (cat): aggregated %d category rows for project %s (excluding transfers)",
                    len(result),
                    proyecto_id,
                )
                return result

            except Exception as e:
                logger.error(
                    "Error getting expenses by category for project %s:  %s",
                    proyecto_id,
                    e,
                )
                return []
                                
    def get_transacciones_gasto_detalle(
        self,
        proyecto_id: str,
        fecha_inicio: date,
        fecha_fin: date,
        cuenta_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Devuelve detalle de transacciones de gasto (para tablas en reportes/dashboard).

        Filtrado de fechas se hace en Python porque 'fecha' es string 'YYYY-MM-DD'.

        Retorna lista de dicts:
          {
            "categoria": nombre_categoria,
            "subcategoria": nombre_subcategoria,
            "monto": float,
            "fecha": "YYYY-MM-DD",
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            from google.cloud.firestore_v1 import FieldFilter

            trans_ref = (
                self.db.collection("proyectos")
                .document(str(proyecto_id))
                .collection("transacciones")
            )

            query = trans_ref.where(filter=FieldFilter("tipo", "==", "Gasto"))
            if cuenta_id is not None:
                query = query.where(filter=FieldFilter("cuenta_id", "==", cuenta_id))

            docs = list(query.stream())
            logger.info(
                "Dashboard gastos detalle: fetched %d raw expense docs for project %s",
                len(docs),
                proyecto_id,
            )

            categorias_map = {int(c["id"]): c for c in self.get_categorias_maestras()}
            subcategorias_map = {int(s["id"]): s for s in self.get_subcategorias_maestras()}

            result: List[Dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}

                # ✅ EXCLUIR TRANSFERENCIAS
                if data.get("es_transferencia") == True:
                    continue

                # Filtrar solo transacciones activas
                activo = data.get("activo", True)
                eliminado = data.get("eliminado", False)
                if not activo or eliminado:
                    continue

                fecha_str = data.get("fecha")
                if not fecha_str:
                    continue
                try:
                    anio, mes, dia = map(int, str(fecha_str).split("-"))
                    fecha_doc = date(anio, mes, dia)
                except Exception:
                    continue

                if not (fecha_inicio <= fecha_doc <= fecha_fin):
                    continue

                cat_id_raw = data.get("categoria_id")
                if cat_id_raw is None:
                    continue
                sub_id_raw = data.get("subcategoria_id")

                try:
                    cat_id = int(cat_id_raw)
                except Exception:
                    continue
                sub_id = int(sub_id_raw) if sub_id_raw is not None else None

                monto = float(data.get("monto", 0.0))

                cat = categorias_map.get(cat_id, {})
                sub = subcategorias_map.get(sub_id, {}) if sub_id is not None else {}
                nombre_cat = cat.get("nombre", f"Categoría {cat_id}")
                nombre_sub = sub.get("nombre", f"Subcategoría {sub_id}") if sub_id is not None else ""

                result.append(
                    {
                        "categoria": nombre_cat,
                        "subcategoria": nombre_sub,
                        "monto": monto,
                        "fecha": fecha_str,
                    }
                )

            result.sort(
                key=lambda x: (
                    x.get("categoria") or "",
                    x.get("subcategoria") or "",
                    x.get("fecha") or "",
                )
            )
            return result

        except Exception as e:
            logger.error(
                "Error getting expense detail transactions for project %s: %s",
                proyecto_id,
                e,
            )
            return []
    # ============================================================
    # Catálogo global de SUBCATEGORÍAS MAESTRAS
    # ============================================================

    def get_subcategorias_maestras(self) -> List[Dict[str, Any]]:
        """
        Devuelve todas las subcategorías maestras desde la colección global 'subcategorias'.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            sub_ref = self.db.collection("subcategorias")
            docs = sub_ref.stream()

            subcategorias:  List[Dict[str, Any]] = []
            for doc in docs:
                data = doc.to_dict() or {}
                
                # ✅ PRIORIZAR CAMPO "id" SOBRE doc.id
                raw_id = data.get("id")
                if raw_id is not None:
                    try:
                        sub_id = int(raw_id)  # Intentar como int primero
                    except (ValueError, TypeError):
                        sub_id = str(raw_id)
                else:
                    # Si no tiene campo "id", usar doc.id (subcategorías antiguas o mal creadas)
                    sub_id = doc.id
                    logger.warning(f"Subcategory document {doc.id} missing 'id' field, using doc.id")
                
                # Normalizar categoria_id
                cat_id_raw = data.get("categoria_id")
                try:
                    cat_id = int(cat_id_raw) if cat_id_raw is not None else None
                except (ValueError, TypeError):
                    cat_id = str(cat_id_raw) if cat_id_raw else None

                subcategorias.append({
                    "id": sub_id,
                    "nombre": data.get("nombre", f"Subcategoría {sub_id}"),
                    "categoria_id": cat_id,
                    "raw": data,
                })

            subcategorias. sort(key=lambda s: (s. get("nombre") or "").upper())
            logger.info(f"Retrieved {len(subcategorias)} global subcategories from 'subcategorias' collection")
            return subcategorias

        except Exception as e:
            logger. error("Error getting global subcategories: %s", e)
            return []

    def get_gastos_agrupados_por_categoria_y_subcategoria(
            self,
            proyecto_id: str,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[Union[int, str]] = None,
        ) -> List[Dict[str, Any]]:
            """
            Agrupa gastos por categoría y subcategoría. 

            Filtrado de fechas se hace en Python porque 'fecha' es string 'YYYY-MM-DD'. 
            ✅ EXCLUYE transferencias internas. 

            Retorna lista de dicts:
            {
                "categoria": nombre_categoria,
                "subcategoria": nombre_subcategoria (o None),
                "cuenta":  nombre_cuenta (opcional),
                "total_gastado": float
            }
            """
            if not self.is_initialized():
                logger.error("Firebase not initialized")
                return []

            try:
                from google.cloud. firestore_v1 import FieldFilter

                trans_ref = (
                    self.db.collection("proyectos")
                    .document(str(proyecto_id))
                    .collection("transacciones")
                )

                # Traer transacciones de tipo Gasto (mayúscula o minúscula)
                query = trans_ref.where(filter=FieldFilter("tipo", "in", ["Gasto", "gasto"]))
                if cuenta_id is not None:
                    query = query.where(filter=FieldFilter("cuenta_id", "==", cuenta_id))

                docs = list(query.stream())
                logger.info(
                    "Dashboard gastos (subcat): fetched %d raw expense docs for project %s",
                    len(docs),
                    proyecto_id,
                )

                # Construir mapas aceptando IDs int o string
                categorias_map = {}
                for c in self.get_categorias_maestras():
                    try: 
                        cid = int(c["id"])
                    except (ValueError, TypeError):
                        cid = str(c["id"])
                    categorias_map[cid] = c

                subcategorias_map = {}
                for s in self.get_subcategorias_maestras():
                    try: 
                        sid = int(s["id"])
                    except (ValueError, TypeError):
                        sid = str(s["id"])
                    subcategorias_map[sid] = s

                cuentas_map = {}
                for c in self.get_cuentas_maestras():
                    try: 
                        cid = int(c["id"])
                    except (ValueError, TypeError):
                        cid = str(c["id"])
                    cuentas_map[cid] = c

                totales: Dict[tuple, float] = {}

                for d in docs: 
                    data = d.to_dict() or {}

                    # Filtrar solo transacciones activas
                    activo = data.get("activo", True)
                    eliminado = data.get("eliminado", False)
                    if not activo or eliminado:
                        continue

                    # ✅ EXCLUIR TRANSFERENCIAS (movimientos internos entre cuentas)
                    if data.get("es_transferencia") == True:
                        continue

                    # Filtrado de fecha en Python
                    fecha_str = data.get("fecha")
                    if not fecha_str:
                        continue
                    try:
                        # Manejar tanto "YYYY-MM-DD" como timestamps
                        fecha_str_clean = str(fecha_str).split()[0]  # Tomar solo la parte de fecha
                        anio, mes, dia = map(int, fecha_str_clean.split("-"))
                        fecha_doc = date(anio, mes, dia)
                    except Exception:
                        continue

                    if not (fecha_inicio <= fecha_doc <= fecha_fin):
                        continue

                    cat_id_raw = data.get("categoria_id")
                    if cat_id_raw is None:
                        continue

                    # ✅ EXCLUIR CATEGORÍA 0 (transferencias sin categoría)
                    if cat_id_raw == 0 or cat_id_raw == '0':
                        continue

                    sub_id_raw = data.get("subcategoria_id")
                    cta_id_raw = data.get("cuenta_id")

                    # Normalizar IDs (int o string)
                    try:
                        cat_id = int(cat_id_raw)
                    except (ValueError, TypeError):
                        cat_id = str(cat_id_raw) if cat_id_raw else None

                    if cat_id is None: 
                        continue

                    # Subcategoría
                    if sub_id_raw is not None: 
                        try:
                            sub_id = int(sub_id_raw)
                        except (ValueError, TypeError):
                            sub_id = str(sub_id_raw)
                    else: 
                        sub_id = None

                    # Cuenta
                    if cta_id_raw is not None:
                        try:
                            cta_id = int(cta_id_raw)
                        except (ValueError, TypeError):
                            cta_id = str(cta_id_raw)
                    else:
                        cta_id = None

                    monto = float(data.get("monto", 0.0))
                    key = (cat_id, sub_id, cta_id)
                    totales[key] = totales.get(key, 0.0) + monto

                result: List[Dict[str, Any]] = []
                for (cat_id, sub_id, cta_id), total in totales.items():
                    cat = categorias_map.get(cat_id, {})
                    sub = subcategorias_map.get(sub_id, {}) if sub_id is not None else {}
                    cta = cuentas_map.get(cta_id, {}) if cta_id is not None else {}

                    nombre_cat = cat.get("nombre", f"Categoría {cat_id}")
                    nombre_sub = sub.get("nombre", f"Subcategoría {sub_id}") if sub_id is not None else None
                    nombre_cta = cta. get("nombre", f"Cuenta {cta_id}") if cta_id is not None else None

                    result.append(
                        {
                            "categoria": nombre_cat,
                            "subcategoria": nombre_sub,
                            "cuenta": nombre_cta,
                            "total_gastado": total,
                        }
                    )

                result.sort(
                    key=lambda x: (
                        x. get("cuenta") or "",
                        x.get("categoria") or "",
                        x.get("subcategoria") or "",
                    )
                )
                logger. info(
                    "Dashboard gastos (subcat): aggregated %d rows for project %s (excluding transfers)",
                    len(result),
                    proyecto_id,
                )
                return result

            except Exception as e:
                logger.error(
                    "Error getting expenses by category and subcategory for project %s: %s",
                    proyecto_id,
                    e,
                )
                return []
    # ============================================================
    # Dashboards: Ingresos vs Gastos (agrupados por mes)
    # ============================================================

    def get_agrupado_ingresos_por_mes(
            self,
            proyecto_id:   str,
            fecha_inicio:  date,
            fecha_fin:  date,
            cuenta_id:  Optional[Union[int, str]] = None,
        ) -> List[Dict[str, Any]]:
            """
            Devuelve ingresos agrupados por mes (YYYY-MM), categoría y subcategoría.

            Estructura de retorno:
            [
                {
                "mes":  "2024-09",
                "categoria": "VENTAS",
                "subcategoria": "VENTA A CREDITO",
                "monto": 1234.56,
                },
                ...
            ]

            Notas:
            - campo 'tipo'       = "Ingreso" o "ingreso"
            - campo 'fecha'      = "YYYY-MM-DD" (string)
            - campo 'categoria_id' y 'subcategoria_id' = números o strings
            - si cuenta_id no es None, filtra por 'cuenta_id'
            - ✅ EXCLUYE transferencias internas
            """
            if not self. is_initialized():
                logger. error("Firebase not initialized")
                return []

            try:
                from google.cloud.firestore_v1 import FieldFilter

                trans_ref = (
                    self.db.collection("proyectos")
                    .document(str(proyecto_id))
                    .collection("transacciones")
                )

                # Traer transacciones de tipo Ingreso (mayúscula o minúscula)
                query = trans_ref.where(filter=FieldFilter("tipo", "in", ["Ingreso", "ingreso"]))
                if cuenta_id is not None: 
                    query = query. where(filter=FieldFilter("cuenta_id", "==", cuenta_id))

                docs = list(query.stream())
                logger.info(
                    "Dashboard IvsE (ingresos): fetched %d raw income docs for project %s",
                    len(docs),
                    proyecto_id,
                )

                # Construir mapas aceptando IDs int o string
                categorias_map = {}
                for c in self.get_categorias_maestras():
                    try:
                        cid = int(c["id"])
                    except (ValueError, TypeError):
                        cid = str(c["id"])
                    categorias_map[cid] = c

                subcategorias_map = {}
                for s in self.get_subcategorias_maestras():
                    try:
                        sid = int(s["id"])
                    except (ValueError, TypeError):
                        sid = str(s["id"])
                    subcategorias_map[sid] = s

                # key:  (mes, cat_id, sub_id) -> total
                totales: Dict[tuple, float] = {}

                for d in docs:
                    data = d.to_dict() or {}

                    # Filtrar solo transacciones activas
                    activo = data. get("activo", True)
                    eliminado = data.get("eliminado", False)
                    if not activo or eliminado: 
                        continue

                    # ✅ EXCLUIR TRANSFERENCIAS (movimientos internos entre cuentas)
                    if data.get("es_transferencia") == True:
                        continue

                    fecha_str = data.get("fecha")
                    if not fecha_str:
                        continue
                    try:
                        # Manejar tanto "YYYY-MM-DD" como timestamps
                        fecha_str_clean = str(fecha_str).split()[0]  # Tomar solo la parte de fecha
                        anio, mes, dia = map(int, fecha_str_clean.split("-"))
                        fecha_doc = date(anio, mes, dia)
                    except Exception:
                        continue

                    if not (fecha_inicio <= fecha_doc <= fecha_fin):
                        continue

                    # mes agrupador YYYY-MM
                    mes_str = f"{fecha_doc.year:04d}-{fecha_doc.month:02d}"

                    cat_id_raw = data.get("categoria_id")
                    sub_id_raw = data.get("subcategoria_id")

                    if cat_id_raw is None:
                        continue

                    # ✅ EXCLUIR CATEGORÍA 0 (transferencias sin categoría)
                    if cat_id_raw == 0 or cat_id_raw == '0':
                        continue

                    # Normalizar IDs (int o string)
                    try: 
                        cat_id = int(cat_id_raw)
                    except (ValueError, TypeError):
                        cat_id = str(cat_id_raw) if cat_id_raw else None

                    if cat_id is None:
                        continue

                    # Subcategoría
                    if sub_id_raw is not None:
                        try:
                            sub_id = int(sub_id_raw)
                        except (ValueError, TypeError):
                            sub_id = str(sub_id_raw)
                    else:
                        sub_id = None

                    monto = float(data.get("monto", 0.0))
                    key = (mes_str, cat_id, sub_id)
                    totales[key] = totales.get(key, 0.0) + monto

                result: List[Dict[str, Any]] = []
                for (mes_str, cat_id, sub_id), total in totales.items():
                    cat = categorias_map.get(cat_id, {})
                    sub = subcategorias_map. get(sub_id, {}) if sub_id is not None else {}
                    nombre_cat = cat.get("nombre", f"Categoría {cat_id}")
                    nombre_sub = sub.get("nombre", f"Subcategoría {sub_id}") if sub_id is not None else None

                    result.append(
                        {
                            "mes":  mes_str,
                            "categoria": nombre_cat,
                            "subcategoria": nombre_sub,
                            "monto":  total,
                        }
                    )

                # ordenar por mes, categoría, subcategoría
                result.sort(
                    key=lambda x: (
                        x.get("mes") or "",
                        x.get("categoria") or "",
                        x. get("subcategoria") or "",
                    )
                )
                logger.info(
                    "Dashboard IvsE (ingresos): aggregated %d rows for project %s (excluding transfers)",
                    len(result),
                    proyecto_id,
                )
                return result

            except Exception as e:
                logger. error(
                    "Error getting grouped incomes by month for project %s: %s",
                    proyecto_id,
                    e,
                )
                return []
                
    def get_agrupado_gastos_por_mes(
            self,
            proyecto_id: str,
            fecha_inicio: date,
            fecha_fin: date,
            cuenta_id: Optional[Union[int, str]] = None,
        ) -> List[Dict[str, Any]]:
            """
            Devuelve gastos agrupados por mes (YYYY-MM), categoría y subcategoría.

            Estructura de retorno:
            [
                {
                "mes": "2024-09",
                "categoria": "COMPRAS",
                "subcategoria": "MADERA",
                "monto": 9876.54,
                },
                ...
            ]

            Notas:
            - campo 'tipo'       = "Gasto" o "gasto"
            - campo 'fecha'      = "YYYY-MM-DD" (string)
            - campo 'categoria_id' y 'subcategoria_id' = números o strings
            - ✅ EXCLUYE transferencias internas
            """
            if not self.is_initialized():
                logger.error("Firebase not initialized")
                return []

            try:
                from google.cloud.firestore_v1 import FieldFilter

                trans_ref = (
                    self.db. collection("proyectos")
                    .document(str(proyecto_id))
                    .collection("transacciones")
                )

                # Traer transacciones de tipo Gasto (mayúscula o minúscula)
                query = trans_ref.where(filter=FieldFilter("tipo", "in", ["Gasto", "gasto"]))
                if cuenta_id is not None: 
                    query = query. where(filter=FieldFilter("cuenta_id", "==", cuenta_id))

                docs = list(query.stream())
                logger.info(
                    "Dashboard IvsE (gastos): fetched %d raw expense docs for project %s",
                    len(docs),
                    proyecto_id,
                )

                # Construir mapas aceptando IDs int o string
                categorias_map = {}
                for c in self. get_categorias_maestras():
                    try:
                        cid = int(c["id"])
                    except (ValueError, TypeError):
                        cid = str(c["id"])
                    categorias_map[cid] = c

                subcategorias_map = {}
                for s in self. get_subcategorias_maestras():
                    try:
                        sid = int(s["id"])
                    except (ValueError, TypeError):
                        sid = str(s["id"])
                    subcategorias_map[sid] = s

                totales: Dict[tuple, float] = {}

                for d in docs:
                    data = d.to_dict() or {}

                    # Filtrar solo transacciones activas
                    activo = data.get("activo", True)
                    eliminado = data. get("eliminado", False)
                    if not activo or eliminado:
                        continue

                    # ✅ EXCLUIR TRANSFERENCIAS (movimientos internos entre cuentas)
                    if data.get("es_transferencia") == True:
                        continue

                    fecha_str = data. get("fecha")
                    if not fecha_str:
                        continue
                    try:
                        # Manejar tanto "YYYY-MM-DD" como timestamps
                        fecha_str_clean = str(fecha_str).split()[0]  # Tomar solo la parte de fecha
                        anio, mes, dia = map(int, fecha_str_clean. split("-"))
                        fecha_doc = date(anio, mes, dia)
                    except Exception: 
                        continue

                    if not (fecha_inicio <= fecha_doc <= fecha_fin):
                        continue

                    mes_str = f"{fecha_doc.year:04d}-{fecha_doc.month:02d}"

                    cat_id_raw = data.get("categoria_id")
                    sub_id_raw = data.get("subcategoria_id")

                    if cat_id_raw is None:
                        continue

                    # ✅ EXCLUIR CATEGORÍA 0 (transferencias sin categoría)
                    if cat_id_raw == 0 or cat_id_raw == '0':
                        continue

                    # Normalizar IDs (int o string)
                    try: 
                        cat_id = int(cat_id_raw)
                    except (ValueError, TypeError):
                        cat_id = str(cat_id_raw) if cat_id_raw else None

                    if cat_id is None:
                        continue

                    # Subcategoría
                    if sub_id_raw is not None: 
                        try:
                            sub_id = int(sub_id_raw)
                        except (ValueError, TypeError):
                            sub_id = str(sub_id_raw)
                    else: 
                        sub_id = None

                    monto = float(data. get("monto", 0.0))
                    key = (mes_str, cat_id, sub_id)
                    totales[key] = totales.get(key, 0.0) + monto

                result: List[Dict[str, Any]] = []
                for (mes_str, cat_id, sub_id), total in totales.items():
                    cat = categorias_map. get(cat_id, {})
                    sub = subcategorias_map.get(sub_id, {}) if sub_id is not None else {}
                    nombre_cat = cat.get("nombre", f"Categoría {cat_id}")
                    nombre_sub = sub.get("nombre", f"Subcategoría {sub_id}") if sub_id is not None else None

                    result.append(
                        {
                            "mes":  mes_str,
                            "categoria": nombre_cat,
                            "subcategoria": nombre_sub,
                            "monto": total,
                        }
                    )

                result.sort(
                    key=lambda x: (
                        x.get("mes") or "",
                        x. get("categoria") or "",
                        x.get("subcategoria") or "",
                    )
                )
                logger.info(
                    "Dashboard IvsE (gastos): aggregated %d rows for project %s (excluding transfers)",
                    len(result),
                    proyecto_id,
                )
                return result

            except Exception as e:
                logger.error(
                    "Error getting grouped expenses by month for project %s: %s",
                    proyecto_id,
                    e,
                )
                return []

    def get_balances_globales_todas_cuentas(self) -> List[Dict[str, Any]]:
        """
        Calcula el resumen global de TODAS las cuentas:

          - total_ingresos: suma de transacciones tipo 'Ingreso'
          - total_gastos:   suma de transacciones tipo 'Gasto'
          - balance:        ingresos - gastos

        Usa:
          - colección global 'cuentas' (catálogo maestro)
          - subcolección 'proyectos/{id}/transacciones' de TODOS los proyectos

        Devuelve una lista de dicts:
          {
            "cuenta_id": int,
            "cuenta": str,
            "total_ingresos": float,
            "total_gastos": float,
            "balance": float,
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            from google.cloud.firestore_v1 import FieldFilter

            # Catálogo global de cuentas
            cuentas_maestras = self.get_cuentas_maestras() or []
            cuentas_map: Dict[int, Dict[str, Any]] = {}
            for c in cuentas_maestras:
                try:
                    cid = int(c["id"])
                except Exception:
                    continue
                cuentas_map[cid] = c

            # Vamos a juntar todas las transacciones de todos los proyectos
            proyectos = self.get_proyectos() or []  # asumiendo que ya tienes este helper
            tot_ing: Dict[int, float] = {}
            tot_gas: Dict[int, float] = {}

            for p in proyectos:
                pid = p.get("id")
                if pid is None:
                    continue

                trans_ref = (
                    self.db.collection("proyectos")
                    .document(str(pid))
                    .collection("transacciones")
                )
                docs = list(trans_ref.stream())
                for d in docs:
                    data = d. to_dict() or {}
                    
                    # ✅ EXCLUIR TRANSFERENCIAS (son movimientos internos)
                    if data.get("es_transferencia") == True:
                        continue
                    
                    # Filtrar solo transacciones activas
                    activo = data.get("activo", True)
                    eliminado = data. get("eliminado", False)
                    if not activo or eliminado:
                        continue
                    
                    tipo = data. get("tipo")
                    cta_raw = data.get("cuenta_id")
                    if cta_raw is None:
                        continue
                    try:
                        cta_id = int(cta_raw)
                    except Exception:
                        continue

                    monto = float(data.get("monto", 0.0))
                    if tipo == "Ingreso":
                        tot_ing[cta_id] = tot_ing.get(cta_id, 0.0) + monto
                    elif tipo == "Gasto":
                        tot_gas[cta_id] = tot_gas.get(cta_id, 0.0) + monto

            # Unimos ingresos y gastos en un listado
            all_ids = set(tot_ing.keys()) | set(tot_gas.keys()) | set(cuentas_map.keys())
            result: List[Dict[str, Any]] = []
            for cid in sorted(all_ids):
                cat = cuentas_map.get(cid, {})
                nombre = cat.get("nombre", f"Cuenta {cid}")
                ingresos = float(tot_ing.get(cid, 0.0))
                gastos = float(tot_gas.get(cid, 0.0))
                balance = ingresos - gastos
                result.append(
                    {
                        "cuenta_id": cid,
                        "cuenta": nombre,
                        "total_ingresos": ingresos,
                        "total_gastos": gastos,
                        "balance": balance,
                    }
                )

            logger.info(
                "Dashboard global cuentas: aggregated %d accounts", len(result)
            )
            return result

        except Exception as e:
            logger.error(
                "Error calculating global balances for all accounts: %s", e
            )
            return []
        
    def get_todas_las_transacciones_globales(self) -> List[Dict[str, Any]]:
        """
        Devuelve todas las transacciones de todos los proyectos,
        normalizando campos clave para dashboards globales:

          {
            "proyecto_id": int,
            "proyecto_nombre": str,
            "cuenta_id": int,
            "cuenta_nombre": str,
            "tipo": str,        # 'Ingreso' o 'Gasto'
            "monto": float,
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proyectos = self.get_proyectos() or []
            cuentas_maestras = self.get_cuentas_maestras() or []
            cuentas_map: Dict[int, Dict[str, Any]] = {}
            for c in cuentas_maestras:
                try:
                    cid = int(c["id"])
                except Exception:
                    continue
                cuentas_map[cid] = c

            result: List[Dict[str, Any]] = []

            for p in proyectos:
                pid = p.get("id")
                pn = p.get("nombre", f"Proyecto {pid}")
                if pid is None:
                    continue

                trans_ref = (
                    self.db.collection("proyectos")
                    .document(str(pid))
                    .collection("transacciones")
                )
                docs = list(trans_ref.stream())
                for d in docs:
                    data = d.to_dict() or {}
                    
                    # ✅ EXCLUIR TRANSFERENCIAS (son movimientos internos)
                    if data. get("es_transferencia") == True:
                        continue
                    
                    # Filtrar solo transacciones activas
                    activo = data.get("activo", True)
                    eliminado = data.get("eliminado", False)
                    if not activo or eliminado: 
                        continue
                    
                    tipo = data.get("tipo")
                    cta_raw = data.get("cuenta_id")
                    if cta_raw is None:
                        continue
                    try:
                        cta_id = int(cta_raw)
                    except Exception:
                        continue
                    monto = float(data.get("monto", 0.0))
                    cat_cta = cuentas_map.get(cta_id, {})
                    cta_nombre = data.get("cuentaNombre") or cat_cta.get("nombre", f"Cuenta {cta_id}")

                    result.append(
                        {
                            "proyecto_id": pid,
                            "proyecto_nombre": pn,
                            "cuenta_id": cta_id,
                            "cuenta_nombre": cta_nombre,
                            "tipo": tipo,
                            "monto": monto,
                        }
                    )

            logger.info(
                "Dashboard global cuentas: retrieved %d global transactions", len(result)
            )
            return result

        except Exception as e:
            logger.error("Error getting all global transactions: %s", e)
            return []
        
    # ============================================================
    # Auditoría: transacciones con categorías / subcategorías huérfanas
    # ============================================================

    def get_transacciones_sin_categoria_activa(
        self, proyecto_id: str
    ) -> list[dict[str, Any]]:
        """
        Devuelve transacciones del proyecto con categoría huérfana PARA ESE PROYECTO.

        Definición de huérfana:
          - categoria_id es None o 0, pero hay categoriaNombre, O
          - categoria_id NO está entre las categorias_activas del proyecto.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            # Categorías activas del proyecto
            cats_proj = self.get_categorias_activas_por_proyecto(proyecto_id) or []
            categorias_activas_ids: set[int] = {
                int(c["id"]) for c in cats_proj if c.get("activo", True)
            }

            # Si no hay configuración por proyecto, consideramos que no hay huérfanas
            if not categorias_activas_ids:
                logger.info(
                    "Auditoría: no project categories defined for project %s; "
                    "skipping orphan-category detection.",
                    proyecto_id,
                )
                return []

            trans_ref = (
                self.db.collection("proyectos")
                .document(str(proyecto_id))
                .collection("transacciones")
            )
            docs = list(trans_ref.stream())

            result: list[dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}

                cat_raw = data.get("categoria_id")
                cat_nombre = data.get("categoriaNombre") or ""

                try:
                    cat_id = int(cat_raw) if cat_raw is not None else None
                except Exception:
                    cat_id = None

                es_huerfana = False

                # Caso 1: id vacío pero hay nombre
                if (cat_id is None or cat_id == 0) and cat_nombre:
                    es_huerfana = True
                else:
                    # Caso 2: id no pertenece al set de categorías activas del proyecto
                    if cat_id is not None and cat_id not in categorias_activas_ids:
                        es_huerfana = True

                if not es_huerfana:
                    continue

                result.append(
                    {
                        "id": data.get("id", d.id),
                        "fecha": data.get("fecha", ""),
                        "descripcion": data.get("descripcion", ""),
                        "categoria_id": cat_id,
                        "categoriaNombre": cat_nombre,
                        "subcategoria_id": data.get("subcategoria_id"),
                        "subcategoriaNombre": data.get("subcategoriaNombre", ""),
                        "cuentaNombre": data.get("cuentaNombre", ""),
                        "monto": float(data.get("monto", 0.0)),
                    }
                )

            logger.info(
                "Auditoría: found %d transactions without active category in project %s",
                len(result),
                proyecto_id,
            )
            return result

        except Exception as e:
            logger.error(
                "Error getting orphan category transactions for project %s: %s",
                proyecto_id,
                e,
            )
            return []


    def get_transacciones_sin_subcategoria_activa(
        self, proyecto_id: str
    ) -> list[dict[str, Any]]:
        """
        Devuelve transacciones del proyecto con subcategoría huérfana PARA ESE PROYECTO.

        Definición de huérfana:
          - subcategoria_id es None o 0, pero hay subcategoriaNombre, O
          - subcategoria_id NO está entre las subcategorias_activas del proyecto.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            subs_proj = self.get_subcategorias_activas_por_proyecto(proyecto_id) or []
            sub_activas_ids: set[int] = {
                int(s["id"]) for s in subs_proj if s.get("activo", True)
            }

            if not sub_activas_ids:
                logger.info(
                    "Auditoría: no project subcategories defined for project %s; "
                    "skipping orphan-subcategory detection.",
                    proyecto_id,
                )
                return []

            trans_ref = (
                self.db.collection("proyectos")
                .document(str(proyecto_id))
                .collection("transacciones")
            )
            docs = list(trans_ref.stream())

            result: list[dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}

                sub_raw = data.get("subcategoria_id")
                sub_nombre = data.get("subcategoriaNombre") or ""

                try:
                    sub_id = int(sub_raw) if sub_raw is not None else None
                except Exception:
                    sub_id = None

                es_huerfana = False

                # Caso 1: id vacío pero hay nombre
                if (sub_id is None or sub_id == 0) and sub_nombre:
                    es_huerfana = True
                else:
                    # Caso 2: id no está entre subcategorías activas del proyecto
                    if sub_id is not None and sub_id not in sub_activas_ids:
                        es_huerfana = True

                if not es_huerfana:
                    continue

                result.append(
                    {
                        "id": data.get("id", d.id),
                        "fecha": data.get("fecha", ""),
                        "descripcion": data.get("descripcion", ""),
                        "categoria_id": data.get("categoria_id"),
                        "categoriaNombre": data.get("categoriaNombre", ""),
                        "subcategoria_id": sub_id,
                        "subcategoriaNombre": sub_nombre,
                        "cuentaNombre": data.get("cuentaNombre", ""),
                        "monto": float(data.get("monto", 0.0)),
                    }
                )

            logger.info(
                "Auditoría: found %d transactions without active subcategory in project %s",
                len(result),
                proyecto_id,
            )
            return result

        except Exception as e:
            logger.error(
                "Error getting orphan subcategory transactions for project %s: %s",
                proyecto_id,
                e,
            )
            return []
        

    # ---------- Helpers de reasignación ----------

    def obtener_o_crear_subcategoria(
        self, nombre: str, categoria_id: int
    ) -> int:
        """
        Devuelve el id de una subcategoría con ese nombre y categoria_id.
        Si no existe, la crea en la colección global 'subcategorias'.

        IMPORTANTE: asume que 'id' en 'subcategorias' es numérico e incremental.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            raise RuntimeError("Firebase not initialized")

        try:
            sub_ref = self.db.collection("subcategorias")
            # Buscar si ya existe
            query = sub_ref.where("nombre", "==", nombre).where(
                "categoria_id", "==", categoria_id
            )
            docs = list(query.stream())
            for d in docs:
                data = d.to_dict() or {}
                try:
                    return int(data.get("id"))
                except Exception:
                    continue

            # Si no existe, creamos una nueva con id incremental
            # Buscamos el máximo id actual
            all_subs = list(sub_ref.stream())
            max_id = 0
            for d in all_subs:
                data = d.to_dict() or {}
                try:
                    sid = int(data.get("id", 0))
                    if sid > max_id:
                        max_id = sid
                except Exception:
                    continue
            new_id = max_id + 1

            doc_ref = sub_ref.document()
            doc_ref.set(
                {
                    "id": new_id,
                    "nombre": nombre,
                    "categoria_id": categoria_id,
                }
            )
            logger.info(
                "Created new subcategory '%s' (id=%s, categoria_id=%s)",
                nombre,
                new_id,
                categoria_id,
            )
            return new_id

        except Exception as e:
            logger.error("Error creating/getting subcategory '%s': %s", nombre, e)
            raise

    def reasignar_multiples_transacciones(
        self,
        proyecto_id: str,
        trans_ids: List[str],
        categoria_destino_id: int,
        subcategoria_destino_id: int,
        categoria_destino_nombre: Optional[str] = None,
        subcategoria_destino_nombre: Optional[str] = None,
    ) -> bool:
        """
        Reasigna un conjunto de transacciones por ID a una categoría/subcategoría destino.
        Actualiza tanto los IDs como los nombres (categoriaNombre, subcategoriaNombre).
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from google.cloud.firestore_v1 import WriteBatch

            if categoria_destino_nombre is None or subcategoria_destino_nombre is None:
                # Resolver nombres desde catálogos si no se pasan
                categorias = {int(c["id"]): c for c in self.get_categorias_maestras()}
                subcats = {int(s["id"]): s for s in self.get_subcategorias_maestras()}
                cat = categorias.get(int(categoria_destino_id), {})
                sub = subcats.get(int(subcategoria_destino_id), {})
                categoria_destino_nombre = categoria_destino_nombre or cat.get(
                    "nombre", f"Categoría {categoria_destino_id}"
                )
                subcategoria_destino_nombre = subcategoria_destino_nombre or sub.get(
                    "nombre", f"Subcategoría {subcategoria_destino_id}"
                )

            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            trans_ref = proj_ref.collection("transacciones")

            batch: WriteBatch = self.db.batch()
            count = 0
            for tid in trans_ids:
                doc_ref = trans_ref.document(str(tid))
                batch.update(
                    doc_ref,
                    {
                        "categoria_id": int(categoria_destino_id),
                        "subcategoria_id": int(subcategoria_destino_id),
                        "categoriaNombre": categoria_destino_nombre,
                        "subcategoriaNombre": subcategoria_destino_nombre,
                    },
                )
                count += 1
                # Para evitar batchs gigantes, puedes cortar cada 400 actualizaciones
                if count % 400 == 0:
                    batch.commit()
                    batch = self.db.batch()
            batch.commit()
            logger.info(
                "Reassigned %d transactions in project %s to cat=%s, subcat=%s",
                len(trans_ids),
                proyecto_id,
                categoria_destino_id,
                subcategoria_destino_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Error reassigning multiple transactions in project %s: %s",
                proyecto_id,
                e,
            )
            return False

    def reasignar_transacciones_por_categoria_origen(
        self,
        proyecto_id: str,
        categoria_origen_id: Optional[int],
        categoria_destino_id: int,
        subcategoria_destino_id: int,
        categoria_destino_nombre: Optional[str] = None,
        subcategoria_destino_nombre: Optional[str] = None,
    ) -> bool:
        """
        Reasigna TODAS las transacciones del proyecto cuya categoria_id == categoria_origen_id
        (incluidas las que no están en la lista parcial) a la nueva categoría/subcategoría destino.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from google.cloud.firestore_v1 import FieldFilter, WriteBatch

            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            trans_ref = proj_ref.collection("transacciones")

            # Query por categoria_origen_id (puede ser None, en cuyo caso filtramos por '== None' no soportado;
            # aquí asumimos que categoria_origen_id es numérico)
            query = trans_ref.where(
                filter=FieldFilter("categoria_id", "==", int(categoria_origen_id))
            )
            docs = list(query.stream())
            if not docs:
                return True

            if categoria_destino_nombre is None or subcategoria_destino_nombre is None:
                categorias = {int(c["id"]): c for c in self.get_categorias_maestras()}
                subcats = {int(s["id"]): s for s in self.get_subcategorias_maestras()}
                cat = categorias.get(int(categoria_destino_id), {})
                sub = subcats.get(int(subcategoria_destino_id), {})
                categoria_destino_nombre = categoria_destino_nombre or cat.get(
                    "nombre", f"Categoría {categoria_destino_id}"
                )
                subcategoria_destino_nombre = subcategoria_destino_nombre or sub.get(
                    "nombre", f"Subcategoría {subcategoria_destino_id}"
                )

            batch: WriteBatch = self.db.batch()
            count = 0
            for d in docs:
                doc_ref = d.reference
                batch.update(
                    doc_ref,
                    {
                        "categoria_id": int(categoria_destino_id),
                        "subcategoria_id": int(subcategoria_destino_id),
                        "categoriaNombre": categoria_destino_nombre,
                        "subcategoriaNombre": subcategoria_destino_nombre,
                    },
                )
                count += 1
                if count % 400 == 0:
                    batch.commit()
                    batch = self.db.batch()
            batch.commit()
            logger.info(
                "Reassigned %d transactions by category origin %s in project %s",
                len(docs),
                categoria_origen_id,
                proyecto_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Error reassigning transactions by origin category in project %s: %s",
                proyecto_id,
                e,
            )
            return False

    def reasignar_transacciones_por_subcategoria_origen(
        self,
        proyecto_id: str,
        subcategoria_origen_id: Optional[int],
        categoria_destino_id: int,
        subcategoria_destino_id: int,
        categoria_destino_nombre: Optional[str] = None,
        subcategoria_destino_nombre: Optional[str] = None,
    ) -> bool:
        """
        Reasigna TODAS las transacciones del proyecto cuya subcategoria_id == subcategoria_origen_id.
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        try:
            from google.cloud.firestore_v1 import FieldFilter, WriteBatch

            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            trans_ref = proj_ref.collection("transacciones")

            query = trans_ref.where(
                filter=FieldFilter("subcategoria_id", "==", int(subcategoria_origen_id))
            )
            docs = list(query.stream())
            if not docs:
                return True

            if categoria_destino_nombre is None or subcategoria_destino_nombre is None:
                categorias = {int(c["id"]): c for c in self.get_categorias_maestras()}
                subcats = {int(s["id"]): s for s in self.get_subcategorias_maestras()}
                cat = categorias.get(int(categoria_destino_id), {})
                sub = subcats.get(int(subcategoria_destino_id), {})
                categoria_destino_nombre = categoria_destino_nombre or cat.get(
                    "nombre", f"Categoría {categoria_destino_id}"
                )
                subcategoria_destino_nombre = subcategoria_destino_nombre or sub.get(
                    "nombre", f"Subcategoría {subcategoria_destino_id}"
                )

            batch: WriteBatch = self.db.batch()
            count = 0
            for d in docs:
                doc_ref = d.reference
                batch.update(
                    doc_ref,
                    {
                        "categoria_id": int(categoria_destino_id),
                        "subcategoria_id": int(subcategoria_destino_id),
                        "categoriaNombre": categoria_destino_nombre,
                        "subcategoriaNombre": subcategoria_destino_nombre,
                    },
                )
                count += 1
                if count % 400 == 0:
                    batch.commit()
                    batch = self.db.batch()
            batch.commit()
            logger.info(
                "Reassigned %d transactions by origin subcategory %s in project %s",
                len(docs),
                subcategoria_origen_id,
                proyecto_id,
            )
            return True

        except Exception as e:
            logger.error(
                "Error reassigning transactions by origin subcategory in project %s: %s",
                proyecto_id,
                e,
            )
            return False
        
    # ============================================================
    # Categorías / Subcategorías activas por proyecto
    # ============================================================

    def get_categorias_activas_por_proyecto(
        self, proyecto_id: str
    ) -> list[dict[str, Any]]:
        """
        Devuelve las categorías activas para un proyecto.

        Lee de:
          proyectos/{proyecto_id}/categorias_proyecto/{doc}

        Estructura real (según Firestore):
          - categoria_maestra_id : str
          - activa               : bool

        Retorna lista de dicts normalizados:
          { "id": int, "activa": bool, "raw": data_original }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            coll = proj_ref.collection("categorias_proyecto")
            docs = list(coll.stream())

            result: list[dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}
                raw_id = data.get("categoria_maestra_id")
                if raw_id is None:
                    continue
                try:
                    cid = int(raw_id)
                except Exception:
                    # si viene como string no numérica, la guardamos igual como str
                    try:
                        cid = int(str(raw_id))
                    except Exception:
                        logger.warning(
                            "Invalid categoria_maestra_id=%r en categorias_proyecto/%s",
                            raw_id,
                            d.id,
                        )
                        continue

                activa = bool(data.get("activa", True))
                result.append({"id": cid, "activa": activa, "raw": data})

            logger.info(
                "Proyecto %s: loaded %d categorias_proyecto (activas=%d)",
                proyecto_id,
                len(result),
                sum(1 for c in result if c["activa"]),
            )
            return result

        except Exception as e:
            logger.error(
                "Error getting project categories for project %s: %s", proyecto_id, e
            )
            return []

    def get_subcategorias_activas_por_proyecto(
        self, proyecto_id: str
    ) -> list[dict[str, Any]]:
        """
        Devuelve las subcategorías activas para un proyecto.

        Lee de:
          proyectos/{proyecto_id}/subcategorias_proyecto/{doc}

        Estructura real (según Firestore):
          - subcategoria_maestra_id : str
          - categoria_id            : str (id de categoría maestra)
          - activa                  : bool

        Retorna lista de dicts normalizados:
          {
            "id": int,                # id de subcategoría maestra
            "categoria_id": int,      # id de categoría maestra
            "activa": bool,
            "raw": data_original
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            coll = proj_ref.collection("subcategorias_proyecto")
            docs = list(coll.stream())

            result: list[dict[str, Any]] = []
            for d in docs:
                data = d.to_dict() or {}

                raw_sub_id = data.get("subcategoria_maestra_id")
                raw_cat_id = data.get("categoria_id")
                if raw_sub_id is None:
                    continue

                try:
                    sid = int(raw_sub_id)
                except Exception:
                    try:
                        sid = int(str(raw_sub_id))
                    except Exception:
                        logger.warning(
                            "Invalid subcategoria_maestra_id=%r en subcategorias_proyecto/%s",
                            raw_sub_id,
                            d.id,
                        )
                        continue

                cat_id_int: Optional[int] = None
                if raw_cat_id is not None:
                    try:
                        cat_id_int = int(raw_cat_id)
                    except Exception:
                        try:
                            cat_id_int = int(str(raw_cat_id))
                        except Exception:
                            cat_id_int = None

                activa = bool(data.get("activa", True))

                result.append(
                    {
                        "id": sid,
                        "categoria_id": cat_id_int,
                        "activa": activa,
                        "raw": data,
                    }
                )

            logger.info(
                "Proyecto %s: loaded %d subcategorias_proyecto (activas=%d)",
                proyecto_id,
                len(result),
                sum(1 for s in result if s["activa"]),
            )
            return result

        except Exception as e:
            logger.error(
                "Error getting project subcategories for project %s: %s",
                proyecto_id,
                e,
            )
            return []        
    # ============================================================
    # Categorías maestras (catálogo global)
    # ============================================================

    def agregar_categoria_maestra(self, nombre: str) -> bool:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False
        try:
            coll = self.db.collection("categorias")
            # buscar max id
            docs = list(coll.stream())
            max_id = 0
            for d in docs:
                data = d.to_dict() or {}
                try:
                    cid = int(data.get("id", 0))
                    if cid > max_id:
                        max_id = cid
                except Exception:
                    continue
            new_id = max_id + 1
            doc_ref = coll.document()
            doc_ref.set({"id": new_id, "nombre": nombre})
            logger.info("Created master category id=%s nombre=%s", new_id, nombre)
            return True
        except Exception as e:
            logger.error("Error creating master category '%s': %s", nombre, e)
            return False

    def renombrar_categoria_maestra(self, categoria_id: int, nuevo_nombre: str) -> bool:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False
        try:
            coll = self.db.collection("categorias")
            docs = list(coll.where("id", "==", int(categoria_id)).stream())
            if not docs:
                logger.warning(
                    "Master category id=%s not found to rename", categoria_id
                )
                return False
            for d in docs:
                d.reference.update({"nombre": nuevo_nombre})
            logger.info(
                "Renamed master category id=%s to '%s'", categoria_id, nuevo_nombre
            )
            return True
        except Exception as e:
            logger.error(
                "Error renaming master category id=%s: %s", categoria_id, e
            )
            return False

    def eliminar_categoria_maestra(self, categoria_id: int) -> bool:
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False
        try:
            coll = self.db.collection("categorias")
            docs = list(coll.where("id", "==", int(categoria_id)).stream())
            if not docs:
                logger.warning(
                    "Master category id=%s not found to delete", categoria_id
                )
                return False
            for d in docs:
                d.reference.delete()
            logger.info("Deleted master category id=%s", categoria_id)
            return True
        except Exception as e:
            logger.error(
                "Error deleting master category id=%s: %s", categoria_id, e
            )
            return False
        
    # ============================================================
    # Categorías por proyecto (relación proyecto-categoría)
    # ============================================================

    def asignar_categorias_a_proyecto_firebase(
        self,
        proyecto_id: str,
        categoria_ids: list[int],
    ) -> bool:
        """
        Sobrescribe las categorías activas de un proyecto.

        Escribe en:
          proyectos/{proyecto_id}/categorias_proyecto

        Un documento por categoría activa:
          {
            "categoria_maestra_id": <str>,
            "activa": True,
            "createdAt": ...,
            "updatedAt": ...
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        from datetime import datetime, timezone

        try:
            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            coll = proj_ref.collection("categorias_proyecto")

            # Borrar relaciones existentes
            existing = list(coll.stream())
            batch = self.db.batch()
            for d in existing:
                batch.delete(d.reference)
            batch.commit()

            # Insertar nuevas
            now = datetime.now(timezone.utc)
            batch = self.db.batch()
            for cid in categoria_ids:
                try:
                    cid_int = int(cid)
                except Exception:
                    continue
                doc_ref = coll.document()
                batch.set(
                    doc_ref,
                    {
                        "categoria_maestra_id": str(cid_int),
                        "activa": True,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()

            logger.info(
                "Proyecto %s: assigned %d categorias_proyecto",
                proyecto_id,
                len(categoria_ids),
            )
            return True

        except Exception as e:
            logger.error(
                "Error assigning project categories for project %s: %s",
                proyecto_id,
                e,
            )
            return False        

    # ============================================================
    # Transacciones: creación desde importador
    # ============================================================

    def agregar_transaccion_a_proyecto(self, proyecto_id:  str, data: Dict[str, Any]) -> bool:
        """Agrega transacción a la subcolección del proyecto"""
        try:
            # ✅ CRÍTICO:   Normalizar cuenta_id a INT
            if 'cuenta_id' in data: 
                try:
                    data['cuenta_id'] = int(data['cuenta_id'])
                except (ValueError, TypeError):
                    data['cuenta_id'] = str(data['cuenta_id'])
            
            trans_ref = (
                self.db.collection('proyectos')
                . document(str(proyecto_id))
                .collection('transacciones')
            )
            
            if 'id' in data and data['id']:
                doc_id = str(data['id'])
                trans_ref. document(doc_id).set(data)
            else:
                doc_ref = trans_ref. document()
                data['id'] = doc_ref. id
                doc_ref.set(data)
            
            # ✅ LOG con cuenta_id
            logger.info(
                f"Transaction {data['id']} created in project {proyecto_id} "
                f"(cuenta_id={data. get('cuenta_id')}, tipo={data.get('tipo')}, monto={data.get('monto')})"
            )
            return True
            
        except Exception as e: 
            logger.error(f"Error adding transaction: {e}", exc_info=True)
            return False
        
    def asignar_subcategorias_a_proyecto(
        self,
        proyecto_id: str,
        subcategoria_ids: list[str],
    ) -> bool:
        """
        Sobrescribe las subcategorías activas de un proyecto.

        Escribe en:
          proyectos/{proyecto_id}/subcategorias_proyecto

        Un documento por subcategoría activa:
          {
            "subcategoria_maestra_id": <str>,
            "categoria_id": <str>,   # se obtiene del maestro de subcategorías
            "activa": True,
            "createdAt": ...,
            "updatedAt": ...
          }
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return False

        from datetime import datetime, timezone

        try:
            proj_ref = self.db.collection("proyectos").document(str(proyecto_id))
            coll = proj_ref.collection("subcategorias_proyecto")

            # Borrar relaciones existentes
            existing = list(coll.stream())
            batch = self.db.batch()
            for d in existing:
                batch.delete(d.reference)
            batch.commit()

            # Necesitamos mapear subcategoria_id -> categoria_id desde el maestro
            sub_maestras = self.get_subcategorias_maestras() or []
            sub_map = {str(s["id"]): s for s in sub_maestras if "id" in s}

            now = datetime.now(timezone.utc)
            batch = self.db.batch()
            for sid_raw in subcategoria_ids:
                sid_str = str(sid_raw)
                sub = sub_map.get(sid_str)
                if not sub:
                    logger.warning(
                        "Subcategoria maestra id=%s no encontrada en maestro al asignar a proyecto %s",
                        sid_str,
                        proyecto_id,
                    )
                    continue
                cat_id_str = str(sub.get("categoria_id", ""))

                doc_ref = coll.document()
                batch.set(
                    doc_ref,
                    {
                        "subcategoria_maestra_id": sid_str,
                        "categoria_id": cat_id_str,
                        "activa": True,
                        "createdAt": now,
                        "updatedAt": now,
                    },
                )
            batch.commit()

            logger.info(
                "Proyecto %s: assigned %d subcategorias_proyecto",
                proyecto_id,
                len(subcategoria_ids),
            )
            return True

        except Exception as e:
            logger.error(
                "Error assigning project subcategories for project %s: %s",
                proyecto_id,
                e,
            )
            return False
        
    def migrate_transaction_attachments_to_paths(
        self,
        proyecto_id: str,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Migra adjuntos de transacciones desde URLs con tokens a storage_paths.
        
        ✅ Maneja formatos:  
        - gs://bucket/path
        - https://storage.googleapis.com/bucket/path? Expires=...
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return {"error": "Firebase not initialized"}
        
        try:
            import urllib.parse
            
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting attachment migration for project {proyecto_id}")
            
            trans_ref = (
                self.db.collection("proyectos")
                .document(str(proyecto_id))
                .collection("transacciones")
            )
            
            docs = list(trans_ref.stream())
            
            stats = {
                "total_transactions": len(docs),
                "with_attachments": 0,
                "migrated": 0,
                "skipped": 0,
                "errors": 0,
                "details": []
            }
            
            for doc in docs:
                data = doc.to_dict() or {}
                trans_id = doc.id
                
                # Si ya tiene adjuntos_paths, verificar si está corrupto
                existing_paths = data.get("adjuntos_paths", [])
                if existing_paths:
                    # Verificar si tiene parámetros de query (corrupto)
                    needs_fix = any('?' in p or 'Expires=' in p for p in existing_paths if isinstance(p, str))
                    if not needs_fix:
                        stats["skipped"] += 1
                        continue
                    else:
                        logger.warning(f"Found corrupted adjuntos_paths in {trans_id}, will re-migrate")
                
                # Si no tiene adjuntos legacy, skip
                adjuntos_legacy = data.get("adjuntos", [])
                if not adjuntos_legacy:
                    continue
                
                stats["with_attachments"] += 1
                
                # Extraer paths de las URLs
                paths = []
                for url in adjuntos_legacy: 
                    if not url or not isinstance(url, str):
                        continue
                    
                    try:
                        path = None
                        
                        # ✅ FORMATO 1: gs://bucket/Proyecto/... 
                        if url.startswith('gs://'):
                            # Formato: gs://progain-25fdf.firebasestorage.app/Proyecto/10/2025/12/file.jpg
                            parts = url. split('. app/')
                            if len(parts) > 1:
                                path = parts[1]
                                # Remover query params si existen
                                path = path.split('?')[0]
                                path = urllib.parse.unquote(path)
                            else:
                                # Formato alternativo:  gs://bucket-name/path
                                parts = url.split('/', 3)
                                if len(parts) > 3:
                                    path = parts[3]
                                    path = path.split('?')[0]
                                    path = urllib.parse. unquote(path)
                        
                        # ✅ FORMATO 2: https://storage.googleapis.com/bucket/Proyecto/...? Expires=...
                        elif url.startswith('https://storage.googleapis.com/'):
                            # Extraer después de . app/ o bucket/
                            if 'firebasestorage.app/' in url:
                                parts = url.split('firebasestorage.app/')
                                if len(parts) > 1:
                                    path_with_query = parts[1]
                                    # ✅ CRÍTICO: Remover parámetros de query
                                    path = path_with_query.split('?')[0]
                                    path = urllib.parse.unquote(path)
                            else: 
                                # https://storage.googleapis.com/bucket-name/Proyecto/... 
                                parts = url.split('googleapis.com/', 1)
                                if len(parts) > 1:
                                    full_path = parts[1]
                                    # Remover bucket y query params
                                    path_parts = full_path.split('/', 1)
                                    if len(path_parts) > 1:
                                        path_with_query = path_parts[1]
                                        # ✅ CRÍTICO: Remover parámetros de query
                                        path = path_with_query.split('?')[0]
                                        path = urllib.parse.unquote(path)
                        
                        # ✅ VALIDAR:  Debe empezar con "Proyecto/" y NO tener "?"
                        if path and path. startswith('Proyecto/') and '?' not in path:
                            paths.append(path)
                            stats["details"].append(f"✓ {trans_id}:  Extracted clean path {path}")
                        else: 
                            stats["details"].append(f"⚠ {trans_id}:  Invalid path extracted:  '{path}' from {url[: 80]}...")
                            
                    except Exception as e:
                        stats["errors"] += 1
                        stats["details"].append(f"✗ {trans_id}: Error parsing URL - {e}")
                        logger.error(f"Error parsing URL for {trans_id}: {e}")
                
                # Actualizar documento
                if paths:
                    if not dry_run:
                        try:
                            doc.reference.update({
                                "adjuntos_paths": paths,
                                "updatedAt": datetime.now()
                            })
                            stats["migrated"] += 1
                            logger.info(f"✓ Migrated {len(paths)} attachments for transaction {trans_id}")
                        except Exception as e:
                            stats["errors"] += 1
                            stats["details"].append(f"✗ {trans_id}: Error updating - {e}")
                    else:
                        stats["migrated"] += 1
                        logger.info(f"[DRY RUN] Would migrate {len(paths)} attachments for transaction {trans_id}")
                else:
                    # No se pudo extraer ningún path
                    if adjuntos_legacy:
                        stats["details"].append(f"⚠ {trans_id}: No valid paths extracted from {len(adjuntos_legacy)} URLs")
            
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Migration completed:")
            logger.info(f"  Total transactions: {stats['total_transactions']}")
            logger.info(f"  With attachments: {stats['with_attachments']}")
            logger.info(f"  Migrated: {stats['migrated']}")
            logger.info(f"  Skipped (already migrated): {stats['skipped']}")
            logger.info(f"  Errors: {stats['errors']}")
            
            return stats
            
        except Exception as e: 
            logger.error(f"Error in migration: {e}")
            return {"error": str(e)}


    def get_transacciones_globales(self, limit:  int = 10000, include_deleted: bool = False) -> List[Dict[str, Any]]: 
        """
        Recupera transacciones de TODOS los proyectos usando Collection Group Query. 
        
        Args:
            limit:  Máximo número de transacciones a recuperar
            include_deleted: Si incluir transacciones eliminadas
            
        Returns: 
            Lista de transacciones con proyecto_id incluido
        """
        if not self.is_initialized():
            logger.error("Firebase not initialized")
            return []

        try:
            # Collection group query busca en todas las subcolecciones 'transacciones'
            query = self.db. collection_group('transacciones')
            
            # Ordenar por fecha descendente (más recientes primero)
            query = query.order_by('fecha', direction=firestore.Query.DESCENDING)
            query = query.limit(limit)

            docs = query.stream()

            transacciones = []
            excluded_count = 0
            
            for doc in docs:
                data = doc.to_dict() or {}
                data['id'] = doc.id
                
                # Filtrar eliminadas si es necesario
                if not include_deleted: 
                    if data.get('deleted') == True or data.get('activo') == False:
                        excluded_count += 1
                        continue
                
                # Obtener el ID del proyecto padre
                try:
                    # La referencia es:  proyectos/{pid}/transacciones/{tid}
                    proyecto_id = doc.reference.parent.parent.id
                    data['_proyecto_id'] = proyecto_id
                except Exception: 
                    data['_proyecto_id'] = None

                # Normalizar cuenta_id a string
                if 'cuenta_id' in data: 
                    data['cuenta_id'] = str(data['cuenta_id'])
                
                # Asegurar que adjuntos_paths existe
                if 'adjuntos_paths' not in data:
                    data['adjuntos_paths'] = (
                        data.get('adjuntos_paths') or 
                        data.get('adjuntos') or 
                        data.get('attachments') or 
                        []
                    )

                transacciones.append(data)

            logger.info(
                f"Recuperadas {len(transacciones)} transacciones globales"
                f"{f' ({excluded_count} excluidas)' if excluded_count > 0 else ''}"
            )
            return transacciones

        except Exception as e:
            logger. error(f"Error en consulta global de transacciones: {e}")
            if "requires an index" in str(e):
                logger.critical("="*80)
                logger.critical("FALTA ÍNDICE DE COLLECTION GROUP PARA 'transacciones'")
                logger.critical("Sigue estos pasos:")
                logger.critical("1. Ve a Firebase Console → Firestore → Indexes")
                logger.critical("2. Crea un índice compuesto:")
                logger.critical("   - Collection group:  transacciones")
                logger.critical("   - Campo: fecha (Descending)")
                logger.critical("3. Espera a que se cree el índice (puede tardar unos minutos)")
                logger.critical("="*80)
            return []