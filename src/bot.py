from strategies.strategy import TradingStrategy
import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os
import logging

# Configurar logging sem timestamp e sem nível de log e sem nível de log
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Carregar as chaves da Binance do arquivo .env
load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# Conectar à Binance API
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# Definições globais
CRIPTO_ATUAL = None
VALOR_OPERACAO = None

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

def obter_dados_historicos(limite=100):
    """
    Obtém dados históricos (candlesticks) e os converte para um DataFrame Pandas.
    Retorna o DataFrame e o preço de fechamento mais recente.
    """
    try:
        if CRIPTO_ATUAL is None:
            raise ValueError("CRIPTO_ATUAL não foi definido! Execute configurar_operacao() primeiro.")

        candles = client.get_klines(symbol=CRIPTO_ATUAL, interval="5m", limit=limite)

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

        logging.info(f"\n📊 Dados históricos carregados ({CRIPTO_ATUAL}, 5m)")
        logging.info(f"💰 Preço atual de {CRIPTO_ATUAL}: ${preco_atual:.2f}")

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
    Executa a lógica principal da estratégia de trading.
    """
    obter_saldo()
    configurar_operacao()

    df, preco = obter_dados_historicos(100)

    if df is not None:
        strategy = TradingStrategy(df)

        logging.info("\n📊 Indicadores Atuais:")
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

        if compra_mm:
            logging.info("✅ Sinal de COMPRA confirmado!")
        elif venda_mm:
            logging.info("🚨 Sinal de VENDA confirmado!")
        elif short_mm:
            logging.info("🚨 Sinal de VENDA SHORT confirmado!")
        elif recompra_mm:
            logging.info("✅ Sinal de RECOMPRA SHORT confirmado!")
        else:
            logging.info("⚠️ Nenhum sinal de operação encontrado no momento.")

# Executar a lógica principal
if __name__ == "__main__":
    executar_estrategia()