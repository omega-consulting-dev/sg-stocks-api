"""
Script pour supprimer tous les emojis des logs et les remplacer par du texte simple
Pour éviter les problèmes d'encodage sur Windows (cp1252)
"""
import os
import re
from pathlib import Path

# Mapping des emojis vers du texte simple
EMOJI_REPLACEMENTS = {
    '[INFO]': '[INFO]',
    '[BLOQUE]': '[BLOQUE]',
    '[OK]': '[OK]',
    '[ERREUR]': '[ERREUR]',
    '[DEBUT]': '[DEBUT]',
    '[PACKAGE]': '[PACKAGE]',
    '[TOOLS]': '[TOOLS]',
    '[SAVE]': '[SAVE]',
    '[TARGET]': '[TARGET]',
    '[NOTE]': '[NOTE]',
    '[UPDATE]': '[UPDATE]',
    '[ATTENTION]': '[ATTENTION]',
    '[TERMINE]': '[TERMINE]',
    '[SUCCES]': '[SUCCES]',
    '[IMPORTANT]': '[IMPORTANT]',
    '[INFO]': '[INFO]',
    '[STATS]': '[STATS]',
    '[SUPPRESSION]': '[SUPPRESSION]',
    '[UP]': '[UP]',
    '[DOWN]': '[DOWN]',
    '[STAR]': '[STAR]',
    '[STAR]': '[STAR]',
    '[STYLE]': '[STYLE]',
    '[LOCK]': '[LOCK]',
    '[UNLOCK]': '[UNLOCK]',
    '[LOCKED]': '[LOCKED]',
    '[SKIP]': '[SKIP]',
    '->': '->',
}

def remove_emojis_from_file(file_path):
    """Remplace tous les emojis par du texte dans un fichier"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remplacer chaque emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)
        
        # Sauvegarder si modifié
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"[ERREUR] Impossible de traiter {file_path}: {e}")
        return False

def main():
    """Parcourt tous les fichiers Python et supprime les emojis"""
    base_dir = Path(__file__).parent
    modified_files = []
    
    print("[DEBUT] Suppression des emojis dans tous les fichiers Python...")
    
    # Parcourir tous les fichiers .py
    for py_file in base_dir.rglob('*.py'):
        # Ignorer les fichiers dans __pycache__ et .venv
        if '__pycache__' in str(py_file) or '.venv' in str(py_file):
            continue
        
        if remove_emojis_from_file(py_file):
            modified_files.append(py_file)
            print(f"  [OK] {py_file.relative_to(base_dir)}")
    
    print(f"\n[STATS] {len(modified_files)} fichier(s) modifie(s)")
    print("[TERMINE] Tous les emojis ont ete remplaces!")

if __name__ == '__main__':
    main()
