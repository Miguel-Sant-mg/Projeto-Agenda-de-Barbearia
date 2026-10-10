// Admin Panel Scripts - Barbearia Arte de Favela

function formatarMoedaBRL(valor) {
  return Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
}

document.addEventListener('DOMContentLoaded', () => {
  // 1. Modais
  const modalTriggers = document.querySelectorAll('[data-open-modal]');
  const modalCloses = document.querySelectorAll('[data-close-modal]');

  function abrirModal(modal) {
    if (!modal) return;
    modal.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function fecharModal(modal) {
    if (!modal) return;
    modal.classList.remove('active');
    const remainingOpen = document.querySelectorAll('.modal-overlay.active');
    if (remainingOpen.length === 0) {
      document.body.style.overflow = '';
    }
  }

  modalTriggers.forEach(btn => {
    btn.addEventListener('click', () => {
      const modalId = btn.getAttribute('data-open-modal');
      const modal = document.getElementById(modalId);
      abrirModal(modal);
    });
  });

  modalCloses.forEach(btn => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('.modal-overlay');
      fecharModal(modal);
    });
  });

  // Fechar ao clicar fora do modal
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        fecharModal(overlay);
      }
    });
  });

  // 2. Máscara de Telefone no painel
  const telInputs = document.querySelectorAll('.mask-phone');
  telInputs.forEach(input => {
    input.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.slice(0, 11);
      if (v.length > 10) {
        v = v.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
      } else if (v.length > 6) {
        v = v.replace(/^(\d{2})(\d{4})(\d{0,4})$/, '($1) $2-$3');
      } else if (v.length > 2) {
        v = v.replace(/^(\d{2})(\d{0,5})$/, '($1) $2');
      } else if (v.length > 0) {
        v = v.replace(/^(\d*)$/, '($1');
      }
      e.target.value = v;
    });
  });

  // 3. Gestão Completa de Faturamento e Gráficos Dinâmicos
  const canvasPrincipal = document.getElementById('chartFaturamentoPrincipal');
  const canvasServ = document.getElementById('chartServicosPizza');

  if (canvasPrincipal || document.getElementById('metricFatHoje')) {
    let chartPrincipal = null;
    let chartServicos = null;
    let modoAtual = 'dia'; // 'dia' ou 'horario'
    let periodoDias = 'ultimos7'; // 'ultimos7' ou 'proximos7'
    let filtroHorario = 'dia'; // 'dia' ou 'geral'

    function inicializarGraficoPrincipal() {
      if (!canvasPrincipal || typeof Chart === 'undefined') return;
      try {
        const ctx = canvasPrincipal.getContext('2d');
        chartPrincipal = new Chart(ctx, {
          type: 'bar',
          data: {
            labels: [],
            datasets: [{
              label: 'Faturamento (R$)',
              data: [],
              backgroundColor: 'rgba(245, 158, 11, 0.75)',
              borderColor: '#f59e0b',
              borderWidth: 2,
              borderRadius: 6,
              hoverBackgroundColor: 'rgba(245, 158, 11, 0.95)'
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            animation: {
              duration: 500,
              easing: 'easeOutQuart'
            },
            plugins: {
              legend: { display: false },
              tooltip: {
                backgroundColor: '#1e222b',
                titleColor: '#f59e0b',
                bodyColor: '#f3f4f6',
                borderColor: 'rgba(245, 158, 11, 0.3)',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                  label: function(context) {
                    const rawVal = context.raw || 0;
                    return `Faturamento: ${formatarMoedaBRL(rawVal)}`;
                  },
                  afterLabel: function(context) {
                    const idx = context.dataIndex;
                    const d = window.dadosFaturamento;
                    if (!d) return '';
                    if (modoAtual === 'dia') {
                      const list = periodoDias === 'ultimos7' ? d.grafico_7_dias : d.grafico_proximos_7_dias;
                      const item = list && list[idx];
                      return item && item.qtd !== undefined ? `Agendamentos: ${item.qtd}` : '';
                    } else {
                      const list = filtroHorario === 'dia' ? d.grafico_horarios_dia : d.grafico_horarios_geral;
                      const item = list && list[idx];
                      let info = item && item.qtd !== undefined ? `Agendamentos: ${item.qtd}` : '';
                      if (item && item.detalhes) {
                        info += `\n${item.detalhes}`;
                      }
                      return info;
                    }
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: 'rgba(255, 255, 255, 0.06)' },
                ticks: {
                  color: '#94a3b8',
                  callback: (value) => formatarMoedaBRL(value)
                }
              },
              x: {
                grid: { display: false },
                ticks: { color: '#94a3b8' }
              }
            },
            onClick: (evt, elements) => {
              if (elements && elements.length > 0 && modoAtual === 'dia') {
                const elemIndex = elements[0].index;
                const d = window.dadosFaturamento;
                const list = periodoDias === 'ultimos7' ? d.grafico_7_dias : d.grafico_proximos_7_dias;
                if (list && list[elemIndex]) {
                  const dataClicada = list[elemIndex].data;
                  const inputData = document.getElementById('inputDataFaturamento');
                  if (inputData) inputData.value = dataClicada;
                  window.filtrarPorData(dataClicada);
                }
              }
            }
          }
        });
      } catch (e) {
        console.warn('Erro ao inicializar Chart Principal:', e);
      }
    }

    function inicializarGraficoServicos() {
      if (!canvasServ || typeof Chart === 'undefined') return;
      try {
        const ctxServ = canvasServ.getContext('2d');
        chartServicos = new Chart(ctxServ, {
          type: 'doughnut',
          data: {
            labels: [],
            datasets: [{
              data: [],
              backgroundColor: [
                '#f59e0b',
                '#3b82f6',
                '#10b981',
                '#a855f7',
                '#ec4899',
                '#06b6d4',
                '#f97316'
              ],
              borderWidth: 0
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'bottom',
                labels: { color: '#94a3b8', font: { size: 11 }, padding: 10 }
              },
              tooltip: {
                callbacks: {
                  label: function(context) {
                    const val = context.raw || 0;
                    return ` ${context.label}: ${val} atendimentos`;
                  }
                }
              }
            }
          }
        });
      } catch (e) {
        console.warn('Erro ao inicializar Chart Serviços:', e);
      }
    }

    function renderizarGraficoPrincipal() {
      if (!chartPrincipal || !window.dadosFaturamento) return;
      const d = window.dadosFaturamento;
      const tituloElem = document.getElementById('tituloGraficoPrincipal');
      const subtituloElem = document.getElementById('subtituloGraficoPrincipal');

      let labels = [];
      let values = [];
      let bgColors = 'rgba(245, 158, 11, 0.75)';
      let borderColors = '#f59e0b';

      if (modoAtual === 'dia') {
        const list = periodoDias === 'ultimos7' ? (d.grafico_7_dias || []) : (d.grafico_proximos_7_dias || []);
        labels = list.map(item => item.label || item.data);
        values = list.map(item => item.valor || 0);

        if (tituloElem) {
          tituloElem.innerHTML = periodoDias === 'ultimos7' 
            ? '📈 Faturamento dos Últimos 7 Dias' 
            : '📈 Faturamento de Hoje + Próximos 7 Dias';
        }
        if (subtituloElem) {
          subtituloElem.innerText = 'Clique em qualquer barra para detalhar os horários daquele dia';
        }
      } else {
        if (filtroHorario === 'dia') {
          const list = d.grafico_horarios_dia || [];
          labels = list.map(item => item.horario + 'h');
          values = list.map(item => item.valor || 0);
          bgColors = values.map(v => v > 0 ? 'rgba(52, 211, 153, 0.85)' : 'rgba(255, 255, 255, 0.08)');
          borderColors = values.map(v => v > 0 ? '#34d399' : 'rgba(255, 255, 255, 0.15)');

          if (tituloElem) {
            tituloElem.innerHTML = `⏰ Faturamento por Horário Marcado em <strong>${d.data_selecionada}</strong>`;
          }
          if (subtituloElem) {
            const agendadosCount = list.filter(item => item.valor > 0).length;
            subtituloElem.innerText = agendadosCount === 0 
              ? 'Nenhum horário marcado com agendamento ativo nesta data.'
              : `${agendadosCount} horário(s) agendado(s) gerando receita neste dia`;
          }
        } else {
          const list = d.grafico_horarios_geral || [];
          labels = list.map(item => item.horario + 'h');
          values = list.map(item => item.valor || 0);
          bgColors = 'rgba(168, 85, 247, 0.75)';
          borderColors = '#c084fc';

          if (tituloElem) {
            tituloElem.innerHTML = '⏰ Faturamento Acumulado por Horário Marcado (Geral)';
          }
          if (subtituloElem) {
            subtituloElem.innerText = 'Distribuição total da receita pelos horários da barbearia';
          }
        }
      }

      chartPrincipal.data.labels = labels;
      chartPrincipal.data.datasets[0].data = values;
      chartPrincipal.data.datasets[0].backgroundColor = bgColors;
      chartPrincipal.data.datasets[0].borderColor = borderColors;
      chartPrincipal.update();
    }

    function renderizarGraficoServicos() {
      if (!chartServicos || !window.dadosFaturamento) return;
      const stats = window.dadosFaturamento.servicos_stats || [];
      chartServicos.data.labels = stats.map(s => s.servico_nome);
      chartServicos.data.datasets[0].data = stats.map(s => s.qtd);
      chartServicos.update();
    }

    function atualizarDOMDetalhes(d) {
      if (!d) return;

      // Atualizar cards de métricas
      const elemHoje = document.getElementById('metricFatHoje');
      if (elemHoje) elemHoje.innerText = formatarMoedaBRL(d.fat_hoje);

      const elemSemana = document.getElementById('metricFatSemana');
      if (elemSemana) elemSemana.innerText = formatarMoedaBRL(d.fat_semana);

      const elemMes = document.getElementById('metricFatMes');
      if (elemMes) elemMes.innerText = formatarMoedaBRL(d.fat_mes);

      const elemTotal = document.getElementById('metricFatTotal');
      if (elemTotal) elemTotal.innerText = formatarMoedaBRL(d.fat_total_geral);

      const lblData = document.getElementById('lblDataSelecionada');
      if (lblData) lblData.innerText = d.data_selecionada;

      const lblTotalDia = document.getElementById('lblTotalDia');
      if (lblTotalDia) lblTotalDia.innerText = formatarMoedaBRL(d.fat_dia_selecionado);

      // Atualizar tabela de agendamentos do dia selecionado
      const containerAg = document.getElementById('containerAgendamentosDia');
      if (containerAg) {
        if (d.agendamentos_dia && d.agendamentos_dia.length > 0) {
          let rowsHtml = '';
          d.agendamentos_dia.forEach(ag => {
            rowsHtml += `
              <tr>
                <td><strong style="color: var(--gold-light);">${ag.horario}</strong></td>
                <td>${ag.cliente || ag.cliente_nome || 'Cliente'}</td>
                <td>${ag.servico_nome}</td>
                <td style="color: #34d399; font-weight: 600;">${formatarMoedaBRL(ag.valor)}</td>
                <td>
                  <span class="badge-status badge-${(ag.status || '').toLowerCase()}">
                    ${ag.status}
                  </span>
                </td>
              </tr>
            `;
          });
          containerAg.innerHTML = `
            <div class="table-responsive">
              <table class="admin-table">
                <thead>
                  <tr>
                    <th>Horário</th>
                    <th>Cliente</th>
                    <th>Serviço</th>
                    <th>Valor</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>${rowsHtml}</tbody>
              </table>
            </div>
          `;
        } else {
          containerAg.innerHTML = `
            <div style="text-align: center; color: var(--text-muted); padding: 36px 0;">
              Nenhum agendamento ativo registrado para o dia <strong>${d.data_selecionada}</strong>.
            </div>
          `;
        }
      }

      // Atualizar lista de serviços do mês
      const listaServ = document.getElementById('listaServicosStats');
      if (listaServ) {
        if (d.servicos_stats && d.servicos_stats.length > 0) {
          let liHtml = '';
          d.servicos_stats.forEach(s => {
            liHtml += `
              <li class="service-stat-item">
                <div class="service-stat-info">
                  <span class="service-stat-badge">${s.qtd}x</span>
                  <span style="font-weight: 500;">${s.servico_nome}</span>
                </div>
                <strong style="color: var(--gold-light);">${formatarMoedaBRL(s.total_valor)}</strong>
              </li>
            `;
          });
          listaServ.innerHTML = liHtml;
        } else {
          listaServ.innerHTML = `
            <li style="text-align: center; color: var(--text-dark); padding: 20px 0;">
              Nenhum serviço registrado este mês.
            </li>
          `;
        }
      }
    }

    async function buscarAtualizacoesFaturamento(dataParam, silencioso = false) {
      try {
        const inputData = document.getElementById('inputDataFaturamento');
        const dataQuery = dataParam || (inputData ? inputData.value : '');
        const resp = await fetch(`/api/admin/faturamento-dados?data=${encodeURIComponent(dataQuery)}`);
        if (!resp.ok) return;
        const novosDados = await resp.json();
        window.dadosFaturamento = novosDados;
        atualizarDOMDetalhes(novosDados);
        renderizarGraficoPrincipal();
        renderizarGraficoServicos();
      } catch (err) {
        if (!silencioso) console.error('Erro ao atualizar faturamento:', err);
      }
    }

    // Inicialização
    inicializarGraficoPrincipal();
    inicializarGraficoServicos();

    if (window.dadosFaturamento) {
      atualizarDOMDetalhes(window.dadosFaturamento);
      renderizarGraficoPrincipal();
      renderizarGraficoServicos();
    } else {
      buscarAtualizacoesFaturamento(null, true);
    }

    // Polling em tempo real a cada 3 segundos na tela de faturamento
    setInterval(() => {
      buscarAtualizacoesFaturamento(null, true);
    }, 3000);

    // Funções Globais expostas para os botões de controle
    window.alternarModoGrafico = function(modo) {
      modoAtual = modo;
      const bDia = document.getElementById('btnModoDia');
      const bHorario = document.getElementById('btnModoHorario');
      if (bDia) bDia.classList.toggle('active', modo === 'dia');
      if (bHorario) bHorario.classList.toggle('active', modo === 'horario');
      
      const cDia = document.getElementById('controlesModoDia');
      const cHorario = document.getElementById('controlesModoHorario');
      if (cDia) cDia.style.display = modo === 'dia' ? 'flex' : 'none';
      if (cHorario) cHorario.style.display = modo === 'horario' ? 'flex' : 'none';

      renderizarGraficoPrincipal();
    };

    window.mudarPeriodoDias = function(periodo) {
      periodoDias = periodo;
      const b7 = document.getElementById('btnFiltro7Dias');
      const bProx = document.getElementById('btnFiltroProx7Dias');
      if (b7) b7.classList.toggle('active', periodo === 'ultimos7');
      if (bProx) bProx.classList.toggle('active', periodo === 'proximos7');
      renderizarGraficoPrincipal();
    };

    window.mudarFiltroHorario = function(tipo) {
      filtroHorario = tipo;
      const bDia = document.getElementById('btnHorarioDia');
      const bGeral = document.getElementById('btnHorarioGeral');
      if (bDia) bDia.classList.toggle('active', tipo === 'dia');
      if (bGeral) bGeral.classList.toggle('active', tipo === 'geral');
      renderizarGraficoPrincipal();
    };

    window.filtrarPorData = function(dataStr) {
      buscarAtualizacoesFaturamento(dataStr);
    };
  }

  // 4. Atualização Automática em Tempo Real no Dashboard
  const dashboardTable = document.getElementById('dashboardTableAgendamentos');
  if (dashboardTable || document.getElementById('dashStatHoje')) {
    let lastTotalConfirmado = null;
    let lastCount = null;

    function tocarSomNotificacao() {
      try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = audioCtx.createOscillator();
        const gain = audioCtx.createGain();
        osc.connect(gain);
        gain.connect(audioCtx.destination);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(587.33, audioCtx.currentTime);
        osc.frequency.setValueAtTime(880, audioCtx.currentTime + 0.1);
        gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.35);
        osc.start();
        osc.stop(audioCtx.currentTime + 0.35);
      } catch (e) {}
    }

    async function atualizarDashboardAoVivo() {
      try {
        const resp = await fetch('/api/admin/dashboard-stats');
        if (!resp.ok) return;
        const data = await resp.json();

        // Atualizar métricas numéricas em tempo real
        if (data.stats) {
          const elHoje = document.getElementById('dashStatHoje');
          if (elHoje && elHoje.innerText != data.stats.agendamentos_hoje) {
            elHoje.innerText = data.stats.agendamentos_hoje;
          }

          const elCli = document.getElementById('dashStatClientes');
          if (elCli && elCli.innerText != data.stats.total_clientes) {
            elCli.innerText = data.stats.total_clientes;
          }

          const elFatMes = document.getElementById('dashStatFatMes');
          if (elFatMes) {
            elFatMes.innerText = formatarMoedaBRL(data.stats.faturamento_mes);
          }

          const elFatTotal = document.getElementById('dashStatFatTotal');
          if (elFatTotal) {
            elFatTotal.innerText = formatarMoedaBRL(data.stats.faturamento_total_confirmado);
          }
        }

        // Se houve novo agendamento ou mudança na receita total
        if (lastTotalConfirmado !== null && data.stats && data.stats.faturamento_total_confirmado > lastTotalConfirmado) {
          tocarSomNotificacao();
          const alertBox = document.getElementById('liveNewBookingAlert');
          if (alertBox && data.agendamentos && data.agendamentos.length > 0) {
            const maisRecente = data.agendamentos[0];
            alertBox.innerHTML = `🔔 <strong>Novo agendamento marcado!</strong> Cliente: <u>${maisRecente.cliente || 'Novo'}</u> às ${maisRecente.horario || ''}h (${maisRecente.data || ''}) &bull; Tel: ${maisRecente.telefone || ''}`;
            alertBox.style.display = 'block';
          }
          setTimeout(() => {
            window.location.reload();
          }, 1800);
        }

        if (data.stats) {
          lastTotalConfirmado = data.stats.faturamento_total_confirmado;
        }
        lastCount = data.total;
      } catch (err) {}
    }

    atualizarDashboardAoVivo();
    setInterval(atualizarDashboardAoVivo, 3000);
  }
});
