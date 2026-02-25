import random
from .constantes import NUM_BARALHOS, LIMITE_CORTE


class Sapato:
    def __init__(self):
        self.cartas: list = []
        self.total_inicial: int = 0
        self.embaralhar()

    def embaralhar(self):
        naipes = ["♠️", "♥️", "♦️", "♣️"]
        valores = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        self.cartas = [{"valor": v, "naipe": n} for v in valores for n in naipes] * NUM_BARALHOS
        random.shuffle(self.cartas)
        self.total_inicial = len(self.cartas)

    def puxar(self) -> dict:
        if len(self.cartas) / self.total_inicial < LIMITE_CORTE:
            self.embaralhar()
        return self.cartas.pop()

    @property
    def precisa_embaralhar(self) -> bool:
        return len(self.cartas) / self.total_inicial < LIMITE_CORTE

    @property
    def cartas_restantes(self) -> int:
        return len(self.cartas)