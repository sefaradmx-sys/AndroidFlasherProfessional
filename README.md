# Android Flasher Professional

Herramienta de escritorio para Windows orientada a operaciones seguras con dispositivos Android mediante ADB y Fastboot.

## Características (v1.1.0)
- Interfaz gráfica completa (Tkinter)
- Detección automática de dispositivos ADB y Fastboot
- Información detallada del dispositivo
- Desbloqueo de bootloader con confirmación crítica (escribir serial)
- Flasheo controlado de imágenes (boot, recovery)
- Flasheo de Magisk (boot parcheado)
- Flasheo de vbmeta
- Backup y restauración de particiones
- Reinicios controlados
- Registro completo de todas las operaciones
- Advertencias de seguridad obligatorias antes de acciones destructivas

## Requisitos
- Windows 10/11
- Python 3.8+
- ADB y Fastboot en PATH o carpeta `tools/`

## Generar el .exe
```bat
pip install pyinstaller
pyinstaller --onefile --windowed --name AndroidFlasherPro android_flasher_pro.py
```

## Advertencia
Úselo únicamente en dispositivos de su propiedad. Desbloquear el bootloader borra todos los datos y puede anular la garantía.
