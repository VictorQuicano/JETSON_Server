# main.py (versión actualizada)
import time
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, Float, String, JSON, DateTime, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Configuración de base de datos SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./sensors.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo para la base de datos
class SensorData(Base):
    __tablename__ = "sensor_data"
    
    id = Column(Integer, primary_key=True, index=True)
    sample_id = Column(Integer, index=True)
    timestamp = Column(Float, index=True)
    ir_sensor = Column(JSON)
    # gyro_sensor = Column(JSON)
    robot_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ActionData(Base):
    __tablename__ = "action_data"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(Float, index=True)
    left_motor = Column(Integer)
    right_motor = Column(Integer)
    source = Column(String(50), default="api")  # 'api' o 'websocket'
    created_at = Column(DateTime, default=datetime.utcnow)

# Crear tablas
Base.metadata.create_all(bind=engine)

# Modelos Pydantic para validación
class GyroData(BaseModel):
    angle: Optional[float] = None
    rate: Optional[float] = None
    calibrated: Optional[bool] = None

class IRSensorData(BaseModel):
    proximity: Optional[int] = None
    remote_buttons: Optional[Any] = None
    beacon_distance: Optional[int] = None
    beacon_heading: Optional[int] = None

class RobotInfo(BaseModel):
    platform: str
    python_version: str

class SensorPayload(BaseModel):
    sample_id: int
    timestamp: float
    ir_sensor: IRSensorData
    # gyro_sensor: GyroData
    robot_info: RobotInfo

class ActionPayload(BaseModel):
    left_motor: int = Field(..., ge=-100, le=100)  # Valor entre -100 y 100
    right_motor: int = Field(..., ge=-100, le=100) # Valor entre -100 y 100
    source: Optional[str] = "api"  # 'api' o 'manual'

class ActionResponse(BaseModel):
    id: int
    left_motor: int
    right_motor: int
    timestamp: float
    source: str
    created_at: datetime

