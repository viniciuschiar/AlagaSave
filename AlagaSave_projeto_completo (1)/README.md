# AlagaSave - arquivos de integracao Wokwi + Supabase

## O que esta configurado
- ESP32 conecta ao Wi-Fi `Wokwi-GUEST`.
- HC-SR04 nos GPIOs 5 (TRIG) e 23 (ECHO).
- Potenciometro no GPIO 34 para simular chuva.
- Envia uma linha para `public.medicoes` a cada 5 segundos.
- Site consulta o Supabase a cada 5 segundos e mostra indicadores, grafico e tabela.

## 1. Wokwi
1. Abra seu projeto Wokwi.
2. Substitua o conteudo de `sketch.ino` pelo arquivo deste pacote.
3. Substitua o conteudo de `diagram.json` pelo arquivo deste pacote (se quiser usar a montagem sugerida).
4. Salve e inicie a simulacao.
5. Abra o Serial Monitor em 115200 baud.

Nao precisa instalar ArduinoJson: o firmware monta o JSON diretamente e usa bibliotecas do core ESP32.

## 2. Supabase
O arquivo `supabase/schema.sql` documenta a estrutura esperada. Como voce ja executou o SQL e a tabela apareceu, nao execute novamente sem necessidade.
A URL e a publishable key estao preenchidas nos arquivos para o projeto informado. A publishable key e publica; nunca coloque uma chave `service_role` ou `secret` no navegador, Wokwi ou GitHub.

## 3. Site
1. Abra a pasta `site`.
2. Para testar localmente, abra `index.html` no navegador. Se o navegador bloquear recursos, use a extensao Live Server do VS Code.
3. O site deve mostrar "Conectado ao Supabase". Os indicadores aparecem depois que a primeira medicao for inserida.

## 4. Respostas comuns do Serial Monitor
- HTTP 201 ou 204: insercao aceita.
- HTTP 401/403: chave ou politica RLS/permissao.
- HTTP 404: confira URL, endpoint ou nome da tabela.
- HTTP negativo: problema de rede/conexao.

## 5. Limites e seguranca
Este e um prototipo academico. As politicas de exemplo permitem leitura e insercao publica para facilitar a demonstracao. Para publicar de verdade, restrinja quem pode inserir e ler, valide os dados e use autenticacao ou uma API intermediaria.
O potenciometro e apenas uma simulacao de chuva. O sensor ultrassonico e a altura de referencia tambem precisam ser calibrados para o ambiente real. Em hardware real, o pino ECHO do HC-SR04 pode fornecer 5 V; use divisor de tensao/level shifter antes do GPIO do ESP32.
