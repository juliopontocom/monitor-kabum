import threading
import json
from monitores import kabum

# Função para carregar URLs e webhooks de um arquivo JSON
def carregar_webhooks(arquivo_json):
    with open(arquivo_json, 'r') as f:
        return json.load(f)

# Carregar os webhooks específicos da Kabum
webhooks = carregar_webhooks('config/kabum.json')

# Função para iniciar o monitoramento
def iniciar_monitoramento(func, url, webhook, log_filename):
    dados_antigos = {}
    func(url, dados_antigos, webhook, log_filename)

# Criação e inicialização dos threads
threads = []
log_filename = 'logs/kabum.txt'
for url, webhook in webhooks.items():
    t = threading.Thread(target=iniciar_monitoramento, args=(kabum.monitorar, url, webhook, log_filename))
    t.start()
    threads.append(t)

# Aguarda a conclusão de todos os threads
for t in threads:
    t.join()
