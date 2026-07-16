# Industrial Bridge

**Plataforma de integración industrial para líneas de producción**

Conecta máquinas y PLCs de planta (vía Raspberry Pi + Modbus) con sistemas de gestión como **Atlas CMMS** y **OpenMES**, sin modificar el PLC existente.

Cada instalación se configura con un archivo YAML por línea o máquina. El mismo software sirve para distintos clientes y tipos de producción.

---

## ¿En qué fase estamos?

```
[████████████████████] Fase 1 completa · Fase 2 ~60% — ~55% del proyecto total
```

| Fase | Estado | Descripción |
|------|--------|-------------|
| **1. Raspberry Agent** | 🟢 Completa | Leer PLC, detectar eventos y buffer local |
| **2. Servidor central** | 🟡 En progreso | Recibir y almacenar snapshots/eventos |
| **3. Integración OpenMES** | ⚪ Pendiente | Enviar producción y OEE al MES |
| **4. Integración Atlas CMMS** | ⚪ Pendiente | Enviar paradas y fallas al mantenimiento |
| **5. Escalar a más líneas** | ⚪ Pendiente | Solo agregar archivos YAML por máquina |

### Lo que ya funciona hoy

- [x] Estructura del proyecto definida
- [x] Driver Modbus TCP (conexión al PLC)
- [x] Modelo de datos `MachineSnapshot`
- [x] Lectura de registros, coils y strings (PLC Fatek y similares)
- [x] Configuración externa YAML por línea de producción
- [x] Generación de `MachineSnapshot` desde datos reales del PLC
- [x] Loop periódico del agente (`poll_interval_seconds`)
- [x] Detección de eventos por flanco (parada, lote, estado, PLC)
- [x] Buffer local JSONL (snapshots + eventos offline)
- [x] Publisher HTTP hacia el servidor central (opcional)
- [x] Tests unitarios de detección de eventos
- [x] Servidor central mínimo (FastAPI + SQLite)
- [x] Dashboard web de estado (`/`)
- [x] Modo simulación sin PLC (`--simulate`)
- [x] Reenvío automático del buffer cuando vuelve el servidor

### Lo que viene a continuación

- [ ] Activar `server_url` en producción (Raspberry → servidor)
- [ ] Connector OpenMES
- [ ] Connector Atlas CMMS
- [ ] Migrar SQLite → PostgreSQL/TimescaleDB en planta

---

## ¿Qué es este proyecto? (en simple)

Cada **línea de producción** puede tener una **Raspberry Pi** conectada al PLC. Esa Raspberry:

1. **Lee** contadores, estado y datos del PLC (Modbus TCP)
2. **Detecta** cambios importantes (parada, cambio de lote, etc.)
3. **Guarda** localmente y **envía** al servidor central cuando esté disponible

El servidor central almacena los datos y los conecta con MES, CMMS y dashboards.

```
┌─────────────┐     Modbus      ┌──────────────┐     REST API     ┌─────────────────┐
│     PLC     │ ◄────────────── │ Raspberry Pi │ ───────────────► │ Servidor Central │
│ (por línea) │                 │   (Agent)    │                  │                  │
└─────────────┘                 └──────────────┘                  └────────┬────────┘
                                                                            │
                                                              ┌─────────────┼─────────────┐
                                                              ▼             ▼             ▼
                                                         OpenMES      Atlas CMMS    Dashboard
```

---

## Estructura del repositorio

```
industrial-bridge/
│
├── src/
│   ├── agent/              Loop, collector, eventos, buffer
│   ├── drivers/            Modbus TCP
│   ├── models/             Snapshot y eventos
│   ├── connectors/         Publicación HTTP
│   ├── server/             API + dashboard + almacenamiento
│   └── utils/              Carga de configuración YAML
│
├── config/machines/
│   ├── example-line.yaml   Plantilla de configuración (ejemplo)
│   └── README.md           Cómo crear configs por cliente
│
├── tests/
├── logs/                   Buffer local del agente (no se sube)
└── data/                   Base SQLite del servidor (no se sube)
```

---

## Configurar una nueva línea

```bash
cp config/machines/example-line.yaml config/machines/mi-linea-local.yaml
```

Edita IP del PLC, registros Modbus y `server_url`. Los archivos `*-local.yaml` **no se suben a GitHub** (cada cliente tiene el suyo).

---

## Eventos que detecta el agente

| Evento | Cuándo se dispara |
|--------|-------------------|
| `plc_connected` / `plc_disconnected` | Cambia la conexión al PLC |
| `running_changed` | La máquina pasa de operando ↔ detenida |
| `stop_started` | Se activa parada |
| `stop_reason_set` | Llega el motivo de detención |
| `stop_ended` | Termina la parada |
| `lot_changed` | Cambia el número de lote/serie |
| `lot_finished` | Fin de lote detectado |

---

## Cómo ejecutar

```bash
git clone git@github.com:tomorecl/industrial-bridge.git
cd industrial-bridge

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Demo sin PLC
uvicorn src.server.main:app --port 8000 --reload          # terminal 1
python -m src.agent.main --simulate                       # terminal 2
# Dashboard: http://localhost:8000

# Lectura real del PLC (requiere red de planta + config YAML)
python -m src.agent.main --config config/machines/mi-linea-local.yaml --once

# Producción (loop continuo)
python -m src.agent.main --config config/machines/mi-linea-local.yaml

pytest -q
```

### Configuración del agente (`example-line.yaml`)

```yaml
agent:
  poll_interval_seconds: 1.0
  server_url: http://192.168.1.10:8000   # IP del servidor central

plc:
  ip: 192.168.1.100   # IP del PLC en la red de planta
  port: 502
  slave: 1
```

---

## Tecnologías

| Componente | Tecnología |
|------------|------------|
| Agente (Raspberry) | Python 3 |
| Comunicación PLC | Modbus TCP (`pymodbus`) |
| Configuración | YAML por línea/cliente |
| Servidor central | FastAPI + SQLite |
| Tests | `pytest` |
| Integraciones | Atlas CMMS, OpenMES |

---

## Licencia y uso

Plataforma modular pensada para integrar **líneas de producción** en distintas plantas. Cada despliegue se adapta vía configuración YAML sin modificar el código base.

**Repositorio:** https://github.com/tomorecl/industrial-bridge
