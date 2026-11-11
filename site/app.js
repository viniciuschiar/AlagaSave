const cfg = window.ALAGASAVE_CONFIG || {};
const client = window.supabase.createClient(cfg.SUPABASE_URL, cfg.SUPABASE_ANON_KEY);
let chart;

function setConnection(ok, message) {
  document.getElementById("dot").className = "dot " + (ok ? "ok" : "bad");
  document.getElementById("connection").textContent = message;
}

function fmt(value, digits=1) {
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(digits) : "--";
}

function renderChart(data) {
  const ordered = [...data].reverse();
  const labels = ordered.map(x => new Date(x.data_hora).toLocaleTimeString("pt-BR"));
  const values = ordered.map(x => Number(x.nivel_agua_percentual));
  if (chart) {
    chart.data.labels = labels;
    chart.data.datasets[0].data = values;
    chart.update();
    return;
  }

  chart = new Chart(document.getElementById("chart"), {
    type: "line",
    data: { labels, datasets: [{ label: "Nivel da agua (%)", data: values, borderColor: "#1685a5", backgroundColor: "rgba(22,133,165,.12)", fill: true, tension: .3 }] },
    options: { responsive: true, maintainAspectRatio: true, scales: { y: { min: 0, max: 100, title: { display: true, text: "%" } } }, plugins: { legend: { display: false } } }
  });
}

function renderRows(data) {
  const tbody = document.getElementById("rows");
  if (!data.length) {
    tbody.innerHTML = '<tr><td colspan="4">Nenhuma medicao encontrada. Inicie a simulacao no Wokwi.</td></tr>';
    return;
  }

  
  tbody.innerHTML = data.slice(0, 12).map(x => `
    <tr>
      <td>${new Date(x.data_hora).toLocaleString("pt-BR")}</td>
      <td>${fmt(x.nivel_agua_percentual)}%</td>
      <td>${fmt(x.chuva_percentual)}%</td>
      <td><span class="pill ${x.status_nivel}">${x.status_nivel}</span></td>
    </tr>`).join("");
}
async function atualizar() {
  try {
    const { data, error } = await client.from("medicoes")
      .select("distancia_cm,nivel_agua_cm,nivel_agua_percentual,chuva_percentual,situacao_chuva,status_nivel,data_hora")
      .order("data_hora", { ascending: false }).limit(50);
    if (error) throw error;
    setConnection(true, "Conectado ao Supabase");
    if (!data.length) return;
    const latest = data[0];
    document.getElementById("level").textContent = fmt(latest.nivel_agua_percentual) + "%";
    document.getElementById("levelcm").textContent = fmt(latest.nivel_agua_cm) + " cm de agua";
    document.getElementById("rain").textContent = fmt(latest.chuva_percentual) + "%";
    document.getElementById("rainstatus").textContent = latest.situacao_chuva || "--";
    document.getElementById("distance").textContent = fmt(latest.distancia_cm) + " cm";
    document.getElementById("status").textContent = latest.status_nivel || "--";
    document.getElementById("updated").textContent = "Atualizado: " + new Date(latest.data_hora).toLocaleTimeString("pt-BR");
    renderChart(data);
    renderRows(data);
  } catch (e) {
    console.error(e);
    setConnection(false, "Erro de conexao");
    document.getElementById("rows").innerHTML = `<tr><td colspan="4">Erro: ${String(e.message || e)}</td></tr>`;
  }
}
atualizar();
setInterval(atualizar, 5000);
