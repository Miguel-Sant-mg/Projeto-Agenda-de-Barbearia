document.addEventListener('DOMContentLoaded', () => {
  // Estado do Agendamento
  const bookingState = {
    servicoId: null,
    servicoNome: '',
    servicoPreco: 0,
    servicoDescricao: '',
    data: '',
    dataFormatada: '',
    horario: '',
    clienteNome: '',
    clienteTelefone: '',
    observacoes: ''
  };

  let currentStep = 1;
  const totalSteps = 4;

  // Elementos DOM
  const stepSections = document.querySelectorAll('.step-section');
  const stepItems = document.querySelectorAll('.step-item');
  const stepperProgressBar = document.querySelector('.stepper-progress');

  const dateInput = document.getElementById('bookingDate');
  const slotsGrid = document.getElementById('slotsGrid');
  const slotsLoading = document.getElementById('slotsLoading');
  const slotsEmpty = document.getElementById('slotsEmpty');

  const inputNome = document.getElementById('clienteNome');
  const inputTelefone = document.getElementById('clienteTelefone');
  const inputObservacoes = document.getElementById('clienteObservacoes');

  // Resumo DOM
  const summaryServico = document.getElementById('summaryServico');
  const summaryData = document.getElementById('summaryData');
  const summaryHorario = document.getElementById('summaryHorario');
  const summaryTotal = document.getElementById('summaryTotal');

  // Stepper Mobile DOM
  const stepperMobileNum = document.getElementById('stepperMobileNum');
  const stepperMobileLabel = document.getElementById('stepperMobileLabel');
  const stepLabels = {
    1: 'Escolha o Serviço',
    2: 'Escolha a Data',
    3: 'Escolha o Horário',
    4: 'Seus Dados e Confirmação'
  };

  // Botões de Navegação
  const btnNext1 = document.getElementById('btnNext1');
  const btnPrev2 = document.getElementById('btnPrev2');
  const btnNext2 = document.getElementById('btnNext2');
  const btnPrev3 = document.getElementById('btnPrev3');
  const btnNext3 = document.getElementById('btnNext3');
  const btnPrev4 = document.getElementById('btnPrev4');

  // 1. Seleção de Serviço
  const serviceCards = document.querySelectorAll('.service-card');
  serviceCards.forEach(card => {
    card.addEventListener('click', () => {
      serviceCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');

      bookingState.servicoId = card.dataset.id;
      bookingState.servicoNome = card.dataset.nome;
      bookingState.servicoPreco = parseFloat(card.dataset.preco);
      bookingState.servicoDescricao = card.dataset.descricao;

      btnNext1.disabled = false;
      // Pequeno delay para feedback visual suave antes de avançar se desejar
      setTimeout(() => goToStep(2), 200);
    });
  });

  // 2. Seleção de Data Fixa (Sextas e Sábados)
  const fixedDaysContainer = document.getElementById('fixedDaysShortcuts');
  const dateAlertWrongDay = document.getElementById('dateAlertWrongDay');

  function isFridayOrSaturday(dateStr) {
    if (!dateStr) return false;
    const parts = dateStr.split('-');
    if (parts.length !== 3) return false;
    const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
    return d.getDay() === 5 || d.getDay() === 6;
  }

  function getNextFridaysAndSaturdays(count = 4) {
    const list = [];
    const today = new Date();
    for (let i = 0; i < 35; i++) {
      const d = new Date(today);
      d.setDate(today.getDate() + i);
      const dayOfWeek = d.getDay();
      if (dayOfWeek === 5 || dayOfWeek === 6) {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const dateStr = `${yyyy}-${mm}-${dd}`;
        const dayName = dayOfWeek === 5 ? 'Sexta' : 'Sábado';
        const label = `${dayName} (${dd}/${mm})`;
        list.push({ dateStr, label, dayOfWeek });
        if (list.length >= count) break;
      }
    }
    return list;
  }

  // Renderizar opções de datas fixas
  if (fixedDaysContainer) {
    const fixedOptions = getNextFridaysAndSaturdays(4);
    fixedOptions.forEach((opt, idx) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `btn-date-shortcut ${idx === 0 ? 'active' : ''}`;
      btn.dataset.date = opt.dateStr;
      btn.innerHTML = `📅 <strong>${opt.label}</strong>`;
      btn.addEventListener('click', () => {
        document.querySelectorAll('.btn-date-shortcut').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        if (dateInput) dateInput.value = opt.dateStr;
        if (dateAlertWrongDay) dateAlertWrongDay.style.display = 'none';
        selectDate(opt.dateStr);
      });
      fixedDaysContainer.appendChild(btn);
    });

    if (fixedOptions.length > 0) {
      if (dateInput) dateInput.value = fixedOptions[0].dateStr;
      selectDate(fixedOptions[0].dateStr);
    }
  }

  if (dateInput) {
    dateInput.addEventListener('change', (e) => {
      const val = e.target.value;
      if (!val) return;

      if (!isFridayOrSaturday(val)) {
        if (dateAlertWrongDay) dateAlertWrongDay.style.display = 'block';
        btnNext2.disabled = true;
        document.querySelectorAll('.btn-date-shortcut').forEach(b => b.classList.remove('active'));
      } else {
        if (dateAlertWrongDay) dateAlertWrongDay.style.display = 'none';
        document.querySelectorAll('.btn-date-shortcut').forEach(b => {
          if (b.dataset.date === val) {
            b.classList.add('active');
          } else {
            b.classList.remove('active');
          }
        });
        selectDate(val);
      }
    });
  }

  function selectDate(dateStr) {
    bookingState.data = dateStr;
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      bookingState.dataFormatada = `${parts[2]}/${parts[1]}/${parts[0]}`;
    } else {
      bookingState.dataFormatada = dateStr;
    }
    btnNext2.disabled = false;
    carregarHorarios(dateStr);
  }

  // 3. Carregar Horários Disponíveis via API
  async function carregarHorarios(dateStr) {
    slotsGrid.innerHTML = '';
    slotsLoading.style.display = 'block';
    slotsEmpty.style.display = 'none';
    btnNext3.disabled = true;
    bookingState.horario = '';

    try {
      const resp = await fetch(`/api/horarios-disponiveis?data=${dateStr}`);
      const data = await resp.json();

      slotsLoading.style.display = 'none';

      if (!data.aberto) {
        slotsEmpty.innerHTML = `<p style="color:#f87171;">⚠️ ${data.mensagem || 'A barbearia está fechada nesta data.'}</p>`;
        slotsEmpty.style.display = 'block';
        return;
      }

      if (!data.horarios || data.horarios.length === 0) {
        slotsEmpty.innerHTML = `<p style="color:#94a3b8;">Nenhum horário disponível para esta data.</p>`;
        slotsEmpty.style.display = 'block';
        return;
      }

      data.horarios.forEach(item => {
        const slotEl = document.createElement('button');
        slotEl.type = 'button';
        slotEl.className = `slot-btn ${item.tipo}`;
        
        let statusBadge = '';
        if (item.tipo === 'disponivel') {
          statusBadge = '<span class="slot-status-text">🟢 LIVRE</span>';
        } else if (item.tipo === 'ocupado') {
          statusBadge = '<span class="slot-status-text">🔴 OCUPADO</span>';
          slotEl.disabled = true;
        } else if (item.tipo === 'almoco') {
          statusBadge = '<span class="slot-status-text">🍽️ ALMOÇO</span>';
          slotEl.title = 'Horário de Almoço (13:00 às 14:00)';
          slotEl.disabled = true;
        } else if (item.tipo === 'bloqueado') {
          statusBadge = '<span class="slot-status-text">🔒 BLOQUEADO</span>';
          slotEl.disabled = true;
        } else {
          statusBadge = '<span class="slot-status-text">PASSO</span>';
          slotEl.disabled = true;
        }

        slotEl.innerHTML = `
          <span>${item.horario}</span>
          ${statusBadge}
        `;

        if (item.disponivel) {
          slotEl.addEventListener('click', () => {
            document.querySelectorAll('.slot-btn').forEach(b => b.classList.remove('selected'));
            slotEl.classList.add('selected');
            bookingState.horario = item.horario;
            btnNext3.disabled = false;
            // Avançar suavemente para o formulário do cliente
            setTimeout(() => goToStep(4), 220);
          });
        }

        slotsGrid.appendChild(slotEl);
      });
    } catch (err) {
      slotsLoading.style.display = 'none';
      slotsEmpty.innerHTML = `<p style="color:#f87171;">Erro ao carregar horários. Tente novamente.</p>`;
      slotsEmpty.style.display = 'block';
    }
  }

  // 4. Máscara de Telefone/WhatsApp: (XX) XXXXX-XXXX
  if (inputTelefone) {
    inputTelefone.addEventListener('input', (e) => {
      let v = e.target.value.replace(/\D/g, '');
      if (v.length > 11) v = v.slice(0, 11);

      if (v.length > 10) {
        // Formato com 9 dígitos: (11) 98888-8888
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
  }

  // Atualizar Resumo no Passo 4
  function atualizarResumo() {
    if (summaryServico) summaryServico.textContent = bookingState.servicoNome || 'Não selecionado';
    if (summaryData) summaryData.textContent = bookingState.dataFormatada || 'Não selecionada';
    if (summaryHorario) summaryHorario.textContent = bookingState.horario ? `${bookingState.horario}h` : 'Não selecionado';
    if (summaryTotal) {
      summaryTotal.textContent = `R$ ${bookingState.servicoPreco.toFixed(2).replace('.', ',')}`;
    }

    // Preencher campos ocultos do form
    const fServico = document.getElementById('formServicoId');
    const fData = document.getElementById('formData');
    const fHorario = document.getElementById('formHorario');
    if (fServico) fServico.value = bookingState.servicoId;
    if (fData) fData.value = bookingState.data;
    if (fHorario) fHorario.value = bookingState.horario;
  }

  // Navegação entre passos
  function goToStep(step) {
    if (step < 1 || step > totalSteps) return;

    // Se estiver avançando para o passo 4, garantir que dados de resumo estejam atualizados
    if (step === 4) {
      atualizarResumo();
    }

    currentStep = step;

    // Atualiza indicador mobile
    if (stepperMobileNum) stepperMobileNum.textContent = step;
    if (stepperMobileLabel) stepperMobileLabel.textContent = stepLabels[step] || '';

    stepSections.forEach(section => {
      section.classList.remove('active');
      if (parseInt(section.dataset.step) === step) {
        section.classList.add('active');
      }
    });

    stepItems.forEach(item => {
      const s = parseInt(item.dataset.step);
      item.classList.remove('active', 'completed');
      if (s === step) {
        item.classList.add('active');
      } else if (s < step) {
        item.classList.add('completed');
      }
    });

    // Atualiza barra de progresso
    const progressPercent = ((step - 1) / (totalSteps - 1)) * 100;
    if (stepperProgressBar) {
      stepperProgressBar.style.width = `${progressPercent}%`;
    }

    // Scroll suave para o topo do formulário no celular
    const bookingCard = document.querySelector('.booking-card');
    if (bookingCard) {
      const isMobile = window.innerWidth <= 768;
      const targetTop = bookingCard.getBoundingClientRect().top + window.pageYOffset;
      const offset = isMobile ? 68 : 86;
      window.scrollTo({ top: Math.max(0, targetTop - offset), behavior: 'smooth' });
    }
  }

  // Permitir toque nos círculos das etapas já concluídas
  stepItems.forEach(item => {
    item.addEventListener('click', () => {
      const targetStep = parseInt(item.dataset.step);
      if (targetStep < currentStep) {
        goToStep(targetStep);
      }
    });
  });

  // Listeners dos botões de navegação
  if (btnNext1) btnNext1.addEventListener('click', () => goToStep(2));
  if (btnPrev2) btnPrev2.addEventListener('click', () => goToStep(1));
  if (btnNext2) btnNext2.addEventListener('click', () => goToStep(3));
  if (btnPrev3) btnPrev3.addEventListener('click', () => goToStep(2));
  if (btnNext3) btnNext3.addEventListener('click', () => goToStep(4));
  if (btnPrev4) btnPrev4.addEventListener('click', () => goToStep(3));
});
