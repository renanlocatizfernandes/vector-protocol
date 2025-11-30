#!/bin/bash

# Script de Deploy para Kubernetes
# Este script aplica os manifestos na ordem correta para garantir que as dependências sejam satisfeitas.

# Obtém o diretório onde o script está localizado
SCRIPT_DIR=$(dirname "$0")

echo "🚀 Iniciando deploy no Kubernetes..."

# 1. Aplicar Configurações e Segredos (Base)
echo "📦 Aplicando ConfigMaps e Secrets..."
kubectl apply -f "$SCRIPT_DIR/api-configmap.yml"
kubectl apply -f "$SCRIPT_DIR/api-secret.yml"
kubectl apply -f "$SCRIPT_DIR/postgres-secret.yml"

# 2. Aplicar Volumes (Persistência)
echo "💾 Criando Volumes Persistentes..."
kubectl apply -f "$SCRIPT_DIR/postgres-pvc.yml"
kubectl apply -f "$SCRIPT_DIR/redis-pvc.yml"
kubectl apply -f "$SCRIPT_DIR/logs-pvc.yml" # Adicionado PVC para logs

# 3. Aplicar Serviços de Backend (Banco de Dados e Cache)
echo "🗄️  Iniciando PostgreSQL e Redis..."
kubectl apply -f "$SCRIPT_DIR/postgres-deployment.yml"
kubectl apply -f "$SCRIPT_DIR/redis-deployment.yml"

# Aguardar um pouco para os serviços de banco iniciarem (opcional, mas boa prática em scripts simples)
echo "⏳ Aguardando serviços de infraestrutura..."
sleep 5

# 4. Aplicar Aplicação Principal (API)
echo "🌐 Iniciando API do Trading Bot..."
kubectl apply -f "$SCRIPT_DIR/api-deployment.yml"

# 5. Aplicar Aplicação Frontend
echo "🖥️  Iniciando Frontend da Aplicação..."
kubectl apply -f "$SCRIPT_DIR/frontend-deployment.yml"

echo "✅ Deploy concluído! Verifique o status com: kubectl get pods"
