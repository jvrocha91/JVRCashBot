from strategies.strategy import TradingStrategy
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

# Definições globais para armazenar as escolhas do usuário
CRIPTO_ATUAL = None
VALOR_OPERACAO = None

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
            if quantidade > 1:
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
    global CRIPTO_ATUAL, VALOR_OPERACAO  # Agora essas variáveis são globais

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
            continue  # Volta ao menu sem continuar

        # Confirmação antes de prosseguir
        while True:
            print(f"\n🔹 Você escolheu: {CRIPTO_ATUAL}")
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
                VALOR_OPERACAO = float(input(f"\n💰 Digite o valor que deseja investir em cada operação ({CRIPTO_ATUAL}): "))
                if VALOR_OPERACAO > 0:
                    break
                else:
                    print("❌ O valor deve ser maior que 0.")
            except ValueError:
                print("❌ Entrada inválida. Digite um número válido.")

        print(f"\n✅ Configuração definida: {CRIPTO_ATUAL} - ${VALOR_OPERACAO:.2f} por operação.\n")
        return

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

        print(f"\n📊 Dados históricos carregados ({CRIPTO_ATUAL}, 5m): {len(df)} candles")
        print(f"💰 Preço atual de {CRIPTO_ATUAL}: ${preco_atual:.2f}\n")

        return df, preco_atual

    except Exception as e:
        print(f"Erro ao buscar dados do mercado: {e}")
        return None, None

# Executar a lógica principal
obter_saldo()
configurar_operacao()  # Agora as variáveis CRIPTO_ATUAL e VALOR_OPERACAO são definidas antes do próximo passo
df, preco = obter_dados_historicos(100)

# Aplicar a estratégia
if df is not None:
    strategy = TradingStrategy(df)

    if strategy.verificar_compra():
        print("📈 SINAL DE COMPRA DETECTADO!")
    elif strategy.verificar_venda():
        print("📉 SINAL DE VENDA DETECTADO!")
    elif strategy.verificar_short():
        print("🔻 SINAL DE VENDA SHORT DETECTADO!")
    elif strategy.verificar_recompra():
        print("🔺 SINAL DE RECOMPRA SHORT DETECTADO!")
    else:
        print("🔎 Nenhum sinal de operação encontrado no momento.")
