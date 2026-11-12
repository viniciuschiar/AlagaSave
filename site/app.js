"use strict";

// Conecta o aplicativo ao Supabase.
const config = window.ALAGASAVE_CONFIG || {};

// Conecta o aplicativo ao Supabase.
const client =
  window.supabase && config.SUPABASE_URL && config.SUPABASE_ANON_KEY
    ? window.supabase.createClient(
        config.SUPABASE_URL,
        config.SUPABASE_ANON_KEY,
      )
    : null;

const $ = (id) => document.getElementById(id);

let grafico = null;
let carregando = false;

// Formata os números recebidos do banco.
function formatar(valor, casas = 1) {
  if (valor === null || valor === undefined || valor === "") {
    return "--";
  }

  const numero = Number(valor);
  return Number.isFinite(numero) ? numero.toFixed(casas) : "--";
}

// Limita os percentuais entre 0 e 100.
function percentual(valor) {
  const numero = Number(valor);
  return Number.isFinite(numero) ? Math.max(0, Math.min(100, numero)) : 0;
}

// Formata a data da medição.
function dataMedicao(registro) {
  const data = new Date(registro?.data_hora);
  return Number.isNaN(data.getTime()) ? null : data;
}

// Define os textos e as cores de cada classificação de risco.
const riscos = {
  NORMAL: {
    cor: "normal",
    titulo: "Condição normal",
    descricao: "Nível dentro da faixa normal da simulação.",
  },
  ATENCAO: {
    cor: "atencao",
    titulo: "Atenção",
    descricao: "Nível de água em atenção na simulação.",
  },
  ALERTA: {
    cor: "critico",
    titulo: "Alerta",
    descricao: "Nível de água elevado na simulação.",
  },
  CRITICO: {
    cor: "critico",
    titulo: "Risco crítico",
    descricao: "Nível de água crítico na simulação.",
  },
};

const nomesRisco = {
  NORMAL: "NORMAL",
  ATENCAO: "ATENÇÃO",
  ALERTA: "ALERTA",
  CRITICO: "CRÍTICO",
};

// Atualiza o resumo principal da Estação 01.
function atualizarResumo(registro) {
  const status = String(registro?.status_nivel || "")
    .trim()
    .toUpperCase();
  const risco = riscos[status];

  $("overview").dataset.state = risco?.cor || "unknown";

  $("state-heading").textContent =
    risco?.titulo || (registro ? "Sem classificação" : "Aguardando medição");

  $("state-description").textContent =
    risco?.descricao ||
    (registro
      ? "Risco não informado no registro."
      : "Nenhuma medição disponível.");

  $("state-badge").textContent = registro
    ? nomesRisco[status] || "INDEFINIDO"
    : "SEM DADOS";

  // Atualiza o nível da água e o medidor circular.
  const nivel = registro?.nivel_agua_percentual;

  $("hero-percent").innerHTML = `${formatar(nivel, 0)}<small>%</small>`;

  $("hero-centimeters").textContent =
    `${formatar(registro?.nivel_agua_cm)} cm registrados`;

  const circunferencia = 2 * Math.PI * 59;
  const preenchimento = (percentual(nivel) / 100) * circunferencia;

  $("donut-progress").style.strokeDasharray =
    `${preenchimento} ${circunferencia}`;

  $("donut").setAttribute(
    "aria-label",
    `Nível registrado: ${formatar(nivel)} por cento`,
  );

  const data = dataMedicao(registro);

  $("last-time").textContent = data
    ? `Medição de ${data.toLocaleString("pt-BR")}`
    : "Aguardando medição";
}

// Preenche os cards com os dados dos sensores.
function atualizarSensores(registro) {
  $("water-cm").textContent = `${formatar(registro?.nivel_agua_cm)} cm`;

  $("water-pct").textContent =
    `${formatar(registro?.nivel_agua_percentual)}% da escala`;

  $("rain-pct").textContent = `${formatar(registro?.chuva_percentual)}%`;

  $("rain-type").textContent = registro?.situacao_chuva || "Sem classificação";

  $("distance").textContent = `${formatar(registro?.distancia_cm)} cm`;

  $("water-bar").style.width =
    `${percentual(registro?.nivel_agua_percentual)}%`;

  $("rain-bar").style.width = `${percentual(registro?.chuva_percentual)}%`;
}

