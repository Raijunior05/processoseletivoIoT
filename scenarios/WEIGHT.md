# Descritivo de Projeto: Monitor de Estoque Kanban Inteligente

Este documento apresenta a especificação técnica e o escopo de desenvolvimento para o projeto de um **Monitor de Estoque Kanban Inteligente**.

O objetivo é criar uma solução automatizada e de baixo custo voltada para almoxarifados e linhas de montagem industriais para monitorar o nível de insumos em tempo real através do peso, eliminando a dependência de inspeções visuais manuais e prevenindo a parada de linhas de produção por falta de componentes.

---

## 1. Visão Geral do Sistema

O sistema utiliza um sensor de peso baseado em célula de carga com o amplificador e conversor **HX711** para monitorar a quantidade de peças armazenadas em uma caixa organizadora sobre uma plataforma. Através da leitura dinâmica do peso, o firmware calcula o estado atual do estoque (regular, abastecido, abaixo do limite crítico ou ausente). O sistema gerencia gatilhos automáticos de reposição e alertas de anomalia estrutural na balança, transmitindo a telemetria e os logs de eventos via comunicação Serial.

---

## 2. Requisitos de Hardware (Arquitetura de Referência no Wokwi)

Para o desenvolvimento e simulação no ambiente Wokwi, os seguintes componentes e identificadores devem ser mapeados no arquivo `diagram.json`:

- **Microcontrolador:** ESP32 DevKit C v4 (ESP32 comum).

<div align="center">
<img width="151" height="269" alt="{530B2ACC-0EF3-438A-A21D-6F977BFB2616}" src="https://github.com/user-attachments/assets/757f01c2-ed9e-4969-b2d1-e63671587d8d" />
</div>

- **Sensor de Peso (Célula de Carga + HX711):** Mapeado com o ID `hx711`, configurado para responder ao controle de carga (`load`) em gramas ($g$). _(Nota: Altere o ID no .json de forma textual)._


<div align="center">
<img width="321" height="193" alt="{81FCE4BA-D114-40BB-AEC7-C5F4B857B16B}" src="https://github.com/user-attachments/assets/95139365-d878-4a7d-913d-dd1aeec81311" />
</div>

- **Interface de Comunicação:** Saída Serial (UART) para transmissão de logs de status, alertas e telemetria para a esteira de integração contínua (CI).

---

## 3. Arquitetura do Firmware e Lógica de Software

O código-fonte do firmware deve implementar as seguintes máquinas de estado, validações de segurança e lógicas de controle:

### A. Inicialização do Sistema

Ao ser energizado, o microcontrolador deve configurar os pinos de interface com o HX711 e imprimir obrigatoriamente a mensagem de inicialização no terminal antes de qualquer leitura.

- **Mensagem Serial Esperada:** `"Sistema Kanban Inicializado"`

### B. Lógica de Monitoramento de Estoque Regular

- **Estado de Espera (Carga Cheia):** O ambiente inicia com a carga máxima nominal da caixa cheia, correspondente a 5000g.
- **Zonas de Segurança:** Durante o consumo parcial dos componentes, enquanto o peso lido estiver acima do limite mínimo de segurança, o sistema deve entender que o estoque opera em faixa segura.
- **Saída Dinâmica:** O firmware deve continuar reportando o estado estável na serial de forma dinâmica.
- **Mensagem Serial Esperada:** `"Status: Estoque Regular (2500g)"`

_(Nota: A string com o valor do peso deve ser atualizada dinamicamente conforme a leitura real do sensor)._

### C. Lógica de Ciclo Completo (Consumo Crítico e Reabastecimento)

- **Detecção de Caixa Vazia:** Quando o peso cair drasticamente para um limiar de sub-estoque ou nível crítico de tara, a lógica deve disparar imediatamente um alerta único de reposição na Serial.
  - **Mensagem Serial Esperada:** `"Evento de reposição disparado! Caixa vazia detectada."`
- **Detecção de Reabastecimento:** Após o disparo do alerta, assim que o sensor registrar o retorno do peso para o patamar de carga cheia (5000g), o firmware deve processar a transição positiva de estoque, saindo do estado de alerta e normalizando o fluxo.
  - **Mensagem Serial Esperada:** `"Abastecimento concluído. Caixa cheia."`

### D. Lógica de Validação de Anomalias e Falhas Críticas

- **Filtro de Segurança:** Em condições operacionais normais, mesmo uma caixa completamente vazia possui um peso mínimo físico residual (tara). Se a leitura do sensor (`load`) for exatamente igual a `0`, o sistema deve tratar o evento como uma falha de hardware ou violação estrutural.
- **Tratamento de Erro:** O firmware deve isolar este cenário para evitar falsos pedidos de reposição e acionar um log de manutenção crítica.
- **Mensagem Serial Esperada:** `"ALERTA: Caixa ausente ou erro de calibração no sensor HX711!"`

---

## 4. Alinhamento com a Automação de Testes (Wokwi CI)

Para garantir que o código desenvolvido esteja correto, o firmware deve responder estritamente aos estímulos configurados nos cenários do Wokwi CI. O código não deve conter funções bloqueantes longas em seu loop principal para que as validações de tempo funcionem perfeitamente. Mensagens com letras maiúsculas e minúsculas diferentes do específicado serão consideradas erradas.

| Cenário de Teste           | Estímulo do Simulador (`hx711` -> `load`)                                     | Validação Serial Esperada (`wait-serial`)                                                                      |
| :------------------------- | :---------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------- |
| **1. Consumo Parcial**     | Inicia em `5000` $\rightarrow$ Altera para `2500`                             | `"Status: Estoque Regular (2500g)"`                                                                            |
| **2. Ciclo Completo**      | Altera para `150` $\rightarrow$ [Espera 1s] $\rightarrow$ Retorna para `5000` | 1º: `"Evento de reposição disparado! Caixa vazia detectada."`<br>2º: `"Abastecimento concluído. Caixa cheia."` |
| **3. Anomalia de Leitura** | Inicia em `5000` $\rightarrow$ Altera para `0`                                | `"ALERTA: Caixa ausente ou erro de calibração no sensor HX711!"`                                               |
