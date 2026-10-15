# Dashboard de Telemetria IoT em Tempo Real

Projeto de IoT com ESP32, sensor MPU6050 e um painel em Python/Flet. O firmware coleta dados de movimento, publica as leituras em JSON via MQTT e o backend recebe, persiste e exibe os dados em tempo real.

## Arquitetura

1. **Hardware:** o ESP32 lê os registradores do MPU6050 por I2C.
2. **Mensageria:** os dados são enviados por Wi-Fi ao broker MQTT público EMQX (`broker.emqx.io`).
3. **Backend:** o aplicativo Python assina o tópico MQTT, interpreta o JSON e grava os registros em SQLite.
4. **Interface:** o painel Flet atualiza os valores de aceleração, rotação e temperatura conforme as mensagens chegam.

O broker desacopla o firmware do backend. O banco é local e criado automaticamente no diretório de execução; ele não é incluído no Git.

## Estrutura

```text
.
├── backend/
│   ├── .vscode/
│   │   └── settings.json
│   └── main.py
├── firmware/
│   └── mpu6050_esp32/
│       └── mpu6050_esp32.ino
├── .gitignore
└── README.md
```

## Tecnologias

- **Firmware:** ESP32, Arduino C++, `Wire.h` e `PubSubClient.h`.
- **Sensor:** MPU6050 via I2C, no endereço `0x68`.
- **Mensageria:** MQTT com o broker público EMQX.
- **Backend e interface:** Python, Flet e Paho MQTT.
- **Persistência:** SQLite3.

## Implementação do firmware

O firmware acorda o MPU6050 escrevendo no registrador `0x6B` e lê 14 bytes a partir do registrador `0x3B`: aceleração nos eixos X/Y/Z, temperatura interna e rotação nos eixos X/Y/Z. As leituras são convertidas e publicadas no tópico `teresina/oficina/giroscopio/eixos` neste formato:

```json
{
  "acel": {"x": 0.0, "y": 0.0, "z": 9.8},
  "giro": {"x": 0.0, "y": 0.0, "z": 0.0},
  "temp": 25.0
}
```

O envio ocorre a cada 5 segundos. O backend grava cada mensagem com um timestamp local.

## Como executar

### ESP32 e MPU6050

Conecte o sensor ao ESP32:

| MPU6050 | ESP32 |
| --- | --- |
| VCC | 3V3 |
| GND | GND |
| SDA | GPIO 21 |
| SCL | GPIO 22 |

1. Abra `firmware/mpu6050_esp32/mpu6050_esp32.ino` na Arduino IDE.
2. Configure `ssid` e `password` com os dados da sua rede Wi-Fi. O repositório contém apenas placeholders; não publique suas credenciais.
3. Selecione a placa **ESP32 Dev Module** e carregue o firmware. Se a conexão travar em `Connecting...`, pressione o botão **BOOT** durante a conexão.

O firmware usa as bibliotecas `Wire` e `PubSubClient`; instale `PubSubClient` pelo gerenciador de bibliotecas da Arduino IDE, se necessário.

### Backend Python

Com Python instalado, execute na raiz do projeto:

```bash
python -m pip install flet paho-mqtt
python backend/main.py
```

O aplicativo abre o painel em um navegador. Para iniciar usando a CLI do Flet em modo web:

```bash
flet run backend/main.py --web
```

O arquivo SQLite `telemetria.db` é criado no diretório de trabalho quando o backend é iniciado. Os arquivos `.db` e o bytecode Python são ignorados pelo Git.

## Observações

- O broker configurado é público e não usa autenticação neste projeto. Não envie dados sensíveis por esse canal.
- Configure as credenciais Wi-Fi localmente no firmware antes de gravá-lo no ESP32 e mantenha-as fora de commits.
- O intervalo de publicação pode ser alterado no `delay(5000)` do firmware.

## Desenvolvedor

**Maurício Mendes de Azevedo**

Teresina - PI, Brasil

[LinkedIn](https://www.linkedin.com/in/maur%C3%ADcio-mendes-01a19a165/)