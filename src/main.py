import time
import machine

# ─── Constantes de Hardware ────────────────────────────────────────────────────
PINO_DT  = 21   # Pino de dados (Data) do HX711
PINO_SCK = 22   # Pino de clock (Serial Clock) do HX711

# ─── Constantes de Calibração ──────────────────────────────────────────────────
# Fator empírico determinado pela relação entre a saída bruta do ADC de 24 bits
# e o valor real em gramas, compensando a sensibilidade da célula de carga.
FATOR_ESCALA_HX711 = 420.0

# ─── Limiares de Estado (em gramas) ────────────────────────────────────────────
LIMITE_ANOMALIA_G = 0     # Peso fisicamente impossível → falha de hardware
LIMITE_VAZIA_G    = 150   # Abaixo disso → apenas a tara da caixa vazia
LIMITE_CHEIO_G    = 4900  # Acima disso → caixa abastecida com carga nominal

# ─── Identificadores de Estado ─────────────────────────────────────────────────
ESTADO_INICIANDO = "INICIANDO"
ESTADO_REGULAR   = "REGULAR"
ESTADO_VAZIA     = "VAZIA"
ESTADO_CHEIA     = "CHEIA"
ESTADO_ANOMALIA  = "ANOMALIA"

# ─── Temporização ──────────────────────────────────────────────────────────────
DELAY_POLL_MS = 10    # Intervalo de re-verificação enquanto o sensor não está pronto
DELAY_LOOP_MS = 100   # Cadência do loop principal (não bloqueante para o CI)


class BalancaHX711:
    """
    Driver bit-bang para o módulo conversor HX711.

    Implementa o protocolo de comunicação manualmente via GPIO, sem depender
    de bibliotecas de terceiros. Isso garante portabilidade total e controle
    preciso sobre o timing dos 24+1 pulsos de clock definidos no datasheet.
    """

    def __init__(self, pino_dt, pino_sck):
        """Inicializa os pinos de interface e coloca o clock em repouso."""
        self.dt  = machine.Pin(pino_dt,  machine.Pin.IN)
        self.sck = machine.Pin(pino_sck, machine.Pin.OUT)
        self.sck.value(0)
        self.fator_escala = FATOR_ESCALA_HX711

    def sensor_pronto(self):
        """Retorna True quando o HX711 sinaliza que uma nova leitura está disponível (DT em LOW)."""
        return self.dt.value() == 0

    def ler_peso(self):
        """
        Lê os 24 bits do ADC via bit-banging e retorna o peso em gramas.

        Aplica a conversão de complemento de dois para suporte a valores negativos
        e divide pelo fator de escala para obter o resultado em gramas inteiros.
        Retorna None se o sensor ainda não estiver pronto para leitura.
        """
        if not self.sensor_pronto():
            return None

        valor = 0

        for _ in range(24):
            self.sck.value(1)
            valor = (valor << 1) | self.dt.value()
            self.sck.value(0)

        # 25º pulso de clock: configura o ganho do canal A para 128 na próxima leitura
        self.sck.value(1)
        self.sck.value(0)

        # Converte para inteiro com sinal (complemento de dois de 24 bits)
        if valor & 0x800000:
            valor -= 0x1000000

        return int(round(valor / self.fator_escala))


def processar_peso(peso, estado_atual):
    """
    Aplica a máquina de estados ao peso lido e retorna o novo estado.

    Separa a lógica de transição de estados do loop de I/O,
    garantindo que cada responsabilidade esteja isolada em sua própria função.

    Args:
        peso (int): Valor em gramas lido pelo sensor.
        estado_atual (str): Estado corrente da máquina de estados.

    Returns:
        str: Novo estado após processar a leitura.
    """
    # ANOMALIA: leitura de 0g é fisicamente impossível → falha estrutural
    if peso == LIMITE_ANOMALIA_G:
        if estado_atual != ESTADO_ANOMALIA:
            print("ALERTA: Caixa ausente ou erro de calibração no sensor HX711!")
        return ESTADO_ANOMALIA

    # VAZIA: peso abaixo do limiar mínimo → dispara evento único de reposição
    if peso <= LIMITE_VAZIA_G:
        if estado_atual != ESTADO_VAZIA:
            print("Evento de reposição disparado! Caixa vazia detectada.")
        return ESTADO_VAZIA

    # CHEIA: peso acima do limiar nominal → confirma reabastecimento se veio de VAZIA
    if peso >= LIMITE_CHEIO_G:
        if estado_atual == ESTADO_VAZIA:
            print("Abastecimento concluído. Caixa cheia.")
        return ESTADO_CHEIA

    # REGULAR: faixa operacional normal → reporta dinamicamente a cada variação
    print(f"Status: Estoque Regular ({peso}g)")
    return ESTADO_REGULAR


def main():
    """Ponto de entrada do firmware: inicializa o hardware e executa o loop de monitoramento."""
    print("Sistema Kanban Inicializado")

    balanca      = BalancaHX711(PINO_DT, PINO_SCK)
    estado       = ESTADO_INICIANDO
    ultimo_peso  = None

    while True:
        peso = balanca.ler_peso()

        if peso is None:
            time.sleep_ms(DELAY_POLL_MS)
            continue

        # Evita reprocessar o mesmo peso no estado REGULAR para não poluir o log
        if estado == ESTADO_REGULAR and peso == ultimo_peso:
            time.sleep_ms(DELAY_LOOP_MS)
            continue

        estado      = processar_peso(peso, estado)
        ultimo_peso = peso

        time.sleep_ms(DELAY_LOOP_MS)


# Executa diretamente no MicroPython (sem bloco __name__ == '__main__')
main()