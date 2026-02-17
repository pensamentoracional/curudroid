# Fase 30 — Arquitetura Segura para AI Advisor (Investigation First)

## Objetivo
Integrar IA no Curudroid de forma **consultiva**, sem alterar governança, sem criar bypass e com comportamento determinístico quando desativada.

## Princípios de integração
1. **Governança-first**: IA não executa, não aprova, não altera estado oficial.
2. **Sidecar consultivo**: IA roda em paralelo ao pipeline decisório.
3. **Fail-open para IA**: falha/timeout da IA não bloqueia fluxo principal.
4. **Determinismo por flag**: `AI_PROVIDER=none` mantém pipeline idêntico à fase anterior.

## Estado atual observado no repositório
A base já possui os elementos necessários para acoplamento seguro:

- Observabilidade estruturada em `core/observability.py`, com `log_decision(...)` para `logs/decisions.log` e métricas em `data/autonomy_metrics.json`.
- Pipeline reativo determinístico em `core/autonomy_reactive.py` com sequência Supervisor → Curupira → decisão de status.
- Configuração por feature flags em `ai/config.py`, incluindo `AI_PROVIDER` e defaults conservadores.
- CLI em `main.py` com pontos de orquestração (`--process-intents`, `--observability-report`) adequados para integração sidecar.

## Onde integrar a IA

### Fluxo recomendado (MVP seguro)

```text
Plan Validator → AI Advisor (consultivo) → Supervisor → Curupira → Policy Lock → Ledger
```

**Regra crítica:** a IA recebe o mesmo plano validado, mas retorna apenas metadado consultivo.

### Ponto técnico preferencial
- Após validação estrutural básica do plano.
- Antes do Supervisor, sem dependência obrigatória do Supervisor na IA.

### Ajuste de robustez operacional
Como hardening adicional, o sistema pode também gerar recomendação **pós-gates** (Supervisor/Curupira) para explicabilidade, sem influenciar decisão oficial.

## Contrato da camada `AIAdvisor`

Arquivo proposto: `core/ai_advisor.py`

```python
class AIAdvisor:
    def analyze(self, plan: dict, context: dict) -> dict | None:
        ...
```

### Estrutura de retorno (imutável e não executável)

```json
{
  "suggested_action": "dry_run | block | review | proceed",
  "risk_assessment": {
    "level": "low | medium | high",
    "score": 0.0
  },
  "confidence": 0.0,
  "explanation": "...",
  "provider": "openai",
  "model": "...",
  "timestamp": "..."
}
```

### Regras do contrato
- Nunca sobrescrever `risk_score` oficial.
- Nunca acionar execução.
- Nunca alterar policy/ledger.
- `confidence` clampado em `[0.0, 1.0]`.
- `suggested_action` em enum fechado.

## Isolamento obrigatório (4 níveis)

### 1) Isolamento de execução
`core/ai_advisor.py`:
- **Não importa** executor.
- **Não importa** policy lock.
- **Não importa** ledger.
- **Não chama** supervisor/curupira para decidir pipeline.

### 2) Isolamento de efeito
- IA não modifica `plan` original.
- IA não escreve estado oficial.
- IA não altera flags/scores oficiais.
- Saída da IA é apenas recomendação.

### 3) Isolamento por feature flag
- `AI_PROVIDER=none` retorna `None` sem chamada externa.
- Resultado do pipeline deve permanecer idêntico ao baseline.

### 4) Isolamento por falha/timeout
- Timeout, erro de provider ou resposta inválida: continuar pipeline normal.
- Registrar falha como observabilidade, nunca como bloqueio de execução.

## Arquitetura mínima viável

```text
core/
 ├── ai_advisor.py
 ├── ai_providers/
 │   ├── base.py
 │   ├── openai_provider.py
 │   └── null_provider.py
```

### `null_provider.py`
Sempre retorna `None` e garante compatibilidade total quando IA desligada.

## Logging e auditoria
Toda interação IA deve registrar evento em `decisions.log`:

- `component="ai_advisor"`
- `status="success|error|timeout|invalid_output"`
- `latency_ms`
- `provider` / `model`
- `plan_id`
- `ai_recommendation` (quando válida)

Exemplo:

```json
{
  "component": "ai_advisor",
  "plan_id": "...",
  "status": "success",
  "latency_ms": 820,
  "provider": "openai",
  "model": "gpt-...",
  "ai_recommendation": {"suggested_action": "review"}
}
```

## Riscos sistêmicos e mitigação

1. **Dependência cognitiva**
   - Mitigação: decisão oficial permanece no pipeline determinístico; mensagens explícitas de “consultivo”.

2. **Prompt injection**
   - Mitigação: contexto sanitizado; nunca enviar credenciais/policy completa/ledger completo.

3. **Não determinismo com IA ativa**
   - Mitigação: teste de regressão garantindo equivalência quando `AI_PROVIDER=none`.

4. **Escalada indevida futura (auto-apply por IA)**
   - Mitigação: teste que falha se recomendação da IA virar gatilho de execução.

5. **Vazamento de dados ao provider**
   - Mitigação: redaction/allowlist de campos e minimização de payload.

6. **Model DoS / custo e latência**
   - Mitigação: timeout curto, budget por execução, retry limitado e circuit breaker.

## Critérios de aceite da Fase 30 (Investigação)
- [ ] Existe proposta de integração sidecar sem bypass.
- [ ] Contrato `AIAdvisor.analyze(plan, context)` definido.
- [ ] Estratégia `null_provider` definida para comportamento idêntico com IA desligada.
- [ ] Esquema de logging `component="ai_advisor"` definido.
- [ ] Riscos sistêmicos e mitigação documentados.
- [ ] Testes de não-bypass e determinismo especificados.

## Respostas diretas
- **Onde integrar?** Após Plan Validator, antes do Supervisor, como camada consultiva paralela.
- **Em qual ponto do fluxo?** Entre intake validado e gates de governança, sem poder decisório.
- **Antes ou depois do Supervisor?** Antes para utilidade consultiva; opcionalmente pós-gates para explicabilidade.
- **Como manter isolamento?** Dependências restritas + sem side-effects + feature flag + fail-open em erro/timeout.
- **Contrato?** `analyze(plan, context) -> AIRecommendation | None`, com schema rígido.
- **Riscos?** Dependência cognitiva, prompt injection, não determinismo, vazamento, bypass futuro e Model DoS.
