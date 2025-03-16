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
        self.order = None  # Controle de ordens

    def notify_order(self, order):
        """
        Imprime logs sempre que uma ordem for executada.
        """
        if order.status in [order.Completed]:
            if order.isbuy():
                logging.info(f"✅ COMPRA Confirmada - Preço: {order.executed.price:.2f}")
            elif order.issell():
                logging.info(f"❌ VENDA Confirmada - Preço: {order.executed.price:.2f}")
            self.order = None  # Resetar a ordem após a execução

    def next(self):
        """
        A cada novo candle, verifica os sinais e executa ordens simuladas.
        """
        if self.order:
            return  # Se há uma ordem pendente, aguarde sua finalização

        # Criar um DataFrame com os dados atuais para passar para a estratégia
        df = pd.DataFrame({
            'tempo': [self.datas[0].datetime.datetime(0)],
            'abertura': [self.datas[0].open[0]],
            'máxima': [self.datas[0].high[0]],
            'mínima': [self.datas[0].low[0]],
            'fechamento': [self.datas[0].close[0]],
            'volume': [self.datas[0].volume[0]]
        })

        trading_strategy = TradingStrategy(df)

        if trading_strategy.verificar_compra():
            self.order = self.buy(size=0.01)  # Ajuste o tamanho da ordem para uma fração do saldo
            logging.info(f"📈 COMPRA enviada - Preço: {self.datas[0].close[0]:.2f}")

        elif trading_strategy.verificar_venda():
            self.order = self.sell(size=0.01)
            logging.info(f"📉 VENDA enviada - Preço: {self.datas[0].close[0]:.2f}")

        elif trading_strategy.verificar_short():
            self.order = self.sell(size=0.01)
            logging.info(f"🔻 SHORT enviado - Preço: {self.datas[0].close[0]:.2f}")

        elif trading_strategy.verificar_recompra():
            self.order = self.buy(size=0.01)
            logging.info(f"🔺 RECOMPRA SHORT enviada - Preço: {self.datas[0].close[0]:.2f}")

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
