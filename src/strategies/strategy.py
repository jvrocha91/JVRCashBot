import pandas as pd

class TradingStrategy:
    def __init__(self, df, preco_entrada=None):
        """
        Inicializa a estratégia com os dados do mercado.
        :param df: DataFrame contendo os dados históricos das candles.
        :param preco_entrada: Preço de entrada da operação atual (opcional).
        """
        self.df = df
        self.preco_entrada = preco_entrada
        self.lowest_price = None  # Menor preço desde o último check ou evento relevante
        self.highest_price = None  # Maior preço desde o último check ou evento relevante
        self.last_check_time = None  # Última vez que os critérios foram verificados
        self.calcular_indicadores()

    def calcular_indicadores(self):
        """
        Calcula os indicadores técnicos necessários para a estratégia.
        Inclui RSI e EMA.
        """
        # RSI (Relative Strength Index)
        self.df["RSI"] = self.calcular_rsi(self.df["fechamento"], window=14)
        
        # EMA (Exponential Moving Average) de 100 períodos
        self.df["EMA_100"] = self.df["fechamento"].ewm(span=100, adjust=False).mean()

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

    def verificar_criterios(self, rsi_limite):
        """
        Verifica se os critérios de RSI, SMA e EMA são atendidos.
        :param rsi_limite: Limite do RSI para a condição.
        :param sma_condicao: Condição para as Médias Móveis Simples.
        :param ema_condicao: Condição para a Média Móvel Exponencial.
        :return: Booleano indicando se os critérios são atendidos.
        """
        ultima_linha = self.df.iloc[-1]
        return (

            rsi_limite(ultima_linha["RSI"])
        )

    def atualizar_extremos(self):
        """
        Atualiza os valores de menor e maior preço desde o último check ou evento relevante.
        """
        if self.last_check_time is None:
            # Inicializa os extremos com base no DataFrame completo
            self.lowest_price = self.df["fechamento"].min()
            self.highest_price = self.df["fechamento"].max()
        else:
            # Filtra os dados desde o último check
            novos_dados = self.df[self.df.index > self.last_check_time]
            if not novos_dados.empty:
                self.lowest_price = min(self.lowest_price, novos_dados["fechamento"].min())
                self.highest_price = max(self.highest_price, novos_dados["fechamento"].max())

        # Atualiza o timestamp do último check
        self.last_check_time = self.df.index[-1]

    def verificar_compra(self):
        """
        Verifica se há sinal de compra no modo Long.
        """
        self.atualizar_extremos()
        ultima_linha = self.df.iloc[-1]

        # Verifica se o preço atual está acima da EMA 100 (tendência de alta)
        if ultima_linha["fechamento"] <= ultima_linha["EMA_100"]:
            return False

        # Critério adicional: preço atual está 0,3% acima do menor preço
        preco_atual = ultima_linha["fechamento"]
        criterio_preco = (preco_atual - self.lowest_price) / self.lowest_price >= 0.003

        return criterio_preco and self.verificar_criterios(
            lambda rsi: rsi < 35
        )

    def verificar_venda(self):
        """
        Verifica se há sinal de venda no modo Long, com variação mínima de 1% de lucro.
        """
        if self.preco_entrada is None:
            return False

        ultima_linha = self.df.iloc[-1]

        # Verifica se o preço atual está acima da EMA 100 (tendência de alta)
        if ultima_linha["fechamento"] <= ultima_linha["EMA_100"]:
            return False

        variacao = (ultima_linha["fechamento"] - self.preco_entrada) / self.preco_entrada

        return (
            variacao >= 0.0005 and (
                ultima_linha["RSI"] > 70
            )
        )

    def verificar_short(self):
        """
        Verifica se há sinal de entrada vendida (Short Selling).
        """
        self.atualizar_extremos()
        ultima_linha = self.df.iloc[-1]

        # Verifica se o preço atual está abaixo da EMA 100 (tendência de baixa)
        if ultima_linha["fechamento"] >= ultima_linha["EMA_100"]:
            return False

        # Critério adicional: preço atual está 0,3% abaixo do maior preço
        preco_atual = ultima_linha["fechamento"]
        criterio_preco = (self.highest_price - preco_atual) / self.highest_price >= 0.003

        return criterio_preco and self.verificar_criterios(
            lambda rsi: rsi > 70
        )

    def verificar_recompra(self):
        """
        Verifica se há sinal para recomprar no Short Selling, com variação mínima de 1% de lucro.
        """
        if self.preco_entrada is None:
            return False

        ultima_linha = self.df.iloc[-1]

        # Verifica se o preço atual está abaixo da EMA 100 (tendência de baixa)
        if ultima_linha["fechamento"] >= ultima_linha["EMA_100"]:
            return False

        variacao = (self.preco_entrada - ultima_linha["fechamento"]) / self.preco_entrada

        return (
            variacao >= 0.0005 and (
                ultima_linha["RSI"] < 35
            )
        )
