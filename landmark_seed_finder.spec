# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Collect all data files from numba_pokemon_prngs (includes encounter tables, species data, etc.)
numba_prngs_datas = collect_data_files('numba_pokemon_prngs')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources/*.json', 'resources'),
        ('resources/maps', 'resources/maps'),
        ('ui/assets', 'ui/assets'),
        ('pla_pid_iv/pla_reverse/pla_reverse/shaders', 'pla_pid_iv/pla_reverse/pla_reverse/shaders'),
    ] + numba_prngs_datas,
    hiddenimports=[
        'pyopencl',
        'PyQt6.QtSvg',
        'PyQt6.QtPrintSupport',
        'numba_pokemon_prngs',
        'numba_pokemon_prngs.data',
        'numba_pokemon_prngs.data.encounter',
        'numba_pokemon_prngs.data.encounter.encounter_area_la',
        'numba_pokemon_prngs.data.personal',
        'numba_pokemon_prngs.enums',
        'numba_pokemon_prngs.xorshift',
        'pla_pid_iv',
        'pla_pid_iv.util',
        'pla_pid_iv.pla_reverse',
        'pla_pid_iv.pla_reverse.pla_reverse',
        'pla_pid_iv.pla_reverse.pla_reverse.matrix',
        'pla_pid_iv.pla_reverse.pla_reverse.shaders',
    ] + collect_submodules('numba_pokemon_prngs'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LandmarkSeedFinder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LandmarkSeedFinder',
)
