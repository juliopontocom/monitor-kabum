import requests
from bs4 import BeautifulSoup
import re
from discord_webhook import DiscordWebhook, DiscordEmbed
import math
import time
from datetime import datetime
import logging

# URLs dos webhooks para diferentes faixas de desconto
WEBHOOKS_DESCONTO = {
    "0_10": "https://discord.com/api/webhooks/1249576687230914612/ELu_efBbVFm7dR7f4XwfF0HAMs3_GDiyCriumZPOtbm_9eXrEmcIczsg4LWgiloPAVrm",
    "10_20": "https://discord.com/api/webhooks/1249219798156443669/tubBeTEIT2QRRSF8uc1NFqpYipjFqn8VDOmuXWiWxmZX14QL9_7BNa35eC3xLnQVD_0t",
    "20_30": "https://discord.com/api/webhooks/1249394506495824054/2w5vNyWe5_HV7I67TmXhcOTbtGWhjmiRefuhhXKGe5m8syvfRfwnHh-saYjGioLkny7j",
    "30_40": "https://discord.com/api/webhooks/1249394553606115519/YJaDFsnz6gy9BvQ3fi--rwbmVC7Fnjnf0IcIb3JZDkOqBii6R3e4l2Af8NCZxtxFQKia",
    "40_50": "https://discord.com/api/webhooks/1249394600045576212/Ob76ME2fqX5BKKgN4RpcNJUGN_NV1OXYITJfqNyOWZ0ir4Y5KnSBcrxOIW9sGpV1IzZ2",
    "50_": "https://discord.com/api/webhooks/1249394638834499594/C65yrKz5gQDZMrt0xAeXPVAYay1Pocm4uvcKSTbTVdTbRwgYik0mWr9N5WI2Izdr1ISo"
}

def configurar_logging(log_filename):
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    open(log_filename, 'w').close()  # Limpa o conteúdo do arquivo no início

def mandar_embed(url_discord, titulo, preco_atual, preco_antigo, link_imagem, footer, url_titulo, tipo_mudanca, cor, diferenca):
    webhook = DiscordWebhook(url=url_discord)
    embed = DiscordEmbed(title=titulo, color=cor)
    embed.set_author(name=tipo_mudanca)
    embed.add_embed_field(name='Preço Atual', value=preco_atual)
    embed.add_embed_field(name='Preço Antigo', value=preco_antigo)
    embed.add_embed_field(name='Diferença', value=f'{diferenca:.2f}%')
    embed.add_embed_field(name='Link', value=f"[AQUI]({url_titulo})")
    embed.set_thumbnail(url=link_imagem)
    embed.set_footer(text=footer)
    webhook.add_embed(embed)
    webhook.execute()
    time.sleep(1.5)

def fazer_requisicao(url, headers, tentativas=3, delay=5):
    for i in range(tentativas):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.warning(f"Tentativa {i + 1} falhou: {e}")
            if i < tentativas - 1:
                time.sleep(delay)
    raise Exception(f"Falha ao acessar {url} após {tentativas} tentativas.")

def extrair_preco(preco_str):
    if not preco_str:
        raise ValueError("Preço não encontrado ou string de preço vazia")
    preco_numerico = re.sub(r'[^\d,]', '', preco_str)
    if not preco_numerico:
        raise ValueError("Preço não encontrado ou string de preço vazia")
    preco_numerico = preco_numerico.replace(',', '.')
    return float(preco_numerico)

def calcular_diferenca(preco_atual, preco_antigo):
    if preco_antigo == 0:
        return 0
    diferenca = ((preco_atual - preco_antigo) / preco_antigo) * 100
    return diferenca

def monitorar(url_principal, dados_antigos, webhook, log_filename):
    configurar_logging(log_filename)
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                              (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    while True:
        try:
            response_principal = fazer_requisicao(url_principal, headers)
        except Exception as e:
            logging.error(f"Erro ao acessar a URL principal {url_principal}: {e}")
            time.sleep(60)
            continue

        sopa_principal = BeautifulSoup(response_principal.content, 'html.parser')
        qtd_itens = sopa_principal.find('div', id='listingCount').get_text().strip()
        index = qtd_itens.find(' ')
        qtd = int(qtd_itens[:index])
        ultima_pagina = math.ceil(qtd / 20)
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

                    try:
                        preco_num_atual = extrair_preco(preco)
                        if preco_antigo:
                            preco_num_antigo = extrair_preco(preco_antigo)
                            if preco_num_atual != preco_num_antigo:
                                tipo_mudanca, cor = determinar_mudanca(preco_num_atual, preco_num_antigo)
                                diferenca = calcular_diferenca(preco_num_atual, preco_num_antigo)
                                mandar_embed(webhook, titulo, preco, preco_antigo, src_value, vendido, link_produto, tipo_mudanca, cor, diferenca)
                                
                                if diferenca < 0:
                                    mandar_webhook_desconto(titulo, preco, preco_antigo, src_value, vendido, link_produto, diferenca)
                                
                                logging.info(f"Produto atualizado: {titulo} - Preço: {preco} (Antigo: {preco_antigo}) - Diferença: {diferenca:.2f}%")
                        elif preco_antigo is None:
                            mandar_embed(webhook, titulo, preco, "N/A", src_value, vendido, link_produto, "Entrou no site", "6D27CF", 0)
                            logging.info(f"Novo produto adicionado: {titulo} - Preço: {preco} - Diferença: 0%")
                        novos_dados[chave] = preco
                    except ValueError as e:
                        logging.error(f"Erro ao processar o preço para o produto {titulo}: {e}")

        dados_antigos.update(novos_dados)
        time.sleep(50)  # Aumentar o tempo de espera entre os ciclos para reduzir a carga

def mandar_webhook_desconto(titulo, preco_atual, preco_antigo, link_imagem, footer, url_titulo, diferenca):
    if -10 <= diferenca < 0:
        url = WEBHOOKS_DESCONTO["0_10"]
    elif -20 <= diferenca < -10:
        url = WEBHOOKS_DESCONTO["10_20"]
    elif -30 <= diferenca < -20:
        url = WEBHOOKS_DESCONTO["20_30"]
    elif -40 <= diferenca < -30:
        url = WEBHOOKS_DESCONTO["30_40"]
    elif -50 <= diferenca < -40:
        url = WEBHOOKS_DESCONTO["40_50"]
    elif diferenca < -50:
        url = WEBHOOKS_DESCONTO["50_"]
    else:
        return

    mandar_embed(url, titulo, preco_atual, preco_antigo, link_imagem, footer, url_titulo, "Diminuiu o preço", "90EE90", diferenca)

def determinar_mudanca(preco, preco_antigo):
    if preco > preco_antigo:
        return "Aumentou o preço", "FF6347"
    elif preco < preco_antigo:
        return "Diminuiu o preço", "90EE90"
    else:
        return "Preço inalterado", "FFFFFF"  # Caso especial para preços iguais
