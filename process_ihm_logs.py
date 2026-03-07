import os
import shutil
import subprocess
import datetime

# -------------------------------------------------
# CONFIGURAÇÕES
# -------------------------------------------------

# Pasta onde ficam os CSVs já enviados pelo outro repositório (fromtherm_ihm_logs_repo)
LOGS_REPO_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm_ihm_logs_repo\ihm_logs"

# Pasta deste repositório (fromtherm-dados)
DADOS_REPO_DIR = r"C:\Users\Bruno\OneDrive\Documentos\FROMTHERM-IHM-ENVIO-AUTOMATICO\fromtherm-dados"

# Pasta dentro do fromtherm-dados onde vamos guardar uma cópia dos CSVs para processamento
DADOS_BRUTOS_DIR = os.path.join(DADOS_REPO_DIR, "dados_brutos")

# Pasta que o dashboard Streamlit usa (para onde o CSV será copiado também)
DADOS_DASHBOARD_DIR = os.path.join(DADOS_REPO_DIR, "dados")

# Arquivo de controle para saber quais CSVs já foram processados
PROCESSED_CSV_LOG = os.path.join(DADOS_REPO_DIR, "processed_csv.log")

# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------

def log_message(message: str):
    """Registra mensagens na tela e em um arquivo de log dentro do fromtherm-dados."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {message}"
    print(line)
    log_path = os.path.join(DADOS_REPO_DIR, "process_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def get_processed_csvs() -> set:
    """Lê o arquivo de controle e devolve um conjunto com os CSVs já processados."""
    if not os.path.exists(PROCESSED_CSV_LOG):
        return set()
    with open(PROCESSED_CSV_LOG, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def add_processed_csv(path: str):
    """Registra um novo CSV como já processado."""
    with open(PROCESSED_CSV_LOG, "a", encoding="utf-8") as f:
        f.write(path + "\n")


def run_git_command(args: list) -> bool:
    """Executa um comando git dentro do repositório fromtherm-dados e registra logs."""
    try:
        result = subprocess.run(
            args,
            cwd=DADOS_REPO_DIR,
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
        log_message(f"Erro Git: {e}")
        if e.stdout:
            log_message(f"Git stdout (erro): {e.stdout.strip()}")
        if e.stderr:
            log_message(f"Git stderr (erro): {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        log_message("Erro: Comando Git não encontrado. Certifique-se de que o Git está instalado e no PATH.")
        return False


def process_ihm_logs():
    """
    Copia CSVs novos do repositório de logs (fromtherm_ihm_logs_repo\ihm_logs)
    para dados_brutos e para a pasta 'dados' do dashboard, e faz push para o GitHub.
    """
    log_message("Iniciando processamento dos logs da IHM...")

    if not os.path.exists(LOGS_REPO_DIR):
        log_message(f"Erro: Pasta de logs de origem não encontrada: {LOGS_REPO_DIR}")
        return

    os.makedirs(DADOS_BRUTOS_DIR, exist_ok=True)
    os.makedirs(DADOS_DASHBOARD_DIR, exist_ok=True) # Garante que a pasta do dashboard existe

    processed = get_processed_csvs()
    novos_csvs = []

    for root, _, files in os.walk(LOGS_REPO_DIR):
        for file in files:
            if not file.lower().endswith(".csv"):
                continue

            source_path = os.path.join(root, file)

            if source_path in processed:
                continue

            # Mantém estrutura de subpastas sob a pasta LOGS_REPO_DIR
            relative_path = os.path.relpath(source_path, LOGS_REPO_DIR)
            dest_path_brutos = os.path.join(DADOS_BRUTOS_DIR, relative_path)

            # Garante subpastas em dados_brutos
            os.makedirs(os.path.dirname(dest_path_brutos), exist_ok=True)

            try:
                # Copia para a pasta de dados brutos
                shutil.copy2(source_path, dest_path_brutos)
                log_message(f"Copiado para dados_brutos: {source_path} -> {dest_path_brutos}")

                # Copia para a pasta 'dados' do dashboard (sem subpastas, direto na raiz de 'dados')
                dest_path_dashboard = os.path.join(DADOS_DASHBOARD_DIR, os.path.basename(source_path))
                shutil.copy2(source_path, dest_path_dashboard)
                log_message(f"Copiado para dados (dashboard): {source_path} -> {dest_path_dashboard}")

                novos_csvs.append(source_path)
                add_processed_csv(source_path)
            except Exception as e:
                log_message(f"Erro ao copiar {source_path} para dados_brutos ou dados do dashboard: {e}")

    if not novos_csvs:
        log_message("Nenhum novo CSV encontrado para processamento.")
        log_message("Processamento finalizado.")
        return

    log_message(f"{len(novos_csvs)} novo(s) CSV(s) copiado(s) para dados_brutos e dados do dashboard. Preparando git add/commit/push...")

    # Aqui você poderia adicionar a lógica de processamento (pandas, etc.)
    # Exemplo (comentado):
    # for csv_path in [os.path.join(DADOS_BRUTOS_DIR, os.path.relpath(p, LOGS_REPO_DIR)) for p in novos_csvs]:
    #     try:
    #         # fazer análise com pandas, gerar gráficos, etc.
    #         pass
    #     except Exception as e:
    #         log_message(f"Erro ao processar {csv_path}: {e}")

    # git add .
    if not run_git_command(["git", "add", "."]):
        log_message("Falha no git add.")
        return

    # Verifica se há mudanças a serem commitadas
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=DADOS_REPO_DIR,
        capture_output=True,
        text=True,
        encoding="utf-8"
    ).stdout.strip()

    if not status:
        log_message("Sem mudanças para commit após git add.")
        log_message("Processamento finalizado.")
        return

    # git commit
    commit_msg = "Atualizando dados brutos e dashboard IHM - " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if not run_git_command(["git", "commit", "-m", commit_msg]):
        log_message("Falha no git commit.")
        return

    # git push
    if not run_git_command(["git", "push", "origin", "main"]):
        log_message("Falha no git push. Verifique branch, conexão ou credenciais.")
        return

    log_message("Processamento concluído e dados enviados ao GitHub com sucesso.")

# -------------------------------------------------
# EXECUÇÃO
# -------------------------------------------------

if __name__ == "__main__":
    process_ihm_logs()