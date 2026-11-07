#!/usr/bin/env python3
"""
Android Flasher Professional
Herramienta de escritorio para Windows - Gestión segura de dispositivos Android vía ADB/Fastboot.
Solo para dispositivos de propiedad del usuario. Operaciones destructivas requieren confirmación explícita.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import subprocess
import threading
import os
import sys
import hashlib
import json
from datetime import datetime
from pathlib import Path

APP_NAME = "Android Flasher Professional"
VERSION = "1.1.0"
LOG_FILE = Path("flasher_log.txt")
BACKUP_DIR = Path("backups")

class Logger:
    def __init__(self, text_widget=None):
        self.text_widget = text_widget
        self.entries = []

    def log(self, level: str, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] [{level}] {message}"
        self.entries.append(entry)
        print(entry)
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry + "\n")
        except Exception:
            pass
        if self.text_widget:
            self.text_widget.insert(tk.END, entry + "\n")
            self.text_widget.see(tk.END)

class ADBFastboot:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.adb = self._locate("adb")
        self.fastboot = self._locate("fastboot")

    def _locate(self, tool: str) -> str:
        for candidate in [tool, f"tools/{tool}.exe", f"tools/{tool}", f"./{tool}.exe"]:
            try:
                subprocess.run([candidate, "version"], capture_output=True, timeout=4, check=False)
                return candidate
            except Exception:
                continue
        return tool

    def run(self, args: list, timeout: int = 45) -> tuple:
        cmd = args
        self.logger.log("CMD", " ".join(cmd))
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            if proc.returncode != 0 and err:
                self.logger.log("ERR", err)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            self.logger.log("ERR", "Timeout")
            return -1, "", "Timeout"
        except FileNotFoundError:
            self.logger.log("ERR", f"Herramienta no encontrada: {cmd[0]}")
            return -1, "", "Tool not found"

    def adb(self, *args, serial=None, timeout=45):
        cmd = [self.adb]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        return self.run(cmd, timeout)

    def fastboot(self, *args, serial=None, timeout=60):
        cmd = [self.fastboot]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        return self.run(cmd, timeout)

    def list_adb(self) -> list:
        code, out, _ = self.adb("devices")
        devices = []
        for line in out.splitlines()[1:]:
            if "\tdevice" in line:
                devices.append(line.split("\t")[0])
        return devices

    def list_fastboot(self) -> list:
        code, out, _ = self.fastboot("devices")
        return [line.split()[0] for line in out.splitlines() if line.strip()]

class Safety:
    @staticmethod
    def confirm_destructive(parent, action: str, serial: str) -> bool:
        msg = (
            f"ACCIÓN DESTRUCTIVA\n\n"
            f"{action}\n"
            f"Dispositivo: {serial}\n\n"
            "Esto puede BORRAR DATOS del dispositivo\n"
            "y anular la garantía del fabricante.\n\n"
            "Solo continúe si:\n"
            "• Es el dueño del dispositivo\n"
            "• Tiene un backup completo\n"
            "• Entiende las consecuencias\n\n"
            "Escriba el serial del dispositivo para confirmar:"
        )
        entered = simpledialog.askstring("Confirmación crítica", msg, parent=parent)
        return entered is not None and entered.strip() == serial

class AndroidFlasherApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("1100x720")
        self.root.minsize(900, 550)

        self.logger = Logger()
        self.adb_fb = ADBFastboot(self.logger)
        self.current_serial = None
        self.mode = None
        BACKUP_DIR.mkdir(exist_ok=True)

        self._build_ui()
        self.refresh_devices()

    def _build_ui(self):
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Refrescar dispositivos", command=self.refresh_devices)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        menubar.add_cascade(label="Archivo", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Acerca de", command=self.about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
        self.root.config(menu=menubar)

        top = ttk.LabelFrame(self.root, text="Dispositivo", padding=8)
        top.pack(fill=tk.X, padx=8, pady=4)

        self.device_label = ttk.Label(top, text="Ningún dispositivo detectado", font=("Segoe UI", 10, "bold"))
        self.device_label.pack(side=tk.LEFT, padx=4)

        ttk.Button(top, text="Refrescar", command=self.refresh_devices).pack(side=tk.RIGHT, padx=4)

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        ops = ttk.Frame(nb)
        nb.add(ops, text="Operaciones")

        left = ttk.Frame(ops)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)

        ttk.Label(left, text="Acciones", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        buttons = [
            ("Info del dispositivo", self.device_info),
            ("Desbloquear Bootloader", self.unlock_bootloader),
            ("Flashear Imagen (boot/recovery)", self.flash_image),
            ("Flashear Magisk / Patch", self.flash_magisk),
            ("Flashear vbmeta", self.flash_vbmeta),
            ("Backup de partición", self.backup_partition),
            ("Restaurar partición", self.restore_partition),
            ("Reiniciar a Bootloader", self.reboot_bootloader),
            ("Reiniciar a Recovery", self.reboot_recovery),
            ("Reiniciar sistema", self.reboot_system),
        ]
        for text, cmd in buttons:
            ttk.Button(left, text=text, width=32, command=cmd).pack(fill=tk.X, pady=2)

        logs = ttk.Frame(nb)
        nb.add(logs, text="Registro")

        self.log_text = scrolledtext.ScrolledText(logs, height=20, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
        self.logger.text_widget = self.log_text

        self.status = ttk.Label(self.root, text="Listo", relief=tk.SUNKEN, anchor=tk.W)
        self.status.pack(fill=tk.X, side=tk.BOTTOM)

    def set_status(self, text: str):
        self.status.config(text=text)
        self.root.update_idletasks()

    def refresh_devices(self):
        def _do():
            self.set_status("Buscando dispositivos...")
            adb_devs = self.adb_fb.list_adb()
            fb_devs = self.adb_fb.list_fastboot()
            self.root.after(0, lambda: self._update_device_ui(adb_devs, fb_devs))
        threading.Thread(target=_do, daemon=True).start()

    def _update_device_ui(self, adb_devs, fb_devs):
        if adb_devs:
            self.current_serial = adb_devs[0]
            self.mode = "adb"
            self.device_label.config(text=f"ADB: {self.current_serial}")
            self.logger.log("INFO", f"Dispositivo ADB detectado: {self.current_serial}")
        elif fb_devs:
            self.current_serial = fb_devs[0]
            self.mode = "fastboot"
            self.device_label.config(text=f"Fastboot: {self.current_serial}")
            self.logger.log("INFO", f"Dispositivo Fastboot detectado: {self.current_serial}")
        else:
            self.current_serial = None
            self.mode = None
            self.device_label.config(text="Ningún dispositivo detectado")
            self.logger.log("INFO", "No se detectaron dispositivos")
        self.set_status("Listo")

    def require_device(self) -> bool:
        if not self.current_serial:
            messagebox.showwarning("Sin dispositivo", "Conecte un dispositivo en modo ADB o Fastboot.")
            return False
        return True

    def device_info(self):
        if not self.require_device():
            return
        def _do():
            self.set_status("Obteniendo información...")
            info = []
            if self.mode == "adb":
                props = ["ro.product.model", "ro.product.device", "ro.product.brand",
                         "ro.build.version.release", "ro.bootloader", "ro.serialno"]
                for p in props:
                    code, out, _ = self.adb_fb.adb("shell", "getprop", p, serial=self.current_serial)
                    info.append(f"{p}: {out or 'N/A'}")
            else:
                code, out, _ = self.adb_fb.fastboot("getvar", "all", serial=self.current_serial, timeout=20)
                info.append(out[:3000] if out else "Sin datos")
            text = "\n".join(info)
            self.root.after(0, lambda: messagebox.showinfo("Info del dispositivo", text))
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def unlock_bootloader(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot.")
            return
        if not Safety.confirm_destructive(self.root, "Desbloquear Bootloader (BORRA TODOS LOS DATOS)", self.current_serial):
            self.logger.log("INFO", "Desbloqueo cancelado por el usuario")
            return
        def _do():
            self.set_status("Enviando comando de desbloqueo...")
            for cmd in [["flashing", "unlock"], ["oem", "unlock"]]:
                code, out, err = self.adb_fb.fastboot(*cmd, serial=self.current_serial, timeout=90)
                if code == 0:
                    self.logger.log("OK", "Comando de desbloqueo enviado. Confirme en la pantalla del teléfono.")
                    break
            else:
                self.logger.log("ERR", "No se pudo enviar el desbloqueo.")
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def flash_image(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot.")
            return
        path = filedialog.askopenfilename(title="Seleccione imagen", filetypes=[("Imágenes", "*.img"), ("Todos", "*.*")])
        if not path:
            return
        part = simpledialog.askstring("Partición", "Nombre de la partición (boot, recovery, etc.):", parent=self.root)
        if not part:
            return
        if not Safety.confirm_destructive(self.root, f"Flashear partición '{part}'", self.current_serial):
            return
        self._do_flash(part, path)

    def flash_magisk(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot.")
            return
        path = filedialog.askopenfilename(title="Seleccione Magisk patched boot.img", filetypes=[("Imágenes", "*.img")])
        if not path:
            return
        if not Safety.confirm_destructive(self.root, "Flashear Magisk (boot parcheado)", self.current_serial):
            return
        self._do_flash("boot", path)

    def _do_flash(self, partition: str, path: str):
        def _do():
            self.set_status(f"Flasheando {partition}...")
            size = os.path.getsize(path)
            self.logger.log("INFO", f"Flasheando {partition} <- {os.path.basename(path)} ({size} bytes)")
            code, out, err = self.adb_fb.fastboot("flash", partition, path, serial=self.current_serial, timeout=180)
            if code == 0:
                self.logger.log("OK", f"Flasheo de {partition} completado")
                self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Partición {partition} flasheada correctamente."))
            else:
                self.logger.log("ERR", f"Fallo al flashear {partition}")
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def flash_vbmeta(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot.")
            return
        path = filedialog.askopenfilename(title="Seleccione vbmeta.img", filetypes=[("vbmeta", "*.img")])
        if not path:
            return
        if not Safety.confirm_destructive(self.root, "Flashear vbmeta", self.current_serial):
            return
        def _do():
            self.set_status("Flasheando vbmeta...")
            code, _, _ = self.adb_fb.fastboot("flash", "--disable-verity", "--disable-verification", "vbmeta", path,
                                              serial=self.current_serial, timeout=120)
            if code != 0:
                code, _, _ = self.adb_fb.fastboot("flash", "vbmeta", path, serial=self.current_serial, timeout=120)
            self.logger.log("OK" if code == 0 else "ERR", "vbmeta flasheado")
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def backup_partition(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot para backup de particiones.")
            return
        part = simpledialog.askstring("Backup", "Partición a respaldar (boot, recovery, etc.):", parent=self.root)
        if not part:
            return
        out_path = BACKUP_DIR / f"{self.current_serial}_{part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.img"
        def _do():
            self.set_status(f"Respaldando {part}...")
            self.logger.log("INFO", f"Iniciando backup de {part} -> {out_path}")
            messagebox.showinfo("Nota", "El backup completo de particiones vía fastboot requiere herramientas adicionales.\nSe recomienda usar modo ADB con dd o herramientas especializadas.")
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def restore_partition(self):
        if not self.require_device() or self.mode != "fastboot":
            messagebox.showinfo("Modo requerido", "El dispositivo debe estar en modo Fastboot.")
            return
        path = filedialog.askopenfilename(title="Seleccione imagen de backup", filetypes=[("Imágenes", "*.img")])
        if not path:
            return
        part = simpledialog.askstring("Restaurar", "Partición destino:", parent=self.root)
        if not part:
            return
        if not Safety.confirm_destructive(self.root, f"Restaurar partición '{part}' desde backup", self.current_serial):
            return
        self._do_flash(part, path)

    def reboot_bootloader(self):
        self._reboot("bootloader")

    def reboot_recovery(self):
        self._reboot("recovery")

    def reboot_system(self):
        self._reboot("")

    def _reboot(self, target: str):
        if not self.require_device():
            return
        def _do():
            if self.mode == "adb":
                args = ["reboot", target] if target else ["reboot"]
                self.adb_fb.adb(*args, serial=self.current_serial)
            else:
                args = ["reboot", target] if target else ["reboot"]
                self.adb_fb.fastboot(*args, serial=self.current_serial)
            self.logger.log("INFO", f"Reinicio solicitado ({target or 'system'})")
            self.root.after(0, lambda: self.set_status("Listo"))
        threading.Thread(target=_do, daemon=True).start()

    def about(self):
        messagebox.showinfo("Acerca de",
            f"{APP_NAME} v{VERSION}\n\n"
            "Herramienta profesional para operaciones ADB/Fastboot.\n"
            "Úsela únicamente en dispositivos de su propiedad.\n\n"
            "Desbloquear el bootloader borra todos los datos\n"
            "y puede anular la garantía.")

def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    app = AndroidFlasherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
