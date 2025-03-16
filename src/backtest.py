import backtrader as bt
import pandas as pd
import logging
from strategies.strategy import TradingStrategy
from bot import obter_dados_historicos

# Configurar logging para exibir informações do backtest
logging.basicConfig(level=logging.INFO, format='%(message)s')

# Definições globais
CRIPTO_ATUAL = "BTCUSDT"  # Par de negociação fixa para o backtest
INTERVALO = "5m"  # Tempo gráfico
VALOR_INICIAL = 10000  # Saldo inicial para o backtest

class BacktestStrategy(bt.Strategy):
    """
    Estratégia para backtesting baseada na implementação do TradingStrategy.
    """

    def __init__(self):
        """
        Inicializa a estratégia no Backtrader e conecta com os dados do bot.
        """
        df = self.datas[0].to_pandas()
        self.trading_strategy = TradingStrategy(df)
        self.order = None  # Controle de ordens

    def next(self):
        """
        A cada novo candle, verifica os sinais e executa ordens simuladas.
        """
        if self.order:
            return  # Se há uma ordem pendente, aguarde sua finalização

        if self.trading_strategy.verificar_compra():
            self.order = self.buy()
            logging.info(f"📈 COMPRA executada - Preço: {self.datas[0].close[0]}")

        elif self.trading_strategy.verificar_venda():
            self.order = self.sell()
            logging.info(f"📉 VENDA executada - Preço: {self.datas[0].close[0]}")

        elif self.trading_strategy.verificar_short():
            self.order = self.sell()
            logging.info(f"🔻 SHORT executado - Preço: {self.datas[0].close[0]}")

        elif self.trading_strategy.verificar_recompra():
            self.order = self.buy()
            logging.info(f"🔺 RECOMPRA SHORT executada - Preço: {self.datas[0].close[0]}")

# Função para converter os dados históricos para o formato do Backtrader
def preparar_dados_backtrader(df):
    """
    Converte o DataFrame de candles da Binance para o formato do Backtrader.
    """
    df = df.copy()
    df.set_index("tempo", inplace=True)
    df = df[["abertura", "máxima", "mínima", "fechamento", "volume"]]
    df.columns = ["open", "high", "low", "close", "volume"]
    df.index = pd.to_datetime(df.index)
    return df

def rodar_backtest():
    """
    Executa o backtest usando os dados históricos da Binance e a estratégia implementada.
    """
    logging.info("\n🚀 Iniciando Backtest...")

    # Agora passamos a criptomoeda manualmente para evitar erro
    df, _ = obter_dados_historicos(500, CRIPTO_ATUAL)

    if df is None:
        logging.error("❌ Erro ao obter dados históricos. Não será possível rodar o backtest.")
        return

    df = preparar_dados_backtrader(df)

    # Criar um feed de dados para o Backtrader
    data = bt.feeds.PandasData(dataname=df)

    # Inicializar o backtest
    cerebro = bt.Cerebro()
    cerebro.addstrategy(BacktestStrategy)
    cerebro.adddata(data)
    cerebro.broker.set_cash(VALOR_INICIAL)
    cerebro.broker.setcommission(commission=0.001)  # Taxa de 0.1% por trade

    logging.info(f"\n💰 Saldo Inicial: ${cerebro.broker.getvalue():.2f}")

    # Executar o backtest
    cerebro.run()

    # Exibir o saldo final
    logging.info(f"💰 Saldo Final: ${cerebro.broker.getvalue():.2f}")

    # Exibir o gráfico da estratégia
    cerebro.plot()

if __name__ == "__main__":
    rodar_backtest()
