# Dockerfile — backend FastAPI
# Imagem base enxuta com Python 3.12 (compatível com supabase 2.8.x)
FROM python:3.12-slim

# Metadados
LABEL maintainer="G04 T16" \
      description="Pier Drone API — backend FastAPI"

# Variáveis de build
ARG APP_DIR=/app

# Usuário não-root para execução segura
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Criar home para o usuário de runtime (evita erros do pip ao tentar usar /nonexistent)
RUN mkdir -p /home/appuser && chown -R appuser:appgroup /home/appuser
ENV HOME=/home/appuser
# Ajusta entrada no /etc/passwd para que o usuário tenha home válido (evita /nonexistent)
RUN usermod -d /home/appuser appuser || true

WORKDIR ${APP_DIR}

# Copia dependências primeiro (camada cacheável)
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
COPY . .

# Ajusta permissões
RUN chown -R appuser:appgroup ${APP_DIR} /home/appuser
USER appuser

# Porta padrão do Uvicorn
EXPOSE 8000

# Health check nativo do Docker (usado pelo Compose e orchestrators)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Entrypoint de produção
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]