from binance.client import Client
from dotenv import load_dotenv
import os

# Carrega as chaves do arquivo .env
load_dotenv()
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")

# Conectar à Binance API
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# Testar a conexão pegando o saldo da conta
def verificar_saldo():
    try:
        saldo = client.get_account()
        print("Conexão bem-sucedida! ✅")
        for asset in saldo['balances']:
            if float(asset['free']) > 1:  # Mostra apenas ativos com saldo disponível
                print(f"{asset['asset']}: {asset['free']}")
    except Exception as e:
        print(f"Erro ao conectar-se à Binance: {e}")

# Executar teste
verificar_saldo()
