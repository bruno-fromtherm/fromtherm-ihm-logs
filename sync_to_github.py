import os
import shutil
import subprocess
import datetime

# CONFIGURAÇÕES
# Pasta onde os arquivos CSV da IHM chegam (raiz dos uploads)
SOURCE_DIR = SOURCE_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\FROMTHERM_IHM_UPLOADS"
# Pasta dentro do repositório LOCAL onde vamos guardar os CSVs
DEST_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm_ihm_logs_repo\ihm_logs"

# Raiz do repositório Git LOCAL
GIT_REPO_PATH = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm_ihm_logs_repo"

# Arquivo que registra quais arquivos já foram processados
PROCESSED_FILES_LOG = os.path.join(GIT_REPO_PATH, "processed_files.log")

def log_message(message: str):
    """Registra mensagens na tela e em um arquivo de log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    # Garante que a pasta do log existe antes de tentar escrever
    os.makedirs(os.path.dirname(PROCESSED_FILES_LOG), exist_ok=True)
    with open(os.path.join(GIT_REPO_PATH, "sync_log.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_processed_files():
    """Lê a lista de arquivos já processados."""
    processed = set()
    if os.path.exists(PROCESSED_FILES_LOG):
        with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
            for line in f:
                processed.add(line.strip())
    return processed

def add_processed_file(filepath: str):
    """Adiciona um arquivo à lista de processados."""
    with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as f:
        f.write(filepath + "\n")

def run_git_command(command: list):
    """Executa um comando Git e loga o resultado."""
    try:
        result = subprocess.run(
            command,
            cwd=GIT_REPO_PATH,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8"
        )
        log_message(f"Git: {' '.join(command)} -> {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"Erro Git: {' '.join(command)} -> {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        log_message("Erro: Git não encontrado. Certifique-se de que o Git está instalado e no PATH.")
        return False

def sync_files():
    log_message("Iniciando sincronização de arquivos CSV para o GitHub...")

    if not os.path.exists(SOURCE_DIR):
        log_message(f"Pasta de origem não encontrada: {SOURCE_DIR}")
        log_message("Sincronização finalizada com erro de configuração.")
        return

    processed = get_processed_files()
    new_files = []

    # Varre a pasta de origem
    for root, _, files in os.walk(SOURCE_DIR):
        for file in files:
            # Só queremos arquivos CSV
            if not file.lower().endswith(".csv"):
                continue

            source_path = os.path.join(root, file)

            # Se já foi processado, pula
            if source_path in processed:
                continue

            # Caminho relativo para manter subpastas (se existirem)
            relative = os.path.relpath(source_path, SOURCE_DIR)
            dest_path = os.path.join(DEST_DIR, relative)

            # Garante que a pasta de destino existe
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            try:
                shutil.copy2(source_path, dest_path)
                log_message(f"Copiado: {source_path} -> {dest_path}")
                new_files.append(source_path)
                add_processed_file(source_path)
            except Exception as e:
                log_message(f"Erro ao copiar {source_path}: {e}")

    if not new_files:
        log_message("Nenhum novo arquivo CSV encontrado.")
        log_message("Sincronização finalizada.")
        return

    log_message(f"{len(new_files)} novo(s) arquivo(s) copiado(s). Preparando git add/commit/push...")

    # git add .
    if not run_git_command(["git", "add", "."]):
        log_message("Falha no git add.")
        return

    # Verifica se realmente há mudanças para commit
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=GIT_REPO_PATH,
        capture_output=True,
        text=True,
        encoding="utf-8"
    ).stdout.strip()

    if not status:
        log_message("Sem mudanças para commit após git add.")
        log_message("Sincronização finalizada.")
        return

    # git commit
    msg = "Atualizando logs IHM - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not run_git_command(["git", "commit", "-m", msg]):
        log_message("Falha no git commit.")
        return

    # git push origin main
    if not run_git_command(["git", "push", "origin", "main"]):
        log_message("Falha no git push. Verifique branch, conexão ou credenciais.")
        return

    log_message("Sincronização com GitHub concluída com sucesso.")

if __name__ == "__main__":
    sync_files()
  