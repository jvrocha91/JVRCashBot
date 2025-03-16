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

def obter_saldo():
    """
    Obtém e exibe o saldo disponível na conta.
    """
    try:
        saldo = client.get_account()
        print("\n💰 SALDO DISPONÍVEL:")
        ativos = []
        for asset in saldo["balances"]:
            quantidade = float(asset["free"])
            if quantidade > 0:
                ativos.append(f"{asset['asset']}: {quantidade:.6f}")
        
        if ativos:
            print("\n".join(ativos))
        else:
            print("Nenhum saldo disponível.")

    except Exception as e:
        print(f"Erro ao obter saldo da conta: {e}")

def configurar_operacao():
    """
    Permite que o usuário escolha a criptomoeda e o valor que deseja negociar.
    Após escolher a criptomoeda, ele pode confirmar ou voltar ao menu inicial.
    """
    while True:
        print("\n📌 SELECIONE A CRIPTOMOEDA PARA OPERAR:")
        print("1 - BTCUSDT (Bitcoin)")
        print("2 - ETHUSDT (Ethereum)")
        print("3 - SOLUSDT (Solana)")
        print("4 - OUTRA (Digite manualmente)")

        escolha = input("\nDigite o número da opção desejada: ")

        if escolha == "1":
            cripto = "BTCUSDT"
        elif escolha == "2":
            cripto = "ETHUSDT"
        elif escolha == "3":
            cripto = "SOLUSDT"
        elif escolha == "4":
            cripto = input("Digite o par de negociação desejado (ex: ADAUSDT, XRPUSDT): ").upper()
        else:
            print("❌ Opção inválida! Tente novamente.")
            continue  # Volta ao menu sem continuar

        # Confirmação antes de prosseguir
        while True:
            print(f"\n🔹 Você escolheu: {cripto}")
            print("1 - CONFIRMAR")
            print("2 - VOLTAR AO MENU INICIAL")

            confirmacao = input("\nDigite o número da opção desejada: ")

            if confirmacao == "1":
                break  # Confirma e continua para definir o valor de operação
            elif confirmacao == "2":
                print("\n🔄 Voltando ao menu...\n")
                return configurar_operacao()  # Reinicia a função para selecionar a cripto novamente
            else:
                print("❌ Opção inválida! Tente novamente.")

        while True:
            try:
                valor = float(input(f"\n💰 Digite o valor que deseja investir em cada operação ({cripto}): "))
                if valor > 0:
                    break
                else:
                    print("❌ O valor deve ser maior que 0.")
            except ValueError:
                print("❌ Entrada inválida. Digite um número válido.")

        print(f"\n✅ Configuração definida: {cripto} - ${valor:.2f} por operação.\n")
        return cripto, valor  # Retorna as configurações

# Executar a função de saldo antes de escolher a cripto
obter_saldo()
CRIPTO_ATUAL, VALOR_OPERACAO = configurar_operacao()

def obter_dados_historicos(limite=100):
    """
    Obtém dados históricos (candlesticks) e os converte para um DataFrame Pandas.
    Retorna o DataFrame e o preço de fechamento mais recente.
    """
    try:
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

        print(f"\n📊 Dados históricos carregados ({CRIPTO_ATUAL}, 5m): {len(df)} candles")
        print(f"💰 Preço atual de {CRIPTO_ATUAL}: ${preco_atual:.2f}\n")

        return df, preco_atual

    except Exception as e:
        print(f"Erro ao buscar dados do mercado: {e}")
        return None, None

# Executar função para obter dados históricos
df, preco = obter_dados_historicos(10)

# Exibir os últimos 5 candles
print(df[["tempo", "abertura", "máxima", "mínima", "fechamento", "volume"]].tail(5))
