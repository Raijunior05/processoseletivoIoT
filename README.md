# Relatório Final - Monitor de Estoque Kanban Inteligente

### Identificação do Candidato
* **Nome completo:** Raimundo Ferreira do Nascimento Junior
* **GitHub:** [Raijunior05](https://github.com/Raijunior05)

---

## Visão Geral da Solução

O projeto implementa um sistema embarcado simulado para monitoramento de estoque em tempo real no contexto de um almoxarifado industrial. Utilizando uma balança digital baseada no módulo HX711, o firmware verifica continuamente o peso de uma caixa de insumos e reporta seu estado (`Regular`, `Vazia`, `Cheia` ou `Anomalia`) via comunicação Serial. O objetivo é automatizar o controle de reposição, eliminando verificações manuais e prevenindo a parada de linhas de produção por falta de componentes.

---

## Arquitetura do Sistema Embarcado

O firmware é estruturado em três camadas de responsabilidade isoladas, seguindo o princípio de separação de responsabilidades (Single Responsibility Principle):

```
┌─────────────────────────────────────────────────────────┐
│                    CAMADA DE HARDWARE                   │
│          class BalancaHX711 — driver bit-bang           │
│   Abstrai o protocolo HX711 (24+1 pulsos de clock)      │
└───────────────────────────┬─────────────────────────────┘
                            │ peso (int | None)
┌───────────────────────────▼─────────────────────────────┐
│                  CAMADA DE LÓGICA                       │
│       def processar_peso(peso, estado_atual)            │
│   Máquina de estados finitos — pura, sem I/O direto     │
└───────────────────────────┬─────────────────────────────┘
                            │ novo_estado
┌───────────────────────────▼─────────────────────────────┐
│                  CAMADA DE CONTROLE                     │
│                    def main()                           │
│   Loop não-bloqueante: lê sensor, chama lógica, aguarda │
└─────────────────────────────────────────────────────────┘
```

### Fluxo da Máquina de Estados

```
                  [INICIANDO]
                       │
                 leitura válida
                       │
         ┌─────────────┼──────────────────┐
         │             │                  │
      peso==0      peso<=150g        peso>=4900g
         │             │                  │
    [ANOMALIA]      [VAZIA]           [CHEIA]
         │             │                  │
   alerta manu-   dispara evento    (aguarda ciclo)
    tenção CI      de reposição          │
                       │            peso<=4900g
                  peso>=4900g            │
                       │            [REGULAR]
                  [CHEIA] ←──── reporta dinamicamente
                  confirma
               reabastecimento
```

---

## Componentes Utilizados na Simulação

| Componente | ID no `diagram.json` | Função |
|---|---|---|
| **ESP32 DevKit C v4** | `esp` | Microcontrolador principal; executa o firmware MicroPython e gerencia o protocolo de comunicação com o HX711 |
| **Módulo HX711 + Célula de Carga** | `hx711` | Converte força mecânica em valor digital de 24 bits via ADC especializado; o pino `DT` sinaliza a disponibilidade de dado e o `SCK` recebe os pulsos de clock |
| **Interface Serial (UART)** | `$serialMonitor` | Canal de telemetria; todas as mensagens de status e alertas são transmitidas por aqui para interceptação pelo robô de integração contínua |

**Conexões de pinos:**
- `ESP32:21 → HX711:DT` — leitura de dados
- `ESP32:22 → HX711:SCK` — clock de sincronização
- `ESP32:3V3 → HX711:VCC` — alimentação
- `ESP32:TX/RX → $serialMonitor` — saída de logs

---

## Decisões Técnicas Relevantes

### Por que implementar o driver HX711 via bit-banging?
O ambiente MicroPython do Wokwi não disponibiliza um driver nativo para o HX711. A implementação manual do protocolo (24 pulsos de clock para leitura dos bits + 1 pulso extra para configurar o ganho em 128×) garante portabilidade total e controle preciso sobre o timing, sem depender de bibliotecas externas que poderiam não existir no ambiente de simulação.

### Por que separar `processar_peso()` do `main()`?
Isolar a máquina de estados em uma função pura (sem efeitos colaterais de I/O) facilita o raciocínio sobre o comportamento do sistema e torna cada transição de estado testável de forma independente. O `main()` fica responsável apenas por orquestrar leitura e escrita, sem conter lógica de negócio.

### Por que usar constantes nomeadas em vez de números diretos?
Limiares como `150g` e `4900g` têm significado físico específico (tara mínima da caixa e carga nominal de operação). Declará-los como `LIMITE_VAZIA_G` e `LIMITE_CHEIO_G` no topo do arquivo torna a intenção explícita, facilita a recalibração futura e elimina o risco de inconsistência ao alterar um limiar em múltiplos pontos do código.

### Por que o loop principal usa `sleep_ms` curtos em vez de bloqueio longo?
O Wokwi CI injeta alterações de carga em janelas de tempo específicas. Um loop bloqueante poderia perder a janela de leitura após a mudança de peso do simulador, causando falha no `wait-serial` por timeout. Os atrasos curtos (`DELAY_POLL_MS = 10ms`, `DELAY_LOOP_MS = 100ms`) garantem que o firmware permaneça responsivo e sincronizado com o ritmo do ambiente automatizado.

### Por que a mensagem "Caixa cheia" só é emitida quando o estado anterior era `VAZIA`?
Evitar impressões duplicadas em loop é fundamental para que o CI encontre exatamente uma ocorrência de cada mensagem esperada. A transição `VAZIA → CHEIA` representa o ciclo completo de reabastecimento, que é o único momento semanticamente correto para confirmar que o operador concluiu o abastecimento.

---

## Resultados Obtidos

O sistema atendeu integralmente a todos os requisitos funcionais e de integração contínua:

- ✅ **Teste 1 — Consumo Parcial:** O firmware detectou corretamente a mudança de 5000g → 2500g e reportou `"Status: Estoque Regular (2500g)"` sem disparar alertas prematuros.
- ✅ **Teste 2 — Ciclo Completo:** A sequência `5000g → 150g → 5000g` gerou exatamente as duas mensagens esperadas na ordem correta, sem repetições.
- ✅ **Teste 3 — Anomalia:** A leitura de `0g` foi imediatamente identificada como falha estrutural, emitindo o alerta de manutenção correto e isolando o evento de qualquer pedido de reposição.

O pipeline completo foi aprovado pelo GitHub Actions com todos os jobs concluídos com sucesso, confirmando a estabilidade do firmware no ambiente automatizado.

---

## Comentários Adicionais

### Dificuldades encontradas
A principal dificuldade foi entender que o Wokwi CI não injeta a carga inicial automaticamente — o sensor começa em `0g` até que o primeiro `set-control` do arquivo YAML seja executado. Isso exigiu cuidado especial para garantir que o firmware não disparasse um falso alerta de anomalia antes da primeira leitura válida. A solução foi usar um estado inicial `INICIANDO` que aguarda a primeira leitura válida sem acionar nenhuma transição de alerta.

### Limitações da solução
O fator de escala (`FATOR_ESCALA_HX711 = 420.0`) foi determinado empiricamente para o ambiente simulado. Em um sistema real, seria necessário um procedimento formal de calibração com pesos conhecidos para determinar esse valor com precisão para cada célula de carga específica.

### Melhorias com mais tempo
Com mais tempo, implementaria um filtro de média móvel sobre as últimas N leituras antes de alimentar a máquina de estados, reduzindo falsos positivos causados por ruído elétrico em ambientes industriais reais. Também consideraria persistir o estado atual em memória não-volátil (NVS) para que o sistema retome corretamente após uma queda de energia.

### Principais aprendizados
O desafio demonstrou na prática como a arquitetura de firmware influencia diretamente a confiabilidade em ambientes de integração contínua. A escolha de um loop não-bloqueante deixou de ser um detalhe de performance para se tornar um requisito funcional — sem ela, o sistema simplesmente não passaria nos testes automatizados.