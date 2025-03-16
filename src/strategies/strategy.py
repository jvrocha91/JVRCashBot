import pandas as pd

class TradingStrategy:
    def __init__(self, df):
        """
        Inicializa a estratégia com os dados do mercado.
        :param df: DataFrame contendo os dados históricos das candles.
        """
        self.df = df
        self.calcular_indicadores()

    def calcular_indicadores(self):
        """
        Calcula os indicadores técnicos necessários para a estratégia.
        Inclui RSI e Médias Móveis.
        """
        # Média Móvel Exponencial (EMA)
        self.df["EMA_100"] = self.df["fechamento"].ewm(span=100, adjust=False).mean()
        self.df["EMA_200"] = self.df["fechamento"].ewm(span=200, adjust=False).mean()

        # Médias Móveis Simples (SMA)
        self.df["SMA_9"] = self.df["fechamento"].rolling(window=9).mean()
        self.df["SMA_21"] = self.df["fechamento"].rolling(window=21).mean()

        # RSI (Relative Strength Index)
        self.df["RSI"] = self.calcular_rsi(self.df["fechamento"], window=14)

    def calcular_rsi(self, serie, window=14):
        """
        Calcula o RSI (Índice de Força Relativa).
        """
        delta = serie.diff(1)
        ganho = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        perda = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = ganho / perda
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def verificar_criterios(self, rsi_limite, sma_condicao, ema_condicao):
        """
        Verifica se os critérios de RSI, SMA e EMA são atendidos.
        :param rsi_limite: Limite do RSI para a condição.
        :param sma_condicao: Condição para as Médias Móveis Simples.
        :param ema_condicao: Condição para a Média Móvel Exponencial.
        :return: Booleano indicando se os critérios são atendidos.
        """
        ultima_linha = self.df.iloc[-1]
        return (
            sma_condicao(ultima_linha["SMA_9"], ultima_linha["SMA_21"]) and
            ema_condicao(ultima_linha["fechamento"], ultima_linha["EMA_100"]) and
            rsi_limite(ultima_linha["RSI"])
        )

    def verificar_compra(self):
        """
        Verifica se há sinal de compra no modo Long.
        """
        return self.verificar_criterios(
            lambda rsi: rsi < 35,
            lambda sma9, sma21: sma9 > sma21,
            lambda fechamento, ema100: fechamento > ema100
        )

    def verificar_venda(self):
        """
        Verifica se há sinal de venda no modo Long.
        """
        ultima_linha = self.df.iloc[-1]
        return (
            (ultima_linha["RSI"] > 70 or ultima_linha["SMA_9"] < ultima_linha["SMA_21"]) and
            ultima_linha["fechamento"] > ultima_linha["EMA_200"]
        )

    def verificar_short(self):
        """
        Verifica se há sinal de entrada vendida (Short Selling).
        """
        return self.verificar_criterios(
            lambda rsi: rsi > 70,
            lambda sma9, sma21: sma9 < sma21,
            lambda fechamento, ema100: fechamento < ema100
        )

    def verificar_recompra(self):
        """
        Verifica se há sinal para recomprar no Short Selling.
        """
        ultima_linha = self.df.iloc[-1]
        return (
            (ultima_linha["RSI"] < 35 or ultima_linha["SMA_9"] > ultima_linha["SMA_21"]) and
            ultima_linha["fechamento"] < ultima_linha["EMA_200"]
        )
