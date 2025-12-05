# Sprint Planner Ruleset - Spec-Kit Style  
Versão: 3.0  
Última atualização: 2025-12-04  

## Objetivo
Gerar tasks técnicas a partir de User Stories.  
Resultado **estritamente JSON**, acionável por IA.

---

## Regras Gerais
- Cada task deve ter `description`, `us_id`, `us_title`, `estimate`  
- `"description"` inicia com verbo de ação (ex.: "Implementar", "Criar", "Validar")  
- Nenhuma task pode exceder o estimate da US  
- Soma das tasks ≈ estimate da US  
- Tasks de implementação → maior parte da estimativa  
- Tasks de teste/documentação → estimativa pequena (1–2)  
- Incluir testes e documentação sempre que aplicável  
- Evitar duplicações, genéricos e múltiplos fluxos  
- Descrição deve indicar resultado entregue  
- Nunca adicionar explicações fora do JSON

---

## Decomposição de User Stories
Para cada US, gerar tasks cobrindo:

### 1. Implementação
- Backend: lógica, serviços, repositórios, validações  
- Frontend: UI, estados, interações, layouts  
- Mobile/APIs/Integrações externas

### 2. Validações e Testes
- Unitários, integração, edge cases

### 3. Infraestrutura
- Endpoints, migrations, configurações adicionais

### 4. Documentação
- Endpoints, arquitetura, README/diagramas

---

## Quantidade de Tasks
- US pequena → 2–4 tasks  
- US média → 4–7 tasks  
- US grande → 7+ tasks  
Evitar single task

---

## Fluxos por domínio
### Backend
- Endpoints, regras, validações, integrações, migrations, tratamento de erros  
### Frontend
- Telas, componentes, estados, chamadas API, validações  
### Testes
- Unitários, integração, mocks, edge cases  
### Documentação
- Endpoints, arquitetura, diagramas

---

## Estrutura JSON obrigatória
```json
{
  "tasks": [
    {
      "description": "Verbo de ação + entrega técnica clara",
      "us_id": "ID da US",
      "us_title": "Título da US",
      "estimate": 1
    }
  ]
}
```

---

## Heurísticas de Estimativa
- Tasks de implementação → maior parte da estimativa  
- Tasks de teste/documentação → 1–2  
- US sem estimate → simples=1, média=2–3, complexa=5

---

## Input Exemplo
```json
[
  {
    "id": "US-01",
    "title": "Cadastro de usuários",
    "story": {
      "role": "Novo usuário",
      "goal": "Criar uma conta",
      "reason": "para acessar os serviços"
    },
    "acceptance_criteria": [
      "Usuário fornece email e senha",
      "Validar formato do email",
      "Gerar conta apenas se email for único"
    ],
    "estimate": 5
  }
]
```

---

## Output Exemplo
```json
{
  "tasks": [
    {
      "description": "Criar endpoint POST /users para cadastro",
      "us_id": "US-01",
      "us_title": "Cadastro de usuários",
      "estimate": 2
    },
    {
      "description": "Implementar validação de formato de email",
      "us_id": "US-01",
      "us_title": "Cadastro de usuários",
      "estimate": 1
    },
    {
      "description": "Implementar verificação de email único no repositório",
      "us_id": "US-01",
      "us_title": "Cadastro de usuários",
      "estimate": 1
    },
    {
      "description": "Criar testes unitários do fluxo de cadastro",
      "us_id": "US-01",
      "us_title": "Cadastro de usuários",
      "estimate": 1
    }
  ]
}
```

---

## Considerações Finais
- Ambiguidade → assumir interpretação mais completa e segura  
- Falta de contexto técnico → gerar tasks acionáveis e precisas  
- Seguir estritamente este ruleset  
- Nenhuma explicação fora do JSON