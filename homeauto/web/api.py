from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any, Optional
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device
from homeauto.config.manager import ConfigManager
from homeauto.devices.gate import HikGateDevice
from homeauto.devices.camera import CameraDevice
from homeauto.devices.tuya import TuyaDevice
import os
import asyncio
import json

app = FastAPI(title="Home Automation API", version="0.1.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize repository and config
repo = DeviceRepository()
config = ConfigManager()


def device_to_dict(device: Device) -> Dict[str, Any]:
    """Convert Device model to dictionary"""
    return {
        "id": device.id,
        "device_type": device.device_type,
        "ip_address": device.ip_address,
        "mac_address": device.mac_address,
        "name": device.name,
        "status": device.status.value,
        "manufacturer": device.manufacturer,
        "model": device.model,
        "confidence_score": device.confidence_score,
        "last_seen": device.last_seen.isoformat(),
    }


def get_device_adapter(device: Device):
    """Get appropriate device adapter for a device"""
    credentials = config.get_credentials(device.device_type) or {}

    if device.device_type == "gate":
        return HikGateDevice(device.ip_address, credentials)
    elif device.device_type == "camera":
        return CameraDevice(device.ip_address, credentials)
    elif device.device_type in ["sensor", "switch"]:
        return TuyaDevice(device.ip_address, credentials)
    else:
        return None


@app.get("/")
async def root():
    """Serve the main dashboard page"""
    # Try multiple HTML files in order of preference
    html_files = [
        os.path.join(os.path.dirname(__file__), "static", "index_clean.html"),
        os.path.join(os.path.dirname(__file__), "static", "index.html"),
    ]
    
    for html_path in html_files:
        if os.path.exists(html_path):
            try:
                # Try UTF-8 first
                with open(html_path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            except UnicodeDecodeError:
                # Fallback to latin-1
                try:
                    with open(html_path, "r", encoding="latin-1") as f:
                        return HTMLResponse(content=f.read())
                except Exception as e:
                    print(f"Error reading {html_path} with latin-1: {e}")
                    continue
            except Exception as e:
                print(f"Error reading {html_path}: {e}")
                continue
    
    # Fallback if no HTML file could be read
    return HTMLResponse(content="""
    <html>
        <head><title>Home Automation Dashboard</title></head>
        <body>
            <h1>Home Automation Dashboard</h1>
            <p>API is running. Visit <a href="/docs">/docs</a> for API documentation.</p>
        </body>
    </html>
    """)

@app.get("/api/devices", response_model=List[Dict[str, Any]])

@app.get("/api/devices", response_model=List[Dict[str, Any]])
async def get_devices():
    """Get all devices"""
    devices = repo.get_all()
    return [device_to_dict(device) for device in devices]


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str):
    """Get device by ID"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device_to_dict(device)


@app.get("/api/devices/type/{device_type}")
async def get_devices_by_type(device_type: str):
    """Get devices by type"""
    devices = repo.get_by_type(device_type)
    return [device_to_dict(device) for device in devices]


@app.get("/api/devices/{device_id}/status")
async def get_device_status(device_id: str):
    """Get detailed device status"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    adapter = get_device_adapter(device)
    if not adapter:
        raise HTTPException(status_code=400, detail="Device type not supported")

    try:
        status = adapter.get_status()
        return {
            "device_id": device_id,
            "online": adapter.test_connection(),
            "status": status,
            "info": adapter.get_info() if hasattr(adapter, "get_info") else {},
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting device status: {str(e)}"
        )


@app.post("/api/devices/{device_id}/control")
async def control_device(device_id: str, command: Dict[str, Any]):
    """Send control command to device"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    adapter = get_device_adapter(device)
    if not adapter:
        raise HTTPException(status_code=400, detail="Device type not supported")

    cmd = command.get("command", "").lower()

    try:
        if device.device_type == "gate":
            if cmd == "open":
                result = adapter.open_gate()
            elif cmd == "close":
                result = adapter.close_gate()
            elif cmd == "toggle":
                result = adapter.toggle_gate()
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unknown command for gate: {cmd}"
                )

        elif device.device_type == "switch":
            if cmd == "on":
                result = adapter.turn_on()
            elif cmd == "off":
                result = adapter.turn_off()
            elif cmd == "toggle":
                result = adapter.toggle()
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unknown command for switch: {cmd}"
                )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Device type {device.device_type} does not support control",
            )

        return {
            "success": result.get("success", False),
            "device_id": device_id,
            "command": cmd,
            "result": result,
            "message": result.get("message", "Command executed"),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error executing command: {str(e)}"
        )


@app.post("/api/gates/{device_id}/open")
async def open_gate(device_id: str):
    """Open a gate (specific endpoint for gate control)"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != "gate":
        raise HTTPException(status_code=400, detail="Device is not a gate")

    adapter = get_device_adapter(device)
    if not isinstance(adapter, HikGateDevice):
        raise HTTPException(status_code=400, detail="Gate adapter not available")

    try:
        result = adapter.open_gate()
        return {
            "success": result.get("success", False),
            "device_id": device_id,
            "command": "open",
            "message": result.get("message", "Gate open command sent"),
            "error_code": result.get("error_code", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening gate: {str(e)}")


@app.post("/api/gates/{device_id}/close")
async def close_gate(device_id: str):
    """Close a gate (specific endpoint for gate control)"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != "gate":
        raise HTTPException(status_code=400, detail="Device is not a gate")

    adapter = get_device_adapter(device)
    if not isinstance(adapter, HikGateDevice):
        raise HTTPException(status_code=400, detail="Gate adapter not available")

    try:
        result = adapter.close_gate()
        return {
            "success": result.get("success", False),
            "device_id": device_id,
            "command": "close",
            "message": result.get("message", "Gate close command sent"),
            "error_code": result.get("error_code", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error closing gate: {str(e)}")


@app.get("/api/gates/{device_id}/status")
async def get_gate_status(device_id: str):
    """Get detailed gate status"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.device_type != "gate":
        raise HTTPException(status_code=400, detail="Device is not a gate")

    adapter = get_device_adapter(device)
    if not isinstance(adapter, HikGateDevice):
        raise HTTPException(status_code=400, detail="Gate adapter not available")

    try:
        status = adapter.get_status()
        info = adapter.get_info()
        config = adapter.get_config() if hasattr(adapter, "get_config") else {}

        return {
            "device_id": device_id,
            "online": adapter.test_connection(),
            "status": status,
            "info": info,
            "config": config,
            "capabilities": [cap.value for cap in adapter.get_capabilities()],
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting gate status: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Send device updates every 5 seconds
            devices = repo.get_all()
            await websocket.send_json(
                {
                    "type": "device_update",
                    "devices": [device_to_dict(device) for device in devices],
                }
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
