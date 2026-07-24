# Relatório Final - Monitor de Estoque Kanban Inteligente

### Identificação do Candidato
* **Nome completo:** Raimundo Ferreira do Nascimento Junior
* **GitHub:** [Raijunior05](https://github.com/Raijunior05)

---

## Visão Geral da Solução
O projeto consiste em um sistema embarcado simulado para monitoramento de estoque em tempo real. Utilizando uma balança digital, o sistema verifica dinamicamente o peso de uma caixa de insumos e reporta seu status (Regular, Vazia, Cheia ou Anomalia) via comunicação Serial. O objetivo principal é automatizar o controle de almoxarifados, eliminando verificações manuais e acionando reposições de forma preditiva e segura.

## Arquitetura do Sistema Embarcado
O firmware foi estruturado em um laço de execução principal não-bloqueante que interage perfeitamente com uma máquina de estados finitos.
* **Leitura de Dados:** Uma classe dedicada (`BalancaHX711`) realiza a leitura dos bits do sensor via *bit-banging*, gerenciando os pulsos de clock (SCK) e a leitura dos dados (DT) sem depender de bibliotecas de terceiros.
* **Máquina de Estados:** O laço principal processa a variável de peso e gerencia de forma limpa as transições lógicas entre os estados de operação.
* **Sincronismo de RTOS:** A arquitetura utiliza pequenas pausas estratégicas (`time.sleep_ms`) para ceder tempo de processamento ao sistema operacional subjacente, garantindo a atualização do hardware virtual sem causar inanição de CPU (*starvation*).

## Componentes Utilizados na Simulação
* **ESP32 DevKit C v4:** Microcontrolador principal responsável por executar o firmware em MicroPython e gerenciar a lógica de controle.
* **Módulo HX711 e Célula de Carga:** Conjunto responsável por converter a força mecânica em sinais elétricos digitais de 24 bits, calibrado com um fator de escala para respostas em gramas reais.
* **Interface Serial (UART):** Mapeada explicitamente nos pinos TX/RX virtuais para a saída de telemetria e logs, garantindo que o robô de integração contínua intercepte os dados.

## Decisões Técnicas Relevantes
* Implementação de um driver *bit-bang* customizado para o HX711, garantindo resposta imediata na leitura dos registradores sem sobrecarregar a memória do microcontrolador.
* Inclusão de um método de espera não-bloqueante durante a verificação do pino `DT`, impedindo o travamento da engine de simulação do Wokwi.
* Adição de um atraso (*delay*) estratégico de 1 segundo no início da inicialização do firmware. Isso garante tempo hábil para a injeção mecânica da carga inicial pela esteira do GitHub Actions antes das leituras, evitando falsos positivos de calibração.
* Tratamento matemático e arredondamento na saída dos valores do ADC, blindando o log da Serial contra falhas de formatação de ponto flutuante.

## Resultados Obtidos
O sistema atendeu a todos os requisitos de software e hardware propostos de forma robusta e otimizada.
* O dimensionamento e detecção das faixas de peso ("Caixa Vazia", "Caixa Cheia" e "Estoque Regular") ocorrem sem latência.
* O filtro de anomalia estrutural (leitura 0g) previne chamados falsos de reposição e responde instantaneamente a desconexões do sensor.
* O firmware roda em perfeita harmonia com o ambiente simulado. O pipeline completo foi aprovado pela validação automatizada do GitHub Actions, registrando tempo de execução eficiente e leitura exata de todos os cenários sem apresentar *timeouts* ou erros de integridade.