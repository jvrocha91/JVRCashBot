from strategies.strategy import TradingStrategy
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os
import logging
import time  
import sys

# Configurar logging para exibir informações gerais
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Configurar logging para registrar operações em um arquivo separado
operacoes_logger = logging.getLogger("operacoes")
operacoes_handler = logging.FileHandler("operacoes.log", mode="a", encoding="utf-8")
operacoes_formatter = logging.Formatter('%(asctime)s - %(message)s')
operacoes_handler.setFormatter(operacoes_formatter)
operacoes_logger.addHandler(operacoes_handler)
operacoes_logger.setLevel(logging.INFO)

# Carregar as chaves da Binance do arquivo .env
load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# Conectar à Binance API
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
MODO_SIMULADO = False  # Se True, simula as ordens sem enviá-las para a Binance

# Definições globais
CRIPTO_ATUAL = None
VALOR_OPERACAO = None
POSICAO_ABERTA = None  # Pode ser 'long', 'short' ou None
PRECO_ENTRADA = None  # Preço de entrada da posição aberta
contador_operacoes = 0  # Contador de operações realizadas no dia

# Parâmetros de gerenciamento de riscos
STOP_LOSS = 0.05  # 5% de perda máxima permitida
TAKE_PROFIT = 0.05  # 5% de lucro desejado
LIMITE_OPERACOES = 10  # Limite de operações por dia

def obter_saldo():
    """
    Obtém e exibe o saldo disponível na conta.
    """
    try:
        saldo = client.get_account()
        logging.info("\n💰 SALDO DISPONÍVEL:")
        ativos = []
        for asset in saldo["balances"]:
            quantidade = float(asset["free"])
            if quantidade > 1:
                ativos.append(f"{asset['asset']}: {quantidade:.6f}")
        
        if ativos:
            logging.info("\n".join(ativos))
        else:
            logging.info("Nenhum saldo disponível.")
    except Exception as e:
        logging.error(f"Erro ao obter saldo da conta: {e}")

def obter_dados_historicos(limite=100, cripto_atual=None):
    """
    Obtém dados históricos (candlesticks) e os converte para um DataFrame Pandas.
    Retorna o DataFrame e o preço de fechamento mais recente.
    """
    try:
        if cripto_atual is None:
            cripto_atual = CRIPTO_ATUAL
        if cripto_atual is None:
            raise ValueError("CRIPTO_ATUAL não foi definido! Execute configurar_operacao() primeiro.")

        candles = client.get_klines(symbol=cripto_atual, interval="5m", limit=limite)

        # Criar DataFrame com os dados
        df = pd.DataFrame(candles, columns=[
            "tempo", "abertura", "máxima", "mínima", "fechamento", "volume",
            "tempo_fechamento", "volume_tickers", "trades", "taker_base", "taker_quote", "ignore"
        ])

        # Convertendo timestamps para datas legíveis
        df["tempo"] = pd.to_datetime(df["tempo"], unit="ms")

        # Convertendo colunas numéricas
        df[["abertura", "máxima", "mínima", "fechamento", "volume"]] = df[
            ["abertura", "máxima", "mínima", "fechamento", "volume"]
        ].astype(float)

        # Calcular EMA 100
        df["EMA_100"] = df["fechamento"].ewm(span=100, adjust=False).mean()

        # Calcular RSI
        df["RSI"] = calcular_rsi(df["fechamento"], window=14)

        # Obter preço de fechamento mais recente
        preco_atual = df["fechamento"].iloc[-1]

        logging.info(f"\n📊 Dados históricos carregados ({cripto_atual}, 5m)")
        logging.info(f"💰 Preço atual de {cripto_atual}: ${preco_atual:.2f}")

        return df, preco_atual
    except Exception as e:
        logging.error(f"Erro ao buscar dados do mercado: {e}")
        return None, None

def calcular_rsi(serie, window=14):
    """
    Calcula o RSI (Índice de Força Relativa).
    """
    delta = serie.diff(1)
    ganho = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    perda = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = ganho / perda
    rsi = 100 - (100 / (1 + rs))
    return rsi

