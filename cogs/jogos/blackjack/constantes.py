NUM_BARALHOS = 6
LIMITE_CORTE = 0.25

LIMITES_CARGO = {
    "Lêmure":      400,
    "Macaquinho":  1500,
    "Babuíno":     4500,
    "Chimpanzé":   12000,
    "Orangutango": 30000,
    "Gorila":      80000,
    "Ancestral":   250000,
    "Rei Símio":   1500000,
}

# 21+3 (suas 2 cartas + carta aberta do dealer)
ODDS_21_3 = {
    "flush":           5,    # mesma naipe, sem sequência
    "sequencia":       10,   # sequência, naipes diferentes
    "trio":            30,   # mesmo valor, naipes diferentes
    "sequencia_color": 40,   # sequência do mesmo naipe
    "trio_perfeito":   100,  # mesmo valor e mesmo naipe
}

# Perfect Pairs (suas 2 cartas iniciais)
ODDS_PERFECT_PAIRS = {
    "par_misto":    6,   # mesmo valor, cores diferentes
    "par_colorido": 12,  # mesmo valor, mesma cor, naipes diferentes
    "par_perfeito": 25,  # mesmo valor e mesmo naipe
}

NAIPE_COR = {
    "♠️": "preta", "♣️": "preta",
    "♥️": "vermelha", "♦️": "vermelha",
}

ORDEM_CARTA = {
    "A": 1,  "2": 2,  "3": 3,  "4": 4,  "5": 5,  "6": 6,
    "7": 7,  "8": 8,  "9": 9,  "10": 10, "J": 11, "Q": 12, "K": 13,
}

NOME_PT = {
    "flush":           "Flush (mesmo naipe)",
    "sequencia":       "Sequência",
    "trio":            "Trio",
    "sequencia_color": "Sequência Colorida",
    "trio_perfeito":   "Trio Perfeito",
    "par_misto":       "Par Misto",
    "par_colorido":    "Par Colorido",
    "par_perfeito":    "Par Perfeito",
}


def get_limite(cargo: str) -> int:
    return LIMITES_CARGO.get(cargo, 250)