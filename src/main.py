import time
import machine


class BalancaHX711:
    def __init__(self, pino_dt, pino_sck):
        self.dt = machine.Pin(pino_dt, machine.Pin.IN)
        self.sck = machine.Pin(pino_sck, machine.Pin.OUT)
        self.sck.value(0)

        # Ajuste caso seja necessário calibrar
        self.fator_escala = 420.0

    def sensor_pronto(self):
        return self.dt.value() == 0

    def ler_peso(self):
        if not self.sensor_pronto():
            return None

        valor = 0

        for _ in range(24):
            self.sck.value(1)
            valor = (valor << 1) | self.dt.value()
            self.sck.value(0)

        # Pulso 25 (ganho 128)
        self.sck.value(1)
        self.sck.value(0)

        # Converte para inteiro com sinal
        if valor & 0x800000:
            valor -= 0x1000000

        return int(round(valor / self.fator_escala))


def main():
    print("Sistema Kanban Inicializado")

    balanca = BalancaHX711(21, 22)

    estado = "INICIANDO"
    ultimo_peso = None

    while True:

        peso = balanca.ler_peso()

        if peso is None:
            time.sleep_ms(10)
            continue

        # ANOMALIA
        if peso == 0:
            if estado != "ANOMALIA":
                print("ALERTA: Caixa ausente ou erro de calibração no sensor HX711!")
                estado = "ANOMALIA"

        # VAZIA
        elif peso <= 150:
            if estado != "VAZIA":
                print("Evento de reposição disparado! Caixa vazia detectada.")
                estado = "VAZIA"

        # CHEIA
        elif peso >= 4900:
            if estado == "VAZIA":
                print("Abastecimento concluído. Caixa cheia.")
            estado = "CHEIA"

        # REGULAR
        else:
            if peso != ultimo_peso:
                print(f"Status: Estoque Regular ({peso}g)")
                ultimo_peso = peso
            estado = "REGULAR"

        time.sleep_ms(100)


# Executa diretamente
main()