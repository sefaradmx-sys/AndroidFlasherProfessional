"""Build helper for Windows .exe"""
import subprocess
import sys

def main():
    print("Instalando PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    print("Construyendo...")
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--onefile", "--windowed", "--name", "AndroidFlasherPro", "android_flasher_pro.py"])
    print("Listo: dist/AndroidFlasherPro.exe")

if __name__ == "__main__":
    main()
