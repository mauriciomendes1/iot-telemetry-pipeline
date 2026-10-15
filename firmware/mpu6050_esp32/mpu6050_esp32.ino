#include <WiFi.h>
#include <PubSubClient.h>
#include <Wire.h>

// 1. Configurações de Rede (Preencha com seus dados)
const char* ssid = "SEU_WIFI";
const char* password = "SUA_SENHA";

// 2. Configurações do Broker MQTT Público
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;
const char* mqtt_topic = "teresina/oficina/giroscopio/eixos";

// Endereço de hardware do MPU6050
const int MPU_ADDR = 0x68; 

WiFiClient espClient;
PubSubClient client(espClient);

void conectar_wifi() {
  Serial.print("\nConectando ao Wi-Fi: ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) { 
    delay(500); 
    Serial.print(".");
  }
  Serial.println("\n[REDE] Wi-Fi Conectado com sucesso!");
}

void reconectar_mqtt() {
  while (!client.connected()) {
    Serial.print("[MQTT] Tentando conexao com o servidor...");
    String clientId = "ESP32_Teresina_Client_" + String(random(0, 0xffff), HEX);
    
    if (client.connect(clientId.c_str())) {
      Serial.println(" Conectado!");
    } else {
      Serial.print(" Falhou, erro rc=");
      Serial.print(client.state());
      Serial.println(" Retando em 5 segundos...");
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n--- Inicializando Hardware do Sistema ---");
  
  // Inicialização direta do barramento I2C
  Wire.begin(21, 22);
  
  // Acorda o giroscópio escrevendo no registrador de energia (PWR_MGMT_1)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); 
  Wire.write(0);    
  byte erro = Wire.endTransmission();
  
  if (erro == 0) {
    Serial.println("[SENSOR] SUCESSO: MPU6050 acordado com sucesso!");
  } else {
    Serial.println("[SENSOR] ERRO: O sensor nao respondeu.");
    while(1); 
  }

  conectar_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) {
    reconectar_mqtt();
  }
  client.loop();

   // Aponta para o primeiro registrador (Início dos dados do Acelerômetro X)
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B); 
  Wire.endTransmission(false);
  
   // Solicita os 14 bytes sequenciais que contêm: 
  // 6 bytes de Aceleração (X,Y,Z) + 2 bytes de Temperatura + 6 bytes de Giroscópio (X,Y,Z)
  Wire.requestFrom(MPU_ADDR, 14, true);
  
  if (Wire.available() >= 14) {
    // 1. Recupera e converte os dados do Acelerômetro (m/s^2)
    int16_t axRaw = (Wire.read() << 8) | Wire.read();
    int16_t ayRaw = (Wire.read() << 8) | Wire.read();
    int16_t azRaw = (Wire.read() << 8) | Wire.read();
    float acelX = (float)axRaw / 16384.0 * 9.8;
    float acelY = (float)ayRaw / 16384.0 * 9.8;
    float acelZ = (float)azRaw / 16384.0 * 9.8;

    // 2. Recupera e converte os dados do Sensor de Temperatura Interno (°C)
    int16_t tempRaw = (Wire.read() << 8) | Wire.read();
    float temperatura = ((float)tempRaw / 340.0) + 36.53;

    // 3. Recupera e converte os dados do Giroscópio (rad/s)
    int16_t gxRaw = (Wire.read() << 8) | Wire.read();
    int16_t gyRaw = (Wire.read() << 8) | Wire.read();
    int16_t gzRaw = (Wire.read() << 8) | Wire.read();
    float giroX = ((float)gxRaw / 131.0) * 0.0174532925;
    float giroY = ((float)gyRaw / 131.0) * 0.0174532925;
    float giroZ = ((float)gzRaw / 131.0) * 0.0174532925;
    
    // Print local para validação rápida na bancada
    Serial.printf("[LOCAL] AcelX: %.2f | GiroX: %.4f | Temp: %.1f°C\n", acelX, giroX, temperatura);

    // Monta o payload JSON completo com os 3 parâmetros estruturados
    String payload = "{"
                     "\"acel\":{\"x\":" + String(acelX, 2) + ",\"y\":" + String(acelY, 2) + ",\"z\":" + String(acelZ, 2) + "},"
                     "\"giro\":{\"x\":" + String(giroX, 4) + ",\"y\":" + String(giroY, 4) + ",\"z\":" + String(giroZ, 4) + "},"
                     "\"temp\":" + String(temperatura, 1) + ""
                     "}";

    // Publica o JSON completo no Broker da EMQX
    client.publish(mqtt_topic, payload.c_str());
    Serial.println("[MQTT] Dados completos enviados para o EMQX!");
  }
  
  delay(5000); // Envia telemetria a cada 5 segundos
}
