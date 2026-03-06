import os
import shutil
import subprocess
import datetime

# CONFIGURAÇÕES
# Pasta onde os arquivos CSV da IHM chegam (via WinSCP/FileZilla)
SOURCE_DIR = r"C:\FROMTHERM_IHM_UPLOADS"

# Pasta dentro do repositório LOCAL onde vamos guardar os CSVs
DEST_DIR = r"C:\fromtherm_ihm_logs_repo\ihm_logs"

# Raiz do repositório Git LOCAL
GIT_REPO_PATH = r"C:\fromtherm_ihm_logs_repo"

# Arquivo que registra quais arquivos já foram processados
PROCESSED_FILES_LOG = os.path.join(GIT_REPO_PATH, "processed_files.log")


def log_message(message: str):
    """Registra mensagens na tela e em um arquivo de log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(os.path.join(GIT_REPO_PATH, "sync_log.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_processed_files():
    """Lê o arquivo de controle e devolve um conjunto com os caminhos já processados."""
    if not os.path.exists(PROCESSED_FILES_LOG):
        return set()
    with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())


def add_processed_file(path: str):
    """Registra um novo arquivo como já processado."""
    with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as f:
        f.write(path + "\n")


def run_git_command(args):
    """Executa um comando git dentro do repositório e registra logs."""
    try:
        result = subprocess.run(
            args,
            cwd=GIT_REPO_PATH,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        if result.stdout.strip():
            log_message(f"Git stdout: {result.stdout.strip()}")
        if result.stderr.strip():
            log_message(f"Git stderr: {result.stderr.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"ERRO git ({' '.join(args)}): {e}")
        if e.stdout:
            log_message(f"stdout: {e.stdout.strip()}")
        if e.stderr:
            log_message(f"stderr: {e.stderr.strip()}")
        return False


def sync_files():
    """Copia novos CSVs, faz commit e envia para o GitHub."""
    log_message("Iniciando sincronização...")
    processed = get_processed_files()
    new_files = []

    # Verifica se a pasta de origem existe
    if not os.path.exists(SOURCE_DIR):
        log_message(f"Pasta de origem não encontrada: {SOURCE_DIR}")
        log_message("Sincronização finalizada com erro de configuração.")
        return

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