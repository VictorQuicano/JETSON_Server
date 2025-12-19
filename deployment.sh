#!/bin/bash
# deployment.sh
# Script para desplegar el servidor FastAPI

set -e  # Salir en caso de error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
IMAGE_NAME="robot-sensor-api"
CONTAINER_NAME="robot-sensor-server"
PORT="8000"
DB_VOLUME="robot-sensor-data"

echo -e "${GREEN}🚀 Iniciando despliegue del Robot Sensor API${NC}"

# Función para limpiar recursos antiguos
cleanup() {
    echo -e "${YELLOW}🔄 Limpiando recursos anteriores...${NC}"
    
    # Detener y eliminar contenedor si existe
    if docker ps -a --filter "name=$CONTAINER_NAME" | grep -q $CONTAINER_NAME; then
        echo -e "  Deteniendo contenedor existente..."
        docker stop $CONTAINER_NAME 2>/dev/null || true
        docker rm $CONTAINER_NAME 2>/dev/null || true
    fi
    
    # Eliminar imagen antigua si existe
    if docker images | grep -q "^$IMAGE_NAME"; then
        echo -e "  Eliminando imagen anterior..."
        docker rmi $IMAGE_NAME 2>/dev/null || true
    fi
}

# Función para construir la imagen Docker
build_image() {
    echo -e "${YELLOW}🔨 Construyendo imagen Docker...${NC}"
    
    # Verificar que tenemos los archivos necesarios
    if [ ! -f "Dockerfile" ]; then
        echo -e "${RED}❌ Error: No se encuentra Dockerfile${NC}"
        exit 1
    fi
    
    if [ ! -f "requirements.txt" ]; then
        echo -e "${RED}❌ Error: No se encuentra requirements.txt${NC}"
        exit 1
    fi
    
    if [ ! -f "main.py" ]; then
        echo -e "${RED}❌ Error: No se encuentra main.py${NC}"
        exit 1
    fi
    
    # Construir imagen
    docker build -t $IMAGE_NAME:latest .
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Imagen construida exitosamente${NC}"
    else
        echo -e "${RED}❌ Error construyendo imagen${NC}"
        exit 1
    fi
}

# Función para ejecutar el contenedor
run_container() {
    echo -e "${YELLOW}🐳 Iniciando contenedor...${NC}"
    
    # Crear volumen para persistencia si no existe
    if ! docker volume ls | grep -q $DB_VOLUME; then
        echo -e "  Creando volumen para persistencia de datos..."
        docker volume create $DB_VOLUME
    fi
    
    # Ejecutar contenedor
    docker run -d \
        --name $CONTAINER_NAME \
        --restart unless-stopped \
        -p $PORT:8000 \
        -v $DB_VOLUME:/app/data \
        -e "PYTHONUNBUFFERED=1" \
        $IMAGE_NAME:latest
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Contenedor iniciado exitosamente${NC}"
    else
        echo -e "${RED}❌ Error iniciando contenedor${NC}"
        exit 1
    fi
}

# Función para verificar el despliegue
verify_deployment() {
    echo -e "${YELLOW}🔍 Verificando despliegue...${NC}"
    
    # Esperar a que el contenedor esté listo
    echo -e "  Esperando a que el servicio esté listo..."
    sleep 5
    
    # Verificar si el contenedor está corriendo
    if docker ps --filter "name=$CONTAINER_NAME" | grep -q $CONTAINER_NAME; then
        echo -e "  ✅ Contenedor en ejecución"
    else
        echo -e "  ${RED}❌ Contenedor no está corriendo${NC}"
        docker logs $CONTAINER_NAME
        exit 1
    fi
    
    # Verificar acceso al API
    echo -e "  Probando conexión al API..."
    if curl -s -f http://localhost:$PORT/ > /dev/null; then
        echo -e "  ✅ API respondiendo correctamente"
    else
        echo -e "  ${RED}❌ No se pudo conectar al API${NC}"
        docker logs $CONTAINER_NAME
        exit 1
    fi
    
    # Mostrar logs iniciales
    echo -e "\n${YELLOW}📝 Últimas líneas del log:${NC}"
    docker logs --tail=10 $CONTAINER_NAME
}

