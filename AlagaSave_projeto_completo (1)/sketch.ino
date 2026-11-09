#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// AlagaSave - ESP32 + HC-SR04 + potenciometro (chuva simulada)
// Wi-Fi da simulacao Wokwi:
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";

// Projeto Supabase:
const char* SUPABASE_URL = "https://wkhhfvhrxglwnxgmpalw.supabase.co";
const char* SUPABASE_ANON_KEY = "sb_publishable_LXZSNUecFGkV8FzztCJH-A_dSyMn59B";

// Pinos (GPIO):
const int TRIG_PIN = 5;
const int ECHO_PIN = 23;
const int RAIN_PIN = 34;

const float ALTURA_REFERENCIA_CM = 100.0;
const unsigned long INTERVALO_ENVIO_MS = 5000;
unsigned long ultimoEnvio = 0;

float lerDistanciaCM() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(3);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  // Timeout de 30 ms evita travamento quando não há eco.
  unsigned long duracao = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duracao == 0) return ALTURA_REFERENCIA_CM;
  return (duracao * 0.0343f) / 2.0f;
}

String classificarNivel(float percentual) {
  if (percentual >= 90.0f) return "CRITICO";
  if (percentual >= 70.0f) return "ALERTA";
  if (percentual >= 30.0f) return "ATENCAO";
  return "NORMAL";
}

String classificarChuva(float percentual) {
  if (percentual >= 60.0f) return "CHUVA_FORTE";
  if (percentual >= 20.0f) return "CHUVA_MODERADA";
  return "SEM_CHUVA";
}

void conectarWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Conectando ao Wi-Fi");
  unsigned long inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 20000) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("Wi-Fi conectado. IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("Nao foi possivel conectar ao Wi-Fi.");
  }
}

void enviarSupabase(float distancia, float nivelCM, float nivelPct,
                    int chuvaADC, float chuvaPct,
                    const String& situacaoChuva, const String& statusNivel) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Sem Wi-Fi; tentando reconectar...");
    conectarWiFi();
    if (WiFi.status() != WL_CONNECTED) return;
  }

  WiFiClientSecure client;
  client.setInsecure(); // Para simulacao/prototipo Wokwi. Em producao, valide o certificado.

  HTTPClient http;
  String endpoint = String(SUPABASE_URL) + "/rest/v1/medicoes";
  if (!http.begin(client, endpoint)) {
    Serial.println("Falha ao iniciar conexao HTTP.");
    return;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("apikey", SUPABASE_ANON_KEY);
  http.addHeader("Authorization", String("Bearer ") + SUPABASE_ANON_KEY);
  http.addHeader("Prefer", "return=minimal");

  String json = "{";
  json += "\"dispositivo\":\"ESP32-AlagaSave\",";
  json += "\"distancia_cm\":" + String(distancia, 2) + ",";
  json += "\"nivel_agua_cm\":" + String(nivelCM, 2) + ",";
  json += "\"nivel_agua_percentual\":" + String(nivelPct, 2) + ",";
  json += "\"chuva_adc\":" + String(chuvaADC) + ",";
  json += "\"chuva_percentual\":" + String(chuvaPct, 2) + ",";
  json += "\"situacao_chuva\":\"" + situacaoChuva + "\",";
  json += "\"status_nivel\":\"" + statusNivel + "\"";
  json += "}";

  int codigo = http.POST(json);
  Serial.print("HTTP Supabase: ");
  Serial.println(codigo);
  if (codigo < 0) {
    Serial.print("Erro HTTP: ");
    Serial.println(http.errorToString(codigo));
  } else if (codigo == 201 || codigo == 200 || codigo == 204) {
    Serial.println("Medicao registrada no Supabase!");
  } else {
    Serial.println(http.getString());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  analogReadResolution(12);
  conectarWiFi();
}

void loop() {
  if (millis() - ultimoEnvio >= INTERVALO_ENVIO_MS || ultimoEnvio == 0) {
    ultimoEnvio = millis();

    float distancia = lerDistanciaCM();
    distancia = constrain(distancia, 0.0f, ALTURA_REFERENCIA_CM);

    float nivelCM = ALTURA_REFERENCIA_CM - distancia;
    nivelCM = constrain(nivelCM, 0.0f, ALTURA_REFERENCIA_CM);
    float nivelPct = (nivelCM / ALTURA_REFERENCIA_CM) * 100.0f;

    int chuvaADC = analogRead(RAIN_PIN);
    float chuvaPct = (chuvaADC / 4095.0f) * 100.0f;

    String statusNivel = classificarNivel(nivelPct);
    String situacaoChuva = classificarChuva(chuvaPct);

    Serial.println("\n--- ALAGASAVE ---");
    Serial.printf("Distancia: %.2f cm\n", distancia);
    Serial.printf("Nivel da agua: %.2f cm (%.1f%%)\n", nivelCM, nivelPct);
    Serial.printf("Chuva simulada: %.1f%% (ADC %d)\n", chuvaPct, chuvaADC);
    Serial.println("Status: " + statusNivel);
    Serial.println("Chuva: " + situacaoChuva);

    enviarSupabase(distancia, nivelCM, nivelPct, chuvaADC, chuvaPct,
                   situacaoChuva, statusNivel);
  }
  delay(20);
}
