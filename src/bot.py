import pandas as pd
from binance.client import Client
from dotenv import load_dotenv
import os

# Carregar as chaves da Binance do arquivo .env
load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# Conectar à Binance API
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# Definições globais para facilitar a modificação
CRIPTO_ATUAL = "BTCUSDT"  # Pode ser "ETHUSDT", "SOLUSDT", etc.
INTERVALO_CANDLE = "5m"  # Pode ser alterado para "15m", "1h", etc.

def obter_saldo():
    """
    Obtém e exibe o saldo disponível na conta.
    """
    try:
        saldo = client.get_account()
        print("\n💰 Saldo disponível:")
        for asset in saldo["balances"]:
            quantidade = float(asset["free"])
            if quantidade > 1:
                print(f"{asset['asset']}: {quantidade:.6f}")
    except Exception as e:
        print(f"Erro ao obter saldo da conta: {e}")

def obter_dados_historicos(limite=100):
    """
    Obtém dados históricos (candlesticks) e os converte para um DataFrame Pandas.
    Retorna o DataFrame e o preço de fechamento mais recente.
    """
    try:
        candles = client.get_klines(symbol=CRIPTO_ATUAL, interval=INTERVALO_CANDLE, limit=limite)

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

        print(f"\n📊 Dados históricos carregados ({CRIPTO_ATUAL}, {INTERVALO_CANDLE}): {len(df)} candles")
        print(f"💰 Preço atual de {CRIPTO_ATUAL}: ${preco_atual:.2f}\n")

        return df, preco_atual

    except Exception as e:
        print(f"Erro ao buscar dados do mercado: {e}")
        return None, None

# Executar funções
obter_saldo()
df, preco = obter_dados_historicos(10)

# Exibir os últimos 5 candles
print(df[["tempo", "abertura", "máxima", "mínima", "fechamento", "volume"]].tail(5))
