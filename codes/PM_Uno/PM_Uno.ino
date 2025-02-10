#include <SPI.h>
#include <MFRC522.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <Servo.h>

#define RST_PIN 9
#define SS_PIN 10
#define SERVO_PIN 3
#define TIME_SERVO 5000 // время открытия/закрытия

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522 rfid(SS_PIN, RST_PIN);   // Объект rfid модуля
MFRC522::MIFARE_Key key;         // Объект ключа
MFRC522::StatusCode status;      // Объект статуса

LiquidCrystal_I2C lcd(0x27, 16, 2); // Адрес LCD 0x27, размер 16x2
Servo gateServo; // сервопривод

void setup() {
  Serial.begin(9600);
  //Serial.println("Start!");
  lcd.init(); // Инициализируем экран
  lcd.clear();
  lcd.backlight();
  lcd.print("Scan RFID card");
  SPI.begin();
  mfrc522.PCD_Init();
  rfid.PCD_SetAntennaGain(rfid.RxGain_max);  // Установка усиления антенны
  rfid.PCD_AntennaOff();           // Перезагружаем антенну
  rfid.PCD_AntennaOn();            // Включаем антенну

  for (byte i = 0; i < 6; i++) { // Наполняем ключ
    key.keyByte[i] = 0xFF;       // Ключ по умолчанию 0xFFFFFFFFFFFF
  }

 gateServo.attach(SERVO_PIN);
 gateServo.write(90); // 90 - для останова
 
}

void loop() {
  static uint32_t rebootTimer = millis(); //  против зависания модуля!
  if (millis() - rebootTimer >= 3000) {   // Таймер с периодом 1000 мс
    rebootTimer = millis();               // Обновляем таймер
    digitalWrite(RST_PIN, HIGH);          // Сбрасываем модуль
    delayMicroseconds(2);                 // Ждем 2 мкс
    digitalWrite(RST_PIN, LOW);           // Отпускаем сброс
    rfid.PCD_Init();                      // Инициализируем заного
  }
  
  
  if (mfrc522.PICC_IsNewCardPresent() && mfrc522.PICC_ReadCardSerial()) {
    String uid = "";
    for (byte i = 0; i < mfrc522.uid.size; i++) {
      uid += String(mfrc522.uid.uidByte[i] < 0x10 ? "0" : "");
      uid += String(mfrc522.uid.uidByte[i], HEX);
    }
    lcd.clear();
    lcd.print("Checking...");
    Serial.println(uid); // Отправка UID на микрокомпьютер

    // Ожидание ответа от микрокомпьютера
    while (!Serial.available());
    String response = Serial.readStringUntil('\n');
    response.trim();

    if (response == "GRANT") {
      lcd.clear();
      lcd.print("Access GRANTED");
      gateServo.write(0); // Открыть ворота; 0 - для серв 360
      delay(TIME_SERVO); // Задержка для открытия
      delay(3000); // задержка на проезд машины
      gateServo.write(180); // Закрыть ворота; 180 - в обратную строну для сервы 360
      delay(TIME_SERVO); // Задержка для закрытия
    } else if (response == "DENY") {
      lcd.clear();
      lcd.print("Access DENIED");
      delay(5000); // Задержка для вывода
    } else if (response == "FAULT"){
      lcd.clear();
      lcd.print("Access Expired!"); // доступ просрочен
      delay(5000); // Задержка для вывода
    }
    // delay(1000);
    lcd.clear();
    lcd.print("Scan RFID card");
    //mfrc522.PICC_HaltA();
  }
}
