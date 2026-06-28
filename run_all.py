import subprocess
import sys
import time

# Запускает Telegram-бота (main.py) и Discord-бота (discord_bot.py) параллельно.
# Если один падает — перезапускает его, второй продолжает работать.

PROCS = {
    "telegram": [sys.executable, "main.py"],
    "discord": [sys.executable, "discord_bot.py"],
}


def main():
    running = {}
    for name, cmd in PROCS.items():
        running[name] = subprocess.Popen(cmd)
        print(f"▶️ Запущен {name}")
    try:
        while True:
            time.sleep(5)
            for name, cmd in PROCS.items():
                p = running[name]
                if p.poll() is not None:
                    print(f"⚠️ {name} упал (код {p.returncode}), перезапуск...")
                    running[name] = subprocess.Popen(cmd)
    except KeyboardInterrupt:
        for p in running.values():
            p.terminate()


if __name__ == "__main__":
    main()
