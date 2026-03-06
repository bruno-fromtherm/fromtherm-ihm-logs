import os
import shutil
import subprocess
import datetime

# CONFIGURAÇÕES
SOURCE_DIR = r"C:\FROMTHERM_IHM_UPLOADS"        # pasta onde o FileZilla grava
DEST_DIR   = r"C:\fromtherm_ihm_logs_repo\ihm_logs"   # pasta dentro DO NOVO REPO
GIT_REPO_PATH = r"C:\fromtherm_ihm_logs_repo"         # raiz do NOVO repositório
PROCESSED_FILES_LOG = os.path.join(GIT_REPO_PATH, "processed_files.log")


def log_message(message: str):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    with open(os.path.join(GIT_REPO_PATH, "sync_log.txt"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_processed_files():
    if not os.path.exists(PROCESSED_FILES_LOG):
        return set()
    with open(PROCESSED_FILES_LOG, "r", encoding="utf-8") as f:
        return set(f.read().splitlines())


def add_processed_file(path: str):
    with open(PROCESSED_FILES_LOG, "a", encoding="utf-8") as f:
        f.write(path + "\n")


def run_git_command(args):
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
    log_message("Iniciando sincronização...")
    processed = get_processed_files()
    new_files = []
# varre a pasta de origem
for root, _, files in os.walk(SOURCE_DIR):
    for file in files:
        if not file.lower().endswith(".csv"):
            continue
    source_path = os.path.join(root, file)
    if source_path in processed:
        continue

    relative = os.path.relpath(source_path, SOURCE_DIR)
    dest_path = os.path.join(DEST_DIR, relative)

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        shutil.copy2(source_path, dest_path)
        log_message(f"Copiado: {source_path} -&amp;gt; {dest_path}")
        new_files.append(source_path)
        add_processed_file(source_path)
    except Exception as e:
        log_message(f"Erro ao copiar {source_path}: {e}")
if not new_files:
    log_message("Nenhum novo arquivo CSV encontrado.")
    log_message("Sincronização finalizada.")
    return

log_message(f"{len(new_files)} novo(s) arquivo(s) copiado(s). Preparando git add/commit/push...")

if not run_git_command(["git", "add", "."]):
    log_message("Falha no git add.")
    return

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

msg = "Atualizando logs IHM - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
if not run_git_command(["git", "commit", "-m", msg]):
    log_message("Falha no git commit.")
    return

# ATENÇÃO: branch 'main'. Se o repo novo criar 'master', trocamos depois.
if not run_git_command(["git", "push", "origin", "main"]):
    log_message("Falha no git push. Verifique branch, conexão ou credenciais.")
    return

log_message("Sincronização com GitHub concluída com sucesso.")
if __name__ == "__main__":
    sync_files()