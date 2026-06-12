import sys
sys.path.insert(0, 'src')
try:
    from ui.app import DeskNoteApp
    print('import_ok')
except Exception as e:
    import traceback
    traceback.print_exc()
    print('IMPORT_ERROR')
