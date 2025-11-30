# Guia de Contribuição para Crypto Trading Bot (Atualizado 2025-11-11)

Agradecemos o seu interesse em contribuir para o projeto Crypto Trading Bot! Este documento descreve as diretrizes para contribuir com código, documentação e testes. Leia com atenção antes de abrir uma issue ou enviar um Pull Request (PR).

## Tipos de Contribuição

- Código (backend FastAPI / frontend React+TS)
- Documentação (README, docs/*.md, CHANGELOG)
- Testes (unitários/integrados)
- DevOps (Docker, compose, scripts)
- Observabilidade (logs, métricas)
- Planejamento (issues, roadmap)

## Fluxo Geral (Fork → Branch → PR)

1) Faça um Fork do repositório
2) Clone seu fork
   ```bash
   git clone https://github.com/SEU_USUARIO/crypto-trading-bot.git
   cd crypto-trading-bot
   ```
3) Crie uma branch descritiva
   ```bash
   git checkout -b feat/nova-estrategia
   # ou fix/ajuste-telegram, docs/atualiza-apispec, chore/ci
   ```
4) Implemente suas mudanças
5) Rode os testes e linters
6) Atualize a documentação e o CHANGELOG
7) Commit e push
   ```bash
   git commit -m "feat(signal): adiciona preset PROD com min_score e thresholds"
   git push origin feat/nova-estrategia
   ```
8) Abra um Pull Request para a branch `main` do projeto, preenchendo a descrição com:
   - Contexto do problema/objetivo
   - Mudanças realizadas
   - Impactos (API/UX/DB/infra)
   - Como testar
   - Seções de docs alteradas

## Convenções

### Mensagens de Commit (Conventional Commits)
Use prefixos padronizados:
- `feat:` nova funcionalidade
- `fix:` correção de bug
- `docs:` documentação
- `test:` testes
- `refactor:` refatoração
- `perf:` performance
- `chore:` tarefas auxiliares (build, deps)
- `ci:` pipelines
- `revert:` reverte commit anterior

Exemplos:
- `feat(scanner): parametriza top N e liquidez mínima via settings`
- `fix(order): corrige cálculo de preço médio no fallback MARKET`
- `docs(api): inclui seção /api/config no API_SPEC`

### Estilo de Código
- Python: PEP 8. Recomenda-se `black`, `flake8`, `isort`.
- TypeScript/React: ESLint + Prettier (padrões do projeto).
- Evite números mágicos; centralize thresholds no `settings` quando fizer sentido.

### Testes
- Backend:
  ```bash
  cd backend
  pytest -q
  ```
- Frontend:
  ```bash
  cd frontend
  npm test
  ```
- Escreva testes para novas funcionalidades e correções de regressões.

## Ambiente de Desenvolvimento

- Backend local:
  ```bash
  cd backend
  pip install -r requirements.txt
  uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
  ```
- Docker Compose (recomendado para dev integrado):
  ```bash
  docker compose up -d --build
  ```
- Frontend:
  ```bash
  cd frontend
  npm ci
  npm run dev
  ```

## Política de Documentação

Toda mudança relevante deve atualizar a documentação pertinente:
- README.md (visão geral e instruções)
- docs/API_SPEC.md (endpoints/contratos)
- docs/ARCHITECTURE.md (fluxos, decisões, módulos)
- docs/DEPLOYMENT.md (deploy/runbook/flags)
- docs/FRONTEND_PLAN.md (páginas/serviços/roadmap)
- CHANGELOG.md (entrada da data com seções Adicionado/Alterado/Corrigido etc.)

Checklist de documentação em PRs (copie/cole no PR):
- [ ] README.md atualizado (se aplicável)
- [ ] docs/API_SPEC.md atualizado
- [ ] docs/ARCHITECTURE.md atualizado
- [ ] docs/DEPLOYMENT.md atualizado
- [ ] docs/FRONTEND_PLAN.md atualizado
- [ ] CHANGELOG.md com entrada desta mudança
- [ ] Notas de migração/compatibilidade adicionadas (se necessário)

## Diretrizes de Qualidade

- Tratamento de erros: logs claros, evitar stacktraces vazios
- Resiliência: timeouts, retries com backoff quando aplicável (Binance/IO)
- Configuração: utilize `backend/config/settings.py` para parâmetros
- Observabilidade: logs estruturados e métricas (quando disponível)
- Segurança: não comitar chaves/API secrets; usar Testnet por padrão
- Performance: limitar concorrência de I/O (ex.: semáforo para klines)

## Abertura de Issues

Inclua:
- Descrição do problema/melhoria
- Passos para reproduzir (se bug)
- Logs ou capturas de tela (se aplicável)
- Ambiente (SO, Python/Node, Docker, etc.)
- Impacto esperado

## PR Template (sugestão)

```
Título: <tipo>: <resumo curto>

Contexto
- <descrição do problema ou objetivo>

Mudanças
- <lista das alterações técnicas>

Impactos
- API/DB/UX/Infra: <detalhar se houver>

Como testar
- Passo 1...
- Passo 2...

Docs
- [ ] README.md
- [ ] docs/API_SPEC.md
- [ ] docs/ARCHITECTURE.md
- [ ] docs/DEPLOYMENT.md
- [ ] docs/FRONTEND_PLAN.md
- [ ] CHANGELOG.md

Outros
- <observações>
```

## Código de Conduta

Seja respeitoso, objetivo e colaborativo nas discussões. Feedbacks são bem-vindos, PRs consistentes e bem testados são ainda melhores.

Agradecemos novamente por sua contribuição!
