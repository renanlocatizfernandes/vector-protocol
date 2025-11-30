# Recomendações de Uso dos Servidores MCP Instalados (Atualizado 2025-11-11)

Este documento fornece um guia rápido sobre os Model Context Protocols (MCPs) instalados e suas principais funcionalidades, para ajudar a escolher a ferramenta certa para cada tarefa. Está alinhado com o estado atual do repositório e documentos atualizados em 2025-11-11.

Observações gerais:
- Em tarefas de documentação/código neste repo, priorize o servidor Filesystem para ler/editar arquivos.
- Use uma ferramenta MCP por vez (consistente com as boas práticas de orquestração).
- Para buscas na web e scraping, prefira Firecrawl MCP. Para documentação de libs, prefira Context7 MCP.
- Para planejamento estruturado com checklists, utilize o Software-planning MCP.
- Para verificação de código deprecado ou pesquisas gerais, utilize Perplexity MCP.
- Respeite a política de “um passo por vez” e aguarde confirmação após cada uso de ferramenta.

---

## 1) github.com/modelcontextprotocol/servers/tree/main/src/filesystem
Descrição: Interage diretamente com o sistema de arquivos do projeto.
Ferramentas principais:
- read_file: Ler conteúdo de um arquivo.
- read_multiple_files: Ler múltiplos arquivos de uma vez.
- write_file: Criar/sobrescrever um arquivo (cuidado).
- edit_file: Edições linha a linha (git-style diff).
- create_directory: Criar diretórios.
- list_directory: Listar arquivos/diretórios.
- directory_tree: Árvore recursiva em JSON.
- move_file: Mover/renomear.
- search_files: Buscar por padrão.
- get_file_info: Metadados de arquivo.
- list_allowed_directories: Listar diretórios permitidos.

Quando usar: Qualquer operação de leitura/escrita/edição/pesquisa em arquivos do repo. É o padrão para atualizar .md e código.

Boas práticas neste repo:
- Para pequenas alterações, prefira “edit_file” (ou replace_in_file na automação local).
- Para substituições grandes ou novos arquivos, use “write_file” com o conteúdo completo.
- Sempre baseie edições no conteúdo final retornado após o último write (evita drift).

---

## 2) github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking
Descrição: Ferramenta de raciocínio sequencial para planejamento/reflexão dinâmica.
Ferramenta principal:
- sequentialthinking: Ajuda a quebrar problemas complexos, revisar passos e ajustar estratégia.

Quando usar: 
- Planejamento de mudanças maiores (refatorações, roadmaps).
- Análises que podem precisar de correções de curso.

---

## 3) github.com/modelcontextprotocol/servers/tree/main/src/memory
Descrição: Grafo de conhecimento para armazenar e consultar entidades/relações/observações.
Ferramentas:
- create_entities, create_relations, add_observations
- delete_entities, delete_observations, delete_relations
- read_graph, search_nodes, open_nodes

Quando usar: 
- Manter um Mapa de Conhecimento para conceitos/decisões/arquitetura.
- Rastrear dependências e anotações de design ao longo do projeto.

---

## 4) github.com/NightTrek/Software-planning-mcp
Descrição: Suporte a planejamento e gestão de tarefas (plan + todos).
Ferramentas:
- start_planning, save_plan
- add_todo, remove_todo, get_todos, update_todo_status

Recursos:
- planning://current-goal
- planning://implementation-plan

Quando usar:
- Estruturar metas, quebrar em tarefas, acompanhar progresso e salvar planos de implementação.

---

## 5) github.com/pashpashpash/perplexity-mcp
Descrição: Integra Perplexity AI para pesquisa, documentação e verificação.
Ferramentas:
- chat_perplexity: Conversa com contexto contínuo.
- search: Pesquisa geral (web).
- get_documentation: Documentação de tecnologias/APIs.
- find_apis: Avaliar APIs para integrar.
- check_deprecated_code: Verificar uso de features deprecadas.

Quando usar:
- Pesquisas abertas na web, documentação de libs, avaliação de APIs, detectar depreciações.

---

## 6) github.com/mendableai/firecrawl-mcp-server
Descrição: Scraping/busca web robustos, com extração e crawl.
Ferramentas:
- firecrawl_scrape: Raspar conteúdo de uma URL (preferida para página única).
- firecrawl_map: Mapear URLs de um site.
- firecrawl_search: Buscar na web com scrape opcional (resultados).
- firecrawl_crawl: Rastreamento de múltiplas páginas (cautela com volume).
- firecrawl_check_crawl_status: Status do crawl.
- firecrawl_extract: Extração estruturada via LLM.

Boas práticas:
- Preferir “search” → escolher resultados → “scrape” nas páginas relevantes.
- Evitar “crawl” sem limites (tokens/tempo).
- Use caching (maxAge/storeInCache) quando aplicável.

---

## 7) github.com/upstash/context7-mcp
Descrição: Acesso à documentação de bibliotecas via Context7.
Ferramentas:
- resolve-library-id: Resolver nome para ID Context7.
- get-library-docs: Buscar docs com o ID retornado.

Regras:
- Sempre chame resolve-library-id antes de get-library-docs (a menos que ID seja fornecido explicitamente no formato /org/proj[/version]).

Quando usar:
- Obter documentação atualizada de libs/frameworks, com foco por tópico se necessário.

---

## Dicas de Uso neste Repositório

- Atualização de documentação:
  - Use Filesystem para ler os .md, consolidar conteúdo e escrever de volta (um arquivo por vez).
- Edição de código:
  - Para mudanças localizadas, use estratégias de busca/replacement precisas (evitando sobrescrever arquivos grandes).
  - Para mudanças extensas ou criação de módulos, gere o conteúdo completo com write_file.
- Pesquisa externa:
  - Use Firecrawl para buscar/scrapear e Perplexity para consolidar/avaliar conteúdo e verificar depreciações.
- Planejamento:
  - Use Software-planning MCP para organizar backlog de melhorias (ex.: parametrização de Scanner/Signal/Risk).
- Conhecimento persistente:
  - Use Memory MCP para registrar decisões arquiteturais e sua evolução.