def configurar_operacao():
    """
    Permite que o usuário escolha a criptomoeda e o valor que deseja negociar.
    """
    global CRIPTO_ATUAL, VALOR_OPERACAO

    while True:
        print("\n📌 SELECIONE A CRIPTOMOEDA PARA OPERAR:")
        print("1 - BTCUSDT (Bitcoin)")
        print("2 - ETHUSDT (Ethereum)")
        print("3 - SOLUSDT (Solana)")
        print("4 - OUTRA (Digite manualmente)")

        escolha = input("\nDigite o número da opção desejada: ")

        if escolha == "1":
            CRIPTO_ATUAL = "BTCUSDT"
        elif escolha == "2":
            CRIPTO_ATUAL = "ETHUSDT"
        elif escolha == "3":
            CRIPTO_ATUAL = "SOLUSDT"
        elif escolha == "4":
            CRIPTO_ATUAL = input("Digite o par de negociação desejado (ex: ADAUSDT, XRPUSDT): ").upper()
        else:
            print("❌ Opção inválida! Tente novamente.")
            continue  

        while True:
            try:
                VALOR_OPERACAO = float(input(f"\n💰 Digite o valor que deseja investir em cada operação ({CRIPTO_ATUAL}): "))
                if VALOR_OPERACAO > 0:
                    break
                else:
                    print("❌ O valor deve ser maior que 0.")
            except ValueError:
                print("❌ Entrada inválida. Digite um número válido.")

        logging.info(f"\n✅ Configuração definida: {CRIPTO_ATUAL} - ${VALOR_OPERACAO:.2f} por operação.")
        return

def verificar_stop_loss(preco_atual):
    """
    Verifica se o preço atual atingiu o stop loss.
    """
    global PRECO_ENTRADA, POSICAO_ABERTA

    if POSICAO_ABERTA == "long" and preco_atual <= PRECO_ENTRADA * (1 - STOP_LOSS):
        return True
    elif POSICAO_ABERTA == "short" and preco_atual >= PRECO_ENTRADA * (1 + STOP_LOSS):
        return True
    return False

def verificar_take_profit(preco_atual):
    """
    Verifica se o preço atual atingiu o take profit.
    """
    global PRECO_ENTRADA, POSICAO_ABERTA

    if POSICAO_ABERTA == "long" and preco_atual >= PRECO_ENTRADA * (1 + TAKE_PROFIT):
        return True
    elif POSICAO_ABERTA == "short" and preco_atual <= PRECO_ENTRADA * (1 - TAKE_PROFIT):
        return True
    return False

