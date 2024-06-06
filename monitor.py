import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from discord_webhook import DiscordWebhook, DiscordEmbed
import math
import time
from datetime import datetime

url = 'https://www.kabum.com.br/computadores/notebooks/macbook'
# metodo que envia mensagem no discord
def mandar_mensagem(url_discord, mensagem):
    webhook = DiscordWebhook(url=url_discord, content=mensagem)
    webhook.execute()


# metodo que envia embed no discord
def mandar_embed(url_discord, titulo, preco_atual, preco_antigo, link_imagem, footer, url_titulo):
    webhook = DiscordWebhook(url=url_discord)
    embed = DiscordEmbed(title=titulo, color='74eb34')
    embed.add_embed_field(name='Preço Atual', value=preco_atual)
    embed.add_embed_field(name='Preço Antigo', value=preco_antigo)
    embed.add_embed_field(name='Link', value="[AQUI](%s)" % url_titulo)
    embed.set_thumbnail(url=link_imagem)
    embed.set_footer(text=footer)
    webhook.add_embed(embed)
    response = webhook.execute()
    return response



# metodo que monitora os produtos
def monitorar(url_principal):

    products = {}

    headers = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                            (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"}
    response_principal = requests.get(url_principal, headers=headers)
    sopa_principal = BeautifulSoup(response_principal.content, 'html.parser')
    qtd_itens = sopa_principal.find('div', id='listingCount').get_text().strip()
    index = qtd_itens.find(' ')
    qtd = qtd_itens[:index]
    ultima_pagina = math.ceil(int(qtd)/20)

    for i in range(1, ultima_pagina+1):
        url_pag = f'{url_principal}?page_number={i}&page_size=20&facet_filters=&sort=most_searched'
        response_pag = requests.get(url_pag, headers=headers)
        sopa_pag = BeautifulSoup(response_pag.content, 'html.parser')
        produtos = sopa_pag.findAll('article', class_=re.compile('productCard'))                    #pega todos produtos

        for produto in produtos:

            #pagina dos 20 produtos
            titulo = produto.find('span', class_=re.compile('nameCard')).get_text().strip()     #pega o titulo
            imagem = produto.find('img', class_=re.compile('imageCard'))                        
            src_value = imagem['src'] if imagem else "Imagem não encontrada"                    #pega o link da imagem
            ancora = produto.find('a', class_='productLink')
            href_value = ancora['href'] if ancora else "Link não encontrado"
            link_produto = f'https://kabum.com.br{href_value}'                                  #pega o link do produto

            #pagina do produto especifico
            site_produto = requests.get(link_produto, headers=headers)                          
            sopa_produto = BeautifulSoup(site_produto.content, 'html.parser')
            preco_elemento = sopa_produto.find('h4', class_=re.compile('finalPrice'))
            preco = preco_elemento.get_text().strip() if preco_elemento else "Preço não encontrado" #pega o preco
            vendido_elemento = sopa_produto.find('div', class_=re.compile('generalInfo'))
            vendido = vendido_elemento.get_text().strip().split('|')[0] if vendido_elemento else "Informação de venda não encontrada" #pega o vendedor
            agora = datetime.now()
            hora_formatada = agora.strftime('%H:%M:%S') #pega a hora atual
            vendido = vendido + f'• {hora_formatada}'
            if __name__ == "__main__":
                url_discord = "https://discord.com/api/webhooks/1245386253470404651/npFRDD-qB26_YhLlrHJVSVSa7_9aoDmgs0Eoc0o-bE5PPv3rtYECAu9w5w3XN_F-Oo82"
                #send_message(url_discord, mensagem)
                mandar_embed(url_discord,titulo,preco,0,src_value,vendido,link_produto)


monitorar(url)