import requests
from bs4 import BeautifulSoup
import re
from discord_webhook import DiscordWebhook, DiscordEmbed
import math
import time
from datetime import datetime

urls = [
    "https://www.kabum.com.br/audio/dj/controladora",
    "https://www.kabum.com.br/celular-smartphone/wearables/kabum-smart"
]

url_discord = "https://discord.com/api/webhooks/1245386253470404651/npFRDD-qB26_YhLlrHJVSVSa7_9aoDmgs0Eoc0o-bE5PPv3rtYECAu9w5w3XN_F-Oo82"
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

def monitorar(url_principal, dados_antigos):
    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                              (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    response_principal = requests.get(url_principal, headers=headers)
    sopa_principal = BeautifulSoup(response_principal.content, 'html.parser')
    qtd_itens = sopa_principal.find('div', id='listingCount').get_text().strip()
    index = qtd_itens.find(' ')
    qtd = int(qtd_itens[:index])
    ultima_pagina = math.ceil(qtd/20)
    novos_dados = {}

    for i in range(1, ultima_pagina + 1):
        url_pag = f'{url_principal}?page_number={i}&page_size=20&facet_filters=&sort=most_searched'
        response_pag = requests.get(url_pag, headers=headers)
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
                site_produto = requests.get(link_produto, headers=headers)
                sopa_produto = BeautifulSoup(site_produto.content, 'html.parser')
                preco_elemento = sopa_produto.find('h4', class_=re.compile('finalPrice'))
                preco = preco_elemento.get_text().strip() if preco_elemento else "Preço não encontrado"
                vendido_elemento = sopa_produto.find('div', class_=re.compile('generalInfo'))
                vendido = vendido_elemento.get_text().strip().split('|')[0] if vendido_elemento else "Informação de venda não encontrada" #pega o vendedor
                agora = datetime.now()
                hora_formatada = agora.strftime('%H:%M:%S') #pega a hora atual
                vendido = vendido + f'• {hora_formatada}'
                chave = f"{titulo}|{link_produto}"
                preco_antigo = dados_antigos.get(chave, None)
                if preco_antigo and preco != preco_antigo:
                    tipo_mudanca, cor = determinar_mudanca(preco, preco_antigo)
                    mandar_embed(url_discord, titulo, preco, preco_antigo, src_value, vendido, link_produto, tipo_mudanca, cor)
                    time.sleep(1) 
                elif preco_antigo is None:
                    mandar_embed(url_discord, titulo, preco, "N/A", src_value, vendido, link_produto, "Entrou no site", "4169E1")
                    time.sleep(1)
                novos_dados[chave] = preco
    dados_antigos[url_principal] = novos_dados
    return novos_dados

def determinar_mudanca(preco, preco_antigo):
    if preco > preco_antigo:
        return "Aumentou o preço", "FF6347"
    elif preco < preco_antigo:
        return "Diminuiu o preço", "90EE90"

while True:
    for url in urls:
        dados_antigos[url] = monitorar(url, dados_antigos[url])  # Passa e atualiza os dados antigos corretamente
        time.sleep(10) 