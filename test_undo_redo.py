#!/usr/bin/env python3
"""
Simple test to verify the undo/redo system works correctly.

This test creates mock commands and tests the UndoRedoManager without Firebase.
"""

import sys
import os
import tempfile
import json

# Add project root to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from progain4.commands.base_command import Command


class MockCommand(Command):
    """Mock command for testing."""
    
    def __init__(self, description: str):
        super().__init__()
        self.description = description
        self.executed = False
        self.undone = False
    
    def execute(self) -> bool:
        self.executed = True
        self.undone = False
        print(f"✅ Executed: {self.description}")
        return True
    
    def undo(self) -> bool:
        self.undone = True
        self.executed = False
        print(f"↩️  Undone: {self.description}")
        return True
    
    def redo(self) -> bool:
        return self.execute()
    
    def get_description(self) -> str:
        return self.description
    
    def to_dict(self):
        return {
            'type': 'Mock',
            'timestamp': self.timestamp,
            'description': self.description
        }
    
    @staticmethod
    def from_dict(data, firebase_client):
        cmd = MockCommand(data['description'])
        cmd.timestamp = data.get('timestamp', cmd.timestamp)
        return cmd


class MockConfigManager:
    """Mock config manager for testing."""
    
    def __init__(self):
        self.config = {}
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value


class MockFirebaseClient:
    """Mock Firebase client for testing."""
    
    def __init__(self):
        self.data = {}


def test_basic_undo_redo():
    """Test basic undo/redo functionality without persistence."""
    print("\n" + "="*60)
    print("TEST 1: Basic Undo/Redo (No Persistence)")
    print("="*60)
    
    from progain4.services.undo_manager import UndoRedoManager
    
    # Create mock dependencies
    mock_fb = MockFirebaseClient()
    mock_config = MockConfigManager()
    
    # Create manager with temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        # Override history file path
        manager = UndoRedoManager(mock_fb, mock_config, max_stack_size=5)
        manager.history_file = temp_file
        
        # Test 1: Execute commands
        cmd1 = MockCommand("Create transaction A")
        cmd2 = MockCommand("Create transaction B")
        cmd3 = MockCommand("Create transaction C")
        
        assert manager.execute_command(cmd1), "Command 1 should execute"
        assert manager.execute_command(cmd2), "Command 2 should execute"
        assert manager.execute_command(cmd3), "Command 3 should execute"
        
        assert cmd1.executed and cmd2.executed and cmd3.executed, "All commands should be executed"
        assert manager.can_undo(), "Should be able to undo"
        assert not manager.can_redo(), "Should not be able to redo yet"
        
        print("✅ Commands executed successfully")
        
        # Test 2: Undo
        assert manager.undo(), "Undo should succeed"
        assert cmd3.undone, "Command 3 should be undone"
        assert manager.can_redo(), "Should be able to redo"
        
        print("✅ Undo works correctly")
        
        # Test 3: Redo
        assert manager.redo(), "Redo should succeed"
        assert cmd3.executed, "Command 3 should be re-executed"
        
        print("✅ Redo works correctly")
        
        # Test 4: Undo all
        manager.undo()
        manager.undo()
        manager.undo()
        
        assert len(manager.undo_stack) == 0, "Undo stack should be empty"
        assert len(manager.redo_stack) == 3, "Redo stack should have 3 commands"
        
        print("✅ Multiple undo works correctly")
        
        # Test 5: New command clears redo stack
        manager.redo()  # Put one back
        cmd4 = MockCommand("Create transaction D")
        manager.execute_command(cmd4)
        
        assert len(manager.redo_stack) == 0, "Redo stack should be cleared"
        assert len(manager.undo_stack) == 2, "Undo stack should have 2 commands"
        
        print("✅ New command clears redo stack")
        
        print("\n✅ All basic tests passed!")
        
    finally:
        # Cleanup
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_persistence():
    """Test JSON persistence."""
    print("\n" + "="*60)
    print("TEST 2: JSON Persistence")
    print("="*60)
    
    from progain4.services.undo_manager import UndoRedoManager
    
    mock_fb = MockFirebaseClient()
    mock_config = MockConfigManager()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        # Create first manager and execute commands
        manager1 = UndoRedoManager(mock_fb, mock_config, max_stack_size=5)
        manager1.history_file = temp_file
        
        cmd1 = MockCommand("Transaction 1")
        cmd2 = MockCommand("Transaction 2")
        
        manager1.execute_command(cmd1)
        manager1.execute_command(cmd2)
        manager1.save_to_file()
        
        print(f"📝 Saved {len(manager1.undo_stack)} commands to file")
        
        # Create second manager and load
        manager2 = UndoRedoManager(mock_fb, mock_config, max_stack_size=5)
        manager2.history_file = temp_file
        manager2.load_from_file()
        
        assert len(manager2.undo_stack) == 2, "Should load 2 commands"
        
        # Check that commands were properly deserialized
        loaded_cmd = manager2.undo_stack[0]
        assert loaded_cmd.get_description() == "Transaction 1", "First command should be Transaction 1"
        
        print(f"✅ Loaded {len(manager2.undo_stack)} commands from file")
        
        # Verify the file contents
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert 'undo_stack' in data, "File should have undo_stack"
            assert 'redo_stack' in data, "File should have redo_stack"
            assert len(data['undo_stack']) == 2, "File should have 2 undo commands"
        
        print("✅ Persistence test passed!")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_stack_size_limit():
    """Test that stack size limit is enforced."""
    print("\n" + "="*60)
    print("TEST 3: Stack Size Limit")
    print("="*60)
    
    from progain4.services.undo_manager import UndoRedoManager
    
    mock_fb = MockFirebaseClient()
    mock_config = MockConfigManager()
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
    
    try:
        manager = UndoRedoManager(mock_fb, mock_config, max_stack_size=3)
        manager.history_file = temp_file
        
        # Execute more commands than the limit
        for i in range(5):
            cmd = MockCommand(f"Transaction {i+1}")
            manager.execute_command(cmd)
        
        assert len(manager.undo_stack) == 3, "Stack should be limited to 3"
        
        # Check that oldest commands were removed
        first_cmd = manager.undo_stack[0]
        assert first_cmd.get_description() == "Transaction 3", "Oldest should be Transaction 3"
        
        print(f"✅ Stack size limit enforced: {len(manager.undo_stack)}/{manager.max_stack_size}")
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