# Función para mostrar información del despliegue
show_info() {
    echo -e "\n${GREEN}✨ Despliegue completado exitosamente!${NC}"
    echo -e "========================================="
    echo -e "${YELLOW}📊 Información del despliegue:${NC}"
    echo -e "  🌐 API URL: http://localhost:$PORT"
    echo -e "  📚 API Docs: http://localhost:$PORT/docs"
    echo -e "  📊 OpenAPI: http://localhost:$PORT/redoc"
    echo -e "  🐳 Contenedor: $CONTAINER_NAME"
    echo -e "  🖼️  Imagen: $IMAGE_NAME:latest"
    echo -e "  💾 Volumen: $DB_VOLUME"
    echo -e "\n${YELLOW}🔧 Comandos útiles:${NC}"
    echo -e "  Ver logs: docker logs -f $CONTAINER_NAME"
    echo -e "  Detener: docker stop $CONTAINER_NAME"
    echo -e "  Iniciar: docker start $CONTAINER_NAME"
    echo -e "  Reiniciar: docker restart $CONTAINER_NAME"
    echo -e "  Shell: docker exec -it $CONTAINER_NAME /bin/bash"
    echo -e "  Eliminar: docker rm -f $CONTAINER_NAME"
    echo -e "========================================="
}

# Función para realizar backup de datos
backup_data() {
    echo -e "${YELLOW}💾 Realizando backup de datos...${NC}"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="backup_${TIMESTAMP}.tar.gz"
    
    # Crear backup del volumen
    docker run --rm \
        -v $DB_VOLUME:/data \
        -v $(pwd):/backup \
        alpine tar czf /backup/$BACKUP_FILE -C /data .
    
    if [ $? -eq 0 ]; then
        echo -e "  ✅ Backup creado: $BACKUP_FILE"
        echo -e "  Tamaño: $(du -h $BACKUP_FILE | cut -f1)"
    else
        echo -e "  ${YELLOW}⚠️  No se pudo crear el backup${NC}"
    fi
}

# Menú principal
main() {
    echo -e "${GREEN}🤖 Robot Sensor API - Sistema de Despliegue${NC}"
    echo -e "================================================"
    
    # Verificar que Docker está instalado
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker no está instalado${NC}"
        echo -e "Por favor instala Docker antes de continuar:"
        echo -e "  https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    # Verificar que docker daemon está corriendo
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker daemon no está corriendo${NC}"
        echo -e "Inicia Docker Desktop o el servicio de Docker"
        exit 1
    fi
    
    # Parsear argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup)
                BACKUP_ONLY=true
                shift
                ;;
            --clean)
                CLEAN_ONLY=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Argumento desconocido: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Ejecutar acciones según argumentos
    if [ "$BACKUP_ONLY" = true ]; then
        backup_data
        exit 0
    fi
    
    if [ "$CLEAN_ONLY" = true ]; then
        cleanup
        echo -e "${GREEN}✅ Limpieza completada${NC}"
        exit 0
    fi
    
    # Flujo normal de despliegue
    echo -e "${YELLOW}⚙️  Modo: Despliegue completo${NC}"
    
    # 1. Backup (opcional)
    read -p "¿Deseas hacer backup antes de continuar? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        backup_data
    fi
    
    # 2. Limpiar
    cleanup
    
    # 3. Construir
    build_image
    
    # 4. Ejecutar
    run_container
    
    # 5. Verificar
    verify_deployment
    
    # 6. Mostrar información
    show_info
    
    echo -e "\n${GREEN}🎉 ¡Servidor listo para recibir datos del robot!${NC}"
}

# Función para mostrar ayuda
show_help() {
    echo -e "${GREEN}Uso: ./deployment.sh [OPCIONES]${NC}"
    echo -e "Despliega el Robot Sensor API en un contenedor Docker"
    echo -e ""
    echo -e "Opciones:"
    echo -e "  --backup    Solo realizar backup de datos"
    echo -e "  --clean     Solo limpiar recursos anteriores"
    echo -e "  --help, -h  Mostrar esta ayuda"
    echo -e ""
    echo -e "Ejemplos:"
    echo -e "  ./deployment.sh           # Despliegue completo"
    echo -e "  ./deployment.sh --backup  # Solo backup"
    echo -e "  ./deployment.sh --clean   # Solo limpiar"
}

# Ejecutar función principal
main "$@"