# test_robot_api.py
import requests
import json
import time
import random
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"
HEADERS = {"Content-Type": "application/json"}

def test_root():
    """Test endpoint raíz"""
    print("\n=== Test Endpoint Raíz ===")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_post_sensor_data():
    """Test para enviar datos de sensores"""
    print("\n=== Test POST Sensores ===")
    
    # Datos de ejemplo coherentes
    sensor_data = {
        "sample_id": random.randint(1, 1000),
        "timestamp": time.time(),
        "ir_sensor": {
            "proximity": random.randint(0, 100),  # 0-100 como en la especificación
            "remote_buttons": None,
            "beacon_distance": random.randint(10, 80) if random.random() > 0.3 else None,
            "beacon_heading": random.randint(0, 360) if random.random() > 0.3 else None
        },
        "gyro_sensor": {
            "angle": random.uniform(-180, 180),  # Ángulo entre -180 y 180 grados
            "rate": random.uniform(-50, 50),     # Tasa de giro en grados/segundo
            "calibrated": random.choice([True, False])
        },
        "robot_info": {
            "platform": "EV3",
            "python_version": "ev3dev2"
        }
    }
    
    print(f"Enviando datos de sensor (sample_id: {sensor_data['sample_id']})")
    response = requests.post(f"{BASE_URL}/sensors/", json=sensor_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.status_code == 200

def test_get_latest_sensors():
    """Test para obtener el último dato de sensores"""
    print("\n=== Test GET Últimos Sensores ===")
    response = requests.get(f"{BASE_URL}/sensors/latest")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Último sample_id: {data.get('sample_id')}")
        print(f"Timestamp: {datetime.fromtimestamp(data.get('timestamp')).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"IR Proximity: {data['ir_sensor'].get('proximity')}")
        print(f"Gyro Angle: {data['gyro_sensor'].get('angle'):.2f}°")
        return True
    elif response.status_code == 404:
        print("No hay datos de sensores aún")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_post_action():
    """Test para enviar una acción al robot"""
    print("\n=== Test POST Acción ===")
    
    # Simular diferentes tipos de movimiento
    movement_types = [
        {"name": "Avanzar", "left": 80, "right": 80},
        {"name": "Retroceder", "left": -60, "right": -60},
        {"name": "Girar derecha", "left": 50, "right": -50},
        {"name": "Girar izquierda", "left": -50, "right": 50},
        {"name": "Curva suave", "left": 70, "right": 40},
        {"name": "Detener", "left": 0, "right": 0}
    ]
    
    movement = random.choice(movement_types)
    
    action_data = {
        "left_motor": movement["left"],
        "right_motor": movement["right"],
        "source": random.choice(["api", "manual", "autonomous", "remote"])
    }
    
    print(f"Enviando acción: {movement['name']}")
    print(f"Motores: L={movement['left']}, R={movement['right']}")
    
    response = requests.post(f"{BASE_URL}/actions/", json=action_data, headers=HEADERS)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"ID Acción: {data['id']}")
        print(f"Fuente: {data['source']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_get_latest_action():
    """Test para obtener la última acción"""
    print("\n=== Test GET Última Acción ===")
    response = requests.get(f"{BASE_URL}/actions/latest")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Última acción ID: {data['id']}")
        print(f"Motores: L={data['left_motor']}, R={data['right_motor']}")
        print(f"Fuente: {data['source']}")
        print(f"Hora: {datetime.fromisoformat(data['created_at']).strftime('%H:%M:%S')}")
        return True
    elif response.status_code == 404:
        print("No hay acciones aún")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_get_actions_list():
    """Test para obtener lista de acciones"""
    print("\n=== Test GET Lista de Acciones ===")
    limit = random.randint(3, 10)
    response = requests.get(f"{BASE_URL}/actions/?limit={limit}")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        actions = response.json()
        print(f"Total acciones obtenidas: {len(actions)}")
        
        if actions:
            print("\nÚltimas acciones:")
            for i, action in enumerate(actions[:3]):  # Mostrar solo las 3 primeras
                print(f"  {i+1}. ID:{action['id']} | L:{action['left_motor']:3} R:{action['right_motor']:3} | {action['source']}")
        
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_get_action_by_id():
    """Test para obtener una acción específica por ID"""
    print("\n=== Test GET Acción por ID ===")
    
    # Primero obtenemos la lista para tener un ID válido
    response = requests.get(f"{BASE_URL}/actions/?limit=1")
    if response.status_code == 200 and response.json():
        action_id = response.json()[0]['id']
        
        print(f"Buscando acción con ID: {action_id}")
        response = requests.get(f"{BASE_URL}/actions/{action_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Encontrada acción ID: {data['id']}")
            print(f"Motores: L={data['left_motor']}, R={data['right_motor']}")
            return True
        elif response.status_code == 404:
            print("Acción no encontrada")
            return True
    else:
        print("No hay acciones para probar")
        return True
    
    return False

def test_sequential_scenario():
    """Test de escenario secuencial más realista"""
    print("\n=== Test Escenario Secuencial ===")
    print("Simulando operación del robot...")
    
    # Paso 1: Robot detecta obstáculo
    print("\n1. Robot detecta obstáculo cercano")
    sensor_data = {
        "sample_id": 100,
        "timestamp": time.time(),
        "ir_sensor": {
            "proximity": 95,  # Muy cerca!
            "remote_buttons": None,
            "beacon_distance": None,
            "beacon_heading": None
        },
        "gyro_sensor": {
            "angle": 45.5,
            "rate": 0.0,
            "calibrated": True
        },
        "robot_info": {
            "platform": "EV3",
            "python_version": "ev3dev2"
        }
    }
    
    response = requests.post(f"{BASE_URL}/sensors/", json=sensor_data, headers=HEADERS)
    print(f"  Sensor: proximity={sensor_data['ir_sensor']['proximity']}")
    
    # Paso 2: Tomar acción evasiva
    print("\n2. Tomando acción evasiva")
    action_data = {
        "left_motor": -80,
        "right_motor": 80,
        "source": "autonomous_avoidance"
    }
    response = requests.post(f"{BASE_URL}/actions/", json=action_data, headers=HEADERS)
    print(f"  Acción: Giro rápido L={action_data['left_motor']}, R={action_data['right_motor']}")
    
    # Paso 3: Nueva lectura después de girar
    time.sleep(0.5)
    print("\n3. Nueva lectura después del giro")
    sensor_data = {
        "sample_id": 101,
        "timestamp": time.time(),
        "ir_sensor": {
            "proximity": 30,  # Ya no hay obstáculo cercano
            "remote_buttons": None,
            "beacon_distance": 50,
            "beacon_heading": 120
        },
        "gyro_sensor": {
            "angle": 135.5,
            "rate": 45.2,
            "calibrated": True
        },
        "robot_info": {
            "platform": "EV3",
            "python_version": "ev3dev2"
        }
    }
    
    response = requests.post(f"{BASE_URL}/sensors/", json=sensor_data, headers=HEADERS)
    print(f"  Sensor: proximity={sensor_data['ir_sensor']['proximity']}, angle={sensor_data['gyro_sensor']['angle']:.1f}°")
    
    # Paso 4: Continuar movimiento
    print("\n4. Continuar movimiento hacia baliza")
    action_data = {
        "left_motor": 60,
        "right_motor": 60,
        "source": "autonomous_navigation"
    }
    response = requests.post(f"{BASE_URL}/actions/", json=action_data, headers=HEADERS)
    print(f"  Acción: Avanzar L={action_data['left_motor']}, R={action_data['right_motor']}")
    
    # Verificar estado final
    print("\n5. Estado final del sistema")
    sensors = requests.get(f"{BASE_URL}/sensors/latest").json()
    action = requests.get(f"{BASE_URL}/actions/latest").json()
    
    print(f"  Último sensor: sample_id={sensors.get('sample_id')}, proximity={sensors['ir_sensor'].get('proximity')}")
    print(f"  Última acción: L={action.get('left_motor')}, R={action.get('right_motor')}, source={action.get('source')}")
    
    return True

def test_batch_operations():
    """Test de operaciones por lotes"""
    print("\n=== Test Operaciones por Lotes ===")
    print("Enviando múltiples lecturas de sensores...")
    
    success_count = 0
    for i in range(5):
        sensor_data = {
            "sample_id": 200 + i,
            "timestamp": time.time() + i * 0.1,
            "ir_sensor": {
                "proximity": random.randint(20, 80),
                "remote_buttons": [random.choice(["red_up", "blue_down", None])],
                "beacon_distance": random.randint(10, 100),
                "beacon_heading": random.randint(0, 359)
            },
            "gyro_sensor": {
                "angle": random.uniform(0, 360),
                "rate": random.uniform(-10, 10),
                "calibrated": True
            },
            "robot_info": {
                "platform": "EV3",
                "python_version": "ev3dev2"
            }
        }
        
        response = requests.post(f"{BASE_URL}/sensors/", json=sensor_data, headers=HEADERS)
        if response.status_code == 200:
            success_count += 1
        
        # Pequeña pausa entre lecturas
        time.sleep(0.1)
    
    print(f"Enviadas {success_count}/5 lecturas de sensores")
    
    # Enviar algunas acciones
    print("\nEnviando múltiples acciones...")
    action_count = 0
    for i in range(3):
        action_data = {
            "left_motor": random.randint(-100, 100),
            "right_motor": random.randint(-100, 100),
            "source": f"batch_test_{i}"
        }
        
        response = requests.post(f"{BASE_URL}/actions/", json=action_data, headers=HEADERS)
        if response.status_code == 200:
            action_count += 1
        
        time.sleep(0.05)
    
    print(f"Enviadas {action_count}/3 acciones")
    return success_count > 0

def run_all_tests():
    """Ejecutar todos los tests"""
    print("=" * 60)
    print("INICIANDO TESTS DEL API DEL ROBOT")
    print("=" * 60)
    
    tests = [
        ("Root endpoint", test_root),
        ("POST sensores (aleatorio)", test_post_sensor_data),
        ("GET últimos sensores", test_get_latest_sensors),
        ("POST acción (aleatoria)", test_post_action),
        ("GET última acción", test_get_latest_action),
        ("GET lista acciones", test_get_actions_list),
        ("GET acción por ID", test_get_action_by_id),
        ("Escenario secuencial", test_sequential_scenario),
        ("Operaciones por lotes", test_batch_operations),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*40}")
            print(f"Ejecutando: {test_name}")
            print('='*40)
            
            success = test_func()
            results.append((test_name, success))
            
            if success:
                print(f"✓ {test_name}: PASS")
            else:
                print(f"✗ {test_name}: FAIL")
            
            # Pequeña pausa entre tests
            time.sleep(0.5)
            
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE TESTS")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests pasados ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n¡Todos los tests pasaron correctamente! 🎉")
    else:
        print(f"\n{total - passed} tests fallaron.")

def quick_test():
    """Test rápido para verificar funcionalidad básica"""
    print("\n=== TEST RÁPIDO ===")
    
    try:
        # Verificar que el servidor está activo
        response = requests.get(f"{BASE_URL}/", timeout=5)
        print(f"Servidor activo: {response.status_code == 200}")
        
        # Enviar un dato de sensor
        sensor_data = {
            "sample_id": 999,
            "timestamp": time.time(),
            "ir_sensor": {"proximity": 50, "remote_buttons": None, "beacon_distance": 30, "beacon_heading": 45},
            "gyro_sensor": {"angle": 90.5, "rate": 2.3, "calibrated": True},
            "robot_info": {"platform": "EV3", "python_version": "ev3dev2"}
        }
        
        response = requests.post(f"{BASE_URL}/sensors/", json=sensor_data, headers=HEADERS)
        print(f"Sensor enviado: {response.status_code == 200}")
        
        # Enviar una acción
        action_data = {"left_motor": 75, "right_motor": 75, "source": "quick_test"}
        response = requests.post(f"{BASE_URL}/actions/", json=action_data, headers=HEADERS)
        print(f"Acción enviada: {response.status_code == 200}")
        
        # Verificar datos
        sensors = requests.get(f"{BASE_URL}/sensors/latest").status_code == 200
        actions = requests.get(f"{BASE_URL}/actions/latest").status_code == 200
        
        print(f"Datos recuperados: Sensores={sensors}, Acciones={actions}")
        
        if all([sensors, actions]):
            print("\n✓ Sistema funcionando correctamente")
            return True
        else:
            print("\n✗ Algunos endpoints no responden")
            return False
            
    except requests.ConnectionError:
        print("\n✗ Error: No se puede conectar al servidor")
        print(f"  Asegúrate de que el servidor está ejecutándose en {BASE_URL}")
        return False
    except Exception as e:
        print(f"\n✗ Error inesperado: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test del API del Robot")
    parser.add_argument("--quick", action="store_true", help="Ejecutar test rápido")
    parser.add_argument("--real-scenario", action="store_true", help="Ejecutar un escenario secuencial realista")
    parser.add_argument("--url", default="http://localhost:8000", help="URL del servidor")
    
    args = parser.parse_args()
    BASE_URL = args.url
    
    print(f"Conectando a: {BASE_URL}")
    
    if args.quick:
        quick_test()
    elif args.real_scenario:
        test_sequential_scenario()
    else:
        run_all_tests()