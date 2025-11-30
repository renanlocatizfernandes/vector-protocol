# Implantação do Crypto Trading Bot no Kubernetes (Produção)

Este diretório contém os manifestos Kubernetes otimizados para implantar a aplicação em um ambiente de produção.

## Estrutura dos Arquivos

A configuração foi separada em arquivos individuais para melhor gerenciamento e manutenção:

*   **Secrets:** Armazenam credenciais sensíveis.
    *   `postgres-secret.yml`: Credenciais do banco de dados.
    *   `api-secret.yml`: Chaves de API da Binance e Telegram.
*   **ConfigMaps:** Armazenam configurações não sensíveis.
    *   `api-configmap.yml`: Variáveis de ambiente da aplicação.
*   **PersistentVolumeClaims (PVC):** Solicitam armazenamento persistente.
    *   `postgres-pvc.yml`: Dados do PostgreSQL.
    *   `redis-pvc.yml`: Dados do Redis.
*   **Deployments & Services:** Definem a aplicação e como acessá-la.
    *   `postgres-deployment.yml`: Banco de dados PostgreSQL.
    *   `redis-deployment.yml`: Cache Redis.
    *   `api-deployment.yml`: API do Trading Bot.

## Otimizações de Produção

Os deployments foram configurados com:
*   **Resource Limits:** Limites de CPU e memória para evitar que um container consuma todos os recursos do nó.
*   **Liveness Probes:** Verificações automáticas para reiniciar containers travados.
*   **Readiness Probes:** Garante que o tráfego só seja enviado para containers prontos para receber requisições.
*   **Rolling Updates:** Estratégia de atualização para a API sem tempo de inatividade (Zero Downtime).

## Pré-requisitos

- Um cluster Kubernetes em execução.
- `kubectl` configurado para se comunicar com o cluster.
- Uma imagem Docker da API (`crypto-trading-bot-api:latest`) disponível em um registro que o seu cluster possa acessar.

## Passos para Implantação

1.  **Construir e Enviar a Imagem Docker:**
    Antes de aplicar os manifestos, você precisa construir a imagem Docker da API e enviá-la para um registro de contêiner.

    ```bash
    # Construa a imagem a partir do diretório raiz do projeto
    docker build -t SEU_REGISTRO/crypto-trading-bot-api:latest -f backend/Dockerfile .

    # Envie a imagem para o seu registro
    docker push SEU_REGISTRO/crypto-trading-bot-api:latest
    ```

    **Importante:** Atualize a imagem no arquivo `kubernetes/api-deployment.yml` para usar o nome do seu registro (`SEU_REGISTRO/crypto-trading-bot-api:latest`).

2.  **Tornar o script de deploy executável:**
    ```bash
    chmod +x kubernetes/deploy.sh
    ```

3.  **Executar o Script de Deploy:**
    Vá para o diretório `kubernetes` e execute o script para aplicar todos os manifestos na ordem correta.

    ```bash
    cd kubernetes/
    ./deploy.sh
    ```

4.  **Verificar o Status:**
    Aguarde alguns minutos e verifique se todos os pods estão em execução (`Running`).

    ```bash
    kubectl get pods
    ```

    Verifique os serviços para obter o IP externo da API (se estiver usando um provedor de nuvem com LoadBalancer):

    ```bash
    kubectl get services
    ```

    Para monitorar os logs da API:

    ```bash
    kubectl logs -f deployment/api-deployment
