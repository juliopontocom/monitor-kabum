import requests
from bs4 import BeautifulSoup
import re
from discord_webhook import DiscordWebhook, DiscordEmbed
import math
import time
from datetime import datetime
import json
import logging

# Configuração do logging para registrar em um arquivo logs.txt
log_filename = 'logs.txt'
open(log_filename, 'w').close()  # Limpa o conteúdo do arquivo no início

logging.basicConfig(
    filename=log_filename,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

# Função para carregar URLs e webhooks de um arquivo JSON
def carregar_webhooks(arquivo_json):
    with open(arquivo_json, 'r') as f:
        return json.load(f)

# Carregar o dicionário de URLs e webhooks
webhooks = carregar_webhooks('./webhook.json')
urls = list(webhooks.keys())

dados_antigos = {url: {} for url in urls}

def mandar_embed(url_discord, titulo, preco_atual, preco_antigo, link_imagem, footer, url_titulo, tipo_mudanca, cor):
    webhook = DiscordWebhook(url=url_discord)
    embed = DiscordEmbed(title=titulo, color=cor)
    embed.set_author(name=tipo_mudanca)
    embed.add_embed_field(name='Preço Atual', value=preco_atual)
    embed.add_embed_field(name='Preço Antigo', value=preco_antigo)
    embed.add_embed_field(name='Link', value=f"[AQUI]({url_titulo})")
    embed.set_thumbnail(url=link_imagem)
    embed.set_footer(text=footer)
    webhook.add_embed(embed)
    webhook.execute()

def fazer_requisicao(url, headers, tentativas=3, delay=5):
    for i in range(tentativas):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Levanta um erro para status HTTP ruins
            return response
        except requests.exceptions.RequestException as e:
            logging.warning(f"Tentativa {i + 1} falhou: {e}")
            if i < tentativas - 1:
                time.sleep(delay)
    raise Exception(f"Falha ao acessar {url} após {tentativas} tentativas.")

def extrair_preco(preco_str):
    if not preco_str:
        raise ValueError("Preço não encontrado ou string de preço vazia")
    # Remove 'R$', pontos e vírgulas para converter para float
    preco_numerico = re.sub(r'[^\d,]', '', preco_str)
    if not preco_numerico:
        raise ValueError("Preço não encontrado ou string de preço vazia")
    preco_numerico = preco_numerico.replace(',', '.')
    return float(preco_numerico)

def monitorar(url_principal, dados_antigos):
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                              (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    try:
        response_principal = fazer_requisicao(url_principal, headers)
    except Exception as e:
        logging.error(f"Erro ao acessar a URL principal {url_principal}: {e}")
        return dados_antigos

    sopa_principal = BeautifulSoup(response_principal.content, 'html.parser')
    qtd_itens = sopa_principal.find('div', id='listingCount').get_text().strip()
    index = qtd_itens.find(' ')
    qtd = int(qtd_itens[:index])
    ultima_pagina = math.ceil(qtd/20)
    novos_dados = {}

    for i in range(1, ultima_pagina + 1):
        url_pag = f'{url_principal}?page_number={i}&page_size=20&facet_filters=&sort=most_searched'
        try:
            response_pag = fazer_requisicao(url_pag, headers)
        except Exception as e:
            logging.error(f"Erro ao acessar a página {url_pag}: {e}")
            continue

        sopa_pag = BeautifulSoup(response_pag.content, 'html.parser')
        produtos = sopa_pag.findAll('article', class_=re.compile('productCard'))

        for produto in produtos:
            titulo = produto.find('span', class_=re.compile('nameCard')).get_text().strip()
            imagem = produto.find('img', class_='imageCard')
            src_value = imagem['src'] if imagem else "Imagem não encontrada"
            ancora = produto.find('a', class_='productLink')
            href_value = ancora['href'] if ancora else None
            if href_value:
                link_produto = f'https://kabum.com.br{href_value}'
                try:
                    site_produto = fazer_requisicao(link_produto, headers)
                except Exception as e:
                    logging.error(f"Falha ao acessar o produto: {e}")
                    continue

                sopa_produto = BeautifulSoup(site_produto.content, 'html.parser')
                preco_elemento = sopa_produto.find('h4', class_=re.compile('finalPrice'))
                preco = preco_elemento.get_text().strip() if preco_elemento else None
                
                if not preco:
                    logging.warning(f"Preço não encontrado para o produto: {titulo}")
                    continue

                vendido_elemento = sopa_produto.find('div', class_=re.compile('generalInfo'))
                vendido = vendido_elemento.get_text().strip().split('|')[0] if vendido_elemento else "Informação de venda não encontrada"
                agora = datetime.now()
                hora_formatada = agora.strftime('%H:%M:%S')
                vendido = vendido + f'• {hora_formatada}'
                chave = f"{titulo}|{link_produto}"
                preco_antigo = dados_antigos.get(chave, None)
                url_discord = webhooks[url_principal]  # Pega o webhook apropriado para a URL
                
                try:
                    preco_num_atual = extrair_preco(preco)
                    if preco_antigo:
                        preco_num_antigo = extrair_preco(preco_antigo)
                        if preco_num_atual != preco_num_antigo:
                            tipo_mudanca, cor = determinar_mudanca(preco_num_atual, preco_num_antigo)
                            mandar_embed(url_discord, titulo, preco, preco_antigo, src_value, vendido, link_produto, tipo_mudanca, cor)
                            logging.info(f"Produto atualizado: {titulo} - Preço: {preco} (Antigo: {preco_antigo})")
                            time.sleep(1)
                    elif preco_antigo is None:
                        mandar_embed(url_discord, titulo, preco, "N/A", src_value, vendido, link_produto, "Entrou no site", "4169E1")
                        logging.info(f"Novo produto adicionado: {titulo} - Preço: {preco}")
                        time.sleep(1)
                    novos_dados[chave] = preco
                except ValueError as e:
                    logging.error(f"Erro ao processar o preço para o produto {titulo}: {e}")

    dados_antigos[url_principal] = novos_dados
    return novos_dados

def determinar_mudanca(preco, preco_antigo):
    if preco > preco_antigo:
        return "Aumentou o preço", "FF6347"
    elif preco < preco_antigo:
        return "Diminuiu o preço", "90EE90"
    else:
        return "Preço inalterado", "FFFFFF"  # Caso especial para preços iguais

while True:
    for url in urls:
        try:
            dados_antigos[url] = monitorar(url, dados_antigos[url])  # Passa e atualiza os dados antigos corretamente
        except Exception as e:
            logging.error(f"Erro ao monitorar a URL {url}: {e}")
        time.sleep(15)  # Aumentar o tempo de espera entre os ciclos para reduzir a carga
