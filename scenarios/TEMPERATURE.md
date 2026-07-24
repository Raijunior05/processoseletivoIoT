# Descritivo de Projeto: Sistema de Monitoramento de Temperatura e Abertura de Porta (Smart Cooler / Estufa)

Este documento apresenta a especificação técnica e o escopo de desenvolvimento para o projeto de um **Sistema de Monitoramento de Temperatura e Abertura de Porta**.

O objetivo é criar uma solução embarcada para controle de qualidade e auditoria em ambientes refrigerados, estufas ou painéis elétricos, monitorando o tempo de exposição térmica e a integridade do isolamento físico para prevenir a degradação de insumos ou sobreaquecimento de componentes.

---

## 1. Visão Geral do Sistema

O sistema utiliza um botão físico para detectar o estado de abertura de uma porta/tampa e um sensor de unidade de medição inercial **MPU6050** para ler a temperatura ambiente local. O firmware monitora duas condições de risco críticas em paralelo: o tempo contínuo em que a porta permanece aberta e variações térmicas abruptas baseadas em um gradiente delta ($\Delta T$). Caso qualquer anomalia ocorra, logs de alerta específicos são enviados via comunicação Serial. Quando o ambiente retorna às condições seguras, o sistema reporta a normalização.

---

## 2. Requisitos de Hardware (Arquitetura de Referência no Wokwi)

Para o desenvolvimento e simulação no ambiente Wokwi, os seguintes componentes e identificadores devem ser mapeados no arquivo `diagram.json`:

- **Microcontrolador:** ESP32 DevKit C v4 (ESP32 comum).

<div align="center">
<img width="151" height="269" alt="{530B2ACC-0EF3-438A-A21D-6F977BFB2616}" src="https://github.com/user-attachments/assets/757f01c2-ed9e-4969-b2d1-e63671587d8d" />
</div>

- **Sensor de Temperatura (MPU6050 IMU):** Mapeado com o ID `imu1`.

<div align="center">
<img width="212" height="170" alt="{D3B91040-97C4-4232-BBB0-3D8FC8D5EF92}" src="https://github.com/user-attachments/assets/4f76422b-fe18-49f8-9e42-b5910daf8e7e" />
</div>

- **Fim de Curso / Sensor de Porta (Botão):** Mapeado obrigatoriamente com o ID `btn1`, simulando o estado da porta (Pressionado/Fechado = `1`, Solto/Aberto = `0`).

<div align="center">
<img width="204" height="143" alt="{06442CCC-FADA-43A3-9C57-6E77FC98C916}" src="https://github.com/user-attachments/assets/22fbbacd-5994-41d1-b0a0-ef120afd6f1a" />
</div>

- **Interface de Comunicação:** Saída Serial (UART) para transmissão de logs de status, alarmes e telemetria para a esteira de integração contínua (CI).

---

## 3. Arquitetura do Firmware e Lógica de Software

O código-fonte do firmware deve implementar as seguintes máquinas de estado, parametrizações e lógicas de controle:

### A. Inicialização do Sistema

Ao ser energizado, o microcontrolador deve inicializar os periféricos, configurar a biblioteca do sensor (ex: `Adafruit_MPU6050`) e estabelecer a comunicação Serial. Logo após este processo, deve imprimir obrigatoriamente a mensagem de inicialização no terminal.

- **Mensagem Serial Esperada:** `"Sistema de Monitoramento Inicializado"`

### B. Lógica de Tempo de Porta Aberta (Limite X)

- **Detecção de Abertura:** Quando o pino do botão `btn1` for solto (leitura igual a `0`), o sistema deve registrar o carimbo de tempo imediatamente.
- **Estouro do Cronômetro:** Caso a porta permaneça aberta continuamente por um tempo igual ou superior ao limite parametrizado constante (ex: `LIMITE_TEMPO_X` configurado em 5000ms), um evento de falha por exposição prolongada deve ser emitido.
- **Mensagem Serial Esperada:** `"ALERTA: Porta aberta por muito tempo!"`

### C. Lógica de Elevação Térmica e Degradação (Variação Y)

- **Temperatura de Referência:** O sistema deve guardar em uma variável a temperatura base de referência coletada enquanto a porta estava fechada e o ambiente estabilizado.
- **Cálculo do Gradiente:** No laço principal, o firmware deve calcular constantemente a variação térmica:
  $$\Delta T = T_{atual} - T_{referencia}$$
- **Disparo de Alarme:** Se o delta de temperatura for maior ou igual ao limite de tolerância estipulado na constante (ex: `LIMITE_VARIACAO_Y` configurado em $3.0^\circ\text{C}$), o sistema altera seu estado para alarme térmico imediato por segurança.
- **Mensagem Serial Esperada:** `"ALERTA: Degradacao termica detectada!"`

### D. Lógica de Normalização e Restauração de Estado

- **Cessação de Riscos:** O sistema só sairá dos estados de erro quando **ambas** as condições retornarem aos limites seguros simultaneamente (botão pressionado representando porta fechada E temperatura dentro do gradiente aceitável).
- **Mensagem Serial Esperada:** `"Status: Sistema Normalizado."`

---

## 4. Alinhamento com a Automação de Testes (Wokwi CI)

Para garantir que o código desenvolvido atenda aos requisitos, o firmware passará por uma esteira de testes estritos caractere por caractere (`wait-serial`).

### Requisitos Críticos de Implementação

Para garantir que o código desenvolvido esteja correto, o firmware deve responder estritamente aos estímulos configurados nos cenários do Wokwi CI. O código não deve conter funções bloqueantes longas em seu loop principal para que as validações de tempo funcionem perfeitamente. Mensagens com letras maiúsculas e minúsculas diferentes do específicado serão consideradas erradas.

### Parâmetros de Validação no CI

| Cenário de Teste                   | Estímulos Injetados pelo Simulador                                                           | Validação Serial Esperada (`wait-serial`)                                                      |
| :--------------------------------- | :------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------- |
| **1. Alarme por Porta Aberta**     | Inicia `btn1: 1` $\rightarrow$ Muda para `btn1: 0` $\rightarrow$ Aguarda tempo limite $X$    | 1º: `"Sistema de Monitoramento Inicializado"`<br>2º: `"ALERTA: Porta aberta por muito tempo!"` |
| **2. Alarme por Elevação Térmica** | `imu1: 20°C` com `btn1: 1` $\rightarrow$ Sobe `imu1` bruscamente para `24°C`                 | 1º: `"Sistema de Monitoramento Inicializado"`<br>2º: `"ALERTA: Degradacao termica detectada!"` |
| **3. Retorno ao Estado Normal**    | Força Alarme de Porta (`btn1: 0`) $\rightarrow$ Aluno fecha a porta alterando para `btn1: 1` | 1º: `"ALERTA: Porta aberta por muito tempo!"`<br>2º: `"Status: Sistema Normalizado."`          |
