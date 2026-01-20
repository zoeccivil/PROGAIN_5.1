#!/usr/bin/env python3
"""
Test script for Undo/Redo system
Tests the command pattern implementation without requiring Firebase
"""
import sys
import os

# Add project root to path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from progain4.commands import Command
from progain4.commands.batch_command import BatchCommand
from progain4.services.undo_manager import UndoRedoManager


class MockCommand(Command):
    """Mock command for testing"""
    
    def __init__(self, name: str):
        super().__init__(f"Mock command: {name}")
        self.name = name
        self.executed = False
        self.undone = False
    
    def execute(self) -> bool:
        print(f"  Executing: {self.name}")
        self.executed = True
        self.undone = False
        return True
    
    def undo(self) -> bool:
        print(f"  Undoing: {self.name}")
        self.undone = True
        self.executed = False
        return True


def test_basic_undo_redo():
    """Test basic undo/redo functionality"""
    print("\n🧪 Test 1: Basic Undo/Redo")
    print("-" * 50)
    
    manager = UndoRedoManager()
    
    # Execute a command
    cmd1 = MockCommand("Command 1")
    assert manager.execute_command(cmd1), "Failed to execute command 1"
    assert cmd1.executed, "Command 1 should be executed"
    print(f"✅ Command executed: {cmd1.get_description()}")
    
    # Check state
    assert manager.can_undo(), "Should be able to undo"
    assert not manager.can_redo(), "Should not be able to redo"
    print(f"✅ State correct: can_undo=True, can_redo=False")
    
    # Undo
    assert manager.undo(), "Failed to undo"
    assert cmd1.undone, "Command 1 should be undone"
    print(f"✅ Command undone")
    
    # Check state
    assert not manager.can_undo(), "Should not be able to undo"
    assert manager.can_redo(), "Should be able to redo"
    print(f"✅ State correct: can_undo=False, can_redo=True")
    
    # Redo
    assert manager.redo(), "Failed to redo"
    assert cmd1.executed, "Command 1 should be executed again"
    print(f"✅ Command redone")
    
    print("✅ Test 1 PASSED\n")


def test_batch_command():
    """Test batch command functionality"""
    print("\n🧪 Test 2: Batch Command")
    print("-" * 50)
    
    manager = UndoRedoManager()
    
    # Create batch of commands
    commands = [
        MockCommand("Batch Item 1"),
        MockCommand("Batch Item 2"),
        MockCommand("Batch Item 3"),
    ]
    
    batch = BatchCommand(commands, "Test Batch")
    
    # Execute batch
    assert manager.execute_command(batch), "Failed to execute batch"
    assert all(cmd.executed for cmd in commands), "All commands should be executed"
    print(f"✅ Batch executed: {len(commands)} commands")
    
    # Undo batch
    assert manager.undo(), "Failed to undo batch"
    assert all(cmd.undone for cmd in commands), "All commands should be undone"
    print(f"✅ Batch undone: {len(commands)} commands")
    
    print("✅ Test 2 PASSED\n")


def test_stack_limit():
    """Test that stack respects max size"""
    print("\n🧪 Test 3: Stack Size Limit")
    print("-" * 50)
    
    manager = UndoRedoManager(max_stack_size=3)
    
    # Add 5 commands (should only keep last 3)
    for i in range(5):
        cmd = MockCommand(f"Command {i+1}")
        manager.execute_command(cmd)
    
    history = manager.get_history()
    undo_count = len(history['undo'])
    
    assert undo_count == 3, f"Stack should have 3 items, has {undo_count}"
    print(f"✅ Stack size limited correctly: {undo_count}/3")
    
    print("✅ Test 3 PASSED\n")


def test_descriptions():
    """Test command descriptions"""
    print("\n🧪 Test 4: Command Descriptions")
    print("-" * 50)
    
    manager = UndoRedoManager()
    
    cmd = MockCommand("Test Command")
    manager.execute_command(cmd)
    
    undo_desc = manager.get_undo_description()
    assert "Test Command" in undo_desc, f"Unexpected description: {undo_desc}"
    print(f"✅ Undo description: {undo_desc}")
    
    manager.undo()
    
    redo_desc = manager.get_redo_description()
    assert "Test Command" in redo_desc, f"Unexpected description: {redo_desc}"
    print(f"✅ Redo description: {redo_desc}")
    
    print("✅ Test 4 PASSED\n")


def main():
    """Run all tests"""
    print("=" * 50)
    print("🚀 Undo/Redo System Tests")
    print("=" * 50)
    
    try:
        test_basic_undo_redo()
        test_batch_command()
        test_stack_limit()
        test_descriptions()
        
        print("=" * 50)
        print("✅ ALL TESTS PASSED")
        print("=" * 50)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
