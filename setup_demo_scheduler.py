"""
Script pour configurer une tâche automatique de réinitialisation du tenant de démo.

Ce script crée une tâche Windows Task Scheduler qui exécute reset_demo_tenant.py
tous les jours à 3h du matin.
"""

import os
import subprocess
from pathlib import Path

# Chemins
SCRIPT_DIR = Path(__file__).parent.absolute()
RESET_SCRIPT = SCRIPT_DIR / "reset_demo_tenant.py"
PYTHON_EXE = SCRIPT_DIR / ".venv" / "Scripts" / "python.exe"

# Configuration de la tâche
TASK_NAME = "SG-Stock Demo Reset"
TASK_TIME = "03:00"  # 3h du matin

def create_scheduled_task():
    """Crée une tâche planifiée Windows pour réinitialiser le tenant de démo."""
    
    print("=" * 80)
    print("CONFIGURATION DE LA RÉINITIALISATION AUTOMATIQUE DU TENANT DÉMO")
    print("=" * 80)
    
    # Vérifier que le script existe
    if not RESET_SCRIPT.exists():
        print(f"\n❌ Script non trouvé: {RESET_SCRIPT}")
        return False
    
    # Vérifier que Python existe
    if not PYTHON_EXE.exists():
        print(f"\n❌ Python non trouvé: {PYTHON_EXE}")
        print("   Utilisez le chemin complet de votre environnement virtuel")
        return False
    
    print(f"\n✅ Script trouvé: {RESET_SCRIPT}")
    print(f"✅ Python trouvé: {PYTHON_EXE}")
    
    # Commande pour créer la tâche planifiée
    task_command = f'"{PYTHON_EXE}" "{RESET_SCRIPT}"'
    
    # Supprimer la tâche existante si elle existe
    try:
        subprocess.run(
            ['schtasks', '/Delete', '/TN', TASK_NAME, '/F'],
            capture_output=True,
            text=True
        )
        print(f"\n♻️  Ancienne tâche '{TASK_NAME}' supprimée")
    except:
        pass
    
    # Créer la nouvelle tâche
    cmd = [
        'schtasks',
        '/Create',
        '/TN', TASK_NAME,
        '/TR', task_command,
        '/SC', 'DAILY',
        '/ST', TASK_TIME,
        '/F',  # Force la création
        '/RL', 'HIGHEST',  # Exécuter avec les privilèges les plus élevés
    ]
    
    print(f"\n📝 Création de la tâche planifiée...")
    print(f"   Nom: {TASK_NAME}")
    print(f"   Fréquence: Quotidienne")
    print(f"   Heure: {TASK_TIME}")
    print(f"   Commande: {task_command}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("\n✅ Tâche planifiée créée avec succès!")
        print("\n📌 La tâche sera exécutée tous les jours à 3h du matin")
        print("   Elle réinitialisera les données du tenant de démo")
        
        # Afficher comment voir/gérer la tâche
        print("\n💡 Pour gérer la tâche:")
        print("   1. Ouvrez le Planificateur de tâches Windows (taskschd.msc)")
        print("   2. Cherchez la tâche 'SG-Stock Demo Reset'")
        print("   3. Vous pouvez l'exécuter manuellement, la modifier ou la supprimer")
        
        # Proposer d'exécuter immédiatement pour tester
        print("\n❓ Voulez-vous exécuter la tâche maintenant pour tester? (o/n)")
        response = input().lower()
        if response == 'o':
            print("\n🔄 Exécution de la tâche...")
            subprocess.run(['schtasks', '/Run', '/TN', TASK_NAME])
            print("✅ Tâche lancée! Vérifiez les résultats dans quelques secondes.")
        
        return True
    else:
        print(f"\n❌ Erreur lors de la création de la tâche:")
        print(result.stderr)
        print("\n💡 Assurez-vous d'exécuter ce script en tant qu'administrateur")
        return False

def show_alternative_methods():
    """Affiche des méthodes alternatives pour planifier la tâche."""
    
    print("\n" + "=" * 80)
    print("MÉTHODES ALTERNATIVES")
    print("=" * 80)
    
    print("\n1️⃣  Script PowerShell (plus simple):")
    print("   Créez un fichier reset_demo.ps1 avec:")
    print(f'   cd "{SCRIPT_DIR}"')
    print(f'   {PYTHON_EXE} reset_demo_tenant.py')
    print("   Puis configurez-le dans le Planificateur de tâches manuellement")
    
    print("\n2️⃣  Cron-like avec Python (APScheduler):")
    print("   pip install apscheduler")
    print("   Créez un service qui tourne en arrière-plan")
    
    print("\n3️⃣  Celery Beat (pour production):")
    print("   Utilisez Celery avec Django pour planifier des tâches périodiques")
    
    print("\n4️⃣  Exécution manuelle:")
    print(f"   python {RESET_SCRIPT}")
    print("   Exécutez simplement ce script manuellement quand nécessaire")

if __name__ == '__main__':
    success = create_scheduled_task()
    
    if not success:
        show_alternative_methods()
    
    print("\n" + "=" * 80)