def test_batch_command():
    """Test batch command functionality."""
    print("\n" + "="*60)
    print("TEST 4: Batch Command")
    print("="*60)
    
    from progain4.commands.batch_command import BatchCommand
    
    # Create batch of commands
    cmd1 = MockCommand("Import transaction 1")
    cmd2 = MockCommand("Import transaction 2")
    cmd3 = MockCommand("Import transaction 3")
    
    batch = BatchCommand([cmd1, cmd2, cmd3], "Import 3 transactions")
    
    assert batch.is_batch, "Batch command should have is_batch=True"
    
    # Execute batch
    assert batch.execute(), "Batch execute should succeed"
    assert cmd1.executed and cmd2.executed and cmd3.executed, "All inner commands should execute"
    
    print("✅ Batch execute works")
    
    # Undo batch
    assert batch.undo(), "Batch undo should succeed"
    assert cmd1.undone and cmd2.undone and cmd3.undone, "All inner commands should undo"
    
    print("✅ Batch undo works")
    
    # Redo batch
    assert batch.redo(), "Batch redo should succeed"
    assert cmd1.executed and cmd2.executed and cmd3.executed, "All inner commands should execute again"
    
    print("✅ Batch redo works")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("UNDO/REDO SYSTEM TESTS")
    print("="*60)
    
    try:
        test_basic_undo_redo()
        test_persistence()
        test_stack_size_limit()
        test_batch_command()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
