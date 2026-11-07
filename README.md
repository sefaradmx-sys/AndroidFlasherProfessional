# Android Flasher Professional

Herramienta de escritorio completa para Windows orientada a operaciones seguras con dispositivos Android mediante ADB y Fastboot.

## Características
- Interfaz gráfica (Tkinter)
- Detección automática de dispositivos en modo ADB y Fastboot
- Información del dispositivo
- Desbloqueo de bootloader con confirmación crítica (escribir serial)
- Flasheo de particiones (boot, recovery, etc.)
- Flasheo de vbmeta con disable-verity
- Reinicios controlados
- Registro completo de operaciones
- Advertencias de seguridad obligatorias

## Requisitos
- Windows 10/11
- Python 3.8+
- ADB y Fastboot en PATH o carpeta tools/

## Generar .exe
```bat
pip install pyinstaller
pyinstaller --onefile --windowed --name AndroidFlasherPro android_flasher_pro.py
```

## Advertencia
Úselo solo en dispositivos de su propiedad. Desbloquear bootloader borra todos los datos y puede anular la garantía.
