"""
Transaction-related commands for undo/redo system
"""
import logging
from progain4.commands import Command

logger = logging.getLogger(__name__)


class CreateTransactionCommand(Command):
    """Command to create a transaction"""
    
    def __init__(self, firebase_client, proyecto_id: str, data: dict):
        """
        Initialize create transaction command
        
        Args:
            firebase_client: Firebase client instance
            proyecto_id: Project ID
            data: Transaction data dictionary with 'id' field
        """
        self.firebase_client = firebase_client
        self.proyecto_id = str(proyecto_id)
        self.data = data.copy()
        self.transaction_id = data.get('id')
        
        # Create description
        fecha = data.get('fecha', 'N/A')
        monto = data.get('monto', 0)
        tipo = data.get('tipo', 'N/A')
        desc = data.get('descripcion', 'Sin descripción')[:30]
        
        super().__init__(f"Crear transacción: {fecha} {tipo} RD${monto:,.2f} - {desc}")
    
    def execute(self) -> bool:
        """Execute creation of transaction"""
        try:
            logger.debug(f"Creando transacción {self.transaction_id} en proyecto {self.proyecto_id}")
            
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(str(self.proyecto_id))
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.set(self.data)
            
            logger.info(f"✅ Transacción creada: {self.transaction_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error creando transacción {self.transaction_id}: {e}")
            return False
    
    def undo(self) -> bool:
        """Undo creation (delete transaction)"""
        try:
            logger.debug(f"Eliminando transacción {self.transaction_id} (undo)")
            
            trans_ref = (
                self.firebase_client.db.collection('proyectos')
                .document(str(self.proyecto_id))
                .collection('transacciones')
                .document(self.transaction_id)
            )
            trans_ref.delete()
            
            logger.info(f"✅ Transacción eliminada (undo): {self.transaction_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error en undo de transacción {self.transaction_id}: {e}")
            return False
