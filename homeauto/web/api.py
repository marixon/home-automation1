from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any
from homeauto.database.repository import DeviceRepository
from homeauto.database.models import Device
import os

app = FastAPI(title="Home Automation API", version="0.1.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize repository
repo = DeviceRepository()


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


@app.get("/")
async def root():
    """Serve the main dashboard page"""
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")

    if os.path.exists(html_path):
        with open(html_path, "r") as f:
            return HTMLResponse(content=f.read())

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


@app.post("/api/devices/{device_id}/control")
async def control_device(device_id: str, command: Dict[str, Any]):
    """Send control command to device"""
    device = repo.get(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # This is a placeholder - would integrate with device adapters
    return {
        "success": True,
        "device_id": device_id,
        "command": command,
        "message": "Command sent (placeholder)"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
