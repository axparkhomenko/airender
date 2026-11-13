FROM python:3.12-slim-bookworm
ARG BLENDER_VERSION=5.2.3
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV BLENDER_EXE=/opt/blender/blender
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl xz-utils \
    libx11-6 libxxf86vm1 libxfixes3 libxi6 libxrender1 libgl1 \
    libxkbcommon0 libsm6 libice6 libdbus-1-3 libfontconfig1 \
    libfreetype6 libxext6 libxrandr2 libxinerama1 libxcursor1 \
    libegl1 libwayland-client0 libdecor-0-0 libharfbuzz0b libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/blender \
    && curl -fsSL "https://download.blender.org/release/Blender5.2/blender-${BLENDER_VERSION}-linux-x64.tar.xz" \
       | tar -xJ --strip-components=1 -C /opt/blender \
    && /opt/blender/blender --background --version
WORKDIR /workspace
COPY server/requirements.txt /tmp/airender-requirements.txt
RUN pip install --no-cache-dir -r /tmp/airender-requirements.txt
EXPOSE 8000
CMD ["uvicorn", "server.airender_api:app", "--host", "0.0.0.0", "--port", "8000"]
