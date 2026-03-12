# ALFRED (Pure Relay Edition)

**ALFRED Relay** is a high-performance command distribution system designed to synchronize actions between Web Dashboards and Mobile/Remote devices.

Originally an AI assistant, ALFRED has been refactored into a **Pure Relay** architecture to prioritize control speed, multi-device queueing, and professional automation without LLM overhead.

---

## 📌 Project Focus: Pure Relay

ALFRED v5.1 functions as a decentralized command gateway. It provides:
- **Device Synchronization**: Relay commands from a centralized dashboard to multiple registered mobile devices.
- **Relay Queuing**: Store commands in device-specific queues for reliable execution even with intermittent connectivity.
- **Multi-User Handshake**: Independent credential management and device registration logic.
- **Pure Data Architecture**: Built strictly with Python (Flask) and a file-based JSON database for high portability and zero heavy dependencies.

---

## 📂 Architecture

- **api/index.py**: Vercel gateway entry point.
- **FILES/backend/server.py**: Core Relay logic, authentication, and execution routing.
- **FILES/backend/db.py**: Decentralized database manager (User & Device registration).
- **FILES/backend/templates/**: Professional Web Dashboard and Login interfaces.

---

## 🚀 Transition from v4.1 to v5.1

- **LLM Removed**: All `llama_cpp` and local AI responder logic has been deleted to reduce latency and dependencies.
- **Automation Stripped**: Local system automation (Windows control) has been removed in favor of remote device execution.
- **Optimized for Relay**: The codebase is now ~80% leaner, focusing exclusively on the bridge between you and your remote hardware.

---

## 🛠️ Usage

1. Start the Relay Server:
   ```bash
   python FILES/backend/server.py
   ```
2. Access the Dashboard at `http://localhost:5000`.
3. Commands typed into the Dashboard are instantly queued for the target device (e.g., your ALFRED Mobile APK).

---

## ⚠️ Status: Pure Relay Mode
The system is currently configured for remote device control ONLY. It does not "think" or "chat"—it executes and relays.
