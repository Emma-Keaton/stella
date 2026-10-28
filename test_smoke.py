import sys
sys.path.insert(0, r'E:\Projects\stella')

# Test imports
from ui import C, StellaUI, WorkspaceSidebar, SettingsWidget
from core.theme_tokens import theme_manager, get_theme, get_token
from core.cloud_config import load_providers, save_provider, get_active_provider
from workspace_store import store

# Test theme system
print('Themes:', theme_manager.list_themes())
for tid in theme_manager.list_themes():
    t = get_theme(tid)
    print(f'  {tid}: bg={t.get("bg")}, primary={t.get("primary")}')

# Test C proxy
print('\nClass C (void):')
print(f'  BG={C.BG}, TEXT={C.TEXT}, PRI={C.PRI}')

C.set_theme('light')
print('\nClass C (light):')
print(f'  BG={C.BG}, TEXT={C.TEXT}, PRI={C.PRI}')

C.set_theme('void')
print('\nClass C (void again):')
print(f'  BG={C.BG}, TEXT={C.TEXT}, PRI={C.PRI}')

# Test workspace store
print('\nWorkspaces:', store().list_workspaces())

# Test cloud config
print('\nProviders:', load_providers())

print('\nALL IMPORTS AND BASIC TESTS PASSED')