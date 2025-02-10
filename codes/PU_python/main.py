import pandas as pd
import serial
from datetime import datetime
import time
import argparse
from sys import platform
import logging

# настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# настройка обработчика и форматировщика для logger
handler = logging.FileHandler(f"{__name__}.log", mode='a')
formatter = logging.Formatter("%(name)s %(asctime)s %(levelname)s %(message)s")
# добавление форматировщика к обработчику
handler.setFormatter(formatter)
# добавление обработчика к логгеру
logger.addHandler(handler)

class AccessControlSystem:
    def __init__(self, simulate=False):
        self.simulate = simulate
        self.ser = None
        self.db = None
        
        # Конфигурация
        self.com_port = '/dev/ttyUSB0' if platform != 'win32' else 'COM3'
        self.baud_rate = 9600
        self.db_file = 'users_db.xlsx'

        if not self.simulate:
            self._init_serial()

        self._load_database()

    def _init_serial(self):
        """Инициализация COM-порта"""
        try:
            self.ser = serial.Serial(
                port=self.com_port,
                baudrate=self.baud_rate,
                timeout=1
            )
            time.sleep(2)
        except serial.SerialException as e:
            print(f"Ошибка инициализации порта: {str(e)}")
            logger.error(f"Ошибка инициализации порта: {str(e)}")
            exit(1)

    def _load_database(self):

        try:
            self.db = pd.read_excel(
                self.db_file, 
                engine='openpyxl',
                dtype={'UID номер карточки': str}  # Принудительно задаем тип строки
            )
            self.db['Срок окончания'] = pd.to_datetime(self.db['Срок окончания'])
            
            # Отладочный вывод первых записей
            # print("\nЗагружены записи из БД:")
            # print(self.db[['Фамилия ИО', 'UID номер карточки', 'Срок окончания']].head(3))
            # print()
            
            # Удаление пробелов в UID
            self.db['UID номер карточки'] = self.db['UID номер карточки'].str.strip()
            
        except Exception as e:
            print(f"Ошибка загрузки БД: {str(e)}")
            logger.error(f"Ошибка загрузки БД: {str(e)}")
            exit(1)


    def check_access(self, uid):
        """Проверка доступа с отправкой FAULT при истекшем сроке"""
        uid = str(uid).strip()
        print(f"\nПоиск UID: '{uid}' (тип: {type(uid)})")
        
        now = datetime.now()
        user = self.db[self.db['UID номер карточки'] == uid]
        
        if not user.empty:
            print(f"Найден пользователь: {user.iloc[0].to_dict()}")
            expiry_date = user['Срок окончания'].iloc[0]
            if now < expiry_date:
                return True, user['Фамилия ИО'].iloc[0], None
            else:
                return False, user['Фамилия ИО'].iloc[0], 'FAULT'
        return False, None, None
    

    def send_command(self, command):
        """Отправка команды на устройство"""
        if self.simulate:
            print(f"[SIM] Отправка команды: {command}")
        else:
            try:
                self.ser.write(command.encode() + b'\n')
            except Exception as e:
                print(f"Ошибка отправки команды: {str(e)}")

    def simulate_input(self):
        
        print("\nРежим симуляции активирован")
        print("Пример корректного UID из БД:", self.db['UID номер карточки'].iloc[0])
        while True:
            try:
                uid = input("\nВведите UID карты: ").strip()
                if uid.lower() == 'exit':
                    break
                
                if uid:
                    access, name, fault = self.check_access(uid)
                    
                    if access:
                        self.send_command('GRANT')
                        print(f"Доступ разрешен для: {name}")
                        logger.info(f"Доступ разрешен для: {name}")
                    else:
                        if name:
                            if fault == 'FAULT':
                                self.send_command('FAULT')
                                print(f"Доступ запрещен! Срок действия карты {name} истек")
                                logger.warning(f"Доступ запрещен! Срок действия карты {name} истек")
                            else:
                                self.send_command('DENY')
                                print(f"Доступ запрещен для: {name}")
                                logger.warning(f"Доступ запрещен для: {name}")
                        else:
                            self.send_command('DENY')
                            print("Карта не найдена в базе данных")
                            logger.warning("Карта не найдена в базе данных")    
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Ошибка: {str(e)}") 
                logger.error(f"Ошибка: {str(e)}")  

    def run(self):
        """Основной цикл работы системы"""
        if self.simulate:
            self.simulate_input()
            return

        print("Система контроля доступа запущена...")
        logger.info("Система контроля доступа запущена...")
        try:
            while True:
                if self.ser.in_waiting > 0:
                    uid = self.ser.readline().decode().strip()
                    if uid:
                        print(f"Получен UID: {uid}")
                        logger.info(f"Получен UID: {uid}")
                        access, name, fault = self.check_access(uid)
                        
                        if access:
                            self.send_command('GRANT')
                            print(f"Доступ разрешен для: {name}")
                            logger.info(f"Доступ разрешен для: {name}")
                        else:
                            if name:
                                if fault == 'FAULT':
                                    self.send_command('FAULT')
                                    print(f"Доступ запрещен! Срок действия карты {name} истек")
                                    logger.warning(f"Доступ запрещен! Срок действия карты {name} истек")    
                                else:
                                    self.send_command('DENY')
                                    print(f"Доступ запрещен для: {name}")
                                    logger.warning(f"Доступ запрещен для: {name}")
                            else:
                                self.send_command('DENY')
                                print("Карта не найдена в базе данных")
                                logger.warning("Карта не найдена в базе данных")
        except KeyboardInterrupt:
            print("\nЗавершение работы...")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Система контроля доступа')
    parser.add_argument('--simulate', action='store_true', 
                       help='Активировать режим симуляции')
    args = parser.parse_args()

    system = AccessControlSystem(simulate=args.simulate)
    system.run()