def executar_estrategia():
    """
    Executa a estratégia de trading em um loop contínuo.
    """
    global POSICAO_ABERTA, PRECO_ENTRADA, contador_operacoes

    obter_saldo()
    configurar_operacao()

    logging.info("\n🚀 Bot iniciado. Monitorando o mercado...")

    try:
        while True:  # Loop contínuo
            df, preco = obter_dados_historicos(100)

            if df is not None:
                strategy = TradingStrategy(df, PRECO_ENTRADA)

                # 🔹 Início do bloco de informações
                logging.info("\n====================")
                logging.info("📊 Indicadores Atuais:")
                logging.info(f"RSI Atual: {df['RSI'].iloc[-1]:.2f}")

                logging.info("\n⚡ Verificação dos Critérios:")

                # Obter valores da EMA 100 e preço atual
                ema_100_atual = df["EMA_100"].iloc[-1]
                preco_atual = df["fechamento"].iloc[-1]

                # Determinar a tendência com base na EMA 100
                if preco_atual > ema_100_atual:
                    tendencia = "Tendência de ALTA (Preço acima da EMA 100)"
                else:
                    tendencia = "Tendência de BAIXA (Preço abaixo da EMA 100)"

                # Exibir informações da EMA 100 e tendência no terminal
                logging.info(f"📈 EMA 100 Atual: {ema_100_atual:.2f}")
                logging.info(f"📊 {tendencia}")

                # Verificar critérios de compra, venda, short e recompra
                compra_mm = strategy.verificar_compra()
                venda_mm = strategy.verificar_venda()
                short_mm = strategy.verificar_short()
                recompra_mm = strategy.verificar_recompra()

                rsi_atual = df["RSI"].iloc[-1]

                # Exibir os critérios e resultados no terminal
                logging.info(f" {'✅' if compra_mm else '❌'} Critério de COMPRA {'atingido' if compra_mm else 'NÃO atingido'}:")
                logging.info(f"    - Preço atual acima da EMA 100: {preco_atual > ema_100_atual}")
                logging.info(f"    - Preço atual 0,3% acima do menor preço: {strategy.lowest_price:.2f}")
                logging.info(f"    - RSI < 35: {rsi_atual:.2f}")

                logging.info(f" {'✅' if venda_mm else '❌'} Critério de VENDA {'atingido' if venda_mm else 'NÃO atingido'}:")
                logging.info(f"    - Preço atual acima da EMA 100: {preco_atual > ema_100_atual}")
                logging.info(f"    - Lucro mínimo de 0,05% atingido: {strategy.preco_entrada:.2f}" if strategy.preco_entrada is not None else "    - Lucro mínimo de 0,05% atingido: N/A")
                logging.info(f"    - RSI > 70: {rsi_atual:.2f}")

                logging.info(f" {'✅' if short_mm else '❌'} Critério de VENDA SHORT {'atingido' if short_mm else 'NÃO atingido'}:")
                logging.info(f"    - Preço atual abaixo da EMA 100: {preco_atual < ema_100_atual}")
                logging.info(f"    - Preço atual 0,3% abaixo do maior preço: {strategy.highest_price:.2f}")
                logging.info(f"    - RSI > 70: {rsi_atual:.2f}")

                logging.info(f" {'✅' if recompra_mm else '❌'} Critério de RECOMPRA SHORT {'atingido' if recompra_mm else 'NÃO atingido'}:")
                logging.info(f"    - Preço atual abaixo da EMA 100: {preco_atual < ema_100_atual}")
                logging.info(f"    - Lucro mínimo de 0,05% atingido: {strategy.preco_entrada:.2f}" if strategy.preco_entrada is not None else "    - Lucro mínimo de 0,05% atingido: N/A")
                logging.info(f"    - RSI < 35: {rsi_atual:.2f}")

                # Verificar stop loss e take profit
                if POSICAO_ABERTA and verificar_stop_loss(preco):
                    logging.info("🚨 Stop Loss atingido!")
                    executar_ordem("sell" if POSICAO_ABERTA == "long" else "buy", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None
                    contador_operacoes += 1

                elif POSICAO_ABERTA and verificar_take_profit(preco):
                    logging.info("🎉 Take Profit atingido!")
                    executar_ordem("sell" if POSICAO_ABERTA == "long" else "buy", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None
                    contador_operacoes += 1

                # 📌 Modo Long: Compra só se não houver posição aberta
                elif compra_mm and POSICAO_ABERTA is None and contador_operacoes < LIMITE_OPERACOES:
                    logging.info("✅ Sinal de COMPRA confirmado!")
                    executar_ordem("buy", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = "long"
                    PRECO_ENTRADA = preco
                    contador_operacoes += 1

                # 📌 Modo Long: Só vende se já tiver comprado antes
                elif venda_mm and POSICAO_ABERTA == "long":
                    logging.info("🚨 Sinal de VENDA confirmado!")
                    executar_ordem("sell", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None  # Fecha a posição
                    contador_operacoes += 1

                # 📌 Modo Short: Vende apenas se não houver posição aberta
                elif short_mm and POSICAO_ABERTA is None and contador_operacoes < LIMITE_OPERACOES:
                    logging.info("🚨 Sinal de VENDA SHORT confirmado!")
                    executar_ordem("short_sell", VALOR_OPERACAO / preco, preco_atual=preco)
                    POSICAO_ABERTA = "short"
                    PRECO_ENTRADA = preco
                    contador_operacoes += 1

                # 📌 Modo Short: Só recompra se já tiver vendido antes
                elif recompra_mm and POSICAO_ABERTA == "short":
                    logging.info("✅ Sinal de RECOMPRA SHORT confirmado!")
                    executar_ordem("short_cover", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None  # Fecha a posição
                    contador_operacoes += 1

                else:
                    logging.info("\n⚠️ Nenhum sinal de operação encontrado no momento.")

                # 🔹 Final do bloco de informações
                logging.info("====================\n")

            # ⏳ Aguarda 60 segundos com contagem regressiva
            for i in range(60, 0, -1):  
                sys.stdout.write(f"\r⏳ Próxima verificação em {i} segundos...")  
                sys.stdout.flush()
                time.sleep(1)

            print("\n")  # Pula linha ao final da contagem regressiva

    except KeyboardInterrupt:
        logging.info("\n🛑 Bot interrompido manualmente. Finalizando execução...")

def executar_ordem(tipo_ordem, quantidade, preco_atual=None):
    """
    Executa uma ordem de compra, venda, venda short ou recompra short na Binance ou simula a operação.
    
    :param tipo_ordem: 'buy', 'sell', 'short_sell', ou 'short_cover'
    :param quantidade: Quantidade de moeda a ser comprada ou vendida
    :param preco_atual: Preço atual da criptomoeda (necessário para venda short)
    """
    try:
        if tipo_ordem not in ["buy", "sell", "short_sell", "short_cover"]:
            raise ValueError("Tipo de ordem inválido. Use 'buy', 'sell', 'short_sell' ou 'short_cover'.")

        if MODO_SIMULADO:
            logging.info(f"🟡 [SIMULADO] Ordem de {tipo_ordem.upper()} enviada para {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")
            operacoes_logger.info(f"[SIMULADO] {tipo_ordem.upper()} - {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")
            return {"status": "simulado", "tipo": tipo_ordem, "quantidade": quantidade}

        # Verificação de saldo diferenciada para cada tipo de operação
        if tipo_ordem == "buy":
            # Verificar saldo em USDT para compra
            saldo = client.get_asset_balance(asset="USDT")
            saldo_disponivel = float(saldo["free"]) if saldo else 0
            valor_necessario = VALOR_OPERACAO

            if saldo_disponivel < valor_necessario:
                logging.error(f"❌ Saldo insuficiente! Disponível: {saldo_disponivel:.2f} USDT, Necessário: {valor_necessario:.2f} USDT")
                return None
            logging.info(f"📈 Enviando ordem de COMPRA: {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")

        elif tipo_ordem == "sell":
            # Verificar saldo do ativo base (ex: BTC) para venda
            ativo = CRIPTO_ATUAL.replace("USDT", "")
            saldo = client.get_asset_balance(asset=ativo)
            saldo_disponivel = float(saldo["free"]) if saldo else 0

            if saldo_disponivel < quantidade:
                logging.error(f"❌ Saldo insuficiente! Disponível: {saldo_disponivel:.6f} {ativo}, Necessário: {quantidade:.6f} {ativo}")
                return None
            logging.info(f"📉 Enviando ordem de VENDA: {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")

        elif tipo_ordem == "short_sell":
            # Venda short: usar o saldo em USDT e converter para a quantidade de criptomoeda
            if preco_atual is None:
                raise ValueError("Preço atual é necessário para realizar uma venda short.")

            saldo = client.get_asset_balance(asset="USDT")
            saldo_disponivel = float(saldo["free"]) if saldo else 0
            valor_necessario = VALOR_OPERACAO

            if saldo_disponivel < valor_necessario:
                logging.error(f"❌ Saldo insuficiente para VENDA SHORT! Disponível: {saldo_disponivel:.2f} USDT, Necessário: {valor_necessario:.2f} USDT")
                return None

            quantidade = VALOR_OPERACAO / preco_atual  # Converter USDT para quantidade de criptomoeda
            logging.info(f"📉 Enviando ordem de VENDA SHORT: {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")

        elif tipo_ordem == "short_cover":
            # Recompra short: verificar saldo do ativo base (ex: BTC)
            ativo = CRIPTO_ATUAL.replace("USDT", "")
            saldo = client.get_asset_balance(asset=ativo)
            saldo_disponivel = float(saldo["free"]) if saldo else 0

            if saldo_disponivel < quantidade:
                logging.error(f"❌ Saldo insuficiente para RECOMPRA SHORT! Disponível: {saldo_disponivel:.6f} {ativo}, Necessário: {quantidade:.6f} {ativo}")
                return None
            logging.info(f"📈 Enviando ordem de RECOMPRA SHORT: {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")

        # Executa a ordem na Binance
        ordem = client.order_market(symbol=CRIPTO_ATUAL, side=tipo_ordem.upper(), quantity=quantidade)

        # Confirma execução da ordem
        logging.info(f"✅ Ordem de {tipo_ordem.upper()} executada com sucesso!")
        logging.info(f"📌 Detalhes da ordem: {ordem}")

        # Registrar a operação no arquivo de log
        preco_executado = ordem["fills"][0]["price"] if "fills" in ordem and ordem["fills"] else "N/A"
        operacoes_logger.info(f"{tipo_ordem.upper()} - {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f} - Preço: {preco_executado}")

        return ordem
    except Exception as e:
        logging.error(f"❌ Erro ao executar ordem: {e}")
        return None


# Executar a lógica principal
if __name__ == "__main__":
    executar_estrategia()