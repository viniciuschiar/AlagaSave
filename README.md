# AlagaSave - arquivos de integracao Wokwi + Supabase

AlagaSave - Sistema Inteligente de Monitoramento de Enchentes

## link do wokwi

https://wokwi.com/projects/480248697531012097

## Sobre o projeto

O AlagaSave é um protótipo de monitoramento de enchentes desenvolvido com o objetivo de acompanhar o nível da água e simular a intensidade da chuva, identificando possíveis situações de risco.

O sistema utiliza um ESP32 conectado a sensores para coletar informações, processar os dados e enviá-los para um banco de dados na nuvem. Essas informações são apresentadas em um site que permite acompanhar as medições e visualizar o histórico.

## Objetivo

Desenvolver uma solução tecnológica capaz de:

Monitorar o nível da água.

Simular a intensidade da chuva.

Identificar situações de risco de alagamento.

Armazenar medições em um banco de dados.

Apresentar informações em um painel atualizado automaticamente.

Facilitar o acompanhamento das condições ambientais.

## Tecnologias utilizadas

ESP32: processamento e comunicação dos dados.

HC-SR04: sensor ultrassônico para medir a distância até a superfície da água.

Potenciômetro: simulação da intensidade da chuva.

Wokwi: ambiente de simulação do circuito eletrônico.

Arduino C++: programação do ESP32.

Supabase: armazenamento dos dados na nuvem.

HTML: estrutura do site.

CSS: estilização e organização visual.

JavaScript: comunicação com o banco de dados e atualização do painel.

**Chart.js: biblioteca utilizada para apresentar o gráfico histórico das medições.**

## Componentes e conexões

| Componente        | Pino ESP32 |
| ----------------- | ---------- |
| HC-SR04 TRIG      | GPIO 5     |
| HC-SR04 ECHO      | GPIO 23    |
| HC-SR04 VCC       | VIN        |
| HC-SR04 GND       | GND        |
| Potenciômetro SIG | GPIO 34    |
| Potenciômetro VCC | 3V3        |
| Potenciômetro GND | GND        |

## Funcionamento do sistema

O funcionamento do AlagaSave acontece em cinco etapas:

Coleta de dados: o sensor HC-SR04 mede a distância entre o sensor e a superfície da água.

Simulação de chuva: o potenciômetro representa diferentes intensidades de chuva.

Processamento: o ESP32 calcula o nível estimado da água e classifica a situação.

Armazenamento: os dados são enviados ao Supabase por meio de requisições HTTP.

Visualização: o site consulta o banco de dados e apresenta as informações em um painel.

O envio e a atualização das informações acontecem em intervalos de aproximadamente 5 segundos.

## Classificação dos níveis de risco

O sistema utiliza quatro classificações para identificar o nível da água:

| Nível da água            | Classificação |
| ------------------------ | ------------- |
| Abaixo de 30%            | NORMAL        |
| De 30% até abaixo de 70% | ATENÇÃO       |
| De 70% até abaixo de 90% | ALERTA        |
| 90% ou mais              | CRÍTICO       |

## Classificação da chuva simulada

| Percentual               | Classificação  |
| ------------------------ | -------------- |
| Abaixo de 20%            | SEM CHUVA      |
| De 20% até abaixo de 60% | CHUVA MODERADA |
| 60% ou mais              | CHUVA FORTE    |

## Painel de monitoramento

O site do AlagaSave apresenta as seguintes informações:

Nível da água em centímetros e porcentagem.

Intensidade da chuva simulada.

Distância identificada pelo sensor ultrassônico.

Classificação automática do risco.

Gráfico com o histórico das medições.

Tabela com os registros recentes.

O painel consulta o Supabase automaticamente a cada 5 segundos.

### Interface da aplicação

A aplicação foi adaptada para um layout **mobile-first**, seguindo o conceito visual Smart City, com navegação entre três páginas:

- **Estação:** painel principal com as medições da Estação 01, classificação do risco, indicadores dos sensores e histórico.
- **Mapa:** página inicial com título, reservada para a visualização geográfica.
- **Assistente:** página inicial com título, reservada para o chatbot.

O painel apresenta o **último risco registrado** no Supabase, acompanhado da data e do horário da medição.

Nesta simulação, as informações são referentes a uma única estação de monitoramento, denominada Estação 01.

## Banco de dados

O projeto utiliza o Supabase para armazenar as medições coletadas pelo ESP32.

A tabela principal utilizada é medicoes, contendo os seguintes campos:

| Campo                 | Descrição                             |
| --------------------- | ------------------------------------- |
| id                    | Identificador da medição              |
| dispositivo           | Identificação do dispositivo          |
| distancia_cm          | Distância medida pelo sensor          |
| nivel_agua_cm         | Nível estimado da água em centímetros |
| nivel_agua_percentual | Nível da água em porcentagem          |
| chuva_adc             | Valor analógico do potenciômetro      |
| chuva_percentual      | Intensidade simulada da chuva         |
| situacao_chuva        | Classificação da chuva                |
| status_nivel          | Classificação do risco                |
| data_hora             | Data e horário do registro            |

## Estrutura do projeto

```text
AlagaSave/
│
├── sketch.ino
├── diagram.json
├── libraries.txt
├── README.md
│
├── supabase/
│   └── schema.sql
│
└── site/
    ├── index.html
    ├── mapa.html
    ├── assistente.html
    ├── style.css
    ├── config.js
    └── app.js
```

### Executar a aplicação

Na pasta `site`, execute:

```bash
python3 -m http.server 8000
```

Acesse http://localhost:8000.

A conexão com o Supabase é configurada no arquivo `config.js`.

## Segurança

O projeto utiliza uma chave pública (publishable key) para realizar a comunicação com o Supabase.

As políticas de segurança RLS devem estar habilitadas e configuradas corretamente.

As permissões públicas utilizadas neste protótipo são destinadas à demonstração acadêmica. Para uma aplicação em produção, é necessário restringir as operações de leitura e inserção, validar os dados recebidos e implementar mecanismos adicionais de autenticação e segurança.

Nunca disponibilize chaves secretas ou service_role em repositórios públicos.

## Limitações do projeto

O potenciômetro representa uma simulação de chuva, não uma medição meteorológica real.

A altura de referência de 100 cm é utilizada como parâmetro demonstrativo.

O sensor ultrassônico pode apresentar variações nas medições.

O protótipo possui finalidade acadêmica e não substitui sistemas profissionais de monitoramento e alerta de enchentes.

## Melhorias futuras

Integração com sensores reais de chuva.

Monitoramento de diferentes pontos de uma região.

Envio de notificações em situações críticas.

Integração com mapas de localização.

Armazenamento de históricos de longo prazo.

Aplicação de inteligência artificial para previsão de alagamentos.

Aprimoramento da segurança e autenticação dos usuários.

## Informações acadêmicas

Projeto: AlagaSave - Sistema Inteligente de Monitoramento de Enchentes.

Instituição: FIAP.

Curso: Ciência da Computação.

Integrantes: [Inserir nomes dos integrantes].