// Cria ou atualiza o gráfico com as últimas 50 medições.
function atualizarGrafico(registros) {
  const dados = [...registros]
    .reverse()
    .filter(
      (r) =>
        dataMedicao(r) &&
        r.nivel_agua_percentual !== null &&
        r.nivel_agua_percentual !== undefined &&
        r.nivel_agua_percentual !== "" &&
        Number.isFinite(Number(r.nivel_agua_percentual)),
    );

  $("chart-placeholder").hidden = dados.length > 0 && !!window.Chart;

  if (!dados.length || !window.Chart) {
    if (grafico) {
      grafico.destroy();
      grafico = null;
    }
    return;
  }

  // Separa horários e percentuais para montar o gráfico.
  const horarios = dados.map((r) => dataMedicao(r).toLocaleTimeString("pt-BR"));

  const niveis = dados.map((r) => Number(r.nivel_agua_percentual));

  // Atualiza o gráfico existente sem recriá-lo.
  if (grafico) {
    grafico.data.labels = horarios;
    grafico.data.datasets[0].data = niveis;
    grafico.update("none");
    return;
  }

  grafico = new Chart($("chart"), {
    type: "line",
    data: {
      labels: horarios,
      datasets: [
        {
          data: niveis,
          borderColor: "#0b9ec6",
          backgroundColor: "rgba(8,167,204,.10)",
          fill: true,
          tension: 0.38,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2.6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (item) => `Nível: ${item.parsed.y}%`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: "#8da1b0", maxTicksLimit: 5 },
        },
        y: {
          min: 0,
          max: 100,
          grid: { color: "#e9eff4" },
          ticks: {
            color: "#8da1b0",
            callback: (valor) => `${valor}%`,
          },
        },
      },
    },
  });
}

// Percorre as medições e preenche a tabela com os 12 registros mais recentes.
function atualizarTabela(registros) {
  const tabela = $("rows");
  tabela.replaceChildren();

  if (!registros.length) {
    const linha = tabela.insertRow();
    const celula = linha.insertCell();

    celula.colSpan = 4;
    celula.textContent = "Nenhuma medição disponível.";
    return;
  }

  registros.slice(0, 12).forEach((registro) => {
    const linha = tabela.insertRow();
    const data = dataMedicao(registro);
    const status = String(registro.status_nivel || "")
      .trim()
      .toUpperCase();

    // Adiciona horário, nível da água e chuva.
    const valores = [
      data ? data.toLocaleString("pt-BR") : "--",
      `${formatar(registro.nivel_agua_percentual)}%`,
      `${formatar(registro.chuva_percentual)}%`,
    ];

    valores.forEach((valor) => {
      linha.insertCell().textContent = valor;
    });

    // Adiciona a classificação de risco com sua cor.
    const celula = linha.insertCell();
    const etiqueta = document.createElement("span");

    etiqueta.className = "pill";

    if (riscos[status]) {
      etiqueta.classList.add(status);
    }

    etiqueta.textContent = nomesRisco[status] || "INDEFINIDO";
    celula.appendChild(etiqueta);
  });
}

// Acessa a tabela "medicoes" do Supabase e busca os últimos 50 registros.
async function atualizarDashboard() {
  if (carregando) return;
  carregando = true;

  try {
    if (!client) {
      throw new Error("Supabase não configurado");
    }

    const { data, error } = await client
      .from("medicoes")

      .select(
        "distancia_cm,nivel_agua_cm,nivel_agua_percentual," +
          "chuva_percentual,situacao_chuva,status_nivel,data_hora",
      )
      .order("data_hora", { ascending: false })
      .limit(50);

    if (error) throw error;

    const registros = data || [];
    const ultimaMedicao = registros[0] || null;

    // Envia os dados do banco para cada parte do dashboard.
    atualizarResumo(ultimaMedicao);
    atualizarSensores(ultimaMedicao);
    atualizarGrafico(registros);
    atualizarTabela(registros);

    $("header-dot").className = "live-dot online";
    $("header-state").textContent = "Banco conectado";
  } catch (error) {
    console.error("Erro ao consultar Supabase:", error);

    $("header-dot").className = "live-dot offline";
    $("header-state").textContent = "Sem conexão";

    // Mantém os dados anteriores se ocorrer uma falha na consulta.
  } finally {
    carregando = false;
  }
}

// Carrega os dados ao abrir o site e atualiza a cada 5 segundos.
atualizarDashboard();
setInterval(atualizarDashboard, 5000);
