import threading
import sqlite3
import json
from datetime import datetime
import flet as ft
import paho.mqtt.client as mqtt

# =====================================================================
# CONFIGURAÇÕES DE REDE (IDÊNTICAS ÀS DO ESP32)
# =====================================================================
BROKER_MQTT = "broker.emqx.io"
PORTA_MQTT = 1883
TOPICO_MQTT = "teresina/oficina/giroscopio/eixos"

# =====================================================================
# 1. PERSISTÊNCIA: INICIALIZAÇÃO DO BANCO DE DADOS
# =====================================================================
def inicializar_banco_dados():
    conexao = sqlite3.connect("telemetria.db", check_same_thread=False)
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetria_completa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            acel_x REAL, acel_y REAL, acel_z REAL,
            giro_x REAL, giro_y REAL, giro_z REAL,
            temperatura REAL
        )
    """)
    conexao.commit()
    conexao.close()

# =====================================================================
# INTERFACE GRÁFICA INTERATIVA (FLET APP)
# =====================================================================
def main(page: ft.Page):
    # Configurações básicas da janela/tela do aplicativo
    page.title = "Dashboard de Telemetria IoT"
    page.theme_mode = ft.ThemeMode.DARK # Ativa o modo escuro nativo
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.padding = 20

    # Inicializa o banco de dados
    inicializar_banco_dados()

    # === ELEMENTOS VISUAIS DA TELA ===
    # Título e Status de Conexão
    txt_titulo = ft.Text("TELEMETRIA EM TEMPO REAL", size=24, weight=ft.FontWeight.BOLD)
    txt_status_mqtt = ft.Text("Aguardando conexão com o Broker...", color=ft.Colors.ORANGE)

    # Textos internos dos cartões de dados
    txt_acel = ft.Text("X: 0.00 | Y: 0.00 | Z: 0.00", size=18)
    txt_giro = ft.Text("X: 0.0000 | Y: 0.0000 | Z: 0.0000", size=18)
    txt_temp = ft.Text("0.0 °C", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_ACCENT)
    txt_ultimo_envio = ft.Text("Nenhum dado recebido ainda.", size=12, italic=True)

    # Construção dos Cartões de Exibição (Design Material)
    card_acel = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.SPEED), title=ft.Text("Acelerômetro (m/s²)")),
                ft.Container(content=txt_acel, padding=ft.Padding.only(left=20, bottom=20))
            ]), width=350
        )
    )

    card_giro = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.SCREEN_ROTATION), title=ft.Text("Giroscópio (rad/s)")),
                ft.Container(content=txt_giro, padding=ft.Padding.only(left=20, bottom=20))
            ]), width=350
        )
    )

    card_temp = ft.Card(
        content=ft.Container(
            content=ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.THERMOSTAT), title=ft.Text("Temperatura Interna")),
                ft.Container(content=txt_temp, padding=ft.Padding.only(left=20, bottom=20))
            ]), width=350
        )
    )

    # Adiciona os elementos criados no layout estruturado da página
    page.add(
        ft.Row([txt_titulo], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([txt_status_mqtt], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(),
        ft.ResponsiveRow([
            ft.Column(controls=[card_acel], col={"sm": 12, "md": 4}),
            ft.Column(controls=[card_giro], col={"sm": 12, "md": 4}),
            ft.Column(controls=[card_temp], col={"sm": 12, "md": 4}),
        ]),
        ft.Divider(),
        ft.Row([txt_ultimo_envio], alignment=ft.MainAxisAlignment.CENTER)
    )

    # =====================================================================
    # LÓGICA DE RECONHECIMENTO DE REDE (MQTT CALLBACKS DENTRO DO APP)
    # =====================================================================
    def ao_conectar(client, userdata, flags, rc):
        if rc == 0:
            txt_status_mqtt.value = "🟢 CONECTADO AO BROKER EMQX"
            txt_status_mqtt.color = ft.Colors.GREEN
            client.subscribe(TOPICO_MQTT)
        else:
            txt_status_mqtt.value = f"🔴 Erro de Conexão MQTT (rc={rc})"
            txt_status_mqtt.color = ft.Colors.RED
        page.update() # Força a tela a se atualizar com o novo status

    def ao_receber_mensagem(client, userdata, msg):
        try:
            # 1. Decodifica o pacote e extrai o JSON aninhado
            payload_texto = msg.payload.decode("utf-8")
            dados = json.loads(payload_texto)

            # Descasca as caixas do dicionário Python
            ax, ay, az = dados["acel"]["x"], dados["acel"]["y"], dados["acel"]["z"]
            gx, gy, gz = dados["giro"]["x"], dados["giro"]["y"], dados["giro"]["z"]
            temperatura = dados["temp"]

            horario_atual = datetime.now().strftime("%H:%M:%S")

            # 2. PERSISTÊNCIA LOCAL: Grava os dados estruturados no SQLite
            conexao = sqlite3.connect("telemetria.db", check_same_thread=False)
            cursor = conexao.cursor()
            cursor.execute("""
                INSERT INTO telemetria_completa (timestamp, acel_x, acel_y, acel_z, giro_x, giro_y, giro_z, temperatura)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ax, ay, az, gx, gy, gz, temperatura))
            conexao.commit()
            conexao.close()

            # 3. REATIVIDADE: Atualiza os textos dos cartões visuais em tempo real
            txt_acel.value = f"X: {ax:.2f} | Y: {ay:.2f} | Z: {az:.2f}"
            txt_giro.value = f"X: {gx:.4f} | Y: {gy:.4f} | Z: {gz:.4f}"
            txt_temp.value = f"{temperatura:.1f} °C"
            txt_ultimo_envio.value = f"Última atualização recebida às: {horario_atual}"

        except Exception as e:
            txt_ultimo_envio.value = f"Erro ao processar pacote: {str(e)}"
        
        page.update() # Atualiza dinamicamente a tela para o usuário (Android, PC ou Web)

    # INICIALIZAÇÃO DO CLIENTE MQTT EM SEGUNDO PLANO
    def iniciar_thread_mqtt():
        cliente_mqtt = mqtt.Client()
        cliente_mqtt.on_connect = ao_conectar
        cliente_mqtt.on_message = ao_receber_mensagem
        cliente_mqtt.connect(BROKER_MQTT, PORTA_MQTT, 60)
        cliente_mqtt.loop_forever()

    # Dispara o MQTT dentro de uma Thread isolada para não travar o desenho da interface
    thread = threading.Thread(target=iniciar_thread_mqtt, daemon=True)
    thread.start()

# Executa o aplicativo Flet
if __name__ == "__main__":
    import os
    # O Render fornece a porta dinamicamente através da variável de ambiente 'PORT'
    porta = int(os.environ.get("PORT", 8000))

    # Força o Flet a rodar como um servidor web na porta correta
    ft.app(target=main, view=ft.AppView.WEB_BROWSER, port=porta, host="0.0.0.0")