# Dependencia de base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inicializar FastAPI
app = FastAPI(title="Robot Sensors API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenar últimas lecturas para WebSocket
last_sensor_data = {}
last_action = {"left_motor": 0, "right_motor": 0, "timestamp": None, "source": None}

# Manejo de conexiones WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_dashboard_connections: list[WebSocket] = []
        self.active_robot_connections: list[WebSocket] = []
        
    async def connect_dashboard(self, websocket: WebSocket):
        await websocket.accept()
        self.active_dashboard_connections.append(websocket)
        
    async def connect_robot(self, websocket: WebSocket):
        await websocket.accept()
        self.active_robot_connections.append(websocket)
        
    def disconnect_dashboard(self, websocket: WebSocket):
        if websocket in self.active_dashboard_connections:
            self.active_dashboard_connections.remove(websocket)
            
    def disconnect_robot(self, websocket: WebSocket):
        if websocket in self.active_robot_connections:
            self.active_robot_connections.remove(websocket)
            
    async def broadcast_sensor_data(self, data: dict):
        """Enviar datos de sensores a todos los dashboards conectados"""
        for connection in self.active_dashboard_connections:
            try:
                await connection.send_json(data)
            except:
                self.disconnect_dashboard(connection)
                
    async def send_action_to_robot(self, data: dict):
        """Enviar acción a todos los robots conectados"""
        for connection in self.active_robot_connections:
            try:
                await connection.send_json(data)
            except:
                self.disconnect_robot(connection)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {
        "message": "Robot Sensors API",
        "endpoints": {
            "POST /sensors": "Guardar datos de sensores",
            "GET /sensors/latest": "Obtener último registro de sensores",
            "POST /actions": "Enviar acción al robot",
            "GET /actions": "Obtener todas las acciones (opcional: ?limit=N)",
            "GET /actions/latest": "Obtener última acción",
            "WebSocket /ws/dashboard": "WebSocket para dashboard",
            "WebSocket /ws/robot": "WebSocket para robot"
        }
    }

@app.post("/sensors/")
async def store_sensor_data(payload: SensorPayload, db: Session = Depends(get_db)):
    """Endpoint para almacenar datos de sensores en SQLite"""
    try:
        # Convertir modelos Pydantic a dict para almacenar en JSON
        sensor_data = SensorData(
            sample_id=payload.sample_id,
            timestamp=payload.timestamp,
            ir_sensor=payload.ir_sensor.dict(),
            # gyro_sensor=payload.gyro_sensor.dict(),
            robot_info=payload.robot_info.dict()
        )
        
        db.add(sensor_data)
        db.commit()
        db.refresh(sensor_data)
        
        # Actualizar último dato para WebSocket
        last_sensor_data.update({
            "sample_id": payload.sample_id,
            "timestamp": payload.timestamp,
            "ir_sensor": payload.ir_sensor.dict(),
            # "gyro_sensor": payload.gyro_sensor.dict(),
            "robot_info": payload.robot_info.dict(),
            "db_id": sensor_data.id,
            "created_at": datetime.utcnow().isoformat()
        })
        
        # Enviar a dashboards conectados
        await manager.broadcast_sensor_data(last_sensor_data)
        
        return {
            "message": "Sensor data stored successfully",
            "id": sensor_data.id,
            "sample_id": sensor_data.sample_id
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error storing sensor data: {str(e)}")

@app.get("/sensors/latest")
async def get_latest_sensor_data(db: Session = Depends(get_db)):
    """Obtener el último registro de sensores"""
    if not last_sensor_data:
        latest = db.query(SensorData).order_by(SensorData.timestamp.desc()).first()
        if latest:
            last_sensor_data.update({
                "sample_id": latest.sample_id,
                "timestamp": latest.timestamp,
                "ir_sensor": latest.ir_sensor,
                # "gyro_sensor": latest.gyro_sensor,
                "robot_info": latest.robot_info,
                "db_id": latest.id,
                "created_at": latest.created_at.isoformat()
            })
    
    if not last_sensor_data:
        raise HTTPException(status_code=404, detail="No sensor data available")
    
    return last_sensor_data

@app.post("/actions/", response_model=ActionResponse)
async def create_action(
    action: ActionPayload, 
    db: Session = Depends(get_db)
):
    """
    Endpoint POST para enviar una acción al robot.
    
    Args:
        action: Datos de la acción (left_motor, right_motor, source)
    
    Returns:
        Información de la acción creada
    """
    try:
        # Validar y ajustar valores de motores
        left_motor = max(-100, min(100, action.left_motor))
        right_motor = max(-100, min(100, action.right_motor))
        
        # Crear registro en base de datos
        action_record = ActionData(
            timestamp=time.time(),
            left_motor=left_motor,
            right_motor=right_motor,
            source=action.source or "api"
        )
        
        db.add(action_record)
        db.commit()
        db.refresh(action_record)
        
        # Actualizar última acción en memoria
        last_action.update({
            "id": action_record.id,
            "left_motor": left_motor,
            "right_motor": right_motor,
            "timestamp": action_record.timestamp,
            "source": action_record.source,
            "created_at": action_record.created_at.isoformat()
        })
        
        # Enviar acción a robots conectados vía WebSocket
        await manager.send_action_to_robot({
            "action": "motor_control",
            "left_motor": left_motor,
            "right_motor": right_motor,
            "timestamp": action_record.timestamp,
            "source": action_record.source
        })
        
        # Notificar a dashboards sobre nueva acción
        await manager.broadcast_sensor_data({
            "type": "action_update",
            "action": last_action,
            "timestamp": time.time()
        })
        
        return action_record
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Error storing action: {str(e)}"
        )

@app.get("/actions/", response_model=List[ActionResponse])
async def get_actions(
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de acciones almacenadas.
    
    Args:
        limit: Número máximo de acciones a retornar (default: 100)
        offset: Número de acciones a saltar (para paginación)
    
    Returns:
        Lista de acciones ordenadas por timestamp descendente
    """
    try:
        actions = db.query(ActionData)\
            .order_by(desc(ActionData.timestamp))\
            .offset(offset)\
            .limit(limit)\
            .all()
        
        return actions
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving actions: {str(e)}"
        )

@app.get("/actions/latest", response_model=ActionResponse)
async def get_latest_action(db: Session = Depends(get_db)):
    """
    Obtener la última acción almacenada.
    
    Returns:
        Última acción registrada
    """
    try:
        # Primero intentar obtener de memoria
        if last_action.get("id"):
            # Buscar en base de datos para asegurar que tenemos el registro completo
            action_record = db.query(ActionData).filter(
                ActionData.id == last_action["id"]
            ).first()
            
            if action_record:
                return action_record
        
        # Si no hay en memoria, buscar en base de datos
        action_record = db.query(ActionData)\
            .order_by(desc(ActionData.timestamp))\
            .first()
        
        if not action_record:
            raise HTTPException(
                status_code=404, 
                detail="No actions available"
            )
        
        # Actualizar último dato en memoria
        last_action.update({
            "id": action_record.id,
            "left_motor": action_record.left_motor,
            "right_motor": action_record.right_motor,
            "timestamp": action_record.timestamp,
            "source": action_record.source,
            "created_at": action_record.created_at.isoformat()
        })
        
        return action_record
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving latest action: {str(e)}"
        )

@app.get("/actions/{action_id}", response_model=ActionResponse)
async def get_action_by_id(
    action_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener una acción específica por ID.
    
    Args:
        action_id: ID de la acción a buscar
    
    Returns:
        Información de la acción solicitada
    """
    action_record = db.query(ActionData).filter(ActionData.id == action_id).first()
    
    if not action_record:
        raise HTTPException(
            status_code=404, 
            detail=f"Action with ID {action_id} not found"
        )
    
    return action_record

@app.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """WebSocket para enviar datos en tiempo real al dashboard"""
    await manager.connect_dashboard(websocket)
    
    # Enviar datos actuales inmediatamente al conectar
    if last_sensor_data:
        try:
            await websocket.send_json({
                "type": "initial_data",
                "sensors": last_sensor_data,
                "last_action": last_action
            })
        except:
            pass
    
    try:
        while True:
            # Mantener conexión activa
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect_dashboard(websocket)

@app.websocket("/ws/robot")
async def robot_websocket(websocket: WebSocket):
    """WebSocket para recibir acciones del dashboard y enviar al robot"""
    await manager.connect_robot(websocket)
    
    try:
        while True:
            # Esperar mensajes del dashboard
            data = await websocket.receive_text()
            
            try:
                action_data = json.loads(data)
                
                # Validar datos recibidos
                if "left_motor" not in action_data or "right_motor" not in action_data:
                    await websocket.send_json({"error": "Invalid action format"})
                    continue
                
                # Validar rango de motores
                left_motor = max(-100, min(100, action_data["left_motor"]))
                right_motor = max(-100, min(100, action_data["right_motor"]))
                
                # Almacenar en base de datos usando el endpoint POST
                db = SessionLocal()
                try:
                    action_record = ActionData(
                        timestamp=time.time(),
                        left_motor=left_motor,
                        right_motor=right_motor,
                        source="websocket"
                    )
                    db.add(action_record)
                    db.commit()
                    db.refresh(action_record)
                    
                    # Actualizar última acción
                    last_action.update({
                        "id": action_record.id,
                        "left_motor": left_motor,
                        "right_motor": right_motor,
                        "timestamp": action_record.timestamp,
                        "source": action_record.source,
                        "created_at": action_record.created_at.isoformat()
                    })
                    
                    # Enviar confirmación
                    await websocket.send_json({
                        "status": "action_received",
                        "left_motor": left_motor,
                        "right_motor": right_motor,
                        "timestamp": action_record.timestamp,
                        "id": action_record.id
                    })
                    
                    # Notificar a dashboards sobre nueva acción
                    await manager.broadcast_sensor_data({
                        "type": "action_update",
                        "action": last_action,
                        "timestamp": time.time()
                    })
                    
                except Exception as e:
                    db.rollback()
                    await websocket.send_json({"error": f"Database error: {str(e)}"})
                finally:
                    db.close()
                    
            except json.JSONDecodeError:
                await websocket.send_json({"error": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                
    except WebSocketDisconnect:
        manager.disconnect_robot(websocket)

# Tarea de fondo para mantener datos actualizados
@app.on_event("startup")
async def startup_event():
    """Inicializar datos al arrancar el servidor"""
    db = SessionLocal()
    try:
        # Cargar último dato de sensores al iniciar
        latest_sensor = db.query(SensorData).order_by(desc(SensorData.timestamp)).first()
        if latest_sensor:
            last_sensor_data.update({
                "sample_id": latest_sensor.sample_id,
                "timestamp": latest_sensor.timestamp,
                "ir_sensor": latest_sensor.ir_sensor,
                # "gyro_sensor": latest_sensor.gyro_sensor,
                "robot_info": latest_sensor.robot_info,
                "db_id": latest_sensor.id,
                "created_at": latest_sensor.created_at.isoformat()
            })
        
        # Cargar última acción al iniciar
        latest_action = db.query(ActionData).order_by(desc(ActionData.timestamp)).first()
        if latest_action:
            last_action.update({
                "id": latest_action.id,
                "left_motor": latest_action.left_motor,
                "right_motor": latest_action.right_motor,
                "timestamp": latest_action.timestamp,
                "source": latest_action.source,
                "created_at": latest_action.created_at.isoformat()
            })
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)