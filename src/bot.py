from strategies.strategy import TradingStrategy
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os
import logging
import time  
import sys

# Configurar logging sem timestamp e sem nível de log e sem nível de log
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Carregar as chaves da Binance do arquivo .env
load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# Conectar à Binance API
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)
MODO_SIMULADO = True  # Se True, simula as ordens sem enviá-las para a Binance


# Definições globais
CRIPTO_ATUAL = None
VALOR_OPERACAO = None
POSICAO_ABERTA = None  # Pode ser 'long', 'short' ou None


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

        # Obter preço de fechamento mais recente
        preco_atual = df["fechamento"].iloc[-1]

        logging.info(f"\n📊 Dados históricos carregados ({cripto_atual}, 5m)")
        logging.info(f"💰 Preço atual de {cripto_atual}: ${preco_atual:.2f}")

        return df, preco_atual
    except Exception as e:
        logging.error(f"Erro ao buscar dados do mercado: {e}")
        return None, None

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

def executar_estrategia():
    """
    Executa a estratégia de trading em um loop contínuo.
    """
    global POSICAO_ABERTA  

    obter_saldo()
    configurar_operacao()

    logging.info("\n🚀 Bot iniciado. Monitorando o mercado...")

    try:
        while True:  # Loop contínuo
            df, preco = obter_dados_historicos(100)

            if df is not None:
                strategy = TradingStrategy(df)

                # 🔹 Início do bloco de informações
                logging.info("\n====================")
                logging.info("📊 Indicadores Atuais:")
                logging.info(f"SMA9: {df['SMA_9'].iloc[-1]:.2f} | SMA21: {df['SMA_21'].iloc[-1]:.2f}")
                logging.info(f"EMA100: {df['EMA_100'].iloc[-1]:.2f} | EMA200: {df['EMA_200'].iloc[-1]:.2f}")
                logging.info(f"RSI Atual: {df['RSI'].iloc[-1]:.2f}")

                logging.info("\n⚡ Verificação dos Critérios:")

                compra_mm = strategy.verificar_compra()
                venda_mm = strategy.verificar_venda()
                short_mm = strategy.verificar_short()
                recompra_mm = strategy.verificar_recompra()

                rsi_atual = df["RSI"].iloc[-1]
                sma9_atual = df["SMA_9"].iloc[-1]
                sma21_atual = df["SMA_21"].iloc[-1]

                logging.info(f" {'✅' if compra_mm else '❌'} Critério de COMPRA {'atingido' if compra_mm else 'NÃO atingido'} (SMA9: {sma9_atual:.2f}, SMA21: {sma21_atual:.2f}, RSI: {rsi_atual:.2f}).")
                logging.info(f" {'✅' if venda_mm else '❌'} Critério de VENDA {'atingido' if venda_mm else 'NÃO atingido'} (RSI > 70 ou SMA9 cruzou abaixo da SMA21).")
                logging.info(f" {'✅' if short_mm else '❌'} Critério de VENDA SHORT {'atingido' if short_mm else 'NÃO atingido'} (RSI: {rsi_atual:.2f}, SMA9: {sma9_atual:.2f}).")
                logging.info(f" {'✅' if recompra_mm else '❌'} Critério de RECOMPRA SHORT {'atingido' if recompra_mm else 'NÃO atingido'} (RSI: {rsi_atual:.2f}).")

                # 📌 Modo Long: Compra só se não houver posição aberta
                if compra_mm and POSICAO_ABERTA is None:
                    logging.info("✅ Sinal de COMPRA confirmado!")
                    executar_ordem("buy", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = "long"

                # 📌 Modo Long: Só vende se já tiver comprado antes
                elif venda_mm and POSICAO_ABERTA == "long":
                    logging.info("🚨 Sinal de VENDA confirmado!")
                    executar_ordem("sell", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None  # Fecha a posição

                # 📌 Modo Short: Vende apenas se não houver posição aberta
                elif short_mm and POSICAO_ABERTA is None:
                    logging.info("🚨 Sinal de VENDA SHORT confirmado!")
                    executar_ordem("sell", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = "short"

                # 📌 Modo Short: Só recompra se já tiver vendido antes
                elif recompra_mm and POSICAO_ABERTA == "short":
                    logging.info("✅ Sinal de RECOMPRA SHORT confirmado!")
                    executar_ordem("buy", VALOR_OPERACAO / preco)
                    POSICAO_ABERTA = None  # Fecha a posição

                else:
                    logging.info("⚠️ Nenhum sinal de operação encontrado no momento.")

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


def executar_ordem(tipo_ordem, quantidade):
    """
    Executa uma ordem de compra ou venda na Binance ou simula a operação.
    
    :param tipo_ordem: 'buy' para compra, 'sell' para venda
    :param quantidade: Quantidade de moeda a ser comprada ou vendida
    """
    try:
        if tipo_ordem not in ["buy", "sell"]:
            raise ValueError("Tipo de ordem inválido. Use 'buy' ou 'sell'.")

        if MODO_SIMULADO:
            logging.info(f"🟡 [SIMULADO] Ordem de {tipo_ordem.upper()} enviada para {CRIPTO_ATUAL} - Quantidade: {quantidade:.6f}")
            return {"status": "simulado", "tipo": tipo_ordem, "quantidade": quantidade}

        # Verifica saldo antes da compra real
        saldo = client.get_asset_balance(asset=CRIPTO_ATUAL[:-4])  # Remove "USDT" do final
        saldo_disponivel = float(saldo["free"]) if saldo else 0

        if tipo_ordem == "buy":
            if saldo_disponivel < quantidade:
                logging.error(f"❌ Saldo insuficiente! Disponível: {saldo_disponivel}, Necessário: {quantidade}")
                return None
            logging.info(f"📈 Enviando ordem de COMPRA: {CRIPTO_ATUAL} - {quantidade}")

        elif tipo_ordem == "sell":
            logging.info(f"📉 Enviando ordem de VENDA: {CRIPTO_ATUAL} - {quantidade}")

        # Executa a ordem na Binance
        ordem = client.order_market(symbol=CRIPTO_ATUAL, side=tipo_ordem.upper(), quantity=quantidade)

        # Confirma execução da ordem
        logging.info(f"✅ Ordem de {tipo_ordem.upper()} executada com sucesso!")
        logging.info(f"📌 Detalhes da ordem: {ordem}")

        return ordem
    except Exception as e:
        logging.error(f"❌ Erro ao executar ordem: {e}")
        return None

# Executar a lógica principal
if __name__ == "__main__":
    executar_estrategia